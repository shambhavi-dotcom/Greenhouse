"""
env/dynamics.py

Environment dynamics: how state variables evolve over time.
Implements the physical simulation of the greenhouse.

This is the core of the environment - it defines:
- Temperature dynamics (heating/cooling, external weather, radiation)
- Humidity dynamics (evapotranspiration, ventilation, humidification)
- Crop growth (health changes based on conditions)
- Resource consumption (water, energy)
- Disease and stress mechanisms (mold, frost damage, heat stress)
"""

from typing import Tuple
import numpy as np
from env.state import GreenhouseState
from env.actions import Action, ActionType
from config import constants


def apply_dynamics(
    state: GreenhouseState,
    actions: list[Action],
    crop_profile: dict,
    dt: float = 1.0,
) -> Tuple[GreenhouseState, dict]:
    """
    Apply one time step of environmental dynamics.
    
    This function is the heart of the simulation. It takes the current state,
    applied actions, and returns the new state after dt hours.
    
    Args:
        state: Current greenhouse state
        actions: List of control actions
        crop_profile: Parameters for current crop
        dt: Time step in hours (default 1.0)
        
    Returns:
        Tuple of (new_state, info_dict)
            - new_state: Updated GreenhouseState
            - info_dict: Additional information (energy used, water used, etc.)
    """
    
    # Create new state from current
    new_state = state.copy()
    info = {
        "energy_used": 0.0,
        "water_used": 0.0,
        "temperature_change": 0.0,
        "humidity_change": 0.0,
        "crop_health_change": 0.0,
    }
    
    # ========================================================================
    # 1. UPDATE TIME
    # ========================================================================
    prev_time = new_state.time_of_day
    new_state.time_of_day = (new_state.time_of_day + int(dt)) % 24
    if new_state.time_of_day < prev_time:
        new_state.day_counter += 1
    
    # ========================================================================
    # 2. EXTRACT ACTION INTENSITIES
    # ========================================================================
    action_dict = {a.action_type: a.intensity for a in actions}
    heating = action_dict.get(ActionType.HEATING, 0.0)
    cooling = action_dict.get(ActionType.COOLING, 0.0)
    humidify = action_dict.get(ActionType.HUMIDIFYING, 0.0)
    dehumidify = action_dict.get(ActionType.DEHUMIDIFYING, 0.0)
    ventilation = action_dict.get(ActionType.VENTILATION, 0.0)
    irrigation = action_dict.get(ActionType.IRRIGATION, 0.0)
    lighting = action_dict.get(ActionType.LIGHTING, 0.0)
    co2_enrichment = action_dict.get(ActionType.CO2_ENRICHMENT, 0.0)
    
    # ========================================================================
    # 3. EXTERNAL WEATHER (varies by difficulty)
    # ========================================================================
    # Base ambient temperature changes throughout the day
    ambient_temp = 15.0 + 8.0 * max(0, np.sin(np.pi * (new_state.time_of_day - 6) / 12))
    # Add small random disturbances if harder difficulty
    if new_state.day_counter > 1:  # Simple pseudo-weather after day 1
        ambient_temp += 0.5 * np.sin(new_state.day_counter * 0.5)
    
    # ========================================================================
    # 4. COMPUTE NATURAL LIGHT (sun position)
    # ========================================================================
    # Light peaks at noon (12:00), zero at night (6PM-6AM)
    if 6 <= new_state.time_of_day <= 18:
        natural_light = 600.0 * np.sin(np.pi * (new_state.time_of_day - 6) / 12)
    else:
        natural_light = 0.0
    
    # Add supplemental lighting
    supplemental_light = lighting * 500.0
    new_state.light_intensity = np.clip(natural_light + supplemental_light, 0, 1000)
    
    # ========================================================================
    # 5. TEMPERATURE DYNAMICS
    # ========================================================================
    prev_temp = new_state.temperature
    
    # Natural decay toward ambient (1/4°C per hour time constant)
    temp_decay = (ambient_temp - new_state.temperature) / 4.0 * dt
    
    # Day/night radiative effects
    if 6 <= new_state.time_of_day <= 18:
        radiative_effect = 0.3  # Warming during day
    else:
        radiative_effect = -0.3  # Cooling at night
    
    # Action effects
    temp_heating = heating * 2.0 * dt  # +2°C per hour at full intensity
    temp_cooling = -cooling * 2.5 * dt  # -2.5°C per hour at full intensity
    temp_ventilation = -ventilation * 0.5 * dt  # Ventilation cools slightly
    
    # Humidification/dehumidification interact with temperature
    # Misting cools (evaporative effect)
    temp_misting = -humidify * 0.2 * dt
    
    new_state.temperature += temp_decay + radiative_effect + temp_heating + temp_cooling + temp_ventilation + temp_misting
    
    info["temperature_change"] = new_state.temperature - prev_temp
    info["energy_used"] += heating * 0.5 + cooling * 0.6 + ventilation * 1.0 + humidify * 2.0 + dehumidify * 1.5 + lighting * 0.1 * new_state.light_intensity / 500 + co2_enrichment * 1.5
    
    # ========================================================================
    # 6. HUMIDITY DYNAMICS
    # ========================================================================
    prev_humidity = new_state.humidity
    
    # Crop evapotranspiration (loses water to air)
    water_loss = new_state.crop_health * (1.0 + abs(new_state.temperature - 22) / 10) * (new_state.light_intensity / 600) * 0.5
    # This increases humidity
    humidity_from_evapotrans = water_loss / 100  # Convert to % contribution
    
    # Temperature affects humidity (warmer air is drier for same absolute moisture)
    temp_effect_on_humidity = -(new_state.temperature - 20) / 10  # Warms dry out
    
    # Humidification and dehumidification
    humidity_humidify = humidify * 5.0 * dt
    humidity_dehumidify = -dehumidify * 8.0 * dt
    
    # Ventilation reduces humidity (outdoor air is drier)
    humidity_ventilation = -ventilation * 10.0 * dt
    
    new_state.humidity += humidity_from_evapotrans + temp_effect_on_humidity + humidity_humidify + humidity_dehumidify + humidity_ventilation
    
    # Saturation limit
    new_state.humidity = min(new_state.humidity, 95.0)
    
    info["humidity_change"] = new_state.humidity - prev_humidity
    
    # ========================================================================
    # 7. CO2 DYNAMICS
    # ========================================================================
    # Plant uptake during photosynthesis
    photosynthesis_rate = new_state.crop_health * new_state.light_intensity / 600
    co2_uptake = photosynthesis_rate * 0.5  # ppm per hour
    
    # Natural ventilation also reduces CO2 (outdoor is ~400 ppm)
    ventilation_effect = -ventilation * 150.0 * dt  # Rapid CO2 removal
    
    # CO2 enrichment
    enrichment_effect = co2_enrichment * 200.0 * dt
    
    # Ambient CO2 (400 ppm outdoor, slowly exchanges)
    ambient_exchange = -(new_state.co2 - 400) / 20 * dt
    
    new_state.co2 += -co2_uptake * dt + ventilation_effect + enrichment_effect + ambient_exchange
    
    # ========================================================================
    # 8. WATER DYNAMICS
    # ========================================================================
    # Crop consumption (from evapotranspiration)
    water_consumption = water_loss * 0.8  # Crops use ~80% of evapotranspired water
    
    # Irrigation adds water (5 units per hour at full intensity)
    water_irrigation = irrigation * 5.0 * dt
    
    new_state.water_level += -water_consumption + water_irrigation
    
    info["water_used"] = water_consumption
    
    # ========================================================================
    # 9. ENERGY DYNAMICS
    # ========================================================================
    # Solar production during day
    solar_production = (new_state.light_intensity / 600) * 30 * dt
    
    # Energy consumption (already computed in action costs)
    energy_consumption = info["energy_used"]
    
    new_state.energy_level += solar_production - energy_consumption
    
    # ========================================================================
    # 10. CROP HEALTH DYNAMICS
    # ========================================================================
    prev_health = new_state.crop_health
    
    # Condition deviations from optimal
    temp_optimal = crop_profile.get("optimal_temperature", 22)
    humidity_optimal = crop_profile.get("optimal_humidity", 65)
    co2_optimal = crop_profile.get("optimal_co2", 1000)
    light_optimal = crop_profile.get("optimal_light", 600)
    
    temp_stress = abs(new_state.temperature - temp_optimal) / 10
    humidity_stress = abs(new_state.humidity - humidity_optimal) / 20
    co2_stress = abs(new_state.co2 - co2_optimal) / 500
    light_stress = max(0, (light_optimal - new_state.light_intensity) / light_optimal)
    water_stress = max(0, (20 - new_state.water_level) / 20) if new_state.water_level < 20 else 0
    
    # Growth under good conditions
    stress_factor = 1.0 - (temp_stress + humidity_stress + co2_stress + light_stress + water_stress) / 5
    stress_factor = max(0, min(1, stress_factor))
    
    growth_rate = crop_profile.get("growth_rate", 0.01)
    health_growth = growth_rate * stress_factor * 0.5  # Slower growth
    
    # Mold damaging health
    mold_damage = 0.0
    if new_state.mold_presence > 0.1:
        mold_damage = -new_state.mold_presence * 0.02
    
    # Extreme condition damage (irreversible)
    extreme_damage = 0.0
    if new_state.temperature < 2:
        extreme_damage = -0.1  # Freeze damage
    elif new_state.temperature > 35:
        extreme_damage = -0.05  # Heat damage
    
    if new_state.water_level < 5 and new_state.crop_health < 0.5:
        extreme_damage = -0.3  # Severe dehydration
    
    new_state.crop_health += health_growth + mold_damage + extreme_damage
    
    # Death condition
    if new_state.crop_health <= 0:
        new_state.crop_health = 0.0
    
    info["crop_health_change"] = new_state.crop_health - prev_health
    
    # ========================================================================
    # 11. MOLD DYNAMICS
    # ========================================================================
    # Mold grows when warm + humid
    mold_growth = 0.0
    if new_state.temperature > 25 and new_state.humidity > 80:
        mold_growth = 0.05 * dt  # 5% per hour growth rate
    
    # Ventilation suppresses mold
    mold_suppression = -ventilation * 0.1 * dt
    
    new_state.mold_presence += mold_growth + mold_suppression
    
    # ========================================================================
    # 12. RESOURCE CONSTRAINTS
    # ========================================================================
    # Hard limits on resources
    if new_state.water_level < 0:
        new_state.water_level = 0
        new_state.crop_health = max(0, new_state.crop_health - 0.1)  # Crop dies if no water
    
    if new_state.energy_level < 0:
        new_state.energy_level = 0
        # No cooling/heating if no energy - but still affects health
        if new_state.temperature < 5 or new_state.temperature > 40:
            new_state.crop_health = max(0, new_state.crop_health - 0.2)
    
    # ========================================================================
    # 13. CLAMP ALL VALUES
    # ========================================================================
    new_state = _clamp_state(new_state)
    
    return new_state, info


