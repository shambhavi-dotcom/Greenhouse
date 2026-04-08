"""
config/constants.py

Global constants and parameters for the greenhouse environment.
Defines all physical limits, control ranges, and default values.

Energy model (v2): Grid-connected with passive refill ("solar + grid").
  - energy_level = remaining capacity in the current charge window
  - Refills passively each step at difficulty-scaled rate
  - No daily hard cap — instead a soft brownout when energy_level = 0
"""

# ============================================================================
# ENVIRONMENTAL CONSTRAINTS
# ============================================================================

TEMP_MIN = 5.0           # Minimum safe temperature (°C)
TEMP_MAX = 40.0          # Maximum safe temperature (°C)
TEMP_OPTIMAL = 22.0      # Reference optimal (tomato) — use crop_profile for others

HUMIDITY_MIN = 20.0      # Minimum relative humidity (%)
HUMIDITY_MAX = 95.0      # Maximum relative humidity (%)
HUMIDITY_OPTIMAL = 65.0  # Reference optimal (tomato)

CO2_MIN = 200.0          # Minimum CO2 (ppm)
CO2_MAX = 2000.0         # Maximum CO2 (ppm)
CO2_OPTIMAL = 900.0      # Reference optimal

LIGHT_MIN = 0.0          # Minimum light intensity (µmol/m²/s)
LIGHT_MAX = 1000.0       # Maximum light intensity (µmol/m²/s)
LIGHT_OPTIMAL = 600.0    # Reference optimal

# ============================================================================
# CROP HEALTH AND RISKS
# ============================================================================

CROP_HEALTH_MIN = 0.0    # Dead
CROP_HEALTH_MAX = 1.0    # Thriving
CROP_HEALTH_INIT = 1.0   # Default initial crop health (Thriving preset)

# Danger thresholds (global fallback; crop_profile values take priority)
FREEZE_DAMAGE_THRESHOLD = 2.0    # Frost damage below this temp
HEAT_STRESS_THRESHOLD = 35.0     # Heat stress above this temp
MOLD_TEMP_THRESHOLD = 25.0       # Mold risk (needs high humidity too)
MOLD_HUMIDITY_THRESHOLD = 80.0   # Mold risk (needs high temp too)

# ============================================================================
# RESOURCE CONSTRAINTS
# ============================================================================

WATER_CAPACITY = 100.0   # Maximum water reservoir (units)
WATER_INIT = 100.0       # Initial water level

ENERGY_CAPACITY = 200.0  # Maximum energy storage / daily budget (units)
ENERGY_INIT = 200.0      # Initial energy level

# ============================================================================
# ACTUATOR ENERGY COSTS (units per hour at intensity = 1.0)
# Calibrated so realistic moderate use (~0.4 average) ~ 1.2 units/step
# Maximum possible (all at 1.0): 3.20 units/step
# ============================================================================

ACT_HEATING_ENERGY     = 0.30   # Heating coil / heat pump
ACT_COOLING_ENERGY     = 0.30   # Refrigeration / evaporative cooler
ACT_HUMIDIFY_ENERGY    = 0.80   # Steam humidifier (energy-intensive)
ACT_DEHUMIDIFY_ENERGY  = 0.60   # Desiccant / condensation unit
ACT_VENTILATION_ENERGY = 0.40   # Fan array
ACT_LIGHTING_ENERGY    = 0.20   # LED supplemental lighting
ACT_CO2_ENERGY         = 0.50   # CO2 generator / tank valve
ACT_IRRIGATION_ENERGY  = 0.10   # Water pumps (low draw)

# Sum of all above (all actuators at full intensity)
MAX_ENERGY_PER_STEP = (
    ACT_HEATING_ENERGY + ACT_COOLING_ENERGY + ACT_HUMIDIFY_ENERGY +
    ACT_DEHUMIDIFY_ENERGY + ACT_VENTILATION_ENERGY + ACT_LIGHTING_ENERGY +
    ACT_CO2_ENERGY + ACT_IRRIGATION_ENERGY
)   # = 3.20 units/step at intensity 1.0

# ============================================================================
# HVAC ACTUATOR POWER (physical effect per unit intensity per hour)
# ============================================================================

HEAT_POWER = 1.5    # Heater: +1.5°C/h at full intensity (calibrated so random agent ≈ 20°C)
COOL_POWER = 1.2    # Cooler: −1.2°C/h at full intensity

# ============================================================================
# ENERGY REFILL RATES  (units per step — "grid + solar" passive recharge)
#
#   Easy   : 5.0  — ~4× typical drain → effectively unlimited power
#   Medium : 2.0  — ~1.3× type. drain → need moderate efficiency
#   Hard   : 0.5  — ~0.3× type. drain → plan carefully or brownout
# ============================================================================

ENERGY_REFILL_EASY   = 5.0
ENERGY_REFILL_MEDIUM = 2.0
ENERGY_REFILL_HARD   = 0.5

ENERGY_REFILL_BY_DIFFICULTY = {
    "easy":   ENERGY_REFILL_EASY,
    "medium": ENERGY_REFILL_MEDIUM,
    "hard":   ENERGY_REFILL_HARD,
}

# ============================================================================
# WATER / IRRIGATION
# ============================================================================

IRRIGATION_RATE = 3.0    # Units of water added per hour at intensity 1.0

# ============================================================================
# TEMPORAL PARAMETERS
# ============================================================================

SIMULATION_STEP_HOURS = 1.0  # Each step = 1 simulated hour
HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365

SUNRISE_HOUR = 6
SUNSET_HOUR  = 18
DAY_LENGTH   = SUNSET_HOUR - SUNRISE_HOUR

# ============================================================================
# REWARD PARAMETERS
# ============================================================================

REWARD_CROP_HEALTH_WEIGHT  = 1.0   # Maps health [0,1] → component [−1,+1]
REWARD_STABILITY_WEIGHT    = 0.5   # Gaussian proximity bonus
REWARD_RESOURCE_COST_WEIGHT= 0.3   # Efficiency bonus (lower energy = higher)

PENALTY_MOLD         = 0.5    # Per unit of mold_presence > 0.5
PENALTY_CROP_DEATH   = 5.0    # Flat penalty when crop dies
PENALTY_FREEZE_DAMAGE= 1.0    # Flat penalty below freeze threshold

# ============================================================================
# EPISODE PARAMETERS
# ============================================================================

MIN_EPISODE_LENGTH = 100
MAX_EPISODE_LENGTH = 1000
DEFAULT_EPISODE_LENGTH = 500

# ============================================================================
# TASK SPECIFICATIONS
# ============================================================================

TASK_EASY_EPISODES   = 10
TASK_EASY_LENGTH     = 100

TASK_MEDIUM_EPISODES = 20
TASK_MEDIUM_LENGTH   = 200

TASK_HARD_EPISODES   = 30
TASK_HARD_LENGTH     = 500
