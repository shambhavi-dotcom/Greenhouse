"""
env/rewards.py

Reward function computation.
Defines how the agent is scored based on state transitions.

Reward structure:
    reward = α * crop_health + β * stability - γ * resource_cost + penalties

This encourages:
- Maintaining high crop health
- Minimizing variance (stability)
- Using resources efficiently
- Avoiding catastrophic failures
"""

from typing import Dict, Any
from env.state import GreenhouseState
from config import constants


def compute_reward(
    prev_state: GreenhouseState,
    new_state: GreenhouseState,
    action_info: Dict[str, Any],
) -> Dict[str, float]:
    """
    Compute reward for state transition.
    
    Args:
        prev_state: State before action
        new_state: State after action
        action_info: Information about actions taken
                    (energy_used, water_used, etc.)
    
    Returns:
        Dictionary with:
            - "total": Total reward
            - "component_crop": Reward from crop health
            - "component_stability": Reward from condition stability
            - "component_resource": Penalty from resource usage
            - "penalty_mold": Penalty if mold detected
            - "penalty_freeze": Penalty if freeze damage
            - "penalty_death": Penalty if crop dies
    """
    
    reward_dict = {
        "component_crop": 0.0,
        "component_stability": 0.0,
        "component_resource": 0.0,
        "penalty_mold": 0.0,
        "penalty_freeze": 0.0,
        "penalty_death": 0.0,
        "penalty_heat": 0.0,
        "total": 0.0,
    }
    
    # ========================================================================
    # 1. CROP HEALTH COMPONENT
    # ========================================================================
    # Reward is proportional to current crop health
    # Bonus if health improved, penalty if health decreased
    
    crop_health_reward = new_state.crop_health * constants.REWARD_CROP_HEALTH_WEIGHT
    health_change = new_state.crop_health - prev_state.crop_health
    if health_change > 0:
        crop_health_reward += health_change * 2.0  # Bonus for improvement
    
    reward_dict["component_crop"] = crop_health_reward
    
    # ========================================================================
    # 2. STABILITY COMPONENT
    # ========================================================================
    # Reward for keeping environmental conditions stable (low variance)
    # Measured as penalty for large swings in temperature/humidity
    
    temp_delta = abs(new_state.temperature - prev_state.temperature)
    humidity_delta = abs(new_state.humidity - prev_state.humidity)
    
    stability_penalty = (
        temp_delta * 0.1 + humidity_delta * 0.05
    ) * constants.REWARD_STABILITY_WEIGHT
    
    reward_dict["component_stability"] = -stability_penalty
    
    # ========================================================================
    # 3. RESOURCE COST COMPONENT
    # ========================================================================
    # Penalty for resource consumption
    
    energy_used = action_info.get("energy_used", 0.0)
    water_used = action_info.get("water_used", 0.0)
    
    resource_penalty = (
        energy_used * 0.05 + water_used * 0.02
    ) * constants.REWARD_RESOURCE_COST_WEIGHT
    
    reward_dict["component_resource"] = -resource_penalty
    
    # ========================================================================
    # 4. RISK PENALTIES
    # ========================================================================
    
    # Mold penalty
    if new_state.mold_presence > 0.5:
        reward_dict["penalty_mold"] = -constants.PENALTY_MOLD * new_state.mold_presence
    
    # Freeze damage penalty
    if new_state.temperature < constants.FREEZE_DAMAGE_THRESHOLD:
        reward_dict["penalty_freeze"] = -constants.PENALTY_FREEZE_DAMAGE
    
    # Heat stress penalty
    if new_state.temperature > constants.HEAT_STRESS_THRESHOLD:
        heat_excess = new_state.temperature - constants.HEAT_STRESS_THRESHOLD
        reward_dict["penalty_heat"] = -heat_excess * 0.5
    
    # Crop death penalty
    if new_state.crop_health <= 0.0:
        reward_dict["penalty_death"] = -constants.PENALTY_CROP_DEATH
    
    # ========================================================================
    # 5. TOTAL REWARD
    # ========================================================================
    
    reward_dict["total"] = sum([
        reward_dict["component_crop"],
        reward_dict["component_stability"],
        reward_dict["component_resource"],
        reward_dict["penalty_mold"],
        reward_dict["penalty_freeze"],
        reward_dict["penalty_heat"],
        reward_dict["penalty_death"],
    ])
    
    return reward_dict


def compute_episode_score(total_rewards: list[float]) -> float:
    """
    Compute total episode score from step rewards.
    
    Args:
        total_rewards: List of rewards from each time step
        
    Returns:
        Total episode score (sum of discounted rewards)
    """
    # Simple: sum of all rewards (can add discounting if needed)
    return sum(total_rewards)


def compute_success_rate(
    episode_results: list[Dict[str, Any]]
) -> float:
    """
    Compute success rate of episodes.
    
    Success = crop survived episode AND resource efficiency > threshold
    
    Args:
        episode_results: List of dictionaries with episode outcomes
        
    Returns:
        Success rate 0.0-1.0
    """
    pass  # Placeholder