def _clamp_state(state: GreenhouseState) -> GreenhouseState:
    """
    Clamp state variables to physical limits.
    
    Args:
        state: State to clamp
        
    Returns:
        State with variables clamped to valid ranges
    """
    state.temperature = np.clip(
        state.temperature,
        constants.TEMP_MIN,
        constants.TEMP_MAX
    )
    state.humidity = np.clip(
        state.humidity,
        constants.HUMIDITY_MIN,
        constants.HUMIDITY_MAX
    )
    state.co2 = np.clip(
        state.co2,
        constants.CO2_MIN,
        constants.CO2_MAX
    )
    state.light_intensity = np.clip(
        state.light_intensity,
        constants.LIGHT_MIN,
        constants.LIGHT_MAX
    )
    state.water_level = np.clip(
        state.water_level,
        0.0,
        constants.WATER_CAPACITY
    )
    state.energy_level = np.clip(
        state.energy_level,
        0.0,
        constants.ENERGY_CAPACITY
    )
    state.crop_health = np.clip(
        state.crop_health,
        constants.CROP_HEALTH_MIN,
        constants.CROP_HEALTH_MAX
    )
    state.mold_presence = np.clip(
        state.mold_presence,
        0.0,
        1.0
    )
    
    return state


def compute_temperature_delta(
    current_temp: float,
    ambient_temp: float,
    heating_intensity: float,
    cooling_intensity: float,
    time_of_day: int,
) -> float:
    """
    Compute temperature change for one time step.
    
    Includes natural cooling/heating toward ambient, day/night radiative effects,
    and active heating/cooling actions.
    """
    pass  # Placeholder


def compute_humidity_delta(
    current_humidity: float,
    current_temp: float,
    crop_health: float,
    humidify_intensity: float,
    dehumidify_intensity: float,
    ventilation_intensity: float,
) -> float:
    """
    Compute humidity change for one time step.
    
    Includes evapotranspiration from crops, active humidification/dehumidification,
    and ventilation effects.
    """
    pass  # Placeholder


def compute_crop_health_delta(
    current_health: float,
    temperature: float,
    humidity: float,
    co2: float,
    light_intensity: float,
    crop_profile: dict,
) -> float:
    """
    Compute crop health change based on environmental conditions.
    
    Health improves when conditions match crop optimal profile,
    decreases under stress, and can be damaged irreversibly.
    """
    pass  # Placeholder


def check_disease_risk(
    temperature: float,
    humidity: float,
    crop_health: float,
) -> Tuple[bool, float]:
    """
    Check for disease (mold) risk and compute mold presence change.
    
    Returns:
        Tuple of (disease_detected, mold_presence_delta)
    """
    pass  # Placeholder
