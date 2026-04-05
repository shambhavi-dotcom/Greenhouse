"""
env/actions.py

Action space definition for the greenhouse environment.
Defines all possible control actions and their effects.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class ActionType(Enum):
    """Enumeration of action categories."""
    HEATING = "heating"
    COOLING = "cooling"
    HUMIDIFYING = "humidifying"
    DEHUMIDIFYING = "dehumidifying"
    VENTILATION = "ventilation"
    IRRIGATION = "irrigation"
    LIGHTING = "lighting"
    CO2_ENRICHMENT = "co2_enrichment"


@dataclass
class Action:
    """
    Action taken by agent to control the greenhouse.
    
    Each action has:
        - action_type: Type of action (heating, cooling, irrigation, etc.)
        - intensity: Strength of action (0.0-1.0, where 1.0 = full power)
    """
    
    action_type: ActionType
    intensity: float  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "action_type": self.action_type.value,
            "intensity": self.intensity,
        }
    
    def is_valid(self) -> bool:
        """Check if action is within valid range."""
        return 0.0 <= self.intensity <= 1.0


class ActionSpace:
    """
    Discrete or continuous action space for the greenhouse.
    
    The agent can apply multiple actions simultaneously.
    This class handles composition of multiple actions.
    """
    
    def __init__(self, num_actions: int = 8):
        """
        Initialize action space.
        
        Args:
            num_actions: Number of discrete action dimensions (one per action type)
        """
        self.num_actions = num_actions
        self.action_types = list(ActionType)
    
    def sample(self) -> list[Action]:
        """Sample random action from space."""
        import random
        actions = []
        for action_type in self.action_types:
            intensity = random.random()  # Random value 0.0-1.0
            actions.append(Action(action_type, intensity))
        return actions
    
    def create_action(self, 
                     action_type: ActionType, 
                     intensity: float) -> Action:
        """
        Create a single action.
        
        Args:
            action_type: Type of action
            intensity: Intensity 0.0-1.0
            
        Returns:
            Action object
        """
        action = Action(action_type, intensity)
        if not action.is_valid():
            raise ValueError(f"Invalid action intensity: {intensity}")
        return action
    
    def from_array(self, action_array: list[float]) -> list[Action]:
        """
        Convert array of intensities to list of actions.
        
        Args:
            action_array: List of intensities matching action types
            
        Returns:
            List of Action objects
        """
        if len(action_array) != len(self.action_types):
            raise ValueError(
                f"Expected {len(self.action_types)} actions, "
                f"got {len(action_array)}"
            )
        
        actions = []
        for action_type, intensity in zip(self.action_types, action_array):
            actions.append(Action(action_type, intensity))
        return actions


# ============================================================================
# ACTION EFFECT DEFINITIONS (REFERENCE)
# ============================================================================

ACTION_EFFECTS = {
    ActionType.HEATING: {
        "description": "Increase temperature",
        "target_var": "temperature",
        "effect_sign": "positive",
        "max_delta_per_step": 2.0,  # °C per step at full intensity
        "energy_cost": 0.5,
    },
    ActionType.COOLING: {
        "description": "Decrease temperature",
        "target_var": "temperature",
        "effect_sign": "negative",
        "max_delta_per_step": 2.5,
        "energy_cost": 0.6,
    },
    ActionType.HUMIDIFYING: {
        "description": "Increase relative humidity",
        "target_var": "humidity",
        "effect_sign": "positive",
        "max_delta_per_step": 5.0,  # % per step
        "energy_cost": 2.0,
    },
    ActionType.DEHUMIDIFYING: {
        "description": "Decrease relative humidity",
        "target_var": "humidity",
        "effect_sign": "negative",
        "max_delta_per_step": 8.0,
        "energy_cost": 1.5,
    },
    ActionType.VENTILATION: {
        "description": "Increase air circulation, reduce CO2",
        "target_var": "co2",
        "effect_sign": "negative",
        "max_delta_per_step": 150.0,  # ppm reduction
        "energy_cost": 1.0,
    },
    ActionType.IRRIGATION: {
        "description": "Water the crops",
        "target_var": "water_level",
        "effect_sign": "positive",
        "max_amount": 5.0,  # units per step
        "energy_cost": 0.5,
    },
    ActionType.LIGHTING: {
        "description": "Supplement light for crops",
        "target_var": "light_intensity",
        "effect_sign": "positive",
        "max_delta_per_step": 500.0,  # µmol/m²/s
        "energy_cost": 0.1,  # Per unit of light
    },
    ActionType.CO2_ENRICHMENT: {
        "description": "Add CO2 to enhance growth",
        "target_var": "co2",
        "effect_sign": "positive",
        "max_delta_per_step": 200.0,  # ppm increase
        "energy_cost": 1.5,
    },
}
