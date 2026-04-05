"""
env/state.py

State representation for the greenhouse environment.
Defines all state variables, their bounds, and methods to interact with state.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import numpy as np


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
    temperature: float = 20.0
    humidity: float = 60.0
    co2: float = 400.0
    light_intensity: float = 0.0
    
    # Resource levels
    water_level: float = 80.0
    energy_level: float = 80.0
    
    # Crop state
    crop_health: float = 0.8
    mold_presence: float = 0.0
    
    # Temporal state
    time_of_day: int = 12  # Hours (0-23)
    day_counter: int = 0
    
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
            external_weather=self.external_weather.copy(),
        )
        return new_state
