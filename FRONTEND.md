"""
FRONTEND.md

Greenhouse Environment Web Interface

## Overview

A Streamlit-based interactive frontend for the greenhouse environment simulator.
Provides real-time visualization, episode simulation, and batch evaluation.

## Features

### 📊 Dashboard
- Real-time state monitoring
- Environmental metrics (temperature, humidity, CO2, light)
- Resource levels (water, energy)
- Crop health and disease status
- Gauge charts for quick status assessment

### 🎮 Single Episode
- Run individual episodes with live visualization
- Step-by-step monitoring
- Interactive plots for all state variables
- Reward tracking (per-step and cumulative)
- CSV export of episode data

### 📈 Batch Evaluation
- Evaluate agent across all three task difficulties
- Configurable number of episodes
- Statistical summaries
- Distribution charts (health, rewards)
- Comparative analysis across tasks
- Results export

## Installation

```bash
pip install -r requirements.txt
```

## Running the Frontend

### Streamlit App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

### Command-line Options

```bash
# Run with specific theme
streamlit run app.py --theme=dark

# Run on specific port
streamlit run app.py --server.port=8502

# Enable developer mode
streamlit run app.py --logger.level=debug
```

## User Interface Guide

### Navigation

The sidebar provides three main modes:

1. **📊 Dashboard** - Real-time monitoring view
   - Current state display
   - Gauge charts for quick assessment
   - Live resource monitors
   - Best for: Understanding current system state

2. **🎮 Single Episode** - Detailed episode simulation
   - Run an episode with full visualization
   - Adjust max steps
   - View step-by-step state evolution
   - Download data for analysis
   - Best for: Detailed analysis and debugging

3. **📈 Batch Evaluation** - Full evaluation suite
   - Run multiple episodes across all tasks
   - Compare performance
   - Statistical analysis
   - Generate reports
   - Best for: Agent evaluation and benchmarking

### Configuration

**Agent Selection**
- Random Baseline: Random action selection
- Custom (Placeholder): Hook for custom agents

**Task Difficulty**
- Easy: Static environment, 100 steps
- Medium: Weather disturbances, 200 steps
- Hard: Resource constraints, 500 steps

**Controls**
- Adjust max steps for episodes
- Toggle live updates
- Download results as CSV
- Export episode data

## Visualizations

### State Variables
- Temperature, humidity, CO2, light intensity
- Water level, energy level
- Crop health, mold presence
- Time-series plots with interactive hover

### Metrics
- Gauge charts for quick status
- Progress bars for resources
- Status indicators

### Rewards
- Per-step reward bars
- Cumulative reward line chart
- Total episode return

## Data Export

All modes support CSV export:

```csv
step,temperature,humidity,co2,light,water,energy,health,mold,reward,cumulative_reward
0,20.0,60.0,400.0,0.0,80.0,80.0,0.8,0.0,0.0,0.0
1,20.1,59.8,399.5,0.0,79.9,80.0,0.801,0.0,0.8,0.8
...
```

## Performance Tips

- Use Dashboard for continuous monitoring
- Use Single Episode for detailed analysis (up to 500 steps)
- Use Batch Evaluation with smaller episode counts (5-10) for quick testing
- Export data for post-analysis in Excel/Python

## Customization

### Adding Custom Agents

Edit `app.py` in the `get_agent()` function:

```python
def get_agent(agent_type: str):
    if agent_type == "Random Baseline":
        return RandomAgent()
    elif agent_type == "My Custom Agent":
        from my_agents import MyAgent
        return MyAgent()
    else:
        return RandomAgent()
```

Then add to Streamlit selectbox:

```python
agent_type = st.sidebar.selectbox(
    "Agent Type",
    ["Random Baseline", "My Custom Agent"],
)
```

### Styling

Modify the CSS in the `st.markdown()` section to customize colors, spacing, and fonts.

### Adding Plots

Use Plotly within the existing framework:

```python
fig = go.Figure()
fig.add_trace(go.Scatter(x=..., y=..., mode='lines'))
st.plotly_chart(fig, use_container_width=True)
```

## Troubleshooting

### Port Already in Use

```bash
streamlit run app.py --server.port=8502
```

### Slow Performance

- Reduce max steps in Single Episode mode
- Reduce episodes in Batch Evaluation mode
- Disable live updates (uncheck "Show Live Updates")

### Charts Not Displaying

- Clear browser cache
- Restart Streamlit: `Ctrl+C` then re-run
- Check console for errors (browser dev tools)

## Browser Compatibility

- Chrome/Chromium: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Edge: ✅ Full support

## Deployment

### Local

```bash
streamlit run app.py
```

### Docker

```bash
docker build -t greenhouse-ui .
docker run -p 8501:8501 greenhouse-ui
# Then visit http://localhost:8501
```

### Streamlit Cloud

```bash
# Push to GitHub, then deploy via Streamlit Cloud
```

## API Integration

The frontend uses the standard `GreenhouseInference` API:

```python
from inference import GreenhouseInference, RandomAgent

agent = RandomAgent()
inference = GreenhouseInference(agent)
results = inference.run_all_tasks()
```

All visualization is built on these standardized interfaces.

## Future Enhancements

- Real-time agent training visualization
- Custom agent upload
- A/B comparison mode
- Advanced analytics dashboard
- Multi-episode replay
- Performance profiling

## Support

For issues or feature requests, see CLAUDE.md for system documentation.
