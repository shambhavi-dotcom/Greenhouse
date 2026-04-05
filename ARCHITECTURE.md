# Architecture Overview

## 🏗️ System Design at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACES                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📊 WEB DASHBOARD (Streamlit)    │  💻 CLI (Python)    │
│  ├─ Real-time Monitoring         │  └─ inference.py    │
│  ├─ Episode Simulation           │     └─ scores       │
│  └─ Batch Evaluation             │                      │
│       (FRONTEND)                  │     (BACKEND)       │
└─────────────────────────────────────────────────────────┘
                    ↓↓↓ Uses ↓↓↓
┌─────────────────────────────────────────────────────────┐
│              AGENT INTERFACE                             │
├─────────────────────────────────────────────────────────┤
│  GreenhouseAgent (abstract base class)                  │
│  ├─ RandomAgent (baseline)                             │
│  ├─ [Your Custom Agent]                                │
│  └─ [Future RL agents]                                 │
│                                                          │
│       (inference.py + app.py)                          │
└─────────────────────────────────────────────────────────┘
                    ↓↓↓ Uses ↓↓↓
┌─────────────────────────────────────────────────────────┐
│              ENVIRONMENT (GreenhouseEnv)                │
├─────────────────────────────────────────────────────────┤
│  Gymnasium-Compatible Interface                         │
│  - reset() → obs, info                                 │
│  - step(action) → obs, reward, terminated, truncated   │
│                                                          │
│  Three Task Variants:                                   │
│  ├─ Easy (100 steps, static)                           │
│  ├─ Medium (200 steps, weather)                        │
│  └─ Hard (500 steps, constrained)                      │
│                                                          │
│       (env/environment.py)                             │
└─────────────────────────────────────────────────────────┘
                    ↓↓↓ Uses ↓↓↓
┌─────────────────────────────────────────────────────────┐
│         CORE SIMULATION COMPONENTS                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  STATE                 ACTIONS              REWARDS    │
│  ├─ Temperature        ├─ Heating           ├─ Health  │
│  ├─ Humidity           ├─ Cooling           ├─ Stabil. │
│  ├─ CO2                ├─ Humidifying       ├─ Res.    │
│  ├─ Light              ├─ Dehumidifying     └─ Penalts │
│  ├─ Water              ├─ Ventilation                  │
│  ├─ Energy             ├─ Irrigation          GRADING  │
│  ├─ Crop Health        ├─ Lighting           ├─ Ease   │
│  ├─ Mold               └─ CO2 Enrichment     ├─ Medium │
│  ├─ Time of Day                              ├─ Hard   │
│  └─ Day Counter                              └─ Ovrl   │
│                                                          │
│  (env/state.py)  (env/actions.py)    (env/rewards.py)  │
│                                       (tasks/graders.py)│
└─────────────────────────────────────────────────────────┘
                    ↓↓↓ Uses ↓↓↓
┌─────────────────────────────────────────────────────────┐
│              PHYSICS SIMULATION                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  apply_dynamics(state, actions) → new_state           │
│  ├─ Temperature Evolution (heat transfer physics)      │
│  ├─ Humidity Dynamics (evapotranspiration + controls)  │
│  ├─ CO2 Cycle (photosynthesis + ventilation)          │
│  ├─ Light Propagation (solar + artificial)            │
│  ├─ Water Balance (consumption + irrigation)          │
│  ├─ Energy Budget (solar + consumption)               │
│  ├─ Crop Health (growth + stress + disease)           │
│  └─ Mold Infection (growth + suppression)             │
│                                                          │
│  + External Disturbances:                              │
│  ├─ Weather (temperature variations)                   │
│  ├─ Disease Pressure (crop-dependent)                 │
│  └─ Time Cycles (day/night, seasonal)                 │
│                                                          │
│       (env/dynamics.py)                                │
└─────────────────────────────────────────────────────────┘
                    ↓↓↓ Uses ↓↓↓
