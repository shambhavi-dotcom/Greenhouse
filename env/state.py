"""
env/state.py

State representation for the greenhouse environment.
Defines all state variables, their bounds, and methods to interact with state.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import numpy as np


# ==============================================================================
# INITIAL CONDITION PRESETS
# ==============================================================================
# Each preset sets ONLY crop health and starting temperature.
# All other variables (humidity, CO2, water, energy, mold) are always
# initialised at their optimal/full values — resource constraints and
# environmental disturbances are governed exclusively by task difficulty.
#
# Temperature is offset from optimal to match the health tier:
#   a lower-health greenhouse was poorly managed, so it's also cooler.
# The agent's goal is always to restore and maintain optimal conditions.

INITIAL_CONDITION_PRESETS: Dict[str, Dict[str, Any]] = {
    "100% — Thriving (Optimal)": {
        "label":       "Thriving",
        "health":      1.0,
        "temperature": 22.0,   # At optimal — maintain excellence
        "description": "Perfect conditions. Agent must sustain high performance.",
        "color":       "#00e676",
    },
    "75% — Healthy (Minor Stress)": {
        "label":       "Healthy",
        "health":      0.75,
        "temperature": 19.5,   # 2.5°C below optimal — mild cold stress
        "description": "Mild temperature stress. Agent must restore and maintain.",
        "color":       "#69f0ae",
    },
    "50% — Stressed (Recovery Needed)": {
        "label":       "Stressed",
        "health":      0.50,
        "temperature": 16.0,   # 6°C below optimal — moderate cold stress
        "description": "Significant cold stress. Active recovery required.",
        "color":       "#ffab40",
    },
    "25% — Critical (Emergency)": {
        "label":       "Critical",
        "health":      0.25,
        "temperature": 12.0,   # 10°C below optimal — severe cold stress
        "description": "Emergency conditions. Prevent crop death immediately.",
        "color":       "#ff5252",
    },
}


def build_initial_state(preset_name: str = "100% — Thriving (Optimal)") -> "GreenhouseState":
    """
    Build a GreenhouseState from a named initial condition preset.

    Only health and temperature are taken from the preset.
    All other variables are set to their optimal/full values so that
    resource constraints and environmental dynamics are governed purely
    by task difficulty (energy refill rate, weather, etc.).

    Args:
        preset_name: Key from INITIAL_CONDITION_PRESETS.

    Returns:
        A GreenhouseState with all variables correctly initialised.
    """
    preset = INITIAL_CONDITION_PRESETS.get(preset_name)
    if preset is None:
        raise ValueError(
            f"Unknown preset '{preset_name}'. "
            f"Available: {list(INITIAL_CONDITION_PRESETS.keys())}"
        )
    return GreenhouseState(
        temperature=preset["temperature"],
        humidity=65.0,        # always optimal — difficulty governs drift
        co2=800.0,            # near-optimal, consistent starting point
        light_intensity=0.0,  # computed each step from time-of-day
        water_level=100.0,    # full reservoir — depletion driven by difficulty
        energy_level=200.0,   # full energy bank — refill rate driven by difficulty
        crop_health=preset["health"],
        mold_presence=0.0,    # clean start regardless of health tier
        time_of_day=12,       # noon — maximum natural light at episode start
        day_counter=0,
    )


@dataclass
class GreenhouseState:
    """
    Complete state representation of the greenhouse at any time point.
    
    Attributes:
        temperature: Current temperature (°C)
        humidity: Current relative humidity (%)
        co2: Current CO2 level (ppm)
        light_intensity: Current light intensity (µmol/m²/s)
        water_level: Current water in system (units)
        energy_level: Current energy/power available (units)
        crop_health: Crop health 0.0 (dead) to 1.0 (thriving)
        mold_presence: Presence of mold (0.0-1.0, where 1.0 = severe)
        time_of_day: Hour in day (0-23)
        day_counter: Day number in episode
        external_weather: Weather condition from external environment
    """
    
    # Environmental variables
    temperature: float = 22.0  # Starts at optimal (TEMP_OPTIMAL)
    humidity: float = 65.0     # Starts at optimal (HUMIDITY_OPTIMAL)
    co2: float = 800.0         # Starts at optimal level
    light_intensity: float = 0.0
    
    # Resource levels
    water_level: float = 100.0  # Starts full (WATER_INIT)
    energy_level: float = 200.0 # Starts full (ENERGY_INIT)
    
    # Crop state
    crop_health: float = 1.0    # Starts thriving
    mold_presence: float = 0.0
    
    # Temporal state
    time_of_day: int = 12  # Hours (0-23)
    day_counter: int = 0

    # Daily usage tracking (resets when a new day starts)
    daily_water_added: float = 0.0
    daily_energy_used: float = 0.0
    
    # External perturbation
    external_weather: Dict[str, float] = field(default_factory=lambda: {
        "temp_shift": 0.0,
        "humidity_shift": 0.0,
    })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for observation."""
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "co2": self.co2,
            "light_intensity": self.light_intensity,
            "water_level": self.water_level,
            "energy_level": self.energy_level,
            "crop_health": self.crop_health,
            "mold_presence": self.mold_presence,
            "time_of_day": self.time_of_day,
            "day_counter": self.day_counter,
        }
    
    def to_array(self) -> np.ndarray:
        """Convert state to 1D numpy array for neural network input."""
        return np.array([
            self.temperature,
            self.humidity,
            self.co2,
            self.light_intensity,
            self.water_level,
            self.energy_level,
            self.crop_health,
            self.mold_presence,
            self.time_of_day / 24.0,  # Normalize to [0, 1]
            self.day_counter / 365.0,  # Normalize to [0, 1]
        ], dtype=np.float32)
    
    @staticmethod
    def from_array(arr: np.ndarray) -> 'GreenhouseState':
        """Reconstruct state from array representation."""
        state = GreenhouseState()
        state.temperature = float(arr[0])
        state.humidity = float(arr[1])
        state.co2 = float(arr[2])
        state.light_intensity = float(arr[3])
        state.water_level = float(arr[4])
        state.energy_level = float(arr[5])
        state.crop_health = float(arr[6])
        state.mold_presence = float(arr[7])
        state.time_of_day = int(arr[8] * 24.0)
        state.day_counter = int(arr[9] * 365.0)
        return state
    
    def is_terminal(self) -> bool:
        """Check if state represents terminal condition (episode over)."""
        # Episode ends if crop dies
        if self.crop_health <= 0.0:
            return True
        # Episode ends if system severely degrades
        if self.water_level <= 0.0 and self.energy_level <= 0.0:
            return True
        return False
    
    def is_critical(self) -> bool:
        """Check if state is in a critical/risky condition."""
        # Mold detected
        if self.mold_presence > 0.5:
            return True
        # Crop severely stressed
        if self.crop_health < 0.3:
            return True
        # Resource depleted
        if self.water_level < 10.0 or self.energy_level < 10.0:
            return True
        return False
    
    def copy(self) -> 'GreenhouseState':
        """Create a deep copy of this state."""
        new_state = GreenhouseState(
            temperature=self.temperature,
            humidity=self.humidity,
            co2=self.co2,
            light_intensity=self.light_intensity,
            water_level=self.water_level,
            energy_level=self.energy_level,
            crop_health=self.crop_health,
            mold_presence=self.mold_presence,
            time_of_day=self.time_of_day,
            day_counter=self.day_counter,
            daily_water_added=self.daily_water_added,
            daily_energy_used=self.daily_energy_used,
            external_weather=self.external_weather.copy(),
        )
        return new_state
