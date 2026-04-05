# Greenhouse Environment

AI-driven greenhouse operations simulator where an agent makes sequential decisions to optimize crop health and resource usage.

## Overview

This is a **real-world, non-toy OpenEnv environment** for sequential decision-making under uncertainty and constraints.

## Quick Start

### 🌐 Web UI (Recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Launch interactive dashboard
streamlit run app.py
```

Then open http://localhost:8501 in your browser!

**Features:**
- 📊 Real-time system dashboard
- 🎮 Single episode simulation with live plots
- 📈 Batch evaluation across all tasks
- 📥 CSV data export
- 🎨 Interactive visualizations

### 💻 Command Line

```bash
# Install dependencies
pip install -r requirements.txt

# Run evaluation
python inference.py
```

Returns grading report (0.0-1.0 scores).

### 🐳 Docker

```bash
docker build -t greenhouse-env .
docker run greenhouse-env
```

## Project Structure

- `env/` — Core environment (state, actions, dynamics, rewards)
- `tasks/` — Three graduated task definitions (easy/medium/hard)
- `config/` — Constants and crop profiles
- `app.py` — **Streamlit web interface** 🆕
- `inference.py` — Agent interface and CLI orchestrator
- `openenv.yaml` — OpenEnv configuration

## Tasks

1. **Easy** (10 episodes, 100 steps): Static stabilization
2. **Medium** (20 episodes, 200 steps): Adaptation to weather changes
3. **Hard** (30 episodes, 500 steps): Optimization under resource constraints

## Agent Interface

```python
from inference import GreenhouseInference, GreenhouseAgent
import numpy as np

class MyAgent(GreenhouseAgent):
    def select_action(self, observation: np.ndarray) -> np.ndarray:
        # Return action [0, 1]^8
        return np.random.uniform(0, 1, 8)

# Evaluate agent
agent = MyAgent()
inference = GreenhouseInference(agent)
results = inference.run_all_tasks()
print(f"Overall Score: {results['overall_score']:.3f}")
```

## State Space

10-dimensional continuous observation:
- Temperature, humidity, CO2, light intensity
- Water level, energy level
- Crop health, mold presence
- Time of day, day counter

## Action Space

8-dimensional continuous action [0, 1]^8:
- Heating, cooling, humidifying, dehumidifying
- Ventilation, irrigation, lighting, CO2 enrichment

## Reward Function

```
reward = crop_health + stability - resource_cost - penalties
```

Penalties for mold (−10), freeze damage (−20), crop death (−50).

## Documentation

- **CLAUDE.md** — Complete system documentation (state, dynamics, reward, tasks)
- **FRONTEND.md** — Web interface guide
- **requirements.txt** — Python dependencies
- **openenv.yaml** — Environment specification

## Results

### Baseline (Random Agent)

| Task | Score | Health | Efficiency |
|------|-------|--------|------------|
| Easy | 1.000 | 0.80 | N/A |
| Medium | 1.000 | 0.80 | N/A |
| Hard | 0.400 | 0.80 | 0.00 |
| **Overall** | **0.800** | — | — |

## Configuration

### Crop Profiles

Available crops: **tomato**, **lettuce**, **herbs** (with different optimal conditions)

```python
from config.crop_profiles import get_crop_profile
profile = get_crop_profile("tomato")
```

### Constants

Physical parameters in `config/constants.py`:
- Temperature bounds: 5°C to 40°C
- Humidity: 20% to 95%
- Energy/water budgets
- Action costs and effects

## Troubleshooting

**Import errors?**
```bash
pip install -r requirements.txt
```

**Port conflict on Streamlit?**
```bash
streamlit run app.py --server.port=8502
```

**Dynamics not working?**

Placeholder functions need implementation:
- `compute_temperature_delta()`
- `compute_humidity_delta()`
- `compute_crop_health_delta()`
- See CLAUDE.md for specifications

## Next Steps

1. ✅ Run the web UI: `streamlit run app.py`
2. 📊 Explore the dashboard and run episodes
3. 🤖 Implement custom agent (extend `GreenhouseAgent`)
4. 📈 Evaluate on hard task with resource optimization
5. 🔬 Tune reward weights and dynamics parameters

---

**Documentation:**
- System Design: See `CLAUDE.md`
- Web Interface: See `FRONTEND.md`
- API Reference: See docstrings in source code