┌─────────────────────────────────────────────────────────┐
│          CONFIGURATION & PROFILES                      │
├─────────────────────────────────────────────────────────┤
│  Constants (100+ parameters)        Crop Profiles       │
│  ├─ Temperature limits              ├─ Tomato           │
│  ├─ Humidity ranges                 ├─ Lettuce          │
│  ├─ CO2 bounds                      └─ Herbs            │
│  ├─ Action costs                       Each defines:    │
│  ├─ Reward weights                     ├─ Optimal       │
│  ├─ Episode params                     │  conditions    │
│  └─ Task settings                      ├─ Growth rate   │
│                                        └─ Constraints   │
│  (config/constants.py)              (config/crop_prof.)│
└─────────────────────────────────────────────────────────┘
```

---

## 📦 File Organization

```
greenhouse/
├── env/                           # Core simulation
│   ├── __init__.py
│   ├── state.py                   # GreenhouseState (10D)
│   ├── actions.py                 # Action types (8D)
│   ├── environment.py             # Gymnasium wrapper
│   ├── dynamics.py                # Physics simulation
│   ├── rewards.py                 # Multi-objective reward
│   └── utils.py                   # Helpers
│
├── config/                        # Settings & profiles
│   ├── __init__.py
│   ├── constants.py               # 100+ parameters
│   └── crop_profiles.py           # Tomato, lettuce, herbs
│
├── tasks/                         # Task definitions
│   ├── __init__.py
│   ├── task_easy.py               # 10 episodes
│   ├── task_medium.py             # 20 episodes
│   ├── task_hard.py               # 30 episodes
│   └── graders.py                 # Scoring (0.0-1.0)
│
├── inference.py                   # CLI agent-runner
├── app.py                         # Streamlit web UI
│
├── CLAUDE.md                      # System documentation (19K lines)
├── FRONTEND.md                    # Web UI guide (3.5K lines)
├── QUICKSTART.md                  # Quick reference (this file)
├── README.md                      # Project overview
│
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container config
├── run_frontend.bat               # Windows launcher
├── run_frontend.ps1               # PowerShell launcher
│
└── LICENSE, .gitignore, etc.
```

---

## 🔄 Data Flow Example: Single Episode

```
1. RESET
   User clicks "Run Episode" in web UI
        ↓
   app.py calls env.reset()
        ↓
   GreenhouseEnv initializes GreenhouseState
        ↓
   Returns: observation (10D array), info (metadata)

2. AGENT LOOP (repeat N times)
   
   For each step:
   
   a) DECISION
      observation (10D) → agent.select_action(obs)
      RandomAgent: generates action[0..1]^8
           ↓
   
   b) EXECUTION
      env.step(action)
           ↓
      Parse action → 8 control intensities
           ↓
      Compute energy/water costs
           ↓
   
   c) SIMULATION
      apply_dynamics(state, actions)
           ↓
      For each state variable:
         - Compute delta based on physics
         - Apply control effects
         - Apply external disturbances
         - Clamp to limits
           ↓
      Update state to new values
           ↓
   
   d) REWARD
      compute_reward(prev_state, new_state)
           ↓
      Combine components:
         health + improvement + stability - cost - penalties
           ↓
   
   e) TERMINATION CHECK
      if health ≤ 0: EPISODE ENDS (death)
      if step ≥ max_steps: EPISODE ENDS (timeout)
      else: continue
           ↓

3. RESULTS
   Collected 100-500 steps of data:
   - timestep data (obs, actions, rewards)
   - final metrics (health, resources, efficiency)
           ↓
   Display in UI:
   - Charts (Plotly time-series)
   - Summary statistics
   - CSV download
           ↓

4. SCORING
   tasks/graders.py computes:
   - health_score (0.0-1.0)
   - efficiency_score (0.0-1.0)
   - success_rate (0.0-1.0)
           ↓
   Weighted average:
   - Easy: 60% health + 30% success + 10% stability → 0.0-1.0
   - Medium: 50% health + 30% adapt + 20% success → 0.0-1.0
   - Hard: 40% health + 40% efficiency + 20% success → 0.0-1.0
           ↓

