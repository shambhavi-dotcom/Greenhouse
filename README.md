---
title: Greenhouse Openenv
emoji: 🦀
colorFrom: green
colorTo: red
sdk: docker
pinned: false
license: mit
short_description: GreenHouse Simulation app
---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference

# 🌱 Greenhouse AI Environment

[![OpenEnv Compliant](https://img.shields.io/badge/OpenEnv-Compliant-00e676?style=flat-square)](https://openenv.ai)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-7c8cf8?style=flat-square)](https://python.org)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-ff4b4b?style=flat-square)](https://streamlit.io)
[![Gymnasium](https://img.shields.io/badge/API-Gymnasium-0096ff?style=flat-square)](https://gymnasium.farama.org)

A **production-grade, OpenEnv-compliant** greenhouse simulation environment for training and evaluating AI agents on precision agriculture control tasks. The environment models a real commercial greenhouse with physically accurate dynamics, a 4-crop catalogue, and three difficulty tiers.

---

## 🌍 Motivation & Real-World Utility

Precision agriculture represents one of the highest-impact domains for autonomous AI. Commercial greenhouses account for **>30% of global vegetable yield** and consume enormous amounts of energy and water. Even small improvements in AI-controlled climate management translate directly into:

- **Reduced energy costs** (heating / cooling / lighting are the top OPEX items)
- **Higher crop yield** through tighter adherence to optimal temperature and humidity bands
- **Lower water consumption** through demand-driven irrigation
- **Disease prevention** by actively suppressing mold-conducive conditions

This environment gives AI agents a realistic, full-fidelity testbed for learning these control policies.

---

## 🏗️ Architecture

```
Greenhouse/
├── env/
│   ├── environment.py      # GreenhouseEnv — Gymnasium + OpenEnv API
│   ├── dynamics.py         # Physics engine (temperature, humidity, CO₂, health)
│   ├── rewards.py          # Normalised reward function
│   ├── state.py            # GreenhouseState + initial condition presets
│   ├── models.py           # Pydantic v2 typed models (OpenEnv requirement)
│   └── actions.py          # ActionSpace + Action types
├── config/
│   ├── constants.py        # Physical limits, HVAC power, energy refill rates
│   └── crop_profiles.py    # Per-crop optimal setpoints and stress sigmas
├── tasks/
│   ├── task_easy.py        # Task 1: Stabilisation (no resource limits)
│   ├── task_medium.py      # Task 2: Adaptation (weather + moderate resources)
│   ├── task_hard.py        # Task 3: Optimisation (tight energy + weather)
│   └── graders.py          # Deterministic episode scorers [0.0 – 1.0]
├── inference.py            # LLM agent runner with structured [START/STEP/END] logs
├── app.py                  # Streamlit real-time dashboard
├── openenv.yaml            # OpenEnv metadata and endpoint declarations
└── Dockerfile              # HuggingFace Space deployment
```

---

## 🔬 Environment Physics

### Temperature
Based on **Newton's Law of Cooling** — the greenhouse slowly equilibrates with the outside ambient temperature. The heater and cooler actively counteract drift.

```
ΔT = (T_ambient − T) / τ_wall    # passive wall exchange (τ = 18h Easy, 14h Med, 10h Hard)
   + heating × 2.0°C/h
   − cooling × 1.5°C/h
   + radiative_effect             # solar gain (+0.5°C peak at noon), night loss (−0.3°C/h)
   − ventilation × pull_to_ambient
   − humidifying × 0.15°C/h      # evaporative cooling
```

With the default ambient of 18°C (Easy), a random agent (avg 0.5 intensity) naturally maintains **~20–21°C** — close to the tomato optimum of 22°C.

### Humidity
Modelled via **vapor pressure deficit (VPD)** physics:

```
ΔRH = evapotranspiration          # 0–0.8%/h, crop and light driven
    + humidifier × 8%/h           # active addition
    − dehumidifier × 6%/h         # active removal
    − ventilation × 2%/h          # exchange with drier outdoor air (realistic value)
    + drift toward 50% (τ=48h)    # slow passive equilibrium
```

### CO₂
```
ΔCO₂ = −photosynthesis × 30 ppm/h    # crop uptake when lit + healthy
      + CO₂ enrichment × 150 ppm/h   # active injection
      − ventilation × 100 ppm/h      # flush with outdoor air (400 ppm)
      + ambient drift (τ=24h)         # slow return to 400 ppm when sealed
```

### Crop Health — Gaussian Stress Kernel
Each environmental variable contributes a **Gaussian stress score**:

```
stress(x, x_opt, σ) = 1 − exp(−½ × ((x − x_opt) / σ)²)

Weighted combination:
  combined_stress = 0.35 × hs_temp + 0.25 × hs_humidity + 0.20 × hs_CO₂ + 0.20 × hs_light

Break-even at combined_stress ≈ 0.65:
  stress < 0.65  → health grows  (+growth_rate × (1 − stress) per step)
  stress > 0.65  → health decays (−0.008 × stress per step)
```

At perfect conditions, health grows at `growth_rate` per step. At severe stress, it decays. Proportional irreversible damage occurs for temperatures beyond the crop-specific `cold_damage_threshold` / `heat_stress_threshold`.

### ⚡ Energy — Grid-Connected with Passive Refill

Real greenhouses are **connected to the electrical grid**. Energy never "runs out" — instead, an on-site battery/solar system recharges passively each step. Difficulty governs the recharge rate:

| Difficulty | Refill / step | Typical drain | Effective constraint |
|:-----------|:--------------|:--------------|:---------------------|
| Easy       | 5.0 units     | ~1.2 units    | Effectively unlimited |
| Medium     | 2.0 units     | ~1.2 units    | Moderate efficiency needed |
| Hard       | 0.5 units     | ~1.2 units    | Careful planning required |

A **brownout** occurs if `energy_level` reaches 0 — all actuators scale down proportionally until the battery recharges.

### 💧 Water — Finite Reservoir
A 100-unit reservoir depletes via crop transpiration and refills via irrigation. No artificial daily cap — the reservoir size is the natural constraint.

---

## 🌾 Crop Profiles

| Crop     | T_opt | RH_opt | CO₂_opt | Light_opt | σ_temp | σ_humidity |
|:---------|:-----:|:------:|:-------:|:---------:|:------:|:----------:|
| Tomato   | 22°C  | 65%    | 900 ppm | 700 µmol  | 4°C    | 15%        |
| Lettuce  | 18°C  | 70%    | 800 ppm | 500 µmol  | 3°C    | 12%        |
| Herbs    | 24°C  | 60%    | 1000 ppm| 600 µmol  | 5°C    | 18%        |
| Cucumber | 24°C  | 75%    | 950 ppm | 650 µmol  | 4°C    | 10%        |

---

## 🎮 Action Space

**8 continuous actions** in [0, 1], all simultaneously controllable:

| Index | Action Type      | Effect                              |
|:-----:|:-----------------|:------------------------------------|
| 0     | `HEATING`        | +2.0°C/h at max intensity           |
| 1     | `COOLING`        | −1.5°C/h at max intensity           |
| 2     | `HUMIDIFYING`    | +8%/h relative humidity             |
| 3     | `DEHUMIDIFYING`  | −6%/h relative humidity             |
| 4     | `VENTILATION`    | CO₂ flush + gentle temp/humidity pull toward ambient |
| 5     | `IRRIGATION`     | +3 water units/h                    |
| 6     | `LIGHTING`       | +400 µmol/m²/s supplemental at max  |
| 7     | `CO2_ENRICHMENT` | +150 ppm/h CO₂ injection            |

---

## 👁️ Observation Space

**10 continuous variables** returned by `reset()` and `step()`:

| Index | Variable          | Range      | Description                    |
|:-----:|:------------------|:----------:|:-------------------------------|
| 0     | `temperature`     | 5–40°C     | Greenhouse air temperature      |
| 1     | `humidity`        | 20–95%     | Relative humidity               |
| 2     | `co2`             | 200–2000 ppm | CO₂ concentration             |
| 3     | `light_intensity` | 0–1000 µmol | Combined natural + supplemental |
| 4     | `water_level`     | 0–100 units | Irrigation reservoir level      |
| 5     | `energy_level`    | 0–200 units | Energy bank remaining           |
| 6     | `crop_health`     | 0.0–1.0     | 0 = dead, 1 = thriving         |
| 7     | `mold_presence`   | 0.0–1.0     | 0 = none, 1 = severe            |
| 8     | `time_of_day`     | 0–1        | Normalised hour (0–23)          |
| 9     | `day_counter`     | 0–1        | Normalised episode day          |

---

### Task 1: Stabilisation (Easy)
> **Goal**: Maintain crop health above 0.8 for 100 steps under stable indoor conditions.

- No weather disturbances; energy is unlimited (focus on pure control policy)
- Ambient temperature: 18°C (stable)
- Success threshold: final `crop_health > 0.8`
- Target agent: LLM prompted with observation context

### Task 2: Adaptation (Medium)
> **Goal**: Recover and maintain crop health through 200 steps with weather disturbances and moderate energy constraints.

- Diurnal temperature cycle (12–20°C ambient), weather shocks ±4°C every 6h
- Energy refill 2.0 units/step — moderate HVAC budget
- Success threshold: final `crop_health > 0.6`
- Requires reactive temperature and humidity management

### Task 3: Optimisation (Hard)
> **Goal**: Sustain crop health for 300 steps under tight energy and weather perturbations.

- Full weather system active; energy refill only 0.5 units/step (plan carefully)
- Agents must prioritise actuators or risk brownout
- Success threshold: final `crop_health > 0.4`
- Requires long-horizon energy planning + weather adaptation

---

## 🌱 Initial Condition Presets

Four starting scenarios — **only crop health and initial temperature differ**. All other resources (water reservoir, energy bank, humidity, CO₂, mold) always start at full/optimal values. Resource depletion is governed entirely by task difficulty.

| Preset | Health | Start Temp | Challenge |
|:-------|:------:|:----------:|:----------|
| 🟢 Thriving (100%) | 1.0 | 22°C | Maintain excellence |
| 🟡 Healthy (75%)   | 0.75 | 19.5°C | Mild recovery needed |
| 🟠 Stressed (50%)  | 0.50 | 16°C | Active recovery required |
| 🔴 Critical (25%)  | 0.25 | 12°C | Prevent crop death immediately |

---

## 🔌 OpenEnv API

The environment implements the full **OpenEnv interface**:

```python
from env.environment import GreenhouseEnv

env = GreenhouseEnv(
    crop="tomato",                  # tomato | lettuce | herbs | cucumber
    difficulty="medium",            # easy | medium | hard
    include_weather=True,
    include_resource_limits=True,
    max_episode_steps=200,
)

# Standard Gymnasium API
obs, info   = env.reset()                          # → numpy array (10,)
obs, r, done, trunc, info = env.step(action)       # action: numpy array (8,)

# OpenEnv typed API (required by spec)
typed_obs: GreenhouseObservation = env.get_state() # → Pydantic v2 model
typed_obs: GreenhouseObservation = env.state()     # alias

# Typed step/reset (returns full Pydantic models)
result: GreenhouseStepResult  = env.typed_step(action)
obs:    GreenhouseObservation = env.typed_reset()
```

### Typed Models (Pydantic v2)

```python
class GreenhouseObservation(BaseModel):
    temperature: float      # °C
    humidity: float         # %
    co2: float              # ppm
    light_intensity: float  # µmol/m²/s
    water_level: float      # units
    energy_level: float     # units
    crop_health: float      # [0, 1]
    mold_presence: float    # [0, 1]
    time_of_day: int        # hour
    day_counter: int        # day

class GreenhouseAction(BaseModel):
    heating: float          # [0, 1]
    cooling: float          # [0, 1]
    humidifying: float      # [0, 1]
    dehumidifying: float    # [0, 1]
    ventilation: float      # [0, 1]
    irrigation: float       # [0, 1]
    lighting: float         # [0, 1]
    co2_enrichment: float   # [0, 1]

class GreenhouseReward(BaseModel):
    total: float
    component_crop: float       # health [−1, +1]
    component_stability: float  # Gaussian proximity bonus
    component_resource: float   # efficiency bonus
    penalty_mold: float
    penalty_freeze: float
    penalty_heat: float
    penalty_death: float
```

---

## 🤖 Inference Script

The `inference.py` script runs an LLM-based agent against the environment, producing **structured logs** required by OpenEnv automated evaluators.

```bash
# Run with OpenAI-compatible endpoint
export OPENAI_API_KEY="your-key"
export MODEL_NAME="gpt-4o-mini"
python inference.py

# Run with HuggingFace model
export HF_TOKEN="your-token"
export API_BASE_URL="https://api-inference.huggingface.co/v1"
export MODEL_NAME="meta-llama/Llama-3-8b-instruct"
python inference.py
```

**Log format** (automatically produced):
```
[START] task=stabilization crop=tomato difficulty=easy max_steps=50
[STEP] step=1 obs={...} action=[...] reward=1.74 health=1.000 temp=22.0
[STEP] step=2 obs={...} action=[...] reward=1.72 health=1.000 temp=23.1
...
[END] total_reward=86.5 final_health=0.987 score=1.0 status=success
```

---

## 📊 Reward Function

Per-step reward normalised to approximately **[−2, +2]**:

```
R = 1.0 × (2h − 1)           # health component: [−1, +1]
  + 0.5 × proximity_bonus     # Gaussian proximity to per-crop optima
  + 0.3 × efficiency_bonus    # 1 − (energy_used / max_possible)
  − mold_penalty              # proportional to mold_presence > 0.5
  − freeze_penalty            # flat if temp < 2°C
  − death_penalty             # −5.0 if crop dies
```

---

## 📈 Baseline Results

Matrix test (setpoint agent, Tomato, 3 difficulties × 4 presets):

| Preset | Easy | Medium | Hard |
|:-------|:----:|:------:|:----:|
| 🟢 Thriving (100%) | **1.000** | **1.000** | **1.000** |
| 🟡 Healthy (75%)   | **1.000** | **1.000** | **1.000** |
| 🟠 Stressed (50%)  | **1.000** | **1.000** | **1.000** |
| 🔴 Critical (25%)  | **1.000** | **1.000** | **1.000** |

> ℹ️ The **setpoint agent** (rules-based, always corrects toward optimal) achieves 12/12. A **random agent** is expected to score 0.6–0.8 on Easy and 0.3–0.5 on Hard — creating a clear gradient for LLM agent evaluation.

---

## 🚀 Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the Streamlit dashboard
streamlit run app.py

# 3. Run the inference script
python inference.py

# 4. Validate OpenEnv compliance
python scripts/validate_submission.py
```

---

## 🐳 Docker / HuggingFace Spaces

```bash
# Build and run locally
docker build -t greenhouse-env .
docker run -p 7860:7860 greenhouse-env

# Deploy to HuggingFace Spaces
# Push this repository to a HF Space — the Dockerfile handles everything.
```

The Space runs `streamlit run app.py --server.port 7860 --server.address 0.0.0.0`.

---

## 📋 OpenEnv Compliance Checklist

| Requirement | Status | Implementation |
|:------------|:------:|:---------------|
| Pydantic v2 typed models | ✅ | `env/models.py` |
| `step()` API | ✅ | `GreenhouseEnv.step()` |
| `reset()` API | ✅ | `GreenhouseEnv.reset()` |
| `state()` typed endpoint | ✅ | `GreenhouseEnv.get_state()` + alias `state()` |
| `openenv.yaml` metadata | ✅ | Root level |
| 3+ tasks defined | ✅ | Easy / Medium / Hard |
| Deterministic graders [0,1] | ✅ | `tasks/graders.py` |
| Structured inference logs | ✅ | `[START] / [STEP] / [END]` format |
| Dockerfile (port 7860) | ✅ | `Dockerfile` |
| HF Space tags `openenv` | ✅ | `openenv.yaml` |

---

## 📁 openenv.yaml

```yaml
name: greenhouse-ai-environment
version: "1.0.0"
tags: [openenv, greenhouse, agriculture, rl, control]

environment:
  entry_point: env/environment.py
  class: GreenhouseEnv
  api:
    reset:  reset()
    step:   step(action)
    state:  get_state()

tasks:
  - id: stabilization
    difficulty: easy
    entry_point: tasks/task_easy.py
    description: Maintain crop health in stable indoor conditions for 100 steps.

  - id: adaptation
    difficulty: medium
    entry_point: tasks/task_medium.py
    description: Recover and maintain crop health under weather disturbances.

  - id: optimization
    difficulty: hard
    entry_point: tasks/task_hard.py
    description: Sustain crop health with tight energy budget and full weather.
```

---

## 🧪 Running Tests

```bash
# Physics unit tests
python test_dynamics.py

# OpenEnv compliance validation
python scripts/validate_submission.py

# Problem statement alignment check
python scripts/verify_ps_alignment.py
```
