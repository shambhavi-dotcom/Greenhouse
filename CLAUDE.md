# CLAUDE.md: Greenhouse Environment System Documentation

**Last Updated:** April 2026  
**Project:** AI-Driven Greenhouse Operations Simulator  
**OpenEnv Compatibility:** Yes  

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Design Philosophy](#core-design-philosophy)
3. [State Definition](#state-definition)
4. [Action Space](#action-space)
5. [Environment Dynamics](#environment-dynamics)
6. [Reward Function](#reward-function)
7. [Task Design](#task-design)
8. [Grader Logic](#grader-logic)
9. [End-to-End Flow](#end-to-end-flow)
10. [File Interaction Map](#file-interaction-map)
11. [Execution Flow Diagram](#execution-flow-diagram)
12. [Design Decisions](#design-decisions)

---

## System Overview

### What is the Greenhouse Environment?

The greenhouse environment is a **sequential decision-making simulator** modeling real-world greenhouse operations. An AI agent controls multiple environmental systems (heating, cooling, irrigation, lighting, etc.) to achieve a compound objective:

**Maximize:** `crop_health + stability - resource_cost`

Over time, subject to constraints (energy budget, water supply, external weather).

### Why is this a Real-World Problem?

1. **Delayed Effects**: Heating takes time to warm the greenhouse; effects compound over multiple steps
2. **Coupled Dynamics**: Temperature affects humidity, which affects disease risk, which affects crop health
3. **Resource Constraints**: Energy and water are limited—overconsumption now starves future actions
4. **External Disturbances**: Weather changes unpredictably; agent must adapt
5. **Irreversible Damage**: Crop death, mold infection, freeze damage cannot be directly reversed
6. **Multi-Objective Tradeoffs**: Must balance health vs. cost efficiently

### Problem Complexity

- **State Space:** Continuous, 10-dimensional
- **Action Space:** Continuous, 8-dimensional (parameterized action intensities)
- **Time Horizon:** Up to 500 steps per episode (~20 simulated days)
- **Stochasticity:** External weather varies; disease risk depends on conditions
- **Observation Type:** Fully observable (agent sees all state variables)
- **Reward Sparsity:** Dense reward signal (computed at every step)

**This is NOT:**
- A simple control problem (state is not linear; effects are delayed/coupled)
- A reference tracking problem (no fixed setpoint; objective is to maximize compound reward)
- A toy problem (real greenhouses operate under exactly these constraints)

---

## Core Design Philosophy

### Why Sequential Decision-Making and Not Simple Control?

**Simple Control Assumption:** "Set temperature to 22°C and forget."

**Reality:**
- External weather changes continuously (morning cold → afternoon hot)
- Resource budget is finite (can't heat and cool simultaneously all day)
- Crop health depends on stability AND resource availability
- Wrong actions now limit options later (exhausted energy budget)

**Sequential Decision-Making:**
- Agent must **continuously decide** which actions to take at each time step
- Decisions are **coupled across time** (today's water use limits tomorrow's irrigation)
- Agent must **plan ahead** to stay within resource budgets
- Agent must **adapt** to unforeseen external changes
- History matters: actions at t=0 affect what's possible at t=100

**Example Scenario:**
```
Step 1-50 (Night):  Heat the greenhouse, conserve water  → healthy start
Step 51-100 (Day):  Cool from morning warmth, water crops  → maintain
Step 101-150:       External cold snap arrives           → rapid adaptation needed
Step 151-200:       Recover health while managing costs  → resource allocation tradeoff
```

An agent that can't plan loses on efficiency. An agent that can't adapt dies.

### Why Three Graduated Tasks?

Tasks have **increasing complexity** to force the agent to develop progressively sophisticated behaviors:

| Task      | Challenge | What Agent Must Learn |
|-----------|-----------|----------------------|
| **Easy**  | Static env | Basic control + state understanding |
| **Medium**| Weather    | Reactive adaptation + prediction |
| **Hard**  | Resources  | Planning + tradeoff optimization |

This mirrors the **transfer learning** pattern: task A acclimates you to task B.

---

## State Definition

### State Variables (10-Dimensional)

The environment tracks these variables at each time step:

#### 1. **Temperature** (°C)
- **Range:** 5°C (lethal cold) to 40°C (lethal heat)
- **Optimal:** 22°C (for tomato)
- **Why it matters:** Affects crop growth rate, disease risk, energy consumption
- **Updated by:** Heating/cooling actions, external weather, day/night cycle
- **Dynamics:** Naturally decays toward ambient temperature + radiative effects

#### 2. **Humidity** (%)
- **Range:** 20% to 95%
- **Optimal:** 65% (for tomato)
- **Why it matters:** Affects disease risk (mold > 80%), transpiration rate
- **Updated by:** Humidification/dehumidification, crop transpiration, ventilation
- **Dynamics:** Couples with temperature (warmer air can hold more moisture)

#### 3. **CO2** (ppm)
- **Range:** 200 ppm (dangerously low) to 2000 ppm (excess)
- **Optimal:** 900-1000 ppm (for tomato)
- **Why it matters:** Directly affects photosynthesis rate and crop growth
- **Updated by:** Plant uptake, ventilation, CO2 enrichment
- **Dynamics:** Reduces when plants photosynthesize; increases with enrichment

#### 4. **Light Intensity** (µmol/m²/s)
- **Range:** 0 (night) to 1000 (bright artificial lighting)
- **Optimal:** 600 µmol/m²/s (for tomato)
- **Why it matters:** Drives photosynthesis; primary energy input to crop
- **Updated by:** Sun position (day/night cycle), supplemental lighting
- **Dynamics:** Varies sinusoidally with time of day; can be artificially augmented

#### 5. **Water Level** (units)
- **Range:** 0 (depleted) to 100 (full tank)
- **Optimal:** maintaining between 30-80
- **Why it matters:** Crop viability; plants wilt if too dry
- **Updated by:** Irrigation (adds water), crop evapotranspiration (removes water)
- **Dynamics:** Decreases continuously due to crop uptake + ambient evaporation
- **Constraint:** Cannot exceed tank capacity; runs out at 0

#### 6. **Energy Level** (units)
- **Range:** 0 (no power) to 100 (full budget)
- **Optimal:** Maintain > 30 for active control
- **Why it matters:** Gating resource; every action costs energy
- **Updated by:** Solar input (day), all control actions (consume)
- **Dynamics:** Charges during the day; depletes with action intensity
- **Constraint:** Limited daily budget; hard stop at 0

#### 7. **Crop Health** (0.0–1.0)
- **Range:** 0.0 (dead) to 1.0 (thriving)
- **Optimal:** Maintain > 0.8 (healthy) or > 0.5 (surviving)
- **Why it matters:** Primary reward signal; measure of success
- **Updated by:** Growth under optimal conditions, decay under stress, disease, damage
- **Dynamics:** Increases under good conditions; crashes irreversibly under extremes
- **Terminal State:** If health ≤ 0, episode ends (crop died)

#### 8. **Mold Presence** (0.0–1.0)
- **Range:** 0.0 (none) to 1.0 (severe infection)
- **Optimal:** 0.0 (no mold)
- **Why it matters:** Disease reduces crop health; risk penalty in reward
- **Updated by:** Increases if temp > 25°C AND humidity > 80%; decreases with ventilation
- **Dynamics:** Accumulates over multiple steps if conditions remain bad
- **Risk:** Severely degrades crop quality and health

#### 9. **Time of Day** (0–23, hour)
- **Range:** 0 (midnight) to 23 (11 PM)
- **Why it matters:** Determines natural light availability, circadian effects
- **Updated by:** Increments each step (1 hour = 1 step)
- **Dynamics:** Cycles over 24 hours; resets to 0 after hour 23
- **Effect on Light:** Full light 6 AM–6 PM; zero else (unless supplemented)

#### 10. **Day Counter** (0+, day)
- **Range:** 0 (day 1) to ~30 (max ~30 days per episode)
- **Why it matters:** Long-term accumulation; tracks episode progress
- **Updated by:** Increments every 24 hours (when hour wraps 23→0)
- **Dynamics:** Only increases; never resets
- **Effect on Crop:** Older crops can grow more; disease risk increases over time

### State as Observation

The **observation** returned to the agent is the normalized state vector:

```python
observation = [
    temperature,           # normalized to typical range
    humidity,
    co2,
    light_intensity,
    water_level / capacity,  # normalized to [0, 1]
    energy_level / capacity,
    crop_health,  # already [0, 1]
    mold_presence,
    time_of_day / 24,  # normalized to [0, 1]
    day_counter / 365,  # normalized to [0, 1]
]
```

Shape: `(10,)` continuous array.

### Initial State

When `env.reset()` is called:
- Temperature: 20°C (neutral)
- Humidity: 60% (comfortable)
- CO2: 400 ppm (ambient)
- Light: 0 µmol/m²/s (night, or off)
- Water: 80 units (well-stocked)
- Energy: 80 units (good battery)
- Crop Health: 0.8 (healthy start)
- Mold: 0.0 (none)
- Time: 12 (noon)
- Day: 0

This represents a greenhouse at midday with healthy crops ready to grow.

---

## Action Space

### What is an Action?

An **action** is a control command sent to the greenhouse's actuators. It specifies:
- **What to control** (e.g., heating system)
- **How intensely** (0.0 = off, 1.0 = full power)

### Action Types (8 Categories)

The environment defines 8 independent continuous control dimensions:

#### 1. **Heating** (intensity ∈ [0, 1])
- **Effect:** Increases temperature
- **Max Effect per Step:** +2.0°C at full intensity
- **Energy Cost:** 0.5 × intensity
- **Physics:** Simulates heating elements, radiative warming

#### 2. **Cooling** (intensity ∈ [0, 1])
- **Effect:** Decreases temperature
- **Max Effect per Step:** -2.5°C at full intensity (more powerful than heating)
- **Energy Cost:** 0.6 × intensity (refrigeration is expensive)
- **Physics:** Simulates evaporative cooling, AC systems

#### 3. **Humidifying** (intensity ∈ [0, 1])
- **Effect:** Increases relative humidity
- **Max Effect per Step:** +5.0% per step at full intensity
- **Energy Cost:** 2.0 × intensity
- **Physics:** Simulates misting systems, fog generators

#### 4. **Dehumidifying** (intensity ∈ [0, 1])
- **Effect:** Decreases relative humidity
- **Max Effect per Step:** -8.0% per step (more effective than humidifying)
- **Energy Cost:** 1.5 × intensity
- **Physics:** Simulates dehumidifier units, condensation

#### 5. **Ventilation** (intensity ∈ [0, 1])
- **Effect:** Reduces CO2 concentration (air exchange)
- **Max Effect per Step:** -150 ppm CO2 reduction at full intensity
- **Energy Cost:** 1.0 × intensity
- **Side Effect:** Also reduces humidity, cools slightly
- **Physics:** Simulates fan ventilation, outdoor air intake

#### 6. **Irrigation** (intensity ∈ [0, 1])
- **Effect:** Supplies water to crops
- **Amount per Step:** 5.0 units of water at full intensity
- **Energy Cost:** 0.5 × intensity (pump power)
- **Constraint:** Cannot exceed available water in tank
- **Physics:** Simulates drip irrigation, watering systems

#### 7. **Lighting** (intensity ∈ [0, 1])
- **Effect:** Supplemental grow lights (µmol/m²/s)
- **Max Effect per Step:** +500 µmol/m²/s at full intensity
- **Energy Cost:** 0.1 × intensity (per unit of light intensity)
- **Benefit:** Extends productive daylight hours artificially
- **Physics:** Simulates LED grow lights, spectrum-optimized

#### 8. **CO2 Enrichment** (intensity ∈ [0, 1])
- **Effect:** Adds CO2 to the air
- **Max Effect per Step:** +200 ppm at full intensity
- **Energy Cost:** 1.5 × intensity (compressor/delivery system)
- **Benefit:** Boosts photosynthesis beyond outdoor ambient
- **Physics:** Simulates CO2 injection, bottled gas delivery

### Action Space Representation

- **Type:** Continuous, Box space
- **Shape:** `(8,)` — one dimension per control type
- **Bounds:** Each element ∈ [0.0, 1.0]
- **Semantics:** Each element is an **intensity** (0 = off, 1 = max power)

**Example Actions:**
```python
action = [0.5, 0.0, 0.3, 0.0, 0.2, 1.0, 0.0, 0.0]
# Interpretation:
# - Half-power heating, no cooling
# - 30% humidification, no dehumidification
# - 20% ventilation, full irrigation
# - No lighting, no CO2 enrichment
```

### Action Composition

**Important:** Multiple actions can be active simultaneously. For example:
- Heating + ventilation both at partial intensity is valid
- The agent must decide which combinations are efficient

This creates **tradeoffs**:
- Heating costs energy but improves temp
- Ventilation also changes humidity and CO2
- Irrigation costs both water and energy
- Decisions are coupled across systems

### Action Constraints

1. **Energy Constraint:** Total energy consumption per step ≤ available energy
2. **Water Constraint:** Irrigation amount ≤ available water in tank
3. **Mutual Exclusivity (Soft):** Heating and cooling simultaneously are wasteful but allowed
4. **Physical Limits (Hard):** No action can push state beyond global min/max bounds

---

## Environment Dynamics

### Overview

**Dynamics** describes how the state evolves in response to actions and external factors. This is the **physics simulation** of the greenhouse.

The core function is:

```python
def apply_dynamics(
    state: GreenhouseState,
    actions: list[Action],
    crop_profile: dict,
    dt: float = 1.0,  # 1 hour per step
) -> Tuple[GreenhouseState, dict]:
    """Apply one time step of simulation."""
```

### Time Scale

- **1 step** = 1 hour of simulated time
- **24 steps** = 1 day
- **500 steps** = ~20 days (typical episode)
- **Real-time correspondence:** 1 hour simulation ≈ instant decision

### Key Principles

1. **Physical Realism:** Variables decay toward equilibrium, not instantly
2. **Coupling:** Changes in one variable affect others (temp ↔ humidity)
3. **Delayed Effects:** Actions take multiple steps to reach full effect
4. **Nonlinearity:** Effects depend on current state (heating is harder when cold outside)
5. **Irreversibility:** Crop death and damage are permanent within an episode

### Detailed Dynamics for Each State Variable

#### Temperature Dynamics

**Differential Equation (Conceptual):**
```
dT/dt = (T_ambient - T) / τ + heating_effect - cooling_effect - ventilation_cooling
```

**Components:**

1. **Natural Decay Toward Ambient:**
   - Temperature naturally drifts toward external ambient temperature
   - Time constant τ depends on greenhouse insulation (typically 2-4 hours)
   - Formula: `T_change = -(T_current - T_ambient) / 4.0 * dt`

2. **External Weather (Task-Dependent):**
   - Easy task: T_ambient = 15°C (constant)
   - Medium task: T_ambient cycles 10°C (night) to 25°C (day)
   - Hard task: T_ambient includes random swings ±5°C every 4 hours
   - Formula: `T_ambient = base_temp + weather_disturbance`

3. **Day/Night Radiative Effects:**
   - During day (6 AM–6 PM): +0.5°C/hour natural solar heating
   - During night (6 PM–6 AM): -0.3°C/hour radiative cooling
   - Formula: applied to natural_change above

4. **Heating Action:**
   - Linear effect: `ΔT_heat = heating_intensity × 2.0°C`
   - Costs energy: `energy_cost = heating_intensity × 0.5`
   - Clamped: `T_new ≤ TEMP_MAX`

5. **Cooling Action:**
   - Linear effect: `ΔT_cool = -cooling_intensity × 2.5°C`
   - Costs energy: `energy_cost = cooling_intensity × 0.6`
   - Clamped: `T_new ≥ TEMP_MIN`

6. **Ventilation Side Effect:**
   - Opening vents cools via air exchange: `ΔT = -ventilation_intensity × 0.5°C`
   - Also reduces humidity (coupled effect)

**Example Trajectory:**
```
t=0:  T=22°C, action=[0.0, 0.0, ...] (no heating/cooling)
t=1:  T=21.5°C (natural decay toward ambient 15°C)
t=2:  T=21.0°C
...
t=10: T≈16°C (would reach 15°C if no intervention)

If agent applies heating at t=10: [0.5, 0.0, ...]
t=11: T = 16°C + (15-16)/4 + 0.5×2.0 = 16.75°C (fights decay, heats)
```

#### Humidity Dynamics

**Key Insight:** Humidity depends on temperature (warm air can hold more moisture).

**Components:**

1. **Evapotranspiration (Crop Transpiration):**
   - Crops release water vapor
   - Rate depends on: temperature (faster when warm), crop health, light intensity
   - Formula: `evapotranspiration_rate = crop_health × (T - 15) × light_intensity / 1000`
   - Effect: `Δhum = -evapotranspiration_rate × dt`

2. **Temperature-Humidity Coupling:**
   - When temperature rises, relative humidity falls (same absolute moisture in warmer air)
   - Formula: `Δhum = -(ΔT / 5.0) × (current_humidity - 50)` (proportional to departure from 50%)

3. **Saturation Constraint:**
   - Humidity naturally caps at 95% (saturated air)
   - If humidity > 95%, water condenses (passive dehumidification)
   - Formula: `if humidity > 95: humidity = 95`

4. **Humidification Action:**
   - Adds moisture directly: `Δhum = +humidify_intensity × 5.0%`
   - Costs energy: `energy_cost = humidify_intensity × 2.0`
   - Effect capped at 95%

5. **Dehumidification Action:**
   - Removes moisture: `Δhum = -dehumidify_intensity × 8.0%`
   - Costs energy: `energy_cost = dehumidify_intensity × 1.5`
   - Effect capped at humidity_min

6. **Ventilation Effect:**
   - Opening vents exchanges indoor humid air for outdoor air
   - Effect depends on outdoor humidity; typical reduction: -10% per step
   - Formula: `Δhum = -ventilation_intensity × 10.0`

**Example Trajectory:**
```
Initial: T=20°C, humidity=70%
Heat by 5°C (no water added):
  New T=25°C
  Coupling effect: Δhum = -(25-20)/5 × (70-50) = -20%
  New humidity = 50% (warmer air is drier for same absolute moisture)

Then humidify at full intensity:
  Δhum = +5.0%
  New humidity = 55%
```

#### CO2 Dynamics

**Components:**

1. **Plant Uptake:**
   - Photosynthesis consumes CO2
   - Rate depends on: light intensity, crop health, temperature
   - Formula: `uptake = crop_health × light_intensity × (1 - 0.5×temp_stress)`
   - Where `temp_stress = |T - optimal_T| / 10`
   - Effect: `Δco2 = -uptake × dt / 30`

2. **Ambient CO2 Exchange:**
   - Without ventilation, CO2 drifts toward 400 ppm (outdoor)
   - Formula: `Δco2 = -(co2 - 400) / 20 * dt` (slow decay)

3. **Ventilation Effect:**
   - Rapidly exchanges indoor CO2 with outdoor (400 ppm)
   - Formula: `Δco2 = -ventilation_intensity × 150 ppm`
   - Immediate effect (not gradual)

4. **CO2 Enrichment Action:**
   - Direct CO2 injection: `Δco2 = +enrichment_intensity × 200 ppm`
   - Costs energy: `energy_cost = enrichment_intensity × 1.5`

**Example:**
```
Initial: CO2=400 ppm, light=0 (night), health=0.8
Step 1 (night, no uptake):
  Uptake ≈ 0 (no light)
  Ambient exchange: ≈ 0 (already at 400)
  New CO2 ≈ 400

Step 12 (noon, light=600):
  Uptake = 0.8 × 600 × 1.0 / 30 ≈ 16 ppm reduction
  New CO2 ≈ 384

If ventilate at intensity 1.0:
  Δco2 = -150 ppm
  New CO2 ≈ 234 (drops fast)
```

#### Light Intensity Dynamics

**Components:**

1. **Solar Cycle:**
   - Base natural light varies with time of day
   - Formula: `natural_light = 600 × max(0, sin(π × (hour - 6) / 12))` for hours 6-18
   - Peaks at 600 µmol/m²/s at noon; zero outside daylight hours

2. **Supplemental Lighting:**
   - Agent adds grow lights: `Δlight = +lighting_intensity × 500`
   - Costs energy: `energy_cost = lighting_intensity × 0.1 × resulting_light`

3. **Clamping:**
   - Light is clamped to 0-1000 µmol/m²/s

**Example:**
```
Hour 12 (noon): natural_light = 600 µmol/m²/s
If no supplemental: light = 600

If lighting_intensity = 0.4:
  supplemental = 0.4 × 500 = 200
  total = 600 + 200 = 800 µmol/m²/s
  energy_cost = 0.1 × 800 = 80 units (expensive!)

Hour 22 (night): natural_light = 0
If lighting_intensity = 1.0:
  total = 0 + 500 = 500 µmol/m²/s
  energy_cost = 0.1 × 500 = 50 units
```

#### Water Level Dynamics

**Components:**

1. **Crop Evapotranspiration:**
   - Crops consume water (both soil uptake + leaf transpiration)
   - Formula: `consumption = crop_health × (1 + temperature_factor) × light_factor`
   - Where `temperature_factor = |T - optimal_T| / 20` (more consumption at extremes)
   - Where `light_factor = light_intensity / 600` (more consumption in sun)
   - Effect: `Δwater = -consumption × dt`

2. **Ambient Evaporation:**
   - Water naturally evaporates (very slow)
   - Formula: `Δwater = -0.1 × dt` (negligible, ~0.1 units/hour)

3. **Irrigation Action:**
   - Agent supplies water: `Δwater = +irrigation_intensity × 5.0`
   - Constraint: `new_water ≤ WATER_CAPACITY (100 units)`
   - Costs energy: `energy_cost = irrigation_intensity × 0.5`

4. **Minimum/Maximum Bound:**
   - Water clamped to [0, 100] unit range

**Example:**
```
Initial water = 80 units
Crop health = 0.8, T=22°C (optimal), light=600

Base consumption = 0.8 × (1 + 0) × (600/600) = 0.8 units/hour
After 1 hour: water = 80 - 0.8 = 79.2 units

If T rises to 30°C:
  consumption = 0.8 × (1 + 8/20) × 1.0 = 1.12 units/hour
After 1 hour: water = 79.2 - 1.12 = 78.08 units (heat stress increases consumption)

If irrigate at intensity 1.0:
  Δwater = +5.0
  water = 78.08 + 5.0 = 83.08 units
```

#### Energy Level Dynamics

**Components:**

1. **Baseline Energy Production:**
   - Solar panels produce energy during day
   - Formula: `production = 30 × light_intensity / 600`
   - Maximum: ~30 units/hour during peak sun (60 units/day)
   - At night: 0 production

2. **Action Energy Costs:**
   - Every action costs energy (see action descriptions above)
   - Total cost = sum of all action costs
   - Formula: `total_cost = Σ(action_cost_i)`

3. **Net Energy Update:**
   - Formula: `Δenergy = production - total_cost`
   - Clamped: `new_energy ∈ [0, 100]`

**Example:**
```
Noon (hour 12):
  light = 600 µmol/m²/s
  production = 30 × 600/600 = 30 units
  
Agent takes action: [0.3, 0.0, 0.2, 0.0, 0.1, 0.5, 0.0, 0.0]
  costs: heating (0.3×0.5=0.15) + humidify (0.2×2=0.4) + vent (0.1×1=0.1) + irrigation (0.5×0.5=0.25)
  total_cost = 0.9 units
  
net = 30 - 0.9 = 29.1 units gained
if energy was 50: new_energy = 50 + 29.1 = 79.1 units
```

#### Crop Health Dynamics

**Components:**

1. **Base Growth (Optimal Conditions):**
   - When conditions are near-optimal, crop health grows
   - Formula: `growth = profile.growth_rate × growth_modifier`
   - Where `growth_modifier = exp(-condition_deviation / scale)`
   - Scale depends on how far off-optimal (temperature, humidity, CO2, light all matter)
   - Typical: +0.015 health per hour under optimal conditions

2. **Stress Penalties:**
   - Temperature stress: if |T - optimal_T| > 5°C, health decays
   - Humidity stress: if humidity outside range [60%, 80%], decay
   - CO2 stress: if CO2 < 400 or > 1500, decay
   - Light stress: if light < 200 µmol/m²/s (insufficient photosynthesis), decay
   - Water stress: if water_level < 20 units, severe decay

3. **Disease Impact:**
   - If mold_presence > 0.5, health decay proportional to mold
   - Formula: `Δhealth_disease = -mold_presence × 0.01`

4. **Irreversible Catastrophic Damage:**
   - Freeze damage: if T < 2°C, immediate -0.2 health (can't reverse)
   - Heat damage: if T > 35°C, immediate -0.1 health (can't reverse)
   - Severe dehydration: if water < 5 units AND health < 0.5, death (health → 0)

**Example:**
```
State: T=22°C (optimal), humidity=65% (optimal), CO2=1000 (optimal), 
       light=600 (optimal), water=50 (adequate), health=0.8

All conditions optimal:
  condition_deviation ≈ 0
  growth ≈ 0.015 / hour = 0.36 / day
  After 1 day: health ≈ 0.836

But if temperature drifts to 28°C (not terrible, but warm):
  deviation = |28-22| = 6
  growth_modifier = exp(-6 / 5) ≈ 0.3
  growth ≈ 0.015 × 0.3 = 0.0045 / hour = 0.11 / day
  After 1 day: health ≈ 0.811 (still growing, just slower)

If temperature reaches 35°C:
  catastrophic_damage: -0.1 instantly
  health = 0.8 - 0.1 = 0.7
  Cannot recover the 0.1 in this episode
```

#### Mold Presence Dynamics

**Components:**

1. **Mold Growth (Favorable Conditions):**
   - Mold thrives when: T > 25°C AND humidity > 80%
   - Formula: `Δmold_growth = 0.05 / hour` when favorable
   - Accumulates over time: mold ∈ [0, 1]

2. **Mold Suppression (Ventilation):**
   - Ventilation creates air flow that inhibits/kills mold
   - Formula: `Δmold_suppression = -ventilation_intensity × 0.1`

3. **Mold Impact on Health:**
   - High mold presence (> 0.5) causes crop damage
   - Health damage: `Δhealth = -mold_presence × 0.01 / hour`

**Example:**
```
Hours 1-3 (T=26°C, humidity=85%, no ventilation):
  Each hour: Δmold = +0.05
  After 3 hours: mold = 0.15 (infection starting)

Hours 4-10 (still warm/humid, no intervention):
  Each hour: Δmold = +0.05
  After 10 hours total: mold = 0.50 (moderate infection)
  
At hour 10, health starts declining:
  health_loss = -0.5 × 0.01 = -0.005 / hour
  Over 10 hours: health loss ≈ -0.05

If ventilation applied at full intensity:
  Δmold = +0.05 * 0 (no growth, conditions not always favorable) - 0.1 = -0.05
  Mold decreases each step until cleared
```

### Summary: Full State Update

The complete update in pseudocode:

```python
def apply_dynamics(state, actions, crop_profile, dt=1):
    new_state = state.copy()
    
    # 1. UPDATE TIME
    new_state.time_of_day = (new_state.time_of_day + int(dt)) % 24
    if new_state.time_of_day == 0:
        new_state.day_counter += 1
    
    # 2. GET EXTERNAL WEATHER (task-dependent)
    external_weather = get_weather(new_state.day_counter, task_difficulty)
    
    # 3. UPDATE TEMPERATURE
    new_state.temperature += compute_temperature_delta(
        state, actions, external_weather, dt
    )
    
    # 4. UPDATE HUMIDITY
    new_state.humidity += compute_humidity_delta(
        state, new_state.temperature, actions, dt
    )
    
    # 5. UPDATE LIGHT
    new_state.light_intensity = compute_light(
        new_state.time_of_day, actions
    )
    
    # 6. UPDATE CO2
    new_state.co2 += compute_co2_delta(
        state, new_state.light_intensity, actions, dt
    )
    
    # 7. UPDATE WATER
    new_state.water_level += compute_water_delta(
        state, new_state.temperature, new_state.light_intensity, actions, dt
    )
    
    # 8. UPDATE ENERGY
    energy_produced = compute_energy_production(new_state.light_intensity, dt)
    energy_consumed = sum(action.cost for action in actions)
    new_state.energy_level += energy_produced - energy_consumed
    
    # 9. UPDATE CROP HEALTH
    new_state.crop_health += compute_health_delta(
        state, new_state, crop_profile, dt
    )
    
    # 10. UPDATE MOLD
    mold_delta = compute_mold_delta(
        new_state.temperature, new_state.humidity, 
        new_state.crop_health, actions, dt
    )
    new_state.mold_presence += mold_delta
    
    # 11. CLAMP ALL VALUES
    new_state = clamp_state(new_state)
    
    # 12. CHECK FOR CATASTROPHIC DAMAGE
    if new_state.temperature < FREEZE_DAMAGE_THRESHOLD:
        new_state.crop_health -= 0.1  # Irreversible damage
    if new_state.temperature > HEAT_DAMAGE_THRESHOLD:
        new_state.crop_health -= 0.05  # Irreversible damage
    
    return new_state, info_dict
```

---

## Reward Function

### Objective

The agent's goal is to maximize:

$$R = \alpha \cdot \text{crop\_health} + \beta \cdot \text{stability} - \gamma \cdot \text{resource\_cost} - \text{penalties}$$

Where:
- $\alpha = 1.0$ (weight on crop health)
- $\beta = 0.5$ (weight on environmental stability)
- $\gamma = 0.3$ (weight on resource cost)
- Penalties are task-specific

### Component Breakdown

#### 1. Crop Health Component

$$R_{\text{health}} = \text{crop\_health} \times \alpha$$

- Direct measure of how thriving the crop is at current step
- Ranges from 0 (dead) to 1 (fully thriving)
- Encourages maintaining high health
- Weight: $\alpha = 1.0$ (primary objective)

#### 2. Health Improvement Bonus

$$R_{\text{improvement}} = \Delta \text{health} \times 2.0 \quad \text{if } \Delta \text{health} > 0$$

- Multiplicative bonus if health improved this step
- Encourages active good management
- Accelerates learning of beneficial behaviors
- Not penalized if health decays (but captured in base reward)

#### 3. Stability Component

$$R_{\text{stability}} = -(\text{ΔT}^2 + 0.5 \times \text{ΔHumidity}^2) \times \beta$$

Where ΔT and ΔHumidity are changes from previous step.

- Penalizes large swings in temperature/humidity
- Encourages smooth, stable control
- Reflects reality: stable conditions are less stressful for crops
- Weight: $\beta = 0.5$ (important but secondary)

**Rationale:** A controller that heats +5°C then cools -5°C each step wastes energy and stresses crops, even if average stays constant.

#### 4. Resource Cost Component

$$R_{\text{resource}} = -(\text{energy\_used} \times 0.05 + \text{water\_used} \times 0.02) \times \gamma$$

- Penalizes resource consumption at each step
- Encourages efficiency (equivalent crop health with lower resource use = higher reward)
- Weight: $\gamma = 0.3$ (meaningful but not dominant)

**Rationale:** An infinite-energy agent could maintain perfect conditions at high cost. Efficient agents find the best tradeoff.

#### 5. Mold Penalty

$$P_{\text{mold}} = -10.0 \times \mathbb{1}[\text{mold\_presence} > 0.5]$$

- Applied only if mold infection is detected (> 0.5 presence)
- Flat penalty of -10 units when triggered
- Strongly discourages mold proliferation
- Amount: 10.0 units

#### 6. Freeze Damage Penalty

$$P_{\text{freeze}} = -20.0 \times \mathbb{1}[T < 2°\text{C}]$$

- Applied when temperature drops below freeze threshold
- Penalizes system failure to prevent crop freezing
- Larger penalty (-20) than mold (-10) because damage is irreversible
- Amount: 20.0 units

#### 7. Heat Stress Penalty

$$P_{\text{heat}} = -0.5 \times \max(0, T - 35°\text{C})$$

- Proportional penalty for severe heat
- Not binary; scales with excess temperature
- Encourages staying below high-stress threshold

#### 8. Crop Death Penalty

$$P_{\text{death}} = -50.0 \times \mathbb{1}[\text{crop\_health} = 0]$$

- Applied when crop dies (health ≤ 0)
- Severe penalty (-50) to terminate failure episodes quickly
- Ensures agent learns to prevent death above all else

### Total Reward Computation

```python
def compute_reward(prev_state, new_state, action_info):
    r_health = new_state.crop_health * 1.0
    
    health_delta = new_state.crop_health - prev_state.crop_health
    if health_delta > 0:
        r_improvement = health_delta * 2.0
    else:
        r_improvement = 0.0
    
    temp_delta = abs(new_state.temperature - prev_state.temperature)
    humidity_delta = abs(new_state.humidity - prev_state.humidity)
    r_stability = -(temp_delta**2 + 0.5 * humidity_delta**2) * 0.5
    
    energy_used = action_info["energy_used"]
    water_used = action_info["water_used"]
    r_resource = -(energy_used * 0.05 + water_used * 0.02) * 0.3
    
    p_mold = -10.0 if new_state.mold_presence > 0.5 else 0.0
    p_freeze = -20.0 if new_state.temperature < 2.0 else 0.0
    p_heat = -0.5 * max(0, new_state.temperature - 35.0)
    p_death = -50.0 if new_state.crop_health <= 0 else 0.0
    
    total = (r_health + r_improvement + r_stability + r_resource + 
             p_mold + p_freeze + p_heat + p_death)
    
    return {
        "total": total,
        "component_health": r_health,
        "component_improvement": r_improvement,
        "component_stability": r_stability,
        "component_resource": r_resource,
        "penalty_mold": p_mold,
        "penalty_freeze": p_freeze,
        "penalty_heat": p_heat,
        "penalty_death": p_death,
    }
```

### Reward Scaling

Typical reward ranges per step:

| Scenario | Reward Range |
|----------|--------------|
| **Perfect management (health 0.9, stable, low resource)** | +0.8 to +1.2 |
| **Good management (health 0.7, slight swings)** | +0.3 to +0.6 |
| **Poor management (health 0.5, big swings, high resource)** | -0.5 to 0.2 |
| **Catastrophic (health -> 0, mold, freeze)** | -60 to -70 |

Over a 500-step episode:
- **Perfect agent:** ~400-600 total reward
- **Good agent:** ~100-200 total reward
- **Poor agent:** -500 to -1000 total reward

### Episode Score

The **episode score** is simply the sum of rewards:

$$S_{\text{episode}} = \sum_{t=0}^{T} R_t$$

Where T is episode length (100-500 steps depending on task).

---

## Task Design

### Philosophy

Tasks escalate in difficulty to progressively challenge the agent:

1. **Easy:** Learn basics (state-action effects, feedback)
2. **Medium:** Adapt to changes (react in real-time)
3. **Hard:** Optimize under constraints (plan ahead)

Each task differs in:
- Environment dynamics (static vs. weather)
- Resource limits (unlimited vs. strict budgets)
- Episode length (short vs. long)
- Evaluation metrics (raw performance vs. efficiency)

---

### Easy Task: Stabilization

**Goal:** Maintain crop health through passive stabilization in a static environment.

**Environment Configuration:**
- No external weather disturbances (T_ambient = 15°C constant)
- No resource limits (water/energy always available)
- Crop: Tomato (standard profile)
- Episodes: 10
- Steps per Episode: 100 (≈ 4 days)

**Initial State:**
- Temperature: 20°C
- Humidity: 60%
- Crop Health: 0.8 (healthy start)
- All resources full

**Characteristics:**
- Dynamics are deterministic (no randomness)
- Agent's decisions have clear, predictable effects
- Can learn basic control policies without adaptation
- Success requires: maintain conditions near-optimal

**Challenges:**
1. Natural temperature decay (greenhouse cools down gradually)
2. Crop evapotranspiration (water consumption, humidity changes)
3. Multi-variable coupling (can't just hold temperature constant)
4. Trade-off between actions (heating costs energy, affects humidity, etc.)

**Success Criteria:**
- Final crop health > 0.7 (at least 70% of max health)
- Zero crop death
- Positive episode reward

**Grading (Easy):**
```
score_easy = 0.60 * health_score + 0.30 * success_rate + 0.10 * consistency

where:
  health_score = average(final_crops_healths) / 0.7 (clamped to [0, 1])
  success_rate = fraction of episodes with health > 0.7
  consistency = 1 - std(final_healths) / range(final_healths)
```

**Example Agent Behavior:**

*Good Agent:*
- Maintains temperature at 20-22°C (near optimal 22°C)
- Keeps humidity at 60-65% (near optimal 65%)
- Waters moderately (6-8 units total per day)
- Average final health: 0.82-0.85
- Easy Score: ~0.85

*Poor Agent:*
- Oscillates: heats to 25°C, cools to 18°C, repeats
- Humidity swings 40% → 80% → 40%
- Average final health: 0.65-0.70
- Easy Score: ~0.50

---

### Medium Task: Adaptation

**Goal:** Maintain crop health while adapting to external weather changes.

**Environment Configuration:**
- Weather disturbances introduced: T_amb varies ±5°C
- Weather changes every 4 hours (semi-predictable but not fully)
- Resource limits activate (finite water/energy budgets)
- Crop: Tomato
- Episodes: 20
- Steps per Episode: 200 (≈ 8 days)

**Initial State:** Same as Easy

**Characteristics:**
- **Non-stationary:** External conditions change unpredictably
- **Reactive Control:** Agent must react to disturbances in real-time
- **Resource Constraints:** Now matter (limited daily budget)
- **Longer Horizon:** More steps to plan with scarce resources

**Weather Model:**
```
base_temp = 15°C (always)
time_of_day_effect = 8 * sin(π * (hour - 6) / 12) for hours 6-18, else 0
  → ranges from 0°C (night) to +8°C (noon)
  → external temp varies 15°C (night) to 23°C (day)

random_disturbance = ±5°C shock every 4-6 hours
  → simulates cold fronts, heat waves, etc.
  → agent must react within 1-2 hours
```

**Challenges:**
1. **Prediction:** Weather is not random but not fully predictable either
2. **Adaptation:** Must change control strategy as conditions change
3. **Trade-offs:** Limited resources force choices (heat now or conserve for later?)
4. **Multiple Time Scales:** Fast weather changes vs. slow crop growth

**Success Criteria:**
- Final crop health > 0.6
- Resource efficiency: total_reward/resource_cost > threshold
- Positive episode reward

**Grading (Medium):**
```
score_medium = 0.50 * health_score + 0.30 * adaptation_score + 0.20 * success_rate

where:
  health_score = average(final_healths) / 0.6
  adaptation_score = (robust to disturbances while maintaining health)
    = 1 - (disturbance_magnitude * 0.5 - avg_health * 0.5)
  success_rate = fraction of episodes with health > 0.6 AND efficiency > threshold
```

**Example Agent Behavior:**

*Good Adaptive Agent:*
- Predicts weather patterns (day warms → night cools)
- Pre-heats before cold snap arrives
- Reduces heating when warming shock comes
- Manages water: heavy irrigation in cool periods, light during hot
- Average final health: 0.70-0.75
- Medium Score: ~0.75

*Reactive Agent:*
- Reacts after each weather change (always behind)
- Oscillates similarly to Easy task
- Depletes water early, struggles later
- Average final health: 0.55-0.60
- Medium Score: ~0.45

---

### Hard Task: Optimization

**Goal:** Maximize crop health AND resource efficiency under strict constraints and weather.

**Environment Configuration:**
- All constraints active (weather + resource limits)
- Daily water budget: 20 units/day max (must plan carefully)
- Daily energy budget: 30 units/day max
- Weather: Highly dynamic, includes unpredictable swings
- Crop: Tomato
- Episodes: 30
- Steps per Episode: 500 (≈ 20 days)

**Initial State:** Same as Easy/Medium

**Characteristics:**
- **Planning Horizon:** Long episodes require forward-looking decisions
- **Resource Scarcity:** Every action consumes limited resources
- **Multi-objective:** Trade health vs. cost; must find Pareto frontier
- **Uncertainty:** Weather and disease introduce variability

**Constraints:**

Daily Water Budget:
- 20 units available per day (renewable at midnight)
- Crops consume ~0.8-1.5 units/hour depending on conditions
- Over 24 hours: 19-36 units needed depending on heat/humidity
- Agent MUST be efficient or crops die of thirst

Daily Energy Budget:
- 30 units available per day (solar production only)
- Peak production at noon: ~30 units
- Night production: 0
- Every action costs energy (heating 0.5/unit intensity, cooling 0.6, etc.)
- Agent must balance: heating at night (no solar) vs. available budget

**Challenges:**
1. **Resource Planning:** Must allocate finite resources over 500 steps
2. **Delayed Consequences:** Depleting water today limits options tomorrow
3. **Weather Unpredictability:** Can't perfectly predict disturbances
4. **Multi-objective Trade-offs:**
   - Heat more? Uses energy, good for health but wasteful
   - Irrigate less? Saves water but stresses crops
   - Use lights? Boosts photosynthesis but very expensive

**Success Criteria:**
- Final crop health > 0.5 (minimum viability)
- Resource efficiency: health_gained / resources_spent > coefficient
- Episode reward > 0

**Grading (Hard):**
```
score_hard = 0.40 * health_score + 0.40 * efficiency_score + 0.20 * success_rate

where:
  health_score = average(final_healths) / 0.5
  efficiency_score = average(resource_efficiency) / 0.02
    resource_efficiency = final_health / (total_energy + total_water + ε)
  success_rate = fraction meeting health AND efficiency thresholds
```

**Example Agent Behavior:**

*Excellent Planner:*
- Uses natural patterns: minimal heating during day, moderate at night
- Water: Irrigates efficiently, accounting for temperature/humidity
- Lighting: Supplements at dusk/dawn, avoids noon excess
- Final health: 0.65-0.75
- Resource efficiency: 0.025-0.03
- Hard Score: ~0.80

*Greedy Agent:*
- Heats aggressively (wastes energy)
- Irrigates whenever water available
- Uses lights all night (excessive)
- Runs out of resources mid-episode
- Final health: 0.30-0.50
- Hard Score: ~0.35

---

## Grader Logic

### Purpose

The grader converts episode results → scores [0.0, 1.0].

Scores are:
- **Interpretable:** 0.0 = failure, 1.0 = perfect, 0.5 = mediocre
- **Comparable:** Can rank agents across tasks
- **Aligned with objectives:** High score ↔ good agent

### Grading Per-Task

#### Easy Task Grading

```python
def grade_easy_task(results: List[Dict]) -> float:
    """
    Criteria:
    1. High final crop health (60% of score)
    2. High success rate (30% of score)
    3. Consistent performance (10% of score)
    """
    
    health_scores = [min(h / 0.7, 1.0) for h in final_healths]
    health_score = mean(health_scores)  # 0.0-1.0
    
    success_score = fraction_with_health > 0.7  # 0.0-1.0
    
    consistency_score = 1 - (std / max_variance)  # 0.0-1.0
    
    return 0.60 * health_score + 0.30 * success_score + 0.10 * consistency_score
```

**Interpretation:**
- 0.90+: Excellent (health 0.8+, 100% success, consistent)
- 0.75-0.89: Good (health 0.75+, 90%+ success)
- 0.50-0.74: Fair (health variable, 70-90% success)
- < 0.50: Poor (health < 0.65, frequent failures)

#### Medium Task Grading

```python
def grade_medium_task(results: List[Dict]) -> float:
    """
    Criteria:
    1. Final crop health (50%)
    2. Adaptation robustness (30%)
    3. Success rate (20%)
    """
    
    health_score = mean([min(h / 0.6, 1.0) for h in final_healths])
    
    adaptation_score = 1 - (disturbance_magnitude - avg_health) * 0.5
    
    success_score = fraction_with_health > 0.6
    
    return 0.50 * health_score + 0.30 * adaptation_score + 0.20 * success_score
```

**Interpretation:**
- 0.85+: Excellent (health 0.6+, adapts well, rarely fails)
- 0.70-0.84: Good (health maintained despite disturbances)
- 0.50-0.69: Fair (health variable, moderate adaptation)
- < 0.50: Poor (reactive, not proactive)

#### Hard Task Grading

```python
def grade_hard_task(results: List[Dict]) -> float:
    """
    Criteria:
    1. Final crop health (40%)
    2. Resource efficiency (40%)
    3. Success rate (20%)
    """
    
    health_score = mean([min(h / 0.5, 1.0) for h in final_healths])
    
    efficiencies = [h / (e + w + ε) for h, e, w in episode
    efficiency_score = mean([min(eff / 0.02, 1.0) for eff in efficiencies])
    
    success_score = fraction meeting health AND efficiency
    
    return 0.40 * health_score + 0.40 * efficiency_score + 0.20 * success_score
```

**Interpretation:**
- 0.80+: Excellent (health 0.5+, efficiency 0.025+, planned well)
- 0.65-0.79: Good (health variable, reasonable efficiency)
- 0.50-0.64: Fair (efficiency poor OR health compromised)
- < 0.50: Poor (both health and efficiency fail)

### Overall Performance Score

```python
def grade_overall(easy_score, medium_score, hard_score):
    overall = (easy_score + medium_score + hard_score) / 3.0
    
    # Bonus for consistent performance
    if easy_score > 0.5 and medium_score > 0.5 and hard_score > 0.5:
        overall *= 1.05  # 5% bonus
    
    return clamp(overall, 0.0, 1.0)
```

**Interpretation:**
- Late 0.85+: World-class agent (strong across all tasks)
- 0.70-0.84: Competent (handles most scenarios)
- 0.50-0.69: Adequate (works in simple cases, struggles in hard)
- < 0.50: Struggling (learning needed)

---

## End-to-End Flow

### Full Episode Loop

```
1. INITIALIZATION
   ├─ Create environment (GreenhouseEnv)
   ├─ Set difficulty level (easy/medium/hard)
   ├─ Load crop profile (tomato/lettuce/herbs)
   └─ Initialize state with GreenhouseState()

2. RESET
   ├─ Call env.reset()
   ├─ Returns: obs (10D array), info (metadata)
   ├─ Agent receives: observation vector
   └─ State: temp=20, humid=60, health=0.8, time=12, day=0

3. STEP LOOP (repeat for 100-500 steps):
   │
   ├─ 3a. AGENT DECISION
   │  ├─ obs → agent.select_action(obs)
   │  ├─ Agent processes 10D observation
   │  ├─ Neural network (or heuristic) computes action
   │  └─ Returns: action ∈ [0,1]^8
   │
   ├─ 3b. ACTION EXECUTION
   │  ├─ env.step(action)
   │  ├─ action parsed into [heating, cooling, humidify, dehumidify, ...)
   │  ├─ Each action has intensity and energy cost
   │  └─ Water cost if irrigation included
   │
   ├─ 3c. DYNAMICS SIMULATION
   │  ├─ apply_dynamics(state, actions, crop_profile, dt=1 hour)
   │  ├─ Compute new temp (heating + cooling + ambient + weather)
   │  ├─ Compute new humidity (evapotranspiration + humidification + ...)
   │  ├─ Compute new CO2 (plant uptake + ventilation + enrichment)
   │  ├─ Compute new light (sun position + supplemental)
   │  ├─ Compute new water (consumption - irrigation)
   │  ├─ Compute new energy (production - costs)
   │  ├─ Update crop health (growth - stress - disease)
   │  ├─ Update mold presence (growth - suppression from ventilation)
   │  ├─ Increment time (hour += 1, day += 1 if hour wraps 23→0)
   │  └─ Check catastrophic damage (freeze, heat, death)
   │
   ├─ 3d. REWARD COMPUTATION
   │  ├─ compute_reward(prev_state, new_state, action_info)
   │  ├─ Reward = health + stability - cost - penalties
   │  ├─ Penalties for mold, freeze, heat, death
   │  └─ Agent receives: reward (scalar float)
   │
   ├─ 3e. TERMINATION CHECK
   │  ├─ terminated = (crop_health <= 0) OR (water_level = 0 AND energy = 0)
   │  ├─ truncated = (step_count >= max_steps)
   │  └─ done = terminated OR truncated
   │
   ├─ 3f. OBSERVATION UPDATE
   │  ├─ new_obs = state.to_array()
   │  ├─ Returns normalized 10D observation
   │  └─ Loop continues with new_obs
   │
   └─ Return: (new_obs, reward, terminated, truncated, info)

4. EPISODE TERMINATION
   ├─ When done = True:
   │  ├─ Compute episode summary:
   │  │  ├─ total_reward = sum(per_step_rewards)
   │  │  ├─ final_crop_health = state.crop_health
   │  │  ├─ episode_length = step_count
   │  │  ├─ resource_efficiency = health / (energy + water)
   │  │  └─ reason = CROP_DEATH | SYSTEM_FAILURE | MAX_STEPS
   │  │
   │  └─ Return: episode result dict

5. TASK EXECUTION
   ├─ Easy task: Run 10 episodes
   │  ├─ For ep in 1..10:
   │  │  └─ Run episode as above, store result
   │  ├─ Aggregate 10 results
   │  └─ Compute easy_score = grade_easy_task(results)
   │
   ├─ Medium task: Run 20 episodes (similar)
   │  ├─ env.include_weather = True (temperature varies)
   │  ├─ env.include_resource_limits = True (budgets enforced)
   │  └─ medium_score = grade_medium_task(results)
   │
   └─ Hard task: Run 30 episodes (similar)
      ├─ Both weather and resource limits active
      └─ hard_score = grade_hard_task(results)

6. OVERALL GRADING
   ├─ overall_score = (easy + medium + hard) / 3 * bonus
   ├─ Print grading report
   └─ Return: {easy: 0.X, medium: 0.Y, hard: 0.Z, overall: 0.W}
```

### Data Flow Diagram

```
Agent Logic
    ↓
    obs(10D)
    ↓
[Agent: neural network | heuristic]
    ↓
    action(8D) ∈ [0,1]^8
    ↓
Environment.step()
    ├─ Parse action → 8 control commands
    ├─ Compute resource costs
    ├─ Call apply_dynamics()
    │   ├─ Compute all delta for temp, humidity, CO2, light,
    │   │  water, energy, health, mold
    │   ├─ Clamp to physical limits
    │   └─ Check catastrophic conditions
    ├─ Call compute_reward()
    │   ├─ Sum component scores
    │   └─ Apply penalties
    ├─ Update state
    └─ Return: (new_obs, reward, terminated, truncated, info)
    ↓
    (obs, reward, done) → loop or terminate
```

---

## File Interaction Map

This section explains how files in the project interact. **Critical for understanding code structure.**

### File Dependencies

```
inference.py (TOP LEVEL - Entry point)
    ├─→ env/environment.py (Main environment)
    │   ├─→ env/state.py (State definition + methods)
    │   ├─→ env/actions.py (Action types + space)
    │   ├─→ env/dynamics.py (Physics simulation)
    │   │   └─→ config/constants.py (Physical parameters)
    │   ├─→ env/rewards.py (Reward computation)
    │   │   └─→ config/constants.py (Weight constants)
    │   └─→ config/crop_profiles.py (Crop-specific parameters)
    │
    ├─→ tasks/task_easy.py
    │   └─→ env/environment.py (uses GreenhouseEasyEnv)
    ├─→ tasks/task_medium.py  
    │   └─→ env/environment.py (uses GreenhouseMediumEnv)
    ├─→ tasks/task_hard.py
    │   └─→ env/environment.py (uses GreenhouseHardEnv)
    │
    └─→ tasks/graders.py (Scoring logic)
        (no dependencies - pure computation)

Config files (referenced by multiple modules):
├─→ config/constants.py (TEMP_OPTIMAL, EMOTION_MAX, etc.)
└─→ config/crop_profiles.py (TOMATO, LETTUCE, HERBS dicts)

Docker/deployment:
├─→ Dockerfile (packages everything)
├─→ requirements.txt (python dependency list)
├─→ openenv.yaml (environment metadata)
└─→ README.md (documentation)

CLAUDE.md (this file - comprehensive documentation)
```

### Key Classes and Their Roles

| File | Class | Purpose |
|------|-------|---------|
| `env/state.py` | `GreenhouseState` | Holds all state variables; methods to convert to/from arrays |
| `env/actions.py` | `Action` | Single action (type + intensity) |
| | `ActionSpace` | Manages all 8 action types; samples/validates actions |
| `env/environment.py` | `GreenhouseEnv` | Main gymnasium environment; orchestrates simulation |
| | `GreenhouseEasyEnv` | Easy task variant (static, no limits) |
| | `GreenhouseMediumEnv` | Medium task variant (weather, limits) |
| | `GreenhouseHardEnv` | Hard task variant (all constraints) |
| `env/dynamics.py` | `apply_dynamics()`| Simulates one time step (→ new state) |
| `env/rewards.py` | `compute_reward()` | Computes reward from state transition |
| `tasks/task_easy.py` | `EasyTask` | Orchestrates 10 easy episodes |
| `tasks/task_medium.py` | `MediumTask` | Orchestrates 20 medium episodes |
| `tasks/task_hard.py` | `HardTask` | Orchestrates 30 hard episodes |
| `tasks/graders.py` | `grade_easy_task()` | Converts easy results → score |
| | `grade_medium_task()` | Converts medium results → score |
| | `grade_hard_task()` | Converts hard results → score |
| | `grade_overall_performance()` | Combines 3 scores → overall |
| `inference.py` | `GreenhouseAgent` | Abstract agent interface |
| | `RandomAgent` | Baseline agent (random actions) |
| | `GreenhouseInference` | Main orchestrator: runs all tasks + scoring |

### Information Flow

**Forward (simulation):**
```
Agent decision (8D action)
    → GreenhouseEnv.step(action)
        → apply_dynamics(state, actions)
            |→ compute_temperature_delta() → uses constants
            |→ compute_humidity_delta()
            |→ compute_crop_health_delta() → uses crop_profile
            └→ ... (all 10 state variables)
        → compute_reward(prev_state, new_state)
            └→ uses reward weights from constants
        → clamp_state()
            └→ uses limits from constants
    → Return (obs, reward, done, info)
```

**Backward (grading):**
```
30 episodes of hard task
    → collect results [ep1, ep2, ..., ep30]
        └─ each result: {episode_return, final_health, efficiency, ...}
    → grade_hard_task(results)
        |→ compute health_score from final_healths
        |→ compute efficiency_score from resource costs
        └→ return scalar score ∈ [0.0, 1.0]

Combine all 3 scores:
    grade_overall_performance(easy_score, medium_score, hard_score)
        |→ average three scores
        |→ apply consistency bonus
        └→ return overall ∈ [0.0, 1.0]
```

### Critical Coupling Points

**Where bugs are likely:**

1. **State → Observation Mismatch**
   - `state.py.to_array()` must match observation_space in `environment.py`
   - If state has 11 variables but observation_space is (10,), error
   - **Fix:** Keep to_array() and observation_space in sync

2. **Action → Dynamics Mismatch**
   - `actions.py` defines 8 action types
   - `dynamics.py` must handle all 8
   - Missing action (e.g., CO2_ENRICHMENT not handled) → ignored
   - **Fix:** Make sure `apply_dynamics()` processes all 8

3. **Reward → Task Objective Mismatch**
   - Easy task: health score is primary
   - Hard task: efficiency score is crucial
   - If reward weights misaligned → wrong incentives
   - **Fix:** Verify reward components in constants.py

4. **Grading → Episode Results Mismatch**
   - Grader expects certain fields in result dict (final_crop_health, resource_efficiency, etc.)
   - If Task doesn't compute these → grader crashes or gets NaN
   - **Fix:** Ensure tasks compute all required metrics

### Example: Adding New Action Type

To add a new action (e.g., "shading" to reduce light):

1. **actions.py:** Add `SHADING = "shading"` to ActionType enum
2. **dynamics.py:** Handle in `apply_dynamics()`:
   ```python
   if action.action_type == ActionType.SHADING:
       new_state.light_intensity -= action.intensity * 300  # reduce light
       energy_cost = action.intensity * 0.2  # cheap
   ```
3. **environment.py:** Update `num_actions=9` (was 8)
4. **openenv.yaml:** Add shading to action description
5. **config/constants.py:** Add SHADING-related constants if needed
6. **Test:** Verify end-to-end (obs → action → new_obs)

---

## Execution Flow Diagram

### High-Level Flow

```
START (main in inference.py)
    ↓
[Create GreenhouseInference(agent)]
    ↓
[run_all_tasks()]
    ├────────────────────────────────┐
    │                                │
    ↓                                ↓
[Easy Task: 10 eps]            [Medium Task: 20 eps]
    ├─ Loop 10×:                   ├─ Loop 20×:
    │  ├─ env.reset()              │  ├─ env.reset()
    │  ├─ Step loop until done      │  ├─ Step loop until done
    │  └─ Append result             │  └─ Append result
    ├─ grade_easy(results)         ├─ grade_medium(results)
    └─ easy_score ready            └─ medium_score ready
                │
                ├────────────────────────────────┐
                │                                │
                ↓                                ↓
           [Hard Task: 30 eps]
               ├─ Loop 30×:
               │  ├─ env.reset()
               │  ├─ Step loop until done
               │  └─ Append result
               ├─ grade_hard(results)
               └─ hard_score ready

               All 3 scores ready
                    ↓
            [grade_overall_performance()]
                    ↓
            overall_score computed
                    ↓
            [print_grading_report()]
                    ↓
                 RETURN results dict
                    ↓
                  END
```

### Single Episode Zoom-In

```
env.reset()
  ├─ Initialize GreenhouseState()
  ├─ state.temperature = 20.0
  ├─ state.crop_health = 0.8
  ├─ ... (all variables reset)
  └─ Return obs = [20, 60, 400, 0, 80, 80, 0.8, 0.0, 0.5, 0.0]

for step in 0..max_steps:
  ├─ obs → agent.select_action(obs) → action [0.3, 0.0, 0.2, ...]
  ├─ env.step(action):
  │  ├─ Parse action: heating=0.3, cooling=0.0, humidify=0.2, ...
  │  ├─ compute_energy_costs()
  │  ├─ apply_dynamics(state, actions):
  │  │  ├─ Update time: hour = (12 + 1) % 24 = hour 13
  │  │  ├─ compute_temp_delta(): ΔT = -(new_T - T_amb)/4 + heating + ...
  │  │  ├─ compute_humidity_delta(): Δhum = evapotrans - humidify + ...
  │  │  ├─ compute_co2_delta(): Δco2 = -uptake + ventilation + ...
  │  │  ├─ compute_light(): light = solar + supplemental
  │  │  ├─ compute_water_delta(): Δwater = -consumption + irrigation
  │  │  ├─ compute_energy_delta(): Δenergy = production - costs
  │  │  ├─ compute_health_delta(): Δhealth = growth - stress - disease
  │  │  ├─ compute_mold_delta(): Δmold = growth - suppression
  │  │  └─ clamp_state(): enforce mins/maxs
  │  ├─ compute_reward(prev, new):
  │  │  ├─ r_health = 0.8 * 1.0
  │  │  ├─ r_stability = -(temp_delta^2 + ...) * 0.5
  │  │  ├─ r_resource = -(energy_used * 0.05 + ...) * 0.3
  │  │  ├─ penalties (mold, freeze, heat, death)
  │  │  └─ total_reward = sum(all)
  │  ├─ terminated = (health <= 0) | (water = 0 AND energy = 0)
  │  ├─ truncated = (step ≥ max_steps)
  │  └─ Return (new_obs, reward, terminated, truncated, info)
  │
  └─ done = terminated | truncated
     ├─ if not done: continue loop
     └─ if done:
        └─ episode_results = {
             "episode_return": sum(rewards),
             "final_crop_health": state.crop_health,
             "steps": step,
             ...
           }
        └─ break loop, return results
```

---

## Design Decisions

### 1. Why Sequential Decision-Making?

**Alternative:** Simple PID controller (setpoint tracking)

**Why Not PID:**
- PID works for holding a single setpoint (e.g., temp = 22°C)
- Greenhouse has multiple objectives: health, stability, resource efficiency
- Resources are finite → can't independently control all variables
- External disturbances require adaptation, not just error correction

**Why Sequential:**
- Agent must decide WHICH subsystems to prioritize at each moment
- Decisions are coupled: heating uses energy needed for irrigation
- Optimal strategy changes over time (day vs. night, growth phase, etc.)
- Requires planning → sequential decision framework is natural

### 2. Why Continuous Action Space [0, 1]^8?

**Alternative 1:** Discrete actions (on/off for each system)

**Why Not Discrete:**
- Greenhouse control is inherently continuous (intensity matters)
- On/off loses efficiency (heat at 50% is better than full power for 30 seconds)
- Discrete actions → large branching factor (2^8 = 256 actions)

**Alternative 2:** Unbounded continuous actions

**Why Not Unbounded:**
- Actions need physical meaning (intensity 0-1)
- Unbounded allows negative cooling/heating (physically meaningless)
- Normalized actions easier to learn (no need to find scale)

### 3. Why Three Tasks (Easy → Medium → Hard)?

**Alternative:** Single hard task

**Why Not Single:**
- Learning hard task directly is difficult (cold start problem)
- Easy task teaches basic state-action effects faster
- Medium task teaches adaptation without planning overhead
- Hard task builds on prior knowledge (transfer learning)
- Matches real training progression: basics → fundamentals → mastery

### 4. Why Fully Observable State?

**Alternative:** Partially observable (sensor noise, missing variables)

**Why Fully Observable Now:**
- Simplifies first version (focus on decision-making, not filtering)
- Real greenhouses have good sensors nowadays
- Partial observability is next research direction
- Reduces confounds (is agent bad at deciding or bad at sensing?)

### 5. Why Dense Reward (Every Step)?

**Alternative:** Sparse reward (only at episode end)

**Why Dense:**
- Large action space (8D continuous) → sparse reward is hard to learn from
- Dense reward provides learning signal at each step (faster convergence)
- Still aligns with episode objective (sum of rewards = total health)
- Practical: dense feedback guides agent toward good policies

### 6. Why Non-Stationary Environment (Tasks 2 & 3)?

**Alternative:** Stationary (always same weather)

**Why Non-Stationary:**
- Real greenhouses have changing weather
- Tests agent's adaptation ability (not just memorizing optimal static strategy)
- Makes planning necessary (today's decision affects tomorrow's options)
- Prevents overfitting to specific initial conditions

### 7. Why Multi-Objective Reward?

**Alternative:** Simple reward = final crop health only

**Why Multi-Objective:**
- Health alone incentivizes wasteful control (infinite energy use)
- Stability matters for real crops (stress from oscillations)
- Resource cost matters (real greenhouses have budgets)
- Reflects real operations: balance health, cost, reliability
- More interesting problem for agents to solve

### 8. Why Crop Health Can't Fully Recover from Damage?

**Alternative:** All damage is reversible

**Why Irreversibility:**
- Real crop damage (e.g., frost) is often permanent
- Creates consequence for agent mistakes (learning signal)
- Prevents "try everything, revert" strategies
- Forces careful planning and prevention

### 9. Why Include Mold as Separate State Variable?

**Alternative:** Just damage crop health directly

**Why Separate:**
- Mold is a distinct risk requiring separate intervention (ventilation)
- Allows modeling tipping point (slow growth → sudden rapid spread)
- Requires temporal reasoning (agent must predict mold risk)
- Makes the problem richer (not just health optimization)

### 10. Why Normalize Actions to [0, 1] for LLM Interface?

**Alternative:** Real physical units (watts, liters)

**Why Normalized:**
- LLM outputs probabilities naturally in [0, 1]
- Easy to convert to physical units in dynamics
- Prevents out-of-range actions (can clamp at output)
- Standard in RL (gymnasium uses normalized spaces)

---

## Summary

The **Greenhouse Environment** is a realistic sequential decision-making problem combining:

- **Physical Simulation:** Nonlinear, coupled dynamics
- **Resource Constraints:** Limited energy/water with tradeoffs
- **External Uncertainty:** Weather disturbances
- **Irreversible Consequences:** Crop death, frost damage
- **Multi-Objective Optimization:** Health vs. cost vs. stability

**Three Tasks** escalate difficulty:
1. **Easy:** Static stabilization (learn basics)
2. **Medium:** Adaptive control (react to weather)
3. **Hard:** Planning under constraints (optimize resources)

**Grading** converts episode results to 0.0-1.0 scores aligned with task objectives.

The **architecture** is modular and extensible:
- Clean separation: state, actions, dynamics, rewards
- Easy to add new crops, action types, task variants
- Gymnasium-compatible for standard RL algorithms
- OpenEnv specification for benchmarking

This design prioritizes **clarity**, **realism**, and **educational value** for researchers learning sequential decision-making.

---

**End of CLAUDE.md**

Documentation version: 1.0  
Last update: April 2026
