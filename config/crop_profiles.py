"""
config/crop_profiles.py

Crop-specific parameters defining optimal conditions and growth dynamics
for different crops that can be grown in the greenhouse.
"""

from typing import Dict, Any


# ============================================================================
# TOMATO PROFILE
# ============================================================================

TOMATO = {
    "name": "Tomato",
    "temp_optimal": 22.0,
    "temp_min": 12.0,
    "temp_max": 28.0,
    "humidity_optimal": 65.0,
    "humidity_min": 50.0,
    "humidity_max": 85.0,
    "light_optimal": 700.0,  # µmol/m²/s
    "light_min": 300.0,
    "co2_optimal": 900.0,
    "growth_rate": 0.015,  # Health gain per day under optimal conditions
    "water_requirement": 2.5,  # per day
    "cold_damage_threshold": 10.0,
    "heat_stress_threshold": 30.0,
    "disease_susceptibility": 0.3,  # 0-1, likelihood of disease
}

# ============================================================================
# LETTUCE PROFILE
# ============================================================================

LETTUCE = {
    "name": "Lettuce",
    "temp_optimal": 18.0,
    "temp_min": 8.0,
    "temp_max": 24.0,
    "humidity_optimal": 70.0,
    "humidity_min": 60.0,
    "humidity_max": 90.0,
    "light_optimal": 500.0,
    "light_min": 200.0,
    "co2_optimal": 800.0,
    "growth_rate": 0.020,
    "water_requirement": 2.0,
    "cold_damage_threshold": 2.0,
    "heat_stress_threshold": 26.0,
    "disease_susceptibility": 0.4,
}

# ============================================================================
# HERBS PROFILE (e.g., Basil)
# ============================================================================

HERBS = {
    "name": "Herbs",
    "temp_optimal": 24.0,
    "temp_min": 15.0,
    "temp_max": 32.0,
    "humidity_optimal": 60.0,
    "humidity_min": 40.0,
    "humidity_max": 80.0,
    "light_optimal": 600.0,
    "light_min": 250.0,
    "co2_optimal": 1000.0,
    "growth_rate": 0.025,
    "water_requirement": 1.5,
    "cold_damage_threshold": 10.0,
    "heat_stress_threshold": 35.0,
    "disease_susceptibility": 0.2,
}

# ============================================================================
# PROFILE REGISTRY
# ============================================================================

CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "tomato": TOMATO,
    "lettuce": LETTUCE,
    "herbs": HERBS,
}


def get_crop_profile(crop_name: str) -> Dict[str, Any]:
    """
    Retrieve crop profile by name.
    
    Args:
        crop_name: Name of crop (tomato, lettuce, herbs)
        
    Returns:
        Dictionary with crop parameters
        
    Raises:
        ValueError: If crop not in registry
    """
    crop_key = crop_name.lower()
    if crop_key not in CROP_PROFILES:
        raise ValueError(f"Unknown crop: {crop_name}. Available: {list(CROP_PROFILES.keys())}")
    return CROP_PROFILES[crop_key]
