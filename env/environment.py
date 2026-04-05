"""
env/environment.py

Main gymnasium-compatible environment class for greenhouse simulation.
Implements the OpenEnv interface for reinforcement learning.
"""

import gymnasium as gym
from gymnasium import spaces
from typing import Tuple, Dict, Any, Optional
import numpy as np

from env.state import GreenhouseState
from env.actions import ActionSpace, Action, ActionType
from env.dynamics import apply_dynamics
from env.rewards import compute_reward
from config import constants, crop_profiles


class GreenhouseEnv(gym.Env):
    """
    Greenhouse environment compatible with gym/gymnasium.
    
    Sequential decision-making problem where an agent controls:
    - Temperature (heating/cooling)
    - Humidity (humidification/dehumidification)
    - CO2 (ventilation/enrichment)
    - Lighting (supplemental lights)
    - Irrigation (water)
    
    Objective: Maximize crop health + stability while keeping resource usage low.
    
    Observation space: Continuous [temp, humidity, CO2, light, water, energy, health, mold, time, day]
    Action space: Continuous [0, 1]^8 (one continuous action per control type)
    """
    
    metadata = {"render_modes": ["human"], "render_fps": 2}
    
    def __init__(
        self,
        crop: str = "tomato",
        max_episode_steps: int = 500,
        include_weather: bool = False,
        include_resource_limits: bool = True,
        difficulty: str = "easy",
    ):
        """
        Initialize the greenhouse environment.
        
        Args:
            crop: Crop type (tomato, lettuce, herbs)
            max_episode_steps: Maximum steps per episode
            include_weather: Whether external weather disturbances occur
            include_resource_limits: Whether resources are limited
            difficulty: Task difficulty (easy, medium, hard)
        """
        super().__init__()
        
        self.crop_name = crop
        self.crop_profile = crop_profiles.get_crop_profile(crop)
        self.max_episode_steps = max_episode_steps
        self.include_weather = include_weather
        self.include_resource_limits = include_resource_limits
        self.difficulty = difficulty
        
        # Initialize state
        self.state = GreenhouseState()
        self.step_count = 0
        self.episode_rewards = []
        self.episode_states = []
        
        # Action space: 8 continuous actions (one per control type)
        self.action_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(8,),
            dtype=np.float32
        )
        
        # Observation space: 10 continuous variables
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(10,),
            dtype=np.float32
        )
        
        self.action_space_obj = ActionSpace(num_actions=8)
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset environment to initial state.
        
        Args:
            seed: Random seed
            options: Additional options
            
        Returns:
            Tuple of (observation, info)
        """
        super().reset(seed=seed)
        
        self.state = GreenhouseState()
        self.step_count = 0
        self.episode_rewards = []
        self.episode_states = []
        
        obs = self.state.to_array()
        info = {"difficulty": self.difficulty, "crop": self.crop_name}
        
        return obs, info
    
    def step(
        self,
        action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one time step of the environment.
        
        Args:
            action: Action array [0, 1]^8
            
        Returns:
            Tuple of (observation, reward, terminated, truncated, info)
        """
        self.step_count += 1
        
        # Convert action array to action objects
        actions = self.action_space_obj.from_array(action)
        
        # Apply dynamics
        prev_state = self.state.copy()
        self.state, action_info = apply_dynamics(
            self.state,
            actions,
            self.crop_profile,
            dt=1.0
        )
        
        # Compute reward
        reward_dict = compute_reward(prev_state, self.state, action_info)
        reward = reward_dict["total"]
        
        # Check terminal conditions
        terminated = self._is_terminal()
        truncated = self.step_count >= self.max_episode_steps
        
        # Prepare info and observation
        obs = self.state.to_array()
        info = {
            "step": self.step_count,
            "reward_breakdown": reward_dict,
            "action_info": action_info,
            "crop_health": self.state.crop_health,
            "terminated_reason": self._get_termination_reason(),
        }
        
        # Store for episode statistics
        self.episode_rewards.append(reward)
        self.episode_states.append(self.state.to_dict())
        
        return obs, reward, terminated, truncated, info
    
    def _is_terminal(self) -> bool:
        """Check if episode should terminate."""
        # Crop died
        if self.state.crop_health <= 0.0:
            return True
        # System failure
        if self.state.water_level <= 0.0 and self.state.energy_level <= 0.0:
            return True
        return False
    
    def _get_termination_reason(self) -> str:
        """Get reason for episode termination."""
        if self.state.crop_health <= 0.0:
            return "CROP_DEATH"
        if self.state.water_level <= 0.0 and self.state.energy_level <= 0.0:
            return "SYSTEM_FAILURE"
        return "NONE"
    
    def get_episode_summary(self) -> Dict[str, Any]:
        """
        Get statistics for completed episode.
        
        Returns:
            Dictionary with episode metrics
        """
        if not self.episode_rewards:
            return {}
        
        return {
            "total_reward": sum(self.episode_rewards),
            "avg_reward": np.mean(self.episode_rewards),
            "final_crop_health": self.state.crop_health,
            "episode_length": len(self.episode_rewards),
            "difficulty": self.difficulty,
        }
    
    def render(self):
        """Render environment state (human readable)."""
        pass  # Placeholder


class GreenhouseEasyEnv(GreenhouseEnv):
    """Easy version: static environment, no disturbances."""
    def __init__(self):
        super().__init__(
            crop="tomato",
            max_episode_steps=100,
            include_weather=False,
            include_resource_limits=False,
            difficulty="easy"
        )


class GreenhouseMediumEnv(GreenhouseEnv):
    """Medium version: weather changes, reactive control needed."""
    def __init__(self):
        super().__init__(
            crop="tomato",
            max_episode_steps=200,
            include_weather=True,
            include_resource_limits=True,
            difficulty="medium"
        )


class GreenhouseHardEnv(GreenhouseEnv):
    """Hard version: limited resources, planning required."""
    def __init__(self):
        super().__init__(
            crop="tomato",
            max_episode_steps=500,
            include_weather=True,
            include_resource_limits=True,
            difficulty="hard"
        )
