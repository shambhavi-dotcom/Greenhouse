"""
env/dynamics.py — Greenhouse Physics Engine (v2)

Real-world greenhouse simulation based on engineering principles:

Temperature:
    Newton's law of cooling (wall exchange τ=12h) + HVAC actuation.
    Heater: +6°C/h at full. Cooler: −5°C/h at full.
    Ventilation pulls interior toward ambient proportionally.

Humidity:
    VPD-driven evapotranspiration (crop transpires moisture into air).
    Humidifier: +8%/h. Dehumidifier: −6%/h. Ventilation: −2%/h (not −10%).
    Natural drift toward equilibrium (~50%) when undisturbed.

CO2:
    Photosynthetic uptake (crop-driven, up to 30 ppm/h).
    Ventilation flushes with outdoor air (~400 ppm).
    CO2 enrichment: +150 ppm/h at full.

Water:
    Finite reservoir (0–100 units). Drains via transpiration each step.
    Irrigation adds to reservoir. No artificial daily cap.

Energy (grid-connected):
    Each actuator consumes energy proportional to usage intensity.
    Passive refill each step (solar panels + grid connection), rate scales
    with difficulty: Easy→5.0, Medium→2.0, Hard→0.5 units/step.
    If energy_level = 0, all actuators scale down (brownout protection).
    No arbitrary daily budget cap.

Health (Gaussian stress kernel):
    stress(x) = 1 − exp(−½ × ((x − x_opt) / σ)²)
    Combined stress = weighted sum over temp, humidity, CO2, light.
    Stress > break-even (≈0.65) → health decays; stress < break-even → health grows.
    Proportional damage for temperatures outside crop-specific danger thresholds.
"""

from typing import Tuple
import numpy as np

from env.state import GreenhouseState
from env.actions import Action, ActionType
from config import constants


