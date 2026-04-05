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

# 🌱 Greenhouse Operations Simulator

An AI-driven sequential decision-making environment modeling realistic greenhouse operations. Agents control multiple environmental systems to maximize crop health while managing limited resources (energy, water). Three graduated difficulty levels test basic control, adaptation, and optimization skills.

**Status:** ✅ Complete scaffold + working baseline (0.794 overall score) + web UI + **dynamics fixed**  
**Framework:** Gymnasium-compatible, OpenEnv-compliant  
**Language:** Python 3.8+  
**License:** MIT

---

## 🔧 Recent Update: Dynamics Implementation ✅

**NEW:** The environment now features **complete physics simulation**!

The `apply_dynamics()` function has been fully implemented with realistic state evolution:
- ✅ Temperature changes based on heating/cooling/weather
- ✅ Humidity responds to humidification, ventilation, and temperature coupling
- ✅ CO2 affected by ventilation, plant uptake, and enrichment
- ✅ Resources (water, energy) deplete with use
- ✅ Crop health grows under good conditions, decays under stress
- ✅ Mold grows when conditions are favorable
- ✅ Rewards vary dynamically based on actions and conditions

**See:** [DYNAMICS_FIX.md](DYNAMICS_FIX.md) for detailed implementation notes.

---

## 📚 Quick Navigation

| Document | Time | Purpose |
|----------|------|---------|
| **[QUICKSTART.md](QUICKSTART.md)** | 5 min | Install & launch web UI |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | 10 min | System design overview |
| **[FRONTEND.md](FRONTEND.md)** | 15 min | Web UI features & customization |
| **[CLAUDE.md](CLAUDE.md)** | 1-2 hours | Deep specification & design |
| **Source Code** | Variable | Implementation details |

---

## 🚀 Get Started in 3 Steps

### Step 1: Install
```bash
pip install -r requirements.txt
```

### Step 2: Launch Web UI
```bash
streamlit run app.py
```
Or use helper scripts:
```bash
./run_frontend.bat          # Windows
./run_frontend.ps1          # PowerShell
```

### Step 3: Open Browser
```
http://localhost:8501
```

---

## 🎮 Web Dashboard Features

### 📊 Dashboard (Real-time Monitoring)
Live display of greenhouse state:
- 🌡️ Temperature gauge (optimal 22°C)
- 💧 Humidity gauge (optimal 65%)
- 🔋 CO2 gauge (optimal 1000 ppm)
- 💡 Light intensity gauge (optimal 600 µmol/m²/s)
- 💙 Water level bar (0-100 units)
- ⚡ Energy level bar (0-100 units)
- 🌿 Crop health status (0.0-1.0, color-coded)
- 🍄 Mold infection indicator (0.0-1.0)

### 🎯 Single Episode (Simulation & Analysis)
Run a complete episode with visualization:
1. Select difficulty (Easy/Medium/Hard)
2. Adjust max steps (10-500)
3. View live plots:
   - Environmental variables (temperature, humidity, CO2, light)
   - Resources (water usage, energy consumption)
   - Crop metrics (health, mold presence)
   - Rewards (per-step and cumulative)
4. **Export CSV** for external analysis

### 📈 Batch Evaluation (Benchmarking)
Auto-runs complete evaluation suite:
- Easy Task: 10 episodes × 100 steps (static baseline)
- Medium Task: 20 episodes × 200 steps (weather adaptation)
- Hard Task: 30 episodes × 500 steps (optimization under constraints)
- Generates reports with:
  - Mean/std performance per task
  - Success rates and distributions
  - Overall score (0.0-1.0 composite)

---

## 💻 Command-Line Interface

For non-interactive evaluation:
```bash
python inference.py
```

**Output:**
```
============================================================
GREENHOUSE TASK GRADING REPORT
============================================================
Easy Task (Stabilization):      1.000
Medium Task (Adaptation):       1.000
Hard Task (Optimization):       0.400
------------------------------------------------------------
OVERALL SCORE:                  0.800
============================================================
```

---

## 🏗️ System Overview

### State Space (10-Dimensional Continuous)