5. REPORT
   Print/display overall score (average of 3 tasks)
```

---

## 🎯 State Space (10 Dimensions)

| Index | Variable | Range | Optimal | Why |
|-------|----------|-------|---------|-----|
| 0 | Temperature | 5-40°C | 22°C | Affects growth rate, disease risk |
| 1 | Humidity | 20-95% | 65% | Affects transpiration, mold risk |
| 2 | CO2 | 200-2000 ppm | 1000 ppm | Drives photosynthesis |
| 3 | Light | 0-1000 µmol/m²/s | 600 | Energy for growth |
| 4 | Water | 0-100 units | 50-80 | Crop survival + transpiration |
| 5 | Energy | 0-100 units | >30 | Resource gating |
| 6 | Crop Health | 0.0-1.0 | 1.0 | Primary success metric |
| 7 | Mold Presence | 0.0-1.0 | 0.0 | Disease risk (>0.5 damages crops) |
| 8 | Time of Day | 0-23 hours | N/A | Affects natural light, crop behavior |
| 9 | Day Counter | 0-30+ days | N/A | Tracks episode progress |

---

## 🎛️ Action Space (8 Dimensions)

| Index | Action | Range | Cost | Effect |
|-------|--------|-------|------|--------|
| 0 | Heating | [0,1] | 0.5× intensity | +2.0°C max |
| 1 | Cooling | [0,1] | 0.6× intensity | -2.5°C max |
| 2 | Humidifying | [0,1] | 2.0× intensity | +5% humidity max |
| 3 | Dehumidifying | [0,1] | 1.5× intensity | -8% humidity max |
| 4 | Ventilation | [0,1] | 1.0× intensity | -150 ppm CO2 max |
| 5 | Irrigation | [0,1] | 0.5× intensity | +5 units water max |
| 6 | Lighting | [0,1] | 0.1× intensity | +500 µmol/m²/s max |
| 7 | CO2 Enrichment | [0,1] | 1.5× intensity | +200 ppm max |

---

## 🏆 Reward Structure

```
Total Reward per Step = Components + Penalties

COMPONENTS (Positive)
├─ Crop Health           (1.0 × crop_health ∈ [0,1])
├─ Health Improvement    (2.0 × Δhealth if positive)
├─ Environmental Stability (-0.5 × (ΔT² + 0.5×Δhum²))
└─ Resource Efficiency   (-0.3 × (energy_used + water_used))

PENALTIES (Negative)
├─ Mold Infection        (-10.0 if mold > 0.5)
├─ Freeze Damage         (-20.0 if T < 2°C)
├─ Heat Stress           (-0.5 × max(0, T - 35°C))
└─ Crop Death            (-50.0 if health ≤ 0)

Typical Range per Step:
├─ Perfect Management    → +0.8 to +1.2
├─ Good Management       → +0.3 to +0.6
├─ Poor Management       → -0.5 to +0.2
└─ Catastrophic Failure  → -60 to -70
```

---

## 📊 Scoring System

```
TASK EVALUATION

Easy Task (Stabilization):
  Score = 0.60 × health + 0.30 × success + 0.10 × consistency
  Range: [0.0, 1.0]
  Interpretation: Can agent maintain crops in static environment?

Medium Task (Adaptation):
  Score = 0.50 × health + 0.30 × adaptation + 0.20 × success
  Range: [0.0, 1.0]
  Interpretation: Can agent react to disturbances?

Hard Task (Optimization):
  Score = 0.40 × health + 0.40 × efficiency + 0.20 × success
  Range: [0.0, 1.0]
  Interpretation: Can agent optimize under constraints?

OVERALL SCORE
  overall = (easy + medium + hard) / 3.0
  If all ≥ 0.5: apply +5% consistency bonus
  Final range: [0.0, 1.0]
  
  Interpretation:
  ├─ 0.85+  → World-class agent
  ├─ 0.70-0.84 → Competent agent
  ├─ 0.50-0.69 → Adequate agent
  └─ <0.50 → Needs improvement
