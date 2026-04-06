"""
env/environment.py

Main gymnasium-compatible environment class for greenhouse simulation.
Implements the full OpenEnv interface: step() / reset() / state() with typed models.

OpenEnv compliance:
  - step(action)  -> (obs_array, reward, terminated, truncated, info)
  - reset()       -> (obs_array, info)
  - state()       -> GreenhouseObservation  [typed Pydantic model]  ← REQUIRED by PS
  - typed_step()  -> GreenhouseStepResult   [full typed step result]
  - typed_reset() -> GreenhouseObservation  [typed reset]

Note: Internal state stored as self._state (GreenhouseState dataclass).
      Public .state property and .state() method both exist for compatibility.
"""

import gymnasium as gym
from gymnasium import spaces
from typing import Tuple, Dict, Any, Optional
import numpy as np

from env.state import GreenhouseState, INITIAL_CONDITION_PRESETS, build_initial_state
from env.actions import ActionSpace, Action, ActionType
from env.dynamics import apply_dynamics
from env.rewards import compute_reward
from env.models import (
    GreenhouseObservation,
    GreenhouseAction,
    GreenhouseReward,
    GreenhouseStepResult,
)
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

        # Internal state — stored as self._state to avoid collision with state() method
        self._state = GreenhouseState()
        self.step_count = 0
        self.episode_rewards = []
        self.episode_states = []
        self.initial_condition = "100% — Thriving (Optimal)"  # default preset

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

    # --------------------------------------------------------------------------
    # Backward-compatibility property: env.state still works (returns GreenhouseState)
    # app.py uses env.state.temperature etc., this keeps those working.
    # --------------------------------------------------------------------------
    @property
    def state(self) -> GreenhouseState:
        """Backward-compatible access to internal GreenhouseState dataclass."""
        return self._state

    @state.setter
    def state(self, value: GreenhouseState):
        """Allow assignment: self.state = GreenhouseState()"""
        self._state = value

    # ==========================================================================
    # GYMNASIUM API
    # ==========================================================================

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
        initial_condition: Optional[str] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset environment to initial state.

        Args:
            seed: Random seed
            options: Additional options
            initial_condition: Name of starting preset from INITIAL_CONDITION_PRESETS.
                One of:
                  '100% — Thriving (Optimal)'
                  '75% — Healthy (Minor Stress)'
                  '50% — Stressed (Recovery Needed)'
                  '25% — Critical (Emergency)'
                Defaults to current env.initial_condition (set in __init__ or last reset).

        Returns:
            Tuple of (observation, info)
        """
        super().reset(seed=seed)

        # Apply preset if specified
        if initial_condition is not None:
            self.initial_condition = initial_condition

        self._state = build_initial_state(self.initial_condition)
        self.step_count = 0
        self.episode_rewards = []
        self.episode_states = []

        obs = self._state.to_array()
        preset_meta = INITIAL_CONDITION_PRESETS[self.initial_condition]
        info = {
            "difficulty": self.difficulty,
            "crop": self.crop_name,
            "initial_condition": self.initial_condition,
            "initial_health": preset_meta["health"],
            "initial_label": preset_meta["label"],
        }

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
        prev_state = self._state.copy()
        self._state, action_info = apply_dynamics(
            self._state,
            actions,
            self.crop_profile,
            include_weather=self.include_weather,
            include_resource_limits=self.include_resource_limits,
            dt=1.0
        )

        # Compute reward
        reward_dict = compute_reward(prev_state, self._state, action_info)
        reward = reward_dict["total"]

        # Check terminal conditions
        terminated = self._is_terminal()
        truncated = self.step_count >= self.max_episode_steps

        # Prepare info and observation
        obs = self._state.to_array()
        info = {
            "step": self.step_count,
            "reward_breakdown": reward_dict,
            "action_info": action_info,
            "crop_health": self._state.crop_health,
            "terminated_reason": self._get_termination_reason(),
        }

        # Store for episode statistics
        self.episode_rewards.append(reward)
        self.episode_states.append(self._state.to_dict())

        return obs, reward, terminated, truncated, info

    def _is_terminal(self) -> bool:
        """Check if episode should terminate."""
        if self._state.crop_health <= 0.0:
            return True
        if self._state.water_level <= 0.0 and self._state.energy_level <= 0.0:
            return True
        return False

    def _get_termination_reason(self) -> str:
        """Get reason for episode termination."""
        if self._state.crop_health <= 0.0:
            return "CROP_DEATH"
        if self._state.water_level <= 0.0 and self._state.energy_level <= 0.0:
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
            "final_crop_health": self._state.crop_health,
            "episode_length": len(self.episode_rewards),
            "difficulty": self.difficulty,
        }

    def render(self):
        """Render environment state (human readable)."""
        pass  # Placeholder

    # ==========================================================================
    # OPENENV REQUIRED: state() API
    # ==========================================================================

    def get_state(self) -> GreenhouseObservation:
        """
        Return current environment state as a typed Pydantic model.

        Required by the OpenEnv spec alongside step() and reset().
        Can be called at any point (before or after reset/step).

        Returns:
            GreenhouseObservation — fully typed snapshot of current state.
        """
        return GreenhouseObservation(
            temperature=float(self._state.temperature),
            humidity=float(self._state.humidity),
            co2=float(self._state.co2),
            light_intensity=float(self._state.light_intensity),
            water_level=float(self._state.water_level),
            energy_level=float(self._state.energy_level),
            crop_health=float(self._state.crop_health),
            mold_presence=float(self._state.mold_presence),
            time_of_day_norm=float(self._state.time_of_day) / 24.0,
            day_counter_norm=float(self._state.day_counter) / 365.0,
            step=self.step_count,
            difficulty=self.difficulty,
            crop=self.crop_name,
        )

    # ==========================================================================
    # OPENENV TYPED WRAPPERS
    # ==========================================================================

    def typed_reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
        initial_condition: Optional[str] = None,
    ) -> GreenhouseObservation:
        """
        Typed reset() — returns GreenhouseObservation instead of raw array.

        For use by inference.py and evaluators that prefer typed interfaces.
        """
        self.reset(seed=seed, options=options, initial_condition=initial_condition)
        return self.get_state()

    def typed_step(self, action: GreenhouseAction) -> GreenhouseStepResult:
        """
        Typed step() — accepts GreenhouseAction, returns GreenhouseStepResult.

        For use by inference.py and evaluators that prefer typed interfaces.

        Args:
            action: GreenhouseAction typed model

        Returns:
            GreenhouseStepResult with typed observation + reward + done + info
        """
        action_array = np.array(action.to_array(), dtype=np.float32)
        obs_array, reward_float, terminated, truncated, info = self.step(action_array)

        typed_obs = self.get_state()
        typed_reward = GreenhouseReward.from_dict(
            info.get("reward_breakdown", {"total": reward_float}),
            step=self.step_count,
            done=(terminated or truncated),
        )

        return GreenhouseStepResult(
            observation=typed_obs,
            reward=typed_reward,
            done=terminated,
            truncated=truncated,
            info=info,
        )


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
