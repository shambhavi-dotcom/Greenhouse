"""Streamlit frontend for the greenhouse simulator — real-time step playback."""

import time
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List

from inference import RandomAgent, SetpointAgent
from env.environment import GreenhouseEnv
from env.state import INITIAL_CONDITION_PRESETS
from config import constants


# ============================================================================
# PAGE SETUP
# ============================================================================

st.set_page_config(
    page_title="Greenhouse AI Control",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { padding: 1.5rem; background: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
        border: 1px solid #2d3561;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
    }
    .status-healthy  { color: #00e676; font-weight: 600; }
    .status-warning  { color: #ffab40; font-weight: 600; }
    .status-critical { color: #ff5252; font-weight: 600; }
    .step-badge {
        display: inline-block;
        background: #2d3561;
        color: #7c8cf8;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    div[data-testid="stProgress"] > div > div { background: linear-gradient(90deg, #7c8cf8, #00e676); }
    .stButton > button {
        background: linear-gradient(135deg, #7c8cf8 0%, #5c6bc0 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(124,140,248,0.4); }
</style>
""", unsafe_allow_html=True)


CROPS = ["tomato", "lettuce", "herbs", "cucumber"]
PRESET_KEYS = list(INITIAL_CONDITION_PRESETS.keys())

st.sidebar.title("🌱 Greenhouse AI Control")
mode = st.sidebar.radio("Mode", ["📊 Dashboard", "🎮 Single Episode"])
difficulty = st.sidebar.selectbox("Task Difficulty", ["Easy", "Medium", "Hard"])
crop_view = st.sidebar.selectbox("Crop", CROPS)
st.sidebar.markdown("---")

# ── Initial Condition Selector ────────────────────────────────────────────────
st.sidebar.markdown("**🌱 Initial Crop Condition**")
initial_condition = st.sidebar.radio(
    "Starting health tier:",
    PRESET_KEYS,
    index=0,
    help="Sets the crop health and matching environmental conditions at episode start.",
)
_preset = INITIAL_CONDITION_PRESETS[initial_condition]
st.sidebar.markdown(
    f"""
    <div style='background:#1a1f2e;border-left:3px solid {_preset["color"]};padding:8px 12px;
    border-radius:6px;margin-top:4px;margin-bottom:8px;'>
        <span style='color:{_preset["color"]};font-weight:600;'>● {_preset["label"]}</span><br/>
        <span style='color:#aaa;font-size:0.82rem;'>
        Start temp: <b>{_preset["temperature"]}°C</b> &nbsp;·&nbsp;
        Health: <b>{int(_preset["health"]*100)}%</b>
        </span><br/>
        <span style='color:#888;font-size:0.78rem;'>{_preset["description"]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
st.sidebar.markdown("**🤖 Controller Configuration**")
agent_type = st.sidebar.selectbox(
    "Agent Architecture",
    ["Setpoint (Logical Control)", "Random (Noise)"],
    index=0,
    help="Logical: proportional control with mutual exclusion. Random: random actions."
)
step_delay = st.sidebar.slider("Step Speed (ms)", min_value=0, max_value=200, value=30,
                               help="Delay between live steps in milliseconds")
st.sidebar.caption("One run produces results for all 4 crops. Use Crop to switch views.")
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Environment API**
- `reset()` → initial obs
- `step(action)` → obs, reward, done
- `get_state()` → typed model
""")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_agent():
    if "Random" in agent_type:
        return RandomAgent()
    return SetpointAgent()


def get_environment(diff: str, crop: str) -> GreenhouseEnv:
    if diff == "Easy":
        return GreenhouseEnv(crop=crop, max_episode_steps=100,
                             include_weather=False, include_resource_limits=False, difficulty="easy")
    if diff == "Medium":
        return GreenhouseEnv(crop=crop, max_episode_steps=200,
                             include_weather=True, include_resource_limits=True, difficulty="medium")
    return GreenhouseEnv(crop=crop, max_episode_steps=300,
                         include_weather=True, include_resource_limits=True, difficulty="hard")


def get_health_status(health: float):
    if health >= 0.8:
        return "🟢 Thriving", "status-healthy"
    elif health >= 0.6:
        return "🟡 Healthy", "status-warning"
    elif health >= 0.4:
        return "🟠 Stressed", "status-warning"
    else:
        return "🔴 Critical", "status-critical"


def create_live_chart(episode_data: Dict, variables: List[str], title: str, height: int = 280):
    df = pd.DataFrame(episode_data)
    if df.empty or "step" not in df.columns:
        return go.Figure()

    fig = make_subplots(
        rows=len(variables), cols=1,
        subplot_titles=variables,
        shared_xaxes=True,
        vertical_spacing=0.06,
    )
    palette = ["#7c8cf8", "#00e676", "#ffab40", "#ff5252", "#40c4ff", "#ea80fc", "#ffd740", "#69f0ae"]
    for i, var in enumerate(variables, 1):
        if var in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["step"], y=df[var],
                    mode="lines",
                    name=var,
                    line=dict(color=palette[(i - 1) % len(palette)], width=2),
                    fill="tozeroy",
                    fillcolor=f"rgba{tuple(list(int(palette[(i-1)%len(palette)].lstrip('#')[j:j+2],16) for j in (0,2,4))+[0.08])}",
                ),
                row=i, col=1,
            )
            fig.update_yaxes(title_text=var, row=i, col=1,
                             title_font=dict(size=10), showgrid=True,
                             gridcolor="#1e2535", title_standoff=4)
    fig.update_xaxes(title_text="Step", row=len(variables), col=1, showgrid=True, gridcolor="#1e2535")
    fig.update_layout(
        height=height * len(variables),
        showlegend=False,
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#c9d1d9"),
        margin=dict(l=10, r=10, t=30, b=10),
        title=dict(text=title, font=dict(size=13, color="#7c8cf8")),
    )
    return fig


def create_rewards_chart(episode_data: Dict):
    df = pd.DataFrame(episode_data)
    if df.empty:
        return go.Figure()

    fig = make_subplots(rows=1, cols=2, subplot_titles=["Per-Step Reward", "Cumulative Reward"])
    fig.add_trace(
        go.Bar(x=df["step"], y=df["reward"], name="Step Reward",
               marker_color="#7c8cf8", marker_line_width=0),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["step"], y=df["cumulative_reward"], mode="lines+markers",
                   name="Cumulative", line=dict(color="#00e676", width=2), marker=dict(size=4)),
        row=1, col=2,
    )
    fig.update_layout(
        height=320, showlegend=False,
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#c9d1d9"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    for ax in ["xaxis", "xaxis2", "yaxis", "yaxis2"]:
        fig.update_layout(**{ax: dict(gridcolor="#1e2535")})
    return fig


def create_state_gauge(value: float, min_val: float, max_val: float, title: str):
    mid = (min_val + max_val) / 2
    fig = go.Figure(data=[go.Indicator(
        mode="gauge+number",
        value=value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 12, "color": "#c9d1d9"}},
        number={"font": {"color": "#7c8cf8", "size": 20}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickcolor": "#c9d1d9"},
            "bar": {"color": "#7c8cf8"},
            "bgcolor": "#1a1f2e",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val, mid], "color": "#1e2535"},
                {"range": [mid, max_val], "color": "#2d3561"},
            ],
        },
    )])
    fig.update_layout(
        height=220, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="#0e1117", font=dict(color="#c9d1d9"),
    )
    return fig


def empty_episode_data():
    return {
        "step": [], "temperature": [], "humidity": [], "co2": [],
        "light": [], "water": [], "energy": [], "health": [],
        "reward": [], "cumulative_reward": [],
        "heating": [], "cooling": [], "humidify": [], "dehumidify": [],
        "ventilation": [], "irrigation": [], "lighting": [], "co2_enrich": [],
    }


# (Batch execution logic removed)


# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

if mode == "📊 Dashboard":
    st.title("🌱 Greenhouse Live Dashboard")
    st.caption("Real-time snapshot across all sensors for the selected crop and difficulty.")

    env = get_environment(difficulty, crop_view)
    obs, _ = env.reset(initial_condition=initial_condition)
    # Dashboard now shows the FRESH state from step 0 to prove the physics are correct

    col1, col2, col3, col4 = st.columns(4)
    s = env.state()
    health_status, health_color = get_health_status(s.crop_health)
    
    with col1:
        st.metric("🌿 Crop Health", f"{s.crop_health:.3f}")
        st.markdown(f"<p class='{health_color}'>{health_status}</p>", unsafe_allow_html=True)
    with col2:
        st.metric("🕰️ Current Time", f"Day {s.day_counter}, {s.time_of_day:02}:00 h")
        dev = abs(s.temperature - 22.0)
        st.caption(f"Optimal 22°C | Deviation: {dev:.1f}°C")
    with col3:
        st.metric("💧 Humidity", f"{s.humidity:.1f}%")
        st.caption("Optimal: 65%")
    with col4:
        st.metric("💦 Soil Moisture", f"{s.water_level:.1f}")
        st.caption(f"Capacity: {constants.WATER_CAPACITY}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    s = env.state()
    with col1:
        st.subheader("💧 Water Reservoir")
        water_pct = s.water_level / constants.WATER_CAPACITY
        st.progress(water_pct)
        st.caption(f"{s.water_level:.1f} / {constants.WATER_CAPACITY} ({water_pct*100:.1f}%)")
    with col2:
        st.subheader("⚡ Energy Level")
        energy_pct = s.energy_level / constants.ENERGY_CAPACITY
        st.progress(energy_pct)
        st.caption(f"{s.energy_level:.1f} / {constants.ENERGY_CAPACITY} ({energy_pct*100:.1f}%)")

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    s = env.state()
    with col1:
        st.plotly_chart(create_state_gauge(s.temperature, constants.TEMP_MIN, constants.TEMP_MAX, "Temp (°C)"), use_container_width=True)
    with col2:
        st.plotly_chart(create_state_gauge(s.humidity, constants.HUMIDITY_MIN, constants.HUMIDITY_MAX, "Humidity (%)"), use_container_width=True)
    with col3:
        st.plotly_chart(create_state_gauge(s.co2, constants.CO2_MIN, constants.CO2_MAX, "CO₂ (ppm)"), use_container_width=True)
    with col4:
        st.plotly_chart(create_state_gauge(s.light_intensity, constants.LIGHT_MIN, constants.LIGHT_MAX, "Light (µmol)"), use_container_width=True)

    st.markdown("---")
    st.info("💡 **OpenEnv API:** `env.reset()` · `env.step(action)` · `env.get_state()` → typed `GreenhouseObservation`")

    # Typed state showcase
    with st.expander("🔬 View Typed State (GreenhouseObservation)"):
        typed_obs = env.get_state()
        st.json(typed_obs.model_dump())


# ============================================================================
# PAGE: SINGLE EPISODE  — REAL-TIME STEP PLAYBACK
# ============================================================================

elif mode == "🎮 Single Episode":
    st.subheader("🎮 Single Episode Simulation")
    st.caption("Execute a multi-hour simulation episode with the selected controller.")

    col1, col2, col3 = st.columns([1.5, 1, 0.5])
    with col1:
        simulation_hours = st.slider("Simulation Duration (Hours)", min_value=12, max_value=240, value=72, step=12)
    with col2:
        render_mode = st.radio("Render Style", ["Live Charts", "Final Summary Only"], horizontal=True)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True) # Spacer for alignment
        run_button = st.button("▶️ Run", key="run_episode", use_container_width=True)
    
    selected_crop = st.selectbox("Crop for Live View", CROPS, index=CROPS.index(crop_view))

    # ── Preset info banner ─────────────────────────────────────────────────────
    _p = INITIAL_CONDITION_PRESETS[initial_condition]
    _diff_note = {"Easy": "💡 Unlimited resources", "Medium": "⚖️ Moderate resource budget", "Hard": "🔋 Tight energy budget + weather"}.get(difficulty, "")
    st.markdown(
        f"""
        <div style='background:#1a1f2e;border:1px solid {_p["color"]}33;
        border-left:4px solid {_p["color"]};padding:10px 16px;border-radius:8px;margin-bottom:12px;'>
            <b style='color:{_p["color"]};'>Starting Condition:</b>
            <span style='color:#c9d1d9;'>
            &nbsp;{initial_condition} &nbsp;·&nbsp;
            Start Temp: <b>{_p["temperature"]}°C</b> &nbsp;·&nbsp;
            Crop Health: <b>{int(_p["health"]*100)}%</b> &nbsp;·&nbsp;
            Resources: <b>Full</b>
            </span>
            &nbsp;&nbsp;<span style='color:#888;font-size:0.85rem;'>{_diff_note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if run_button:
        agent = get_agent()
        env = get_environment(difficulty, selected_crop)
        obs, info = env.reset(initial_condition=initial_condition)

        # ── Live metric placeholders ──────────────────────────────────────
        st.subheader("⚡ Live Step Metrics")
        live_col1, live_col2, live_col3, live_col4, live_col5 = st.columns(5)
        metric_health = live_col1.empty()
        metric_temp   = live_col2.empty()
        metric_humid  = live_col3.empty()
        metric_reward = live_col4.empty()
        metric_step   = live_col5.empty()

        progress_bar = st.progress(0.0)
        status_text  = st.empty()

        # ── Chart placeholders ────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📈 Live State Traces")
        chart_env     = st.empty()   # env variables chart
        chart_health  = st.empty()   # crop health chart
        chart_actions = st.empty()   # actions chart
        chart_rewards = st.empty()   # rewards chart
        reasoning_container = st.empty()   # reasoning panel

        # ── Run loop ──────────────────────────────────────────────────────
        episode_data = empty_episode_data()
        done = False
        step = 0
        cumulative_reward = 0.0
        
        while not done and step < simulation_hours:
            # 1. Select and execute action
            action = agent.select_action(obs)
            obs, reward, terminated, truncated, step_info = env.step(action)
            cumulative_reward += reward
            done = terminated or truncated
            s = env.state()

            # 2. Update live metrics
            health_label, _ = get_health_status(s.crop_health)
            metric_health.metric("🌿 Health",  f"{s.crop_health:.3f}")
            metric_temp.metric("🌡️ Temp",      f"{s.temperature:.1f}°C")
            metric_humid.metric("💧 Humidity", f"{s.humidity:.1f}%")
            metric_reward.metric("🎯 Reward",  f"{cumulative_reward:.2f}")
            metric_step.metric("📍 Duration",  f"{step + 1} / {simulation_hours} h")

            progress_bar.progress(min((step + 1) / simulation_hours, 1.0))
            status_text.markdown(
                f"<span class='step-badge'>Hour {step+1}</span>  "
                f"Health: **{s.crop_health:.3f}** · "
                f"Temp: **{s.temperature:.1f}°C** · "
                f"Reward: **{reward:+.3f}**",
                unsafe_allow_html=True,
            )

            # 3. Append data to traces
            episode_data["step"].append(step)
            episode_data["temperature"].append(s.temperature)
            episode_data["humidity"].append(s.humidity)
            episode_data["co2"].append(s.co2)
            episode_data["light"].append(s.light_intensity)
            episode_data["water"].append(s.water_level)
            episode_data["energy"].append(s.energy_level)
            episode_data["health"].append(s.crop_health)
            episode_data["reward"].append(reward)
            episode_data["cumulative_reward"].append(cumulative_reward)
            
            # Map actions for charts
            episode_data["heating"].append(float(action[0]))
            episode_data["cooling"].append(float(action[1]))
            episode_data["humidify"].append(float(action[2]))
            episode_data["dehumidify"].append(float(action[3]))
            episode_data["ventilation"].append(float(action[4]))
            episode_data["irrigation"].append(float(action[5]))
            episode_data["lighting"].append(float(action[6]))
            episode_data["co2_enrich"].append(float(action[7]))

            # 4. Update reasoning (if available)
            if hasattr(agent, "get_reasoning"):
                reasoning_container.markdown(f"**🧠 Decision Intelligence:** _{agent.get_reasoning()}_")

            # 5. Update charts every 5 hours
            if (step + 1) % 5 == 0 or done:
                chart_env.plotly_chart(
                    create_live_chart(episode_data, ["temperature", "humidity", "co2", "light"], "🌡️ Environmental Variables", height=180),
                    use_container_width=True,
                )
                chart_health.plotly_chart(
                    create_live_chart(episode_data, ["health", "water", "energy"], "🌿 Crop & Resources", height=180),
                    use_container_width=True,
                )
                chart_actions.plotly_chart(
                    create_live_chart(episode_data, ["heating", "cooling", "humidify", "dehumidify", "ventilation", "irrigation", "lighting", "co2_enrich"], "🛠️ Actuator Intensities", height=140),
                    use_container_width=True,
                )
                chart_rewards.plotly_chart(
                    create_rewards_chart(episode_data),
                    use_container_width=True,
                )

            step += 1
            if step_delay > 0:
                time.sleep(step_delay / 1000.0)

        # ── Episode complete ──────────────────────────────────────────────
        progress_bar.progress(1.0)
        final_health = env.state().crop_health
        health_label, health_class = get_health_status(final_health)
        status_text.success(f"✅ Episode complete! Final health: {final_health:.3f} — {health_label}")

        st.markdown("---")
        st.subheader("📊 Episode Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Final Health", f"{env.state().crop_health:.3f}")
        col2.metric("Total Duration", f"{len(episode_data['step'])} Hours")
        col3.metric("Total Reward", f"{episode_data['cumulative_reward'][-1]:.2f}")
        
        health_label, health_emoji = get_health_status(env.state().crop_health)

        # Typed state from OpenEnv state() API
        st.markdown("---")
        with st.expander("🔬 Final State — Typed GreenhouseObservation (via get_state())"):
            st.json(env.get_state().model_dump())

        # Download
        df_download = pd.DataFrame(episode_data)
        st.download_button(
            label="📥 Download Episode Data (CSV)",
            data=df_download.to_csv(index=False),
            file_name=f"episode_{difficulty.lower()}_{selected_crop}.csv",
            mime="text/csv",
        )


# (Batch Evaluation page removed)


# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align:center; color:#555; font-size:0.78rem; padding: 0.5rem 0;'>
    🌱 Greenhouse AI Environment &nbsp;·&nbsp; OpenEnv Compliant
    &nbsp;·&nbsp;
    <code>step() · reset() · get_state()</code>
</div>
""", unsafe_allow_html=True)
