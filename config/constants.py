"""
config/constants.py

Global constants and parameters for the greenhouse environment.
Defines all physical limits, control ranges, and default values.
"""

# ============================================================================
# ENVIRONMENTAL CONSTRAINTS
# ============================================================================

TEMP_MIN = 5.0           # Minimum safe temperature (°C)
TEMP_MAX = 40.0          # Maximum safe temperature (°C)
TEMP_OPTIMAL = 22.0      # Optimal growing temperature (°C)

HUMIDITY_MIN = 20.0      # Minimum relative humidity (%)
HUMIDITY_MAX = 95.0      # Maximum relative humidity (%)
HUMIDITY_OPTIMAL = 65.0  # Optimal growing humidity (%)

CO2_MIN = 200.0          # Minimum CO2 (ppm)
CO2_MAX = 2000.0         # Maximum CO2 (ppm)
CO2_OPTIMAL = 1000.0     # Optimal CO2 (ppm)

LIGHT_MIN = 0.0          # Minimum light intensity (µmol/m²/s)
LIGHT_MAX = 1000.0       # Maximum light intensity (µmol/m²/s)
LIGHT_OPTIMAL = 600.0    # Optimal light for crops (µmol/m²/s)

# ============================================================================
# CROP HEALTH AND RISKS
# ============================================================================

CROP_HEALTH_MIN = 0.0    # Dead
CROP_HEALTH_MAX = 1.0    # Thriving
CROP_HEALTH_INIT = 0.8   # Initial crop health

# Disease/stress thresholds
MOLD_TEMP_THRESHOLD = 25.0  # Mold risk above this temperature + high humidity
MOLD_HUMIDITY_THRESHOLD = 80.0  # Mold risk above this humidity
FREEZE_DAMAGE_THRESHOLD = 2.0   # Crop damage if below this temp
HEAT_STRESS_THRESHOLD = 35.0    # Heat stress above this temp

# ============================================================================
# RESOURCE CONSTRAINTS
# ============================================================================

WATER_CAPACITY = 100.0   # Maximum water in system (units)
WATER_INIT = 100.0       # Initial water level (starts optimal/full)

ENERGY_CAPACITY = 200.0  # Maximum energy/power budget (units)
ENERGY_INIT = 200.0      # Initial energy level (starts optimal/full)

# Daily resource limits
DAILY_WATER_LIMIT = 20.0   # Max water that can be added per day
DAILY_ENERGY_LIMIT = 30.0  # Max energy per day

# ============================================================================
# ACTION COSTS AND EFFECTS
# ============================================================================

# Heating/cooling costs (energy per degree adjustment)
HEATING_COST_PER_DEGREE = 0.5
COOLING_COST_PER_DEGREE = 0.6  # Cooling is more expensive

# Humidification/dehumidification
HUMIDIFY_COST = 2.0
DEHUMIDIFY_COST = 1.5

# Irrigation
IRRIGATION_WATER_AMOUNT = 5.0
IRRIGATION_ENERGY_COST = 0.5

# Lighting
LIGHTING_COST_PER_UNIT = 0.1  # Energy cost per unit of light intensity

# Ventilation
VENTILATION_COST = 1.0
VENTILATION_CO2_REDUCTION = 100.0  # CO2 reduction per time step

# ============================================================================
# TEMPORAL PARAMETERS
# ============================================================================

SIMULATION_STEP_HOURS = 1.0  # Each step = 1 hour
HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365

# External cycles
SUNRISE_HOUR = 6
SUNSET_HOUR = 18
DAY_LENGTH = SUNSET_HOUR - SUNRISE_HOUR  # Hours of daylight

# ============================================================================
# REWARD PARAMETERS
# ============================================================================

REWARD_CROP_HEALTH_WEIGHT = 1.0
REWARD_STABILITY_WEIGHT = 0.5      # Penalizes variance in conditions
REWARD_RESOURCE_COST_WEIGHT = 0.3  # Penalizes resource usage

PENALTY_MOLD = 10.0          # Penalty for mold detection
PENALTY_CROP_DEATH = 50.0    # Severe penalty for crop death
PENALTY_FREEZE_DAMAGE = 20.0 # Penalty for freeze damage

# ============================================================================
# EPISODE PARAMETERS
# ============================================================================

MIN_EPISODE_LENGTH = 100    # Minimum steps
MAX_EPISODE_LENGTH = 1000   # Maximum steps per episode
DEFAULT_EPISODE_LENGTH = 500  # Default episode length

# ============================================================================
# TASK SPECIFICATIONS
# ============================================================================

TASK_EASY_EPISODES = 10
TASK_EASY_LENGTH = 100

TASK_MEDIUM_EPISODES = 20
TASK_MEDIUM_LENGTH = 200

TASK_HARD_EPISODES = 30
TASK_HARD_LENGTH = 500