| Variable | Range | Optimal | Purpose |
|----------|-------|---------|---------|
| Temperature | 5-40°C | 22°C | Primary growth factor |
| Humidity | 20-95% | 65% | Affects transpiration, disease |
| CO2 | 200-2000 ppm | 1000 | Photosynthesis driver |
| Light Intensity | 0-1000 µmol/m²/s | 600 | Energy input for growth |
| Water Level | 0-100 units | 50-80 | Crop viability |
| Energy Level | 0-100 units | >30 | Resource gate |
| Crop Health | 0.0-1.0 | 1.0 | Success metric |
| Mold Presence | 0.0-1.0 | 0.0 | Disease risk (>0.5 damages) |
| Time of Day | 0-23 hours | N/A | Natural light cycle |
| Day Counter | 0-30+ | N/A | Episode progress |

### Action Space (8-Dimensional Continuous)

Each action is intensity ∈ [0, 1] (0 = off, 1 = full power):

| Action | Effect Range | Energy Cost | Purpose |
|--------|--------------|-------------|---------|
| Heating | +2.0°C max | 0.5× intensity | Raise temperature |
| Cooling | -2.5°C max | 0.6× intensity | Lower temperature |
| Humidifying | +5% max | 2.0× intensity | Raise humidity |
| Dehumidifying | -8% max | 1.5× intensity | Lower humidity |
| Ventilation | -150 ppm CO2 max | 1.0× intensity | Reduce CO2 + humidity |
| Irrigation | +5 units max | 0.5× intensity | Water crops |
| Lighting | +500 µmol/m²/s max | 0.1× intensity | Artificial light |
| CO2 Enrichment | +200 ppm max | 1.5× intensity | Boost photosynthesis |

### Reward Structure

**Multi-objective reward function:**

```
Total Reward = Health + Improvement + Stability - ResourceCost - Penalties
```

Components:
- **Crop Health:** Direct measure (0.0-1.0)
- **Improvement:** Bonus if health increased this step
- **Stability:** Penalty for large swings in temperature/humidity
- **Resource Cost:** Energy + water consumption discounted
- **Penalties:** Mold (-10), freeze (-20), heat, death (-50)

**Typical ranges per step:**
- Perfect management: +0.8 to +1.2
- Good management: +0.3 to +0.6
- Poor management: -0.5 to +0.2
- Catastrophic failure: -60 to -70

### Task Definitions

#### Easy Task (10 episodes, 100 steps)
- **Environment:** Static, no weather disturbances
- **Resources:** Unlimited (no constraints)
- **Challenge:** Learn basic control and state-action relationships
- **Success Threshold:** Final crop health > 0.7
- **Score Weight:** 60% health + 30% success + 10% consistency

#### Medium Task (20 episodes, 200 steps)
- **Environment:** Weather varies ±5°C unpredictably
- **Resources:** Limited (energy, water budgets enforced)
- **Challenge:** React to disturbances while managing resources
- **Success Threshold:** Final crop health > 0.6
- **Score Weight:** 50% health + 30% adaptation + 20% success

#### Hard Task (30 episodes, 500 steps)
- **Environment:** Highly dynamic weather + unpredictable events
- **Resources:** Strict daily budgets (20 water/30 energy per day)
- **Challenge:** Plan ahead, optimize trade-offs, adapt to surprises
- **Success Threshold:** Final crop health > 0.5 + efficiency target
- **Score Weight:** 40% health + 40% efficiency + 20% success

### Scoring System

```
Task Score = Weighted combination of:
  - health_score (final crop health vs. threshold)
  - success_rate (% episodes meeting threshold)
  - efficiency_score / adaptation_score (task-specific)

Overall Score = Average(Easy, Medium, Hard)
  - If all ≥ 0.5: apply +5% consistency bonus
  - Final range: [0.0, 1.0]
  
Interpretation:
  0.85+     → World-class agent
  0.70-0.84 → Competent agent
  0.50-0.69 → Adequate agent
  <0.50     → Needs improvement
```

---

## 🤖 Agent Implementation

### Using the Baseline

The repository includes randomized baseline for testing:

```python
from inference import GreenhouseInference, RandomAgent

agent = RandomAgent()
inference = GreenhouseInference(agent)
results = inference.run_all_tasks()

print(f"Overall Score: {results['overall_score']:.3f}")
print(f"  Easy:   {results['easy_score']:.3f}")
print(f"  Medium: {results['medium_score']:.3f}")
print(f"  Hard:   {results['hard_score']:.3f}")
```

### Building Your Own Agent

Create a custom agent by subclassing `GreenhouseAgent`:

```python
from inference import GreenhouseAgent
import numpy as np

class MySmartAgent(GreenhouseAgent):
    def select_action(self, observation: np.ndarray) -> np.ndarray:
        """
        Select control action based on observation.
        
        Args:
            observation: 10D array [temp, humidity, CO2, light, 
                        water, energy, health, mold, time_of_day, day]
        
        Returns:
            action: 8D array [heating, cooling, humidify, dehumidify,
                   ventilation, irrigation, lighting, CO2_enrichment]
                   All values ∈ [0.0, 1.0]
        """
        temp, humidity, co2, light, water, energy, health, mold, time_of_day, day = observation
        
        # Example logic: simple feedback control
        action = np.zeros(8)
        
        # Heat if too cold
        if temp < 20:
            action[0] = (20 - temp) / 10  # heating intensity
        
        # Cool if too hot
        if temp > 24:
            action[1] = (temp - 24) / 10  # cooling intensity
        
        # Water if dry
        if water < 30:
            action[5] = 1.0  # irrigation at full
        
        # Return clipped to [0, 1]
        return np.clip(action, 0, 1)

# Evaluate your agent
if __name__ == "__main__":
    agent = MySmartAgent()
    inference = GreenhouseInference(agent)
    results = inference.run_all_tasks()
    print(f"Overall Score: {results['overall_score']:.3f}")
```

Then register in `app.py`:

```python
def get_agent(agent_type: str):
    if agent_type == "Random Baseline":
        return RandomAgent()
    elif agent_type == "My Smart Agent":
        from my_agents import MySmartAgent
        return MySmartAgent()
    else:
        return RandomAgent()
```

---

## 📁 Project Structure

```
greenhouse/
├── env/                          # Core simulation engine
│   ├── state.py                  # GreenhouseState (10D)
│   ├── actions.py                # ActionSpace (8D) 
│   ├── environment.py            # Gymnasium wrapper
│   ├── dynamics.py               # Physics simulation
│   ├── rewards.py                # Multi-objective reward
│   └── utils.py                  # Helpers
│
├── config/                       # Settings & profiles
│   ├── constants.py              # ~100 parameters
│   └── crop_profiles.py          # Tomato, lettuce, herbs
│
├── tasks/                        # Task definitions
│   ├── task_easy.py              # 10 episodes
│   ├── task_medium.py            # 20 episodes
│   ├── task_hard.py              # 30 episodes
│   └── graders.py                # Scoring logic
│
├── inference.py                  # CLI interface
├── app.py                        # Streamlit web UI
│
├── CLAUDE.md                     # System design (19K lines)
├── FRONTEND.md                   # Web UI guide (3.5K lines)
├── ARCHITECTURE.md               # System overview
├── QUICKSTART.md                 # Quick reference
├── README.md                     # This file
│
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container config
├── run_frontend.bat              # Windows launcher
└── run_frontend.ps1              # PowerShell launcher
```

---

## 🔧 Customization

### Adding a New Crop

Edit `config/crop_profiles.py`:

```python
RICE = {
    "name": "Rice",
    "optimal_temperature": 25,
    "optimal_humidity": 80,
    "optimal_co2": 800,
    "optimal_light": 500,
    "growth_rate": 0.02,
    "stress_sensitivity": 0.7,
    "disease_susceptibility": 0.6,
    "water_demand": "high",
    "freeze_threshold": 10,
    "max_health": 1.0,
}

CROP_REGISTRY["rice"] = RICE
```

### Changing Reward Weights

Edit `config/constants.py`:

```python
REWARD_WEIGHT_HEALTH = 1.5      # Prioritize health more
REWARD_WEIGHT_STABILITY = 0.8   # Value stability less
REWARD_WEIGHT_RESOURCE = 0.2    # Less penalty for resource use
```

### Adding a New Task

Create `tasks/task_custom.py`:

```python
from tasks.task_easy import EasyTask
from config.constants import *

class CustomTask(EasyTask):
    def __init__(self):
        self.name = "Custom"
        self.num_episodes = 15
        self.max_steps = 250
        self.difficulty = "custom"
```

---

## 🧪 Development

### Run Tests

```bash
python -m pytest  # (if using pytest)
```

### Check Code

```bash
python -m py_compile app.py
python -m py_compile inference.py
```

### Profile Performance

```bash
python -m cProfile inference.py
```

---

## 🐳 Docker Deployment

Build and run in container:

```bash
# Build image
docker build -t greenhouse-env .

# Run with web UI exposed on port 8501
docker run -p 8501:8501 greenhouse-env

# Or run CLI
docker run greenhouse-env python inference.py
```

---

## 📊 Example Results

**Random Baseline (10 trials):**
```
Easy Task (Stabilization):      Score 1.000
├─ Episodes: 10/10 success (100%)
├─ Avg final health: 0.82
└─ Notes: No strategy, but random tends to stabilize

Medium Task (Adaptation):       Score 1.000
├─ Episodes: 20/20 success (100%)
├─ Avg final health: 0.71
└─ Notes: Weather helps luck factor

Hard Task (Optimization):       Score 0.400
├─ Episodes: 6/30 success (20%)
├─ Avg final health: 0.42
├─ Avg efficiency: 0.08
└─ Notes: Resource constraints revealed limitation

OVERALL SCORE: 0.800
```

---

## 📖 Detailed Documentation

- **[CLAUDE.md](CLAUDE.md)** — Complete technical specification
  - System overview and design philosophy
  - Detailed state/action/reward definitions
  - Physics equations and dynamics
  - Task specifications and grading logic
  - File interaction map and execution diagrams
  
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design overview
  - ASCII architecture diagram
  - Component responsibilities
  - Data flow examples
  - Learning path (beginner → expert)

- **[FRONTEND.md](FRONTEND.md)** — Web UI guide
  - Feature overview
  - Installation instructions
  - UI customization
  - Troubleshooting

- **[QUICKSTART.md](QUICKSTART.md)** — Quick reference
  - Launch commands
  - Interface overview
  - Data export
  - Common tasks

---

## 🎓 Learning Resources

### For Beginners
1. Read QUICKSTART.md (5 min)
2. Launch web UI and explore Dashboard (10 min)
3. Run a Single Episode (10 min)
4. Look at Random Baseline results (5 min)

### For Intermediate Users
1. Read ARCHITECTURE.md (10 min)
2. Run Batch Evaluation to understand scoring (15 min)
3. Build a simple feedback controller agent
4. Compare your agent vs. baseline

### For Advanced Users
1. Study CLAUDE.md sections 3-6 (state/actions/dynamics/rewards) (2 hours)
2. Implement your own physics-aware agent
3. Extend with new crops or environmental factors
4. Contribute improvements!

---

## 🤝 Contributing

Contributions welcome! Areas for enhancement:

- [ ] Implement physics dynamics (12 functions in env/dynamics.py)
- [ ] Add advanced agent implementations (RL, MPC, etc.)
- [ ] Performance optimization
- [ ] Additional crop profiles
- [ ] Extended weather models
- [ ] Unit test suite

---

## 📝 License

MIT License — See LICENSE file for details.

---

## 🔗 References

- OpenEnv: https://github.com/openrlbenchmark/openenv
- Gymnasium: https://gymnasium.farama.org/
- Streamlit: https://streamlit.io/

---

## 📞 Support

For questions:
1. Check QUICKSTART.md or ARCHITECTURE.md
2. Review source code comments and docstrings
3. See TROUBLESHOOTING in FRONTEND.md

---

**Version:** 1.0 (April 2026)  
**Status:** Complete scaffold + working baseline + web UI  
**Next Steps:** Implement physics dynamics or add your own agent!

🌱 Happy farming!