```

---

## 🔗 Interaction Examples

### Example 1: Temperature Control
```
State: T=18°C, ambient=15°C (cold day)
Action: heating=0.5, others=0

Step 1:
├─ Heating effect: +2.0 × 0.5 = +1.0°C
├─ Natural decay: -(18-15)/4 = -0.75°C
├─ New T = 18 + 1.0 - 0.75 = 18.25°C
└─ Energy cost: 0.5 × 0.5 = 0.25 units

Result: Agent heats greenhouse; temp rises but at cost to energy.
```

### Example 2: Coupled Effects
```
State: Humidity=40% (too low), T=20°C

Action: Heating=0.3, Humidifying=0.4

Step 1:
├─ Heating adds 0.6°C
├─ Temperature rises to 20.6°C
├─ Humidity coupling: warmer air is drier → -3% humidity (automatic)
├─ But humidification action: +2% humidity
├─ Net humidity: 40% - 3% + 2% = 39% (still too low!)
├─ Energy cost: 0.3×0.5 + 0.4×2.0 = 0.95 units

Result: Agent learned heating worsens dry conditions; needs more humidification.
```

### Example 3: Resource Constraint
```
State: Water=15 units, Energy=10 units
Max Daily Budget: Water 20, Energy 30

Action: Irrigation=0.8, Cooling=0.5, Lighting=0.3

Costs:
├─ Irrigation: 0.8 × 5 units = 4 water (OK, 15→11 water left)
├─ Cooling: 0.5 × 0.6 = 0.3 energy
└─ Lighting: 0.3 × 0.1 × light_intensity = 0.1 energy
├─ Total energy: 0.4 (OK, 10→9.6 energy left)

Result: Action permitted. But if plants need more irrigation
        later today, budget is tighter.
```

---

## 🚀 Getting Started

**3-Step Launch:**

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the web UI**
   ```bash
   streamlit run app.py
   ```

3. **Open browser**
   ```
   http://localhost:8501
   ```

**Then:**
- Explore the Dashboard (real-time state monitoring)
- Run a Single Episode (watch the agent control the greenhouse)
- Evaluate the agent (Batch Evaluation)
- Add your own agent (edit app.py's get_agent() function)

---

## 📚 Documentation Map

| Document | Purpose | Length | When to Read |
|----------|---------|--------|--------------|
| **README.md** | Project overview | 2KB | First (entry point) |
| **QUICKSTART.md** | Quick reference | 5KB | Before running |
| **Architecture Overview** (this) | System design | 8KB | Understanding flow |
| **CLAUDE.md** | Deep documentation | 19KB | Deep dive on design |
| **FRONTEND.md** | Web UI guide | 3.5KB | Customizing dashboard |
| **Source Code** | Implementation | Variable | Debugging/extending |

---

## 🎓 Learning Path

### Beginner (Just Run It)
1. Run `streamlit run app.py`
2. Click buttons, watch visualizations
3. Export and analyze CSV data

### Intermediate (Understand It)
1. Read QUICKSTART.md (5 min)
2. Read Architecture Overview (10 min)
3. Run episodes and interpret results (30 min)
4. Explore source code (30 min)

### Advanced (Extend It)
1. Study CLAUDE.md sections 3-6 (state/actions/dynamics/rewards) (2 hours)
2. Implement a new crop profile in config/crop_profiles.py
3. Implement a new agent (see inference.py for interface)
4. Add custom visualization to app.py

### Expert (Modify Physics)
1. Study CLAUDE.md section 6 (Environment Dynamics) (2 hours)
2. Read env/dynamics.py (understand structure)
3. Implement physics functions (apply_dynamics → temperature/humidity/CO2/light/water/energy/health/mold)
4. Validate with unit tests

---

**Last Updated:** April 2026  
**Status:** Complete Scaffold + Web UI Ready  
**Next:** Implement physics dynamics or add your own agent!
