"""
env/rewards.py — Greenhouse Reward Function (v2)

Normalised reward signal designed for stable agent learning.

Structure:
    R = α × health_component
      + β × stability_component
      + γ × efficiency_component
      − mold_penalty
      − freeze_penalty
      − heat_penalty
      − death_penalty

Where:
    health_component   = (2 × health − 1) ∈ [−1, +1]     maps dead=−1, thriving=+1
    stability_component= Gaussian proximity to crop optima ∈ [0, 1]
    efficiency_component= (1 − energy_use / max_energy)   ∈ [0, 1]

Typical per-step reward range:
    Optimal conditions, efficient use  →  ~+1.8
    Mediocre conditions, wasteful      →  ~+0.4
    Stressed (health=0.5, bad env)     →  ~−0.1
    Dead crop                          →  ~−5.0 (one-off death penalty)
"""

from typing import Dict, Any, Optional
import numpy as np

from env.state import GreenhouseState
from config import constants


def compute_reward(
    prev_state: GreenhouseState,
    new_state: GreenhouseState,
    action_info: Dict[str, Any],
    crop_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    Compute reward for a single state transition.

    Args:
        prev_state:   State before the step.
        new_state:    State after the step.
        action_info:  Dict from apply_dynamics (energy_used, stress_total, …).
        crop_profile: Crop-specific parameters for per-crop optimal targets.
                      Falls back to global constants if None.

    Returns:
        Dict with keys:
            total, component_crop, component_stability,
            component_resource, penalty_mold, penalty_freeze,
            penalty_heat, penalty_death
    """

    reward_dict: Dict[str, float] = {
        "component_crop":      0.0,
        "component_stability": 0.0,
        "component_resource":  0.0,
        "penalty_mold":        0.0,
        "penalty_freeze":      0.0,
        "penalty_heat":        0.0,
        "penalty_death":       0.0,
        "total":               0.0,
    }

    # Pull crop optima (with sensible fallbacks)
    T_opt   = crop_profile.get("temp_optimal",     22.0) if crop_profile else 22.0
    RH_opt  = crop_profile.get("humidity_optimal", 65.0) if crop_profile else 65.0
    co2_opt = crop_profile.get("co2_optimal",      900.0) if crop_profile else 900.0

    σ_T  = crop_profile.get("temp_stress_sigma",     4.0)  if crop_profile else 4.0
    σ_RH = crop_profile.get("humidity_stress_sigma", 15.0) if crop_profile else 15.0
    σ_C  = crop_profile.get("co2_stress_sigma",      300.0)if crop_profile else 300.0

    # ========================================================================
    # 1. CROP HEALTH COMPONENT  — maps [0, 1] → [−1, +1]
    #    Core signal: thriving = positive, deteriorating = negative.
    #    Bonus for positive health change (recovery reward).
    # ========================================================================
    health_r  = (2.0 * new_state.crop_health - 1.0) * constants.REWARD_CROP_HEALTH_WEIGHT
    delta_h   = new_state.crop_health - prev_state.crop_health
    improve_r = delta_h * 2.0   # extra incentive for recovery; 0 during plateau

    reward_dict["component_crop"] = float(health_r + improve_r)

    # ========================================================================
    # 2. ENVIRONMENTAL STABILITY — Gaussian proximity to optima
    #    Reward = (1 − stress): 1.0 at perfect, 0.0 at extreme.
    #    Same σ as used in dynamics health cost → consistent signals.
    # ========================================================================
    def _gauss_proximity(val: float, opt: float, sigma: float) -> float:
        return float(np.exp(-0.5 * ((val - opt) / sigma) ** 2))

    prox_T  = _gauss_proximity(new_state.temperature, T_opt,   σ_T)
    prox_RH = _gauss_proximity(new_state.humidity,    RH_opt,  σ_RH)
    prox_C  = _gauss_proximity(new_state.co2,         co2_opt, σ_C)

    # Weighted proximity bonus (temp most important, then humidity, CO2)
    stability_r = (0.45 * prox_T + 0.35 * prox_RH + 0.20 * prox_C) * constants.REWARD_STABILITY_WEIGHT

    reward_dict["component_stability"] = float(stability_r)

    # ========================================================================
    # 3. RESOURCE EFFICIENCY COMPONENT
    #    Rewards moderate energy use; penalises waste.
    #    Normalised so zero use = full bonus, max use = 0.
    # ========================================================================
    energy_used = float(action_info.get("energy_used", 0.0))
    max_e  = max(constants.MAX_ENERGY_PER_STEP, 0.001)
    efficiency_r = (1.0 - min(energy_used / max_e, 1.0)) * constants.REWARD_RESOURCE_COST_WEIGHT

    reward_dict["component_resource"] = float(efficiency_r)

    # ========================================================================
    # 4. RISK PENALTIES
    # ========================================================================

    # Mold (proportional above 0.5)
    if new_state.mold_presence > 0.5:
        reward_dict["penalty_mold"] = -constants.PENALTY_MOLD * new_state.mold_presence

    # Cold stress (global freeze threshold; crop-specific damage handled in dynamics)
    if new_state.temperature < constants.FREEZE_DAMAGE_THRESHOLD:
        reward_dict["penalty_freeze"] = -constants.PENALTY_FREEZE_DAMAGE

    # Heat stress (proportional above global threshold)
    if new_state.temperature > constants.HEAT_STRESS_THRESHOLD:
        excess = new_state.temperature - constants.HEAT_STRESS_THRESHOLD
        reward_dict["penalty_heat"] = -excess * 0.1

    # Crop death (one-off large penalty)
    if new_state.crop_health <= 0.0:
        reward_dict["penalty_death"] = -constants.PENALTY_CROP_DEATH

    # ========================================================================
    # 5. TOTAL
    # ========================================================================
    reward_dict["total"] = float(sum([
        reward_dict["component_crop"],
        reward_dict["component_stability"],
        reward_dict["component_resource"],
        reward_dict["penalty_mold"],
        reward_dict["penalty_freeze"],
        reward_dict["penalty_heat"],
        reward_dict["penalty_death"],
    ]))

    return reward_dict


def compute_episode_score(total_rewards: list) -> float:
    """
    Normalise a list of step rewards to a [0, 1] episode score.

    Max per-step reward ≈ 1.8 (optimal conditions, zero waste).
    Clipping to [0, 1] handles the upside-unbounded case.
    """
    if not total_rewards:
        return 0.0
    raw = sum(total_rewards) / len(total_rewards)   # per-step average
    # Map: 0 avg reward → score ≈ 0.5, +1.8 → 1.0, negative → <0.5
    # Simple normalise: assume max mean = 1.8
    score = (raw + 1.0) / (1.8 + 1.0)   # shift to [0, 1] for typical range
    return float(np.clip(score, 0.0, 1.0))


def compute_success_rate(episode_results: list) -> float:
    """
    Compute success rate from list of episode result dicts.
    Success: final crop_health > 0.5 and episode completed without death.
    """
    if not episode_results:
        return 0.0
    successes = sum(
        1 for r in episode_results
        if r.get("final_crop_health", 0.0) > 0.5
    )
    return float(successes / len(episode_results))
