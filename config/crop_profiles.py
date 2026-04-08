"""
config/crop_profiles.py

Crop-specific parameters: optimal conditions, growth dynamics, damage thresholds,
and Gaussian stress σ values used in the health cost function.

Health stress formula (per variable):
    stress(x) = 1 − exp(−0.5 × ((x − x_opt) / σ)²)

    σ controls sharpness:
        Δ = 1σ  → stress = 0.22  (mild)
        Δ = 2σ  → stress = 0.63  (significant)
        Δ = 3σ  → stress = 0.89  (severe)
"""

from typing import Dict, Any


# ============================================================================
# TOMATO  — warm-season, moderate water, medium temp range
# ============================================================================

TOMATO = {
    "name": "Tomato",

    # Optimal growing conditions
    "temp_optimal":     22.0,   # °C
    "humidity_optimal": 65.0,   # %
    "co2_optimal":      900.0,  # ppm
    "light_optimal":    700.0,  # µmol/m²/s

    # Tolerable range (crop survives but doesn't thrive at edges)
    "temp_min":         12.0,
    "temp_max":         28.0,
    "humidity_min":     50.0,
    "humidity_max":     85.0,
    "light_min":        300.0,

    # Damage thresholds (beyond these = irreversible per-step damage)
    "cold_damage_threshold": 10.0,  # damage below this °C
    "heat_stress_threshold": 30.0,  # damage above this °C

    # Growth and water
    "growth_rate":       0.015,   # max health gain per step at optimal conditions
    "water_requirement": 2.5,     # units consumed per 24h at full health

    # Gaussian stress widths — how sensitive this crop is per variable
    "temp_stress_sigma":     4.0,    # ±4°C → 22% stress (tomato tolerates small swings)
    "humidity_stress_sigma": 15.0,   # ±15% RH → 22% stress
    "co2_stress_sigma":      300.0,  # ±300 ppm → 22% stress
    "light_stress_sigma":    200.0,  # ±200 µmol → 22% stress

    "disease_susceptibility": 0.3,
}


# ============================================================================
# LETTUCE  — cool-season, low light, narrow temp range
# ============================================================================

LETTUCE = {
    "name": "Lettuce",

    "temp_optimal":     18.0,
    "humidity_optimal": 70.0,
    "co2_optimal":      800.0,
    "light_optimal":    500.0,

    "temp_min":         8.0,
    "temp_max":         24.0,
    "humidity_min":     60.0,
    "humidity_max":     90.0,
    "light_min":        200.0,

    "cold_damage_threshold": 2.0,    # very cold-hardy
    "heat_stress_threshold": 26.0,   # bolts quickly above this

    "growth_rate":       0.020,
    "water_requirement": 2.0,

    # Lettuce is more sensitive to temp (bolts above threshold → sharp stress)
    "temp_stress_sigma":     3.0,    # tighter: ±3°C → 22% stress
    "humidity_stress_sigma": 12.0,
    "co2_stress_sigma":      250.0,
    "light_stress_sigma":    150.0,

    "disease_susceptibility": 0.4,
}


# ============================================================================
# HERBS  (Basil) — warm-season, moderate light, sensitive to cold
# ============================================================================

HERBS = {
    "name": "Herbs",

    "temp_optimal":     24.0,
    "humidity_optimal": 60.0,
    "co2_optimal":      1000.0,
    "light_optimal":    600.0,

    "temp_min":         15.0,
    "temp_max":         32.0,
    "humidity_min":     40.0,
    "humidity_max":     80.0,
    "light_min":        250.0,

    "cold_damage_threshold": 10.0,
    "heat_stress_threshold": 35.0,

    "growth_rate":       0.025,
    "water_requirement": 1.5,

    # Herbs are moderately sensitive — wider sigmas, more forgiving
    "temp_stress_sigma":     3.1,   # was 4.0
    "humidity_stress_sigma": 11.5,  # was 15.0
    "co2_stress_sigma":      350.0,
    "light_stress_sigma":    200.0,

    "disease_susceptibility": 0.2,
}


# ============================================================================
# CUCUMBER  — warm, high humidity, sensitive to cold, water-hungry
# ============================================================================

CUCUMBER = {
    "name": "Cucumber",

    "temp_optimal":     24.0,
    "humidity_optimal": 75.0,
    "co2_optimal":      950.0,
    "light_optimal":    650.0,

    "temp_min":         16.0,
    "temp_max":         30.0,
    "humidity_min":     60.0,
    "humidity_max":     90.0,
    "light_min":        300.0,

    "cold_damage_threshold": 10.0,
    "heat_stress_threshold": 34.0,

    "growth_rate":       0.018,
    "water_requirement": 3.0,

    # Cucumber is sensitive to humidity deviations (fungal disease risk)
    "temp_stress_sigma":     3.2,   # was 4.0
    "humidity_stress_sigma": 8.5,   # was 10.0
    "co2_stress_sigma":      300.0,
    "light_stress_sigma":    200.0,

    "disease_susceptibility": 0.35,
}


# ============================================================================
# PROFILE REGISTRY
# ============================================================================

CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "tomato":   TOMATO,
    "lettuce":  LETTUCE,
    "herbs":    HERBS,
    "cucumber": CUCUMBER,
}


def get_crop_profile(crop_name: str) -> Dict[str, Any]:
    """
    Retrieve crop profile by name.

    Args:
        crop_name: Name of crop (tomato, lettuce, herbs, cucumber)

    Returns:
        Dictionary with crop parameters

    Raises:
        ValueError: If crop not in registry
    """
    crop_key = crop_name.lower()
    if crop_key not in CROP_PROFILES:
        raise ValueError(
            f"Unknown crop: '{crop_name}'. Available: {list(CROP_PROFILES.keys())}"
        )
    return CROP_PROFILES[crop_key]
