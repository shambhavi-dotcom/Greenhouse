# Greenhouse OpenEnv Control System

A high-fidelity greenhouse simulation environment and dashboard aligned with the OpenEnv Problem Statement. This project enables testing and evaluating AI agents on resource-constrained, multi-variable agricultural control tasks.

## 🌿 Environment Overview

The Greenhouse environment challenges agents to maintain optimal growing conditions for different crops (`tomato`, `lettuce`, `herbs`, `cucumber`) through 8 continuous control actuators while managing limited water and energy stocks.

- **Simulation Engine**: Custom Gymnasium-compatible physics engine.
- **Complexity**: Stochastic weather disturbances, realistic humidity/CO2 dynamics, and cumulative crop health degradation.
- **Tasks**: 3 predefined tasks focusing on **Stabilization** (Easy), **Adaptation** (Medium), and **Optimization** (Hard).

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Dashboard (Streamlit)
```bash
streamlit run app.py
```
*The dashboard features real-time step playback for interactive episode viewing.*

### 3. Run Inference (PS-Compliant)
```bash
# Set your API keys and model
export HF_TOKEN="your_key"
export MODEL_NAME="gpt-4o-mini"
python inference.py
```

## 🛠️ OpenEnv Specification

This environment strictly follows the OpenEnv interface for automated evaluation.

### 🧩 Observation Space (10 Continuous Variables)
| Index | Name | Unit | Scale |
|---|---|---|---|
| 0 | Temperature | °C | -inf to +inf |
| 1 | Humidity | % | 0.0 to 100.0 |
| 2 | CO2 | ppm | 0.0 to 1000.0+ |
| 3 | Light Intensity | µmol | 0.0 to 1000.0+ |
| 4 | Water Level | units | 0.0 to 100.0 (Capacity) |
| 5 | Energy Level | units | 0.0 to 200.0 (Capacity) |
| 6 | Crop Health | score | 0.0 to 1.0 (0=Dead) |
| 7 | Mold Presence | score | 0.0 to 1.0 |
| 8 | Time of Day | norm | 0.0 to 1.0 (0=Midnight) |
| 9 | Day Counter | norm | 0.0 to 1.0 (1=365 Days) |

### 🕹️ Action Space (8 Continuous Control Actuators)
*All intensities are normalized from 0.0 (off) to 1.0 (full capacity).*
1. **Heating**: Increases temperature.
2. **Cooling**: Decreases temperature.
3. **Humidifying**: Increases humidity.
4. **Dehumidifying**: Decreases humidity.
5. **Ventilation**: Exchanges air (impacts CO2 and Humidity).
6. **Irrigation**: Adds water to soil/reservoir.
7. **Lighting**: Supplemental artificial lighting.
8. **CO2 Enrichment**: Direct CO2 injection.

### 📝 Typed Models (Pydantic)
- `GreenhouseObservation`: Typed sensory input.
- `GreenhouseAction`: Typed actuator commands.
- `GreenhouseReward`: Detailed reward breakdown.

## 📊 Evaluation & Scoring

Episodes are scored based on:
1. **Crop Health**: Primary reward component (1.0 weight).
2. **Stability**: Rewards keeping variables within optimal thresholds.
3. **Resource Efficiency**: Penalizes excessive energy and water usage.

The environment provides an `overall_score` (0.0 to 1.0) derived from performance across all three task difficulties.

## 📁 Repository Structure
- `env/`: Core physics and environment logic.
  - `models.py`: Pydantic V2 typed models.
  - `environment.py`: Gymnasium/OpenEnv interface class.
- `tasks/`: Logic for stabilization, adaptation, and optimization tasks.
- `scripts/`: Validation tools for submission.
- `app.py`: Real-time Streamlit visualization dashboard.
- `inference.py`: Standard baseline agent and evaluation script.
- `openenv.yaml`: Environment metadata for Hugging Face integration.

## 🧪 Validation

To ensure your environment is submission-ready, run:
```bash
python scripts/validate_submission.py https://your-space.hf.space
```

## 📜 License
MIT
