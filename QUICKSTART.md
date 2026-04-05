# Quick Start Guide

## 🚀 Running the Greenhouse Environment

### Start the Web Interface (Recommended)

**Option 1: PowerShell**
```powershell
.\run_frontend.ps1
```

**Option 2: Command Prompt**
```bash
run_frontend.bat
```

**Option 3: Direct Command**
```bash
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

---

## 📊 Web Interface Features

### Mode 1: 📊 Dashboard
**Real-time system monitoring**

- Live temperature, humidity, CO2, light readings
- Resource gauges (water, energy)
- Crop health status with visual indicators
- Mold detection status
- Optimal condition reference points

**Best for:** Understanding current system state at a glance

### Mode 2: 🎮 Single Episode
**Run and analyze a complete episode**

- Configurable max steps (10-500)
- Step-by-step visualization
- Interactive time-series charts:
  - Environmental variables (temp, humidity, CO2, light)
  - Resources (water, energy)
  - Crop state (health, mold)
  - Rewards (per-step and cumulative)
- CSV data export for external analysis

**Best for:** Debugging, detailed analysis, understanding agent behavior

### Mode 3: 📈 Batch Evaluation
**Full evaluation suite across all tasks**

- Auto-runs across Easy (10 eps), Medium (20), Hard (30)
- Statistical summary table
- Distribution charts (box plots)
- Comparative analysis
- Results export

**Best for:** Agent benchmarking and performance measurement

---

## 🎛️ Sidebar Controls

### Agent Selection
- **Random Baseline** — Random action selection (baseline)
- **Custom (Placeholder)** — Hook for your custom agent

### Task Difficulty
- **Easy** — Static environment, 100 steps
- **Medium** — Weather disturbances, 200 steps  
- **Hard** — Resource constraints, 500 steps

### Mode-Specific Controls
- **Dashboard:** Real-time display
- **Single Episode:** Max steps slider, live updates toggle
- **Batch:** Episodes per task slider, detailed results checkbox

---

## 💾 Data Export

All modes support CSV export:

```csv
step,temperature,humidity,co2,light,water,energy,health,mold,reward,cumulative_reward
0,20.0,60.0,400.0,0.0,80.0,80.0,0.8,0.0,0.0,0.0
1,20.1,59.8,399.5,0.0,79.9,80.0,0.801,0.0,0.8,0.8
...
```

Use for:
- Post-analysis in Excel/Pandas
- Performance visualization
- Report generation
- Data archival

---

## 📋 Command-Line Interface

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

## 🔧 Customization

### Adding Your Own Agent

1. Edit `app.py`, find the `get_agent()` function
2. Add your agent import and logic:

```python
def get_agent(agent_type: str):
    if agent_type == "Random Baseline":
        return RandomAgent()
    elif agent_type == "My Smart Agent":
        from my_agents import SmartAgent
        return SmartAgent()
    else:
        return RandomAgent()
```

3. Update the Streamlit selectbox:

```python
agent_type = st.sidebar.selectbox(
    "Agent Type",
    ["Random Baseline", "My Smart Agent"],
)
```

Your agent will now appear in the sidebar!

### Changing Default Settings

Edit `app.py` defaults:
```python
difficulty = st.sidebar.selectbox(
    "Task Difficulty",
    ["Easy", "Medium", "Hard"],
    index=1  # Default: Medium (was 0=Easy)
)

num_episodes = st.slider(
    "Episodes per Task",
    min_value=1,
    max_value=30,
    value=10,  # Change from 5 to 10
)
```

---

## 🌐 Accessing the UI from Another Computer

By default, Streamlit only listens on localhost. To access from another machine:

```bash
streamlit run app.py --server.address=0.0.0.0
```

Then access from another computer:
```
http://<your-machine-ip>:8501
```

**Warning:** This makes the UI accessible to all computers on your network!

---

## ⚡ Performance Tips

| Task | Recommended | Max |
|------|------------|-----|
| Dashboard | Real-time | N/A |
| Single Episode | 100 steps | 500 steps |
| Batch Evaluation | 5 episodes | 30 episodes |

**For Quick Testing:**
- Dashboard: Always fast
- Single Episode: Use 50-100 max steps
- Batch: Use 3-5 episodes per task

---

## 🐛 Troubleshooting

### Port 8501 Already In Use
```bash
streamlit run app.py --server.port=8502
```

### Slow Performance
- Reduce number of episodes in Batch Evaluation
- Reduce max steps in Single Episode
- Close other browser tabs
- Disable live updates (uncheck box)

### Charts Not Showing
- Clear browser cache (Ctrl+Shift+Delete)
- Restart Streamlit (Ctrl+C, then re-run)
- Try different browser

### Import Errors
```bash
pip install -r requirements.txt
python -m streamlit --version
```

---

## 📚 Documentation

- **CLAUDE.md** — Complete system design (state, dynamics, reward, grading)
- **FRONTEND.md** — Detailed web UI guide
- **README.md** — Overview and usage
- **Source Code** — Docstrings in every function/class

---

## 🎯 Next Steps

1. ✅ Start frontend: `streamlit run app.py`
2. 📊 Explore Dashboard (get familiar with state variables)
3. 🎮 Run a Single Episode (watch the agent control the greenhouse)
4. 📈 Run Batch Evaluation (see overall performance)
5. 🤖 Implement your own agent and test it

---

Happy farming! 🌱
