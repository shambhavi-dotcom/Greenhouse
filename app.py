"""
app.py

Streamlit frontend for the greenhouse environment.
Provides interactive visualization, real-time monitoring, and episode simulation.

Features:
- Real-time state visualization
- Episode simulation with live plots
- Agent selection and configuration
- Metric tracking and analysis
- Task comparison and grading
"""

import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any

from inference import GreenhouseInference, RandomAgent
from env.environment import GreenhouseEnv, GreenhouseEasyEnv, GreenhouseMediumEnv, GreenhouseHardEnv
from config import constants, crop_profiles


# ============================================================================
# PAGE SETUP
# ============================================================================

st.set_page_config(
    page_title="🌱 Greenhouse AI Control",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme configuration
st.markdown("""
<style>
    .main { padding: 2rem; }
    .metric-card { 
        background-color: #f0f2f6; 
        padding: 1.5rem; 
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .status-healthy { color: #09ab3b; font-weight: bold; }
    .status-warning { color: #ff9800; font-weight: bold; }
    .status-critical { color: #f44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================

st.sidebar.title("🌱 Greenhouse Control")
st.sidebar.markdown("---")

# Mode selection
mode = st.sidebar.radio(
    "Select Mode",
    ["📊 Dashboard", "🎮 Single Episode", "📈 Batch Evaluation"],
    help="Choose what you want to do"
)

# Agent selection
agent_type = st.sidebar.selectbox(
    "Agent Type",
    ["Random Baseline", "Custom (Placeholder)"],
    help="Select the agent to use"
)

# Difficulty selection
difficulty = st.sidebar.selectbox(
    "Task Difficulty",
    ["Easy", "Medium", "Hard"],
    help="Choose task complexity"
)

st.sidebar.markdown("---")
st.sidebar.info("""
**How to use:**
1. Select mode (Dashboard/Episode/Batch)
2. Choose agent and difficulty
3. Configure parameters
4. Run simulation
5. View results and plots
""")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent(agent_type: str):
    """Get agent instance by type."""
    if agent_type == "Random Baseline":
        return RandomAgent()
    else:
        return RandomAgent()  # Placeholder


def get_environment(difficulty: str):
    """Get environment instance by difficulty."""
    if difficulty == "Easy":
        return GreenhouseEasyEnv()
    elif difficulty == "Medium":
        return GreenhouseMediumEnv()
    else:
        return GreenhouseHardEnv()


def run_episode(env, agent, max_steps: int = None):
    """Run a single episode and collect data."""
    obs, info = env.reset()
    
    episode_data = {
        "step": [],
        "temperature": [],
        "humidity": [],
        "co2": [],
        "light": [],
        "water": [],
        "energy": [],
        "health": [],
        "mold": [],
        "reward": [],
        "cumulative_reward": [],
    }
    
    done = False
    step = 0
    cumulative_reward = 0.0
    
    max_steps = max_steps or env.max_episode_steps
    
    while not done and step < max_steps:
        # Agent selects action
        action = agent.select_action(obs)
        
        # Environment step
        obs, reward, terminated, truncated, info = env.step(action)
        cumulative_reward += reward
        done = terminated or truncated
        
        # Collect data
        episode_data["step"].append(step)
        episode_data["temperature"].append(env.state.temperature)
        episode_data["humidity"].append(env.state.humidity)
        episode_data["co2"].append(env.state.co2)
        episode_data["light"].append(env.state.light_intensity)
        episode_data["water"].append(env.state.water_level)
        episode_data["energy"].append(env.state.energy_level)
        episode_data["health"].append(env.state.crop_health)
        episode_data["mold"].append(env.state.mold_presence)
        episode_data["reward"].append(reward)
        episode_data["cumulative_reward"].append(cumulative_reward)
        
        step += 1
    
    return episode_data, env.state


def get_health_status(health: float) -> str:
    """Get status emoji and color for health value."""
    if health >= 0.8:
        return "🟢 Thriving", "status-healthy"
    elif health >= 0.6:
        return "🟡 Healthy", "status-warning"
    elif health >= 0.4:
        return "🟠 Stressed", "status-warning"
    else:
        return "🔴 Critical", "status-critical"


def get_mold_status(mold: float) -> str:
    """Get status for mold presence."""
    if mold < 0.2:
        return "✅ None"
    elif mold < 0.5:
        return "⚠️ Detected"
    else:
        return "🚨 Critical"


def create_state_gauge(value: float, min_val: float, max_val: float, title: str):
    """Create a gauge chart for a state variable."""
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [min_val, (max_val + min_val) / 3], "color": "lightgray"},
                {"range": [(max_val + min_val) / 3, 2 * (max_val + min_val) / 3], "color": "gray"},
                {"range": [2 * (max_val + min_val) / 3, max_val], "color": "lightgreen"}
            ],
        }
    )])
    fig.update_layout(height=300)
    return fig


def create_timeseries_chart(episode_data: Dict, variables: List[str], title: str):
    """Create interactive timeseries chart."""
    df = pd.DataFrame(episode_data)
    
    fig = make_subplots(
        rows=len(variables),
        cols=1,
        subplot_titles=variables,
        shared_xaxes=True,
        vertical_spacing=0.08
    )
    
    colors = px.colors.qualitative.Plotly
    for i, var in enumerate(variables, 1):
        fig.add_trace(
            go.Scatter(
                x=df["step"],
                y=df[var],
                mode="lines+markers",
                name=var,
                line=dict(color=colors[(i-1) % len(colors)]),
                marker=dict(size=4)
            ),
            row=i,
            col=1
        )
        fig.update_yaxes(title_text=var, row=i, col=1)
    
    fig.update_xaxes(title_text="Step", row=len(variables), col=1)
    fig.update_layout(height=300 * len(variables), showlegend=False)
    return fig


def create_rewards_chart(episode_data: Dict):
    """Create reward visualization."""
    df = pd.DataFrame(episode_data)
    
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=["Per-Step Reward", "Cumulative Reward"]
    )
    
    # Per-step rewards
    fig.add_trace(
        go.Bar(
            x=df["step"],
            y=df["reward"],
            name="Step Reward",
            marker_color="royalblue"
        ),
        row=1,
        col=1
    )
    
    # Cumulative rewards
    fig.add_trace(
        go.Scatter(
            x=df["step"],
            y=df["cumulative_reward"],
            mode="lines+markers",
            name="Cumulative Reward",
            line=dict(color="darkgreen"),
            marker=dict(size=5)
        ),
        row=1,
        col=2
    )
    
    fig.update_xaxes(title_text="Step", row=1, col=1)
    fig.update_xaxes(title_text="Step", row=1, col=2)
    fig.update_yaxes(title_text="Reward", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative Reward", row=1, col=2)
    fig.update_layout(height=400, showlegend=False)
    return fig


# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

if mode == "📊 Dashboard":
    st.title("🌱 Greenhouse Dashboard")
    st.markdown("Real-time monitoring and system overview")
    
    # Create three columns for key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Generate current state for demo
    env = get_environment(difficulty)
    obs, _ = env.reset()
    
    # Simulate a few steps
    agent = get_agent(agent_type)
    for _ in range(50):
        action = agent.select_action(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break
    
    # Display key metrics
    with col1:
        health_status, health_color = get_health_status(env.state.crop_health)
        st.metric("🌿 Crop Health", f"{env.state.crop_health:.2f}", delta=None)
        st.markdown(f"<p class='{health_color}'>{health_status}</p>", unsafe_allow_html=True)
    
    with col2:
        st.metric("🌡️ Temperature", f"{env.state.temperature:.1f}°C", delta=None)
        optimal_temp = 22.0
        deviation = abs(env.state.temperature - optimal_temp)
        st.caption(f"Optimal: {optimal_temp}°C (Dev: {deviation:.1f}°C)")
    
    with col3:
        st.metric("💧 Humidity", f"{env.state.humidity:.1f}%", delta=None)
        optimal_humidity = 65.0
        st.caption(f"Optimal: {optimal_humidity}%")
    
    with col4:
        mold_status = get_mold_status(env.state.mold_presence)
        st.metric("🦠 Mold Presence", f"{env.state.mold_presence:.3f}", delta=None)
        st.caption(mold_status)
    
    st.markdown("---")
    
    # Resource levels
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💧 Water Level")
        water_pct = (env.state.water_level / constants.WATER_CAPACITY) * 100
        st.progress(water_pct / 100)
        st.caption(f"{env.state.water_level:.1f} / {constants.WATER_CAPACITY} units ({water_pct:.1f}%)")
    
    with col2:
        st.subheader("⚡ Energy Level")
        energy_pct = (env.state.energy_level / constants.ENERGY_CAPACITY) * 100
        st.progress(energy_pct / 100)
        st.caption(f"{env.state.energy_level:.1f} / {constants.ENERGY_CAPACITY} units ({energy_pct:.1f}%)")
    
    st.markdown("---")
    
    # Environmental factors
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        fig = create_state_gauge(env.state.temperature, constants.TEMP_MIN, constants.TEMP_MAX, "Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_state_gauge(env.state.humidity, constants.HUMIDITY_MIN, constants.HUMIDITY_MAX, "Humidity (%)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = create_state_gauge(env.state.co2, constants.CO2_MIN, constants.CO2_MAX, "CO2 (ppm)")
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        fig = create_state_gauge(env.state.light_intensity, constants.LIGHT_MIN, constants.LIGHT_MAX, "Light (µmol/m²/s)")
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.info("💡 Tip: Use the controls in the sidebar to switch modes, select agent, and change difficulty!")


# ============================================================================
# PAGE: SINGLE EPISODE
# ============================================================================

elif mode == "🎮 Single Episode":
    st.title("🎮 Run Single Episode")
    st.markdown("Simulate a complete episode with visualization")
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_steps = st.number_input(
            "Max Steps",
            min_value=10,
            max_value=500,
            value=100,
            help="Maximum number of steps in episode"
        )
    
    with col2:
        show_live = st.checkbox("Show Live Updates", value=True)
    
    with col3:
        run_button = st.button("▶️ Run Episode", key="run_episode")
    
    st.markdown("---")
    
    if run_button:
        st.info("🚀 Running episode...")
        
        # Get environment and agent
        env = get_environment(difficulty)
        agent = get_agent(agent_type)
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Run episode with progress updates
        episode_data, final_state = run_episode(env, agent, max_steps)
        
        progress_bar.progress(1.0)
        status_text.success("✅ Episode completed!")
        
        st.markdown("---")
        st.subheader("📊 Episode Results")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Final Health", f"{final_state.crop_health:.3f}")
        
        with col2:
            st.metric("Episode Length", len(episode_data["step"]))
        
        with col3:
            total_reward = episode_data["cumulative_reward"][-1] if episode_data["cumulative_reward"] else 0
            st.metric("Total Reward", f"{total_reward:.2f}")
        
        with col4:
            final_health_status, _ = get_health_status(final_state.crop_health)
            st.metric("Status", final_health_status)
        
        st.markdown("---")
        
        # Timestamped visualizations
        st.subheader("📈 State Variables Over Time")
        
        # Key environmental variables
        fig = create_timeseries_chart(
            episode_data,
            ["temperature", "humidity", "co2", "light"],
            "Environmental Variables"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Resources
        fig = create_timeseries_chart(
            episode_data,
            ["water", "energy"],
            "Resources"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Crop health and mold
        fig = create_timeseries_chart(
            episode_data,
            ["health", "mold"],
            "Crop State"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Rewards
        st.subheader("🎯 Rewards")
        fig = create_rewards_chart(episode_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # Download data
        df = pd.DataFrame(episode_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Episode Data (CSV)",
            data=csv,
            file_name=f"episode_{difficulty.lower()}.csv",
            mime="text/csv"
        )


# ============================================================================
# PAGE: BATCH EVALUATION
# ============================================================================

elif mode == "📈 Batch Evaluation":
    st.title("📈 Batch Evaluation")
    st.markdown("Run full evaluation across all tasks")
    
    # Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        num_episodes = st.slider(
            "Episodes per Task",
            min_value=1,
            max_value=30,
            value=5,
            help="Number of episodes for evaluation"
        )
    
    with col2:
        show_detailed = st.checkbox("Show Detailed Results", value=True)
    
    run_eval_button = st.button("▶️ Start Evaluation", key="run_eval")
    
    st.markdown("---")
    
    if run_eval_button:
        st.info("🚀 Running batch evaluation...")
        
        # Get agent
        agent = get_agent(agent_type)
        
        # Container for progress
        progress_container = st.container()
        results_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # Run evaluations
        evaluation_results = {
            "easy": [],
            "medium": [],
            "hard": []
        }
        
        difficulties_list = ["Easy", "Medium", "Hard"]
        task_keys = ["easy", "medium", "hard"]
        
        for difficulty_idx, (difficulty, task_key) in enumerate(zip(difficulties_list, task_keys)):
            st.info(f"Running {difficulty} task ({num_episodes} episodes)...")
            
            for ep in range(num_episodes):
                env = get_environment(difficulty)
                episode_data, final_state = run_episode(env, agent)
                
                result = {
                    "episode": ep + 1,
                    "health": final_state.crop_health,
                    "reward": episode_data["cumulative_reward"][-1] if episode_data["cumulative_reward"] else 0,
                    "steps": len(episode_data["step"]),
                }
                evaluation_results[task_key].append(result)
                
                # Update progress
                total_progress = (difficulty_idx * num_episodes + ep + 1) / (len(difficulties_list) * num_episodes)
                progress_bar.progress(total_progress)
                status_text.text(f"{difficulty} - Episode {ep+1}/{num_episodes}")
            
            st.success(f"✅ {difficulty} task completed!")
        
        progress_bar.progress(1.0)
        status_text.success("✅ Evaluation completed!")
        
        st.markdown("---")
        st.subheader("📊 Results Summary")
        
        # Summary table
        summary_data = []
        for task_key, difficulty in zip(task_keys, difficulties_list):
            results = evaluation_results[task_key]
            avg_health = np.mean([r["health"] for r in results])
            avg_reward = np.mean([r["reward"] for r in results])
            success_rate = sum(1 for r in results if r["health"] > 0.5) / len(results)
            
            summary_data.append({
                "Task": difficulty,
                "Avg Health": f"{avg_health:.3f}",
                "Avg Reward": f"{avg_reward:.2f}",
                "Success Rate": f"{success_rate:.1%}",
                "Episodes": len(results)
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed charts
        if show_detailed:
            st.subheader("📈 Detailed Results")
            
            # Health by task
            col1, col2 = st.columns(2)
            
            with col1:
                health_data = []
                for task_key, difficulty in zip(task_keys, difficulties_list):
                    results = evaluation_results[task_key]
                    for r in results:
                        health_data.append({"Task": difficulty, "Health": r["health"]})
                
                if health_data:
                    health_df = pd.DataFrame(health_data)
                    fig = px.box(health_df, x="Task", y="Health", color="Task", title="Crop Health Distribution")
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                reward_data = []
                for task_key, difficulty in zip(task_keys, difficulties_list):
                    results = evaluation_results[task_key]
                    for r in results:
                        reward_data.append({"Task": difficulty, "Reward": r["reward"]})
                
                if reward_data:
                    reward_df = pd.DataFrame(reward_data)
                    fig = px.box(reward_df, x="Task", y="Reward", color="Task", title="Episode Reward Distribution")
                    st.plotly_chart(fig, use_container_width=True)
        
        # Download results
        results_df = pd.DataFrame(summary_data)
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Evaluation Results (CSV)",
            data=csv,
            file_name="evaluation_results.csv",
            mime="text/csv"
        )


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.8rem;'>
    🌱 Greenhouse AI Environment | OpenEnv Compatible | Sequential Decision-Making Simulator
    <br>
    <a href='https://github.com'>Documentation</a> • 
    <a href='https://github.com'>GitHub</a> • 
    <a href='https://github.com'>Report Issue</a>
</div>
""", unsafe_allow_html=True)