def apply_dynamics(
    state: GreenhouseState,
    actions: list,
    crop_profile: dict,
    include_weather: bool = False,
    include_resource_limits: bool = True,
    dt: float = 1.0,
    difficulty: str = "medium",
) -> Tuple[GreenhouseState, dict]:
    """
    Apply one time step of greenhouse physics.

    Args:
        state:                  Current greenhouse state.
        actions:                List of Action objects (from ActionSpace).
        crop_profile:           Crop-specific parameter dictionary.
        include_weather:        Whether external weather disturbances occur.
        include_resource_limits: Whether energy/water are finite resources.
        dt:                     Time step in hours (default 1.0).
        difficulty:             'easy' | 'medium' | 'hard' — controls energy refill rate.

    Returns:
        (new_state, info_dict)
            new_state:  Updated GreenhouseState.
            info_dict:  energy_used, water_used, temperature_change,
                        humidity_change, crop_health_change, stress_total.
    """

    new_state = state.copy()
    info = {
        "energy_used":        0.0,
        "water_used":         0.0,
        "temperature_change": 0.0,
        "humidity_change":    0.0,
        "crop_health_change": 0.0,
        "stress_total":       0.0,
    }

    # ========================================================================
    # 1. UPDATE TIME
    # ========================================================================
    prev_time = new_state.time_of_day
    new_state.time_of_day = (new_state.time_of_day + int(dt)) % 24
    if new_state.time_of_day < prev_time:
        new_state.day_counter += 1
        new_state.daily_water_added = 0.0
        new_state.daily_energy_used = 0.0

    # ========================================================================
    # 2. EXTRACT ACTION INTENSITIES
    # ========================================================================
    action_dict = {a.action_type: a.intensity for a in actions}

    heating     = float(action_dict.get(ActionType.HEATING,        0.0))
    cooling     = float(action_dict.get(ActionType.COOLING,        0.0))
    humidify    = float(action_dict.get(ActionType.HUMIDIFYING,    0.0))
    dehumidify  = float(action_dict.get(ActionType.DEHUMIDIFYING,  0.0))
    ventilation = float(action_dict.get(ActionType.VENTILATION,    0.0))
    irrigation  = float(action_dict.get(ActionType.IRRIGATION,     0.0))
    lighting    = float(action_dict.get(ActionType.LIGHTING,       0.0))
    co2_enrich  = float(action_dict.get(ActionType.CO2_ENRICHMENT, 0.0))

    # ========================================================================
    # 3. ENERGY — grid-connected with passive refill ("solar + grid" model)
    #
    #   step_energy = sum(intensity_i × cost_i) × dt
    #   Each step the energy bank refills by difficulty-scaled rate.
    #   If bank = 0, apply brownout scale (actuators derate proportionally).
    # ========================================================================
    step_energy = (
        heating     * constants.ACT_HEATING_ENERGY     +
        cooling     * constants.ACT_COOLING_ENERGY     +
        humidify    * constants.ACT_HUMIDIFY_ENERGY    +
        dehumidify  * constants.ACT_DEHUMIDIFY_ENERGY  +
        ventilation * constants.ACT_VENTILATION_ENERGY +
        lighting    * constants.ACT_LIGHTING_ENERGY    +
        co2_enrich  * constants.ACT_CO2_ENERGY         +
        irrigation  * constants.ACT_IRRIGATION_ENERGY
    ) * dt

    if include_resource_limits:
        # Passive refill first (solar/grid tops up battery each hour)
        refill_rate = constants.ENERGY_REFILL_BY_DIFFICULTY.get(
            difficulty, constants.ENERGY_REFILL_MEDIUM
        )
        new_state.energy_level = min(
            constants.ENERGY_CAPACITY,
            new_state.energy_level + refill_rate * dt,
        )

        # Brownout scale: proportionally reduce actuators if energy is too low
        if new_state.energy_level <= 0.0:
            act_scale = 0.0
        elif step_energy <= 0.0:
            act_scale = 1.0
        else:
            act_scale = min(1.0, new_state.energy_level / step_energy)

        # Deduct energy (after scaling)
        actual_energy = step_energy * act_scale
        new_state.energy_level = max(0.0, new_state.energy_level - actual_energy)
    else:
        # Easy mode: unlimited power (learning control, not resource planning)
        act_scale = 1.0
        actual_energy = step_energy

    # Scale all actuators by the brownout factor
    heating     *= act_scale
    cooling     *= act_scale
    humidify    *= act_scale
    dehumidify  *= act_scale
    ventilation *= act_scale
    irrigation  *= act_scale
    lighting    *= act_scale
    co2_enrich  *= act_scale

    info["energy_used"] = actual_energy
    new_state.daily_energy_used += actual_energy

    # ========================================================================
    # 4. NATURAL LIGHT (solar position)
    #    Peaks at noon (600 µmol/m²/s), zero at night (18:00–06:00).
    # ========================================================================
    tod = new_state.time_of_day
    if 6 <= tod <= 18:
        natural_light = 600.0 * np.sin(np.pi * (tod - 6) / 12)
    else:
        natural_light = 0.0

    supplemental_light = lighting * 400.0   # LEDs add up to 400 µmol at full
    new_state.light_intensity = float(np.clip(
        natural_light + supplemental_light,
        constants.LIGHT_MIN, constants.LIGHT_MAX,
    ))

    # ========================================================================
    # 5. EXTERNAL WEATHER (stochastic disturbances in medium/hard modes)
    # ========================================================================
    if include_weather:
        # Diurnal cycle: ambient 12°C at night, up to 20°C at noon
        base_ambient = 12.0 + 8.0 * max(0.0, np.sin(np.pi * (tod - 6) / 12))
        # Slowly-varying weather shock (updated every 6 hours)
        if tod % 6 == 0:
            phase = (new_state.day_counter * 24 + tod) * 0.37
            new_state.external_weather["temp_shift"] = float(4.0 * np.sin(phase))
        ambient_temp = base_ambient + new_state.external_weather.get("temp_shift", 0.0)
    else:
        # Easy: stable 18°C outside (mild, closer to optimal → smaller drift)
        ambient_temp = 18.0
        new_state.external_weather["temp_shift"] = 0.0

    # ========================================================================
    # 6. TEMPERATURE DYNAMICS
    #    Newton's law: T → T_ambient at rate 1/τ_wall (τ=12h → slow leak).
    #    HVAC can overcome this easily at moderate intensity.
    # ========================================================================
    prev_temp = new_state.temperature

    # Passive wall exchange — τ varies with difficulty (insulation quality)
    # Easy: 18h (new, well-insulated greenhouse)
    # Medium: 14h (average)
    # Hard: 10h (older structure, more heat loss)
    tau_wall = {"easy": 18.0, "medium": 14.0, "hard": 10.0}.get(difficulty, 14.0)
    wall_exchange = (ambient_temp - new_state.temperature) / tau_wall * dt

    # Day/night radiative balance (solar gain midday, radiative loss at night)
    if 6 <= tod <= 18:
        radiative = 0.5 * float(np.sin(np.pi * (tod - 6) / 12))  # up to +0.5°C/h
    else:
        radiative = -0.3                                           # −0.3°C/h at night

    # HVAC effects
    act_heat = heating    * constants.HEAT_POWER * dt          # +2.0°C/h max
    act_cool = -cooling   * constants.COOL_POWER * dt          # −1.5°C/h max

    # Ventilation: pulls interior temp proportionally toward ambient
    temp_diff = new_state.temperature - ambient_temp
    act_vent  = -ventilation * abs(temp_diff) / max(abs(temp_diff), 1.0) * 1.0 * dt

    # Evaporative cooling from humidifier misting
    act_mist  = -humidify * 0.15 * dt

    new_state.temperature = float(np.clip(
        new_state.temperature + wall_exchange + radiative + act_heat + act_cool + act_vent + act_mist,
        constants.TEMP_MIN, constants.TEMP_MAX,
    ))
    info["temperature_change"] = new_state.temperature - prev_temp

    # ========================================================================
    # 7. HUMIDITY DYNAMICS
    #    Sources: crop evapotranspiration (small, crop-driven).
    #    Sinks:   VPD effect (warm air is drier), ventilation (−2%/h max).
    #    Active:  humidifier (+8%/h), dehumidifier (−6%/h).
    #    Drift:   slow return toward 50% when undisturbed (τ=48h).
    # ========================================================================
    prev_humidity = new_state.humidity

    # Crop evapotranspiration: healthy crops transpire moisture into air
    light_opt    = crop_profile.get("light_optimal", 600.0)
    photo_factor = new_state.light_intensity / max(light_opt, 1.0)
    evapotrans   = new_state.crop_health * photo_factor * 0.8 * dt  # 0–0.8 %/h

    # VPD effect: warmer air drives higher vapour pressure deficit
    vpd_pull = -(new_state.temperature - 20.0) * 0.05 * dt

    # Slow equilibrium drift toward ~50% (represents passive moisture exchange)
    drift_eq = (50.0 - new_state.humidity) / 48.0 * dt

    # Actuator effects
    act_humid    =  humidify    * 8.0 * dt   # +8%/h at full intensity
    act_dehumid  = -dehumidify  * 6.0 * dt   # −6%/h at full intensity
    act_vent_hum = -ventilation * 2.0 * dt   # −2%/h at full (realistic, not −10%)

    new_state.humidity = float(np.clip(
        new_state.humidity + evapotrans + vpd_pull + drift_eq +
        act_humid + act_dehumid + act_vent_hum,
        constants.HUMIDITY_MIN, constants.HUMIDITY_MAX,
    ))
    info["humidity_change"] = new_state.humidity - prev_humidity

    # ========================================================================
    # 8. CO2 DYNAMICS
    #    Photosynthesis uptake (crop removes CO2 when lit and healthy).
    #    Ventilation flushes interior with outdoor air (400 ppm).
    #    CO2 enrichment injects up to 150 ppm/h.
    #    Slow ambient drift toward 400 ppm (τ=24h) when sealed.
    # ========================================================================
    photo_rate  = new_state.crop_health * photo_factor
    co2_uptake  = photo_rate   * 30.0  * dt   # up to 30 ppm/h at full health + light
    vent_co2    = -ventilation * 100.0 * dt   # flushes with outdoor 400 ppm air
    enrich_co2  = co2_enrich   * 150.0 * dt  # +150 ppm/h at full
    ambient_ex  = (400.0 - new_state.co2) / 24.0 * dt   # passive drift toward 400

    new_state.co2 = float(np.clip(
        new_state.co2 - co2_uptake + vent_co2 + enrich_co2 + ambient_ex,
        constants.CO2_MIN, constants.CO2_MAX,
    ))

    # ========================================================================
    # 9. WATER DYNAMICS — reservoir model
    #    Crops consume water via transpiration (proportional to health).
    #    Irrigation refills the reservoir directly.
    #    No artificial daily cap (finite tank is the natural limit).
    # ========================================================================
    water_req_per_hour = crop_profile.get("water_requirement", 2.5) / 24.0
    water_drain = water_req_per_hour * new_state.crop_health * dt    # slow, continuous
    water_add   = irrigation * constants.IRRIGATION_RATE * dt        # +3 units/h at full

    new_state.water_level = float(np.clip(
        new_state.water_level - water_drain + water_add,
        0.0, constants.WATER_CAPACITY,
    ))
    new_state.daily_water_added += water_add
    info["water_used"] = water_drain

    # ========================================================================
    # 10. CROP HEALTH — Gaussian stress kernel
    #
    #     stress(x, x_opt, σ) = 1 − exp(−½ × ((x − x_opt) / σ)²)
    #
    #     Combined stress = weighted sum (temp 35%, humidity 25%, CO2 20%, light 20%).
    #     Collision stress = punitive factor for fighting actuators.
    #
    #     Break-even stress ≈ 0.65 (before metabolic cost).
    # ========================================================================
    prev_health = new_state.crop_health

    T_opt   = crop_profile.get("temp_optimal",     22.0)
    RH_opt  = crop_profile.get("humidity_optimal", 65.0)
    co2_opt = crop_profile.get("co2_optimal",      900.0)
    L_opt   = crop_profile.get("light_optimal",    600.0)

    σ_T  = crop_profile.get("temp_stress_sigma",     4.0)
    σ_RH = crop_profile.get("humidity_stress_sigma", 15.0)
    σ_C  = crop_profile.get("co2_stress_sigma",      300.0)
    σ_L  = crop_profile.get("light_stress_sigma",    200.0)

    def _gauss_stress(val: float, opt: float, sigma: float) -> float:
        return float(1.0 - np.exp(-0.5 * ((val - opt) / sigma) ** 2))

    hs_T  = _gauss_stress(new_state.temperature,     T_opt,   σ_T)
    hs_RH = _gauss_stress(new_state.humidity,         RH_opt,  σ_RH)
    hs_C  = _gauss_stress(new_state.co2,              co2_opt, σ_C)
    hs_L  = _gauss_stress(new_state.light_intensity,  L_opt,   σ_L)

    # Actuator collision penalty (fighting heaters/coolers stresses the biological structure)
    collision_stress = (heating * cooling) * 0.2 + (humidify * dehumidify) * 0.1

    # Weighted combined stress [0, 1]
    combined_stress = float(np.clip(
        0.35 * hs_T + 0.25 * hs_RH + 0.20 * hs_C + 0.20 * hs_L + collision_stress,
        0.0, 1.0,
    ))
    info["stress_total"] = combined_stress

    # Growth / decay driven by combined stress
    growth_rate  = crop_profile.get("growth_rate", 0.015)
    health_grow  =  growth_rate * (1.0 - combined_stress) * dt   # + when conditions good
    health_decay = -combined_stress * 0.008 * dt                 # − proportional to stress

    # Real-world biological constraint: Metabolic maintenance cost
    # A crop naturally consumes energy just to stay alive (Natural Decay).
    metabolic_maintenance = -0.003 * dt

    # Proportional extreme-temperature damage (beyond crop-specific thresholds)
    cold_thresh = crop_profile.get("cold_damage_threshold", 10.0)
    heat_thresh = crop_profile.get("heat_stress_threshold", 34.0)
    extreme_dmg = 0.0

    if new_state.temperature < cold_thresh:
        excess      = cold_thresh - new_state.temperature          # °C below threshold
        extreme_dmg = -(excess / 10.0) * 0.03 * dt                # up to −0.03/h at 10°C below
    elif new_state.temperature > heat_thresh:
        excess      = new_state.temperature - heat_thresh
        extreme_dmg = -(excess / 10.0) * 0.02 * dt                # up to −0.02/h at 10°C above

    # Water stress (reservoir near empty)
    water_dmg = 0.0
    if new_state.water_level < 10.0:
        depletion = (10.0 - new_state.water_level) / 10.0         # 0→1 as water→0
        water_dmg = -depletion * 0.01 * dt

    # Mold damage
    mold_dmg = 0.0
    if new_state.mold_presence > 0.1:
        mold_dmg = -new_state.mold_presence * 0.015 * dt

    new_state.crop_health = float(np.clip(
        new_state.crop_health + health_grow + health_decay + metabolic_maintenance + extreme_dmg + water_dmg + mold_dmg,
        constants.CROP_HEALTH_MIN, constants.CROP_HEALTH_MAX,
    ))
    info["crop_health_change"] = new_state.crop_health - prev_health

    # ========================================================================
    # 11. MOLD DYNAMICS
    #    Grows only when warm (>25°C) AND humid (>80%).
    #    Ventilation suppresses mold.
    # ========================================================================
    mold_growth = 0.0
    if new_state.temperature > 25.0 and new_state.humidity > 80.0:
        mold_growth = 0.03 * dt   # +3% mold per hour when conditions ideal for mold

    mold_suppress = -ventilation * 0.05 * dt

    new_state.mold_presence = float(np.clip(
        new_state.mold_presence + mold_growth + mold_suppress,
        0.0, 1.0,
    ))

    return new_state, info


# ============================================================================
# INTERNAL CLAMP (kept for safety; main clamps are inline above)
# ============================================================================

def _clamp_state(state: GreenhouseState) -> GreenhouseState:
    """Clamp all state variables to physical limits."""
    state.temperature    = float(np.clip(state.temperature,    constants.TEMP_MIN,     constants.TEMP_MAX))
    state.humidity       = float(np.clip(state.humidity,       constants.HUMIDITY_MIN, constants.HUMIDITY_MAX))
    state.co2            = float(np.clip(state.co2,            constants.CO2_MIN,      constants.CO2_MAX))
    state.light_intensity= float(np.clip(state.light_intensity,constants.LIGHT_MIN,    constants.LIGHT_MAX))
    state.water_level    = float(np.clip(state.water_level,    0.0,                    constants.WATER_CAPACITY))
    state.energy_level   = float(np.clip(state.energy_level,   0.0,                    constants.ENERGY_CAPACITY))
    state.crop_health    = float(np.clip(state.crop_health,    constants.CROP_HEALTH_MIN, constants.CROP_HEALTH_MAX))
    state.mold_presence  = float(np.clip(state.mold_presence,  0.0, 1.0))
    return state
