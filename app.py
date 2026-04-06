"""Streamlit frontend for the greenhouse simulator — real-time step playback."""

import time
import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List

from inference import RandomAgent
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
mode = st.sidebar.radio("Mode", ["📊 Dashboard", "🎮 Single Episode", "📈 Batch Evaluation"])
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
        <span style='color:#888;font-size:0.8rem;'>{_preset["description"]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
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
    return RandomAgent()


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
        "soil_moisture": [], "reward": [], "cumulative_reward": [],
        "fan": [], "water_sprinter": [], "co2_emitter": [], "light_control": [],
    }


# ============================================================================
# COMPLETE BATCH EPISODE (non-live, for Dashboard / Batch Evaluation)
# ============================================================================

def run_episode(env, agent, max_steps=None):
    obs, info = env.reset()
    episode_data = empty_episode_data()
    done = False
    step = 0
    cumulative_reward = 0.0
    max_steps = max_steps or env.max_episode_steps

    while not done and step < max_steps:
        action = agent.select_action(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        cumulative_reward += reward
        done = terminated or truncated

        episode_data["step"].append(step)
        episode_data["temperature"].append(env.state.temperature)
        episode_data["humidity"].append(env.state.humidity)
        episode_data["co2"].append(env.state.co2)
        episode_data["light"].append(env.state.light_intensity)
        episode_data["water"].append(env.state.water_level)
        episode_data["soil_moisture"].append(env.state.water_level)
        episode_data["energy"].append(env.state.energy_level)
        episode_data["health"].append(env.state.crop_health)
        episode_data["reward"].append(reward)
        episode_data["cumulative_reward"].append(cumulative_reward)
        episode_data["fan"].append(float(action[4]))
        episode_data["water_sprinter"].append(float(action[5]))
        episode_data["co2_emitter"].append(float(action[7]))
        episode_data["light_control"].append(float(action[6]))
        step += 1

    return episode_data, env.state


# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

if mode == "📊 Dashboard":
    st.title("🌱 Greenhouse Live Dashboard")
    st.caption("Real-time snapshot across all sensors for the selected crop and difficulty.")

    env = get_environment(difficulty, crop_view)
    agent = get_agent()
    obs, _ = env.reset(initial_condition=initial_condition)
    for _ in range(50):
        action = agent.select_action(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            break

    col1, col2, col3, col4 = st.columns(4)
    health_status, health_color = get_health_status(env.state.crop_health)
    with col1:
        st.metric("🌿 Crop Health", f"{env.state.crop_health:.3f}")
        st.markdown(f"<p class='{health_color}'>{health_status}</p>", unsafe_allow_html=True)
    with col2:
        st.metric("🌡️ Temperature", f"{env.state.temperature:.1f}°C")
        dev = abs(env.state.temperature - 22.0)
        st.caption(f"Optimal 22°C | Deviation: {dev:.1f}°C")
    with col3:
        st.metric("💧 Humidity", f"{env.state.humidity:.1f}%")
        st.caption("Optimal: 65%")
    with col4:
        st.metric("💦 Soil Moisture", f"{env.state.water_level:.1f}")
        st.caption(f"Capacity: {constants.WATER_CAPACITY}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💧 Water Reservoir")
        water_pct = env.state.water_level / constants.WATER_CAPACITY
        st.progress(water_pct)
        st.caption(f"{env.state.water_level:.1f} / {constants.WATER_CAPACITY} ({water_pct*100:.1f}%)")
    with col2:
        st.subheader("⚡ Energy Level")
        energy_pct = env.state.energy_level / constants.ENERGY_CAPACITY
        st.progress(energy_pct)
        st.caption(f"{env.state.energy_level:.1f} / {constants.ENERGY_CAPACITY} ({energy_pct*100:.1f}%)")

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.plotly_chart(create_state_gauge(env.state.temperature, constants.TEMP_MIN, constants.TEMP_MAX, "Temp (°C)"), use_container_width=True)
    with col2:
        st.plotly_chart(create_state_gauge(env.state.humidity, constants.HUMIDITY_MIN, constants.HUMIDITY_MAX, "Humidity (%)"), use_container_width=True)
    with col3:
        st.plotly_chart(create_state_gauge(env.state.co2, constants.CO2_MIN, constants.CO2_MAX, "CO₂ (ppm)"), use_container_width=True)
    with col4:
        st.plotly_chart(create_state_gauge(env.state.light_intensity, constants.LIGHT_MIN, constants.LIGHT_MAX, "Light (µmol)"), use_container_width=True)

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
    st.title("🎮 Real-Time Episode Playback")
    st.caption("Watch the agent interact with the environment step-by-step in real time.")

    col1, col2, col3 = st.columns(3)
    with col1:
        max_steps = st.number_input("Max Steps", min_value=10, max_value=500, value=100)
    with col2:
        selected_crop = st.selectbox("Crop for Live View", CROPS, index=CROPS.index(crop_view))
    with col3:
        run_button = st.button("▶️ Run Episode (Live)", key="run_episode")

    # ── Preset info banner ─────────────────────────────────────────────────────
    _p = INITIAL_CONDITION_PRESETS[initial_condition]
    st.markdown(
        f"""
        <div style='background:#1a1f2e;border:1px solid {_p["color"]}33;
        border-left:4px solid {_p["color"]};padding:10px 16px;border-radius:8px;margin-bottom:12px;'>
            <b style='color:{_p["color"]};'>Starting Condition:</b>
            <span style='color:#c9d1d9;'>
            &nbsp;{initial_condition} &nbsp;·&nbsp;
            Temp: {_p["temperature"]}°C &nbsp;·&nbsp;
            Humidity: {_p["humidity"]}% &nbsp;·&nbsp;
            CO₂: {_p["co2"]} ppm &nbsp;·&nbsp;
            Energy: {_p["energy_level"]} / {constants.ENERGY_CAPACITY}
            </span>
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

        # ── Run loop ──────────────────────────────────────────────────────
        episode_data = empty_episode_data()
        done = False
        step = 0
        cumulative_reward = 0.0

        while not done and step < max_steps:
            action = agent.select_action(obs)
            obs, reward, terminated, truncated, step_info = env.step(action)
            cumulative_reward += reward
            done = terminated or truncated

            # Append data
            episode_data["step"].append(step)
            episode_data["temperature"].append(env.state.temperature)
            episode_data["humidity"].append(env.state.humidity)
            episode_data["co2"].append(env.state.co2)
            episode_data["light"].append(env.state.light_intensity)
            episode_data["water"].append(env.state.water_level)
            episode_data["soil_moisture"].append(env.state.water_level)
            episode_data["energy"].append(env.state.energy_level)
            episode_data["health"].append(env.state.crop_health)
            episode_data["reward"].append(reward)
            episode_data["cumulative_reward"].append(cumulative_reward)
            episode_data["fan"].append(float(action[4]))
            episode_data["water_sprinter"].append(float(action[5]))
            episode_data["co2_emitter"].append(float(action[7]))
            episode_data["light_control"].append(float(action[6]))

            # ── Update live metrics ───────────────────────────────────────
            health_label, _ = get_health_status(env.state.crop_health)
            metric_health.metric("🌿 Health",  f"{env.state.crop_health:.3f}")
            metric_temp.metric("🌡️ Temp",      f"{env.state.temperature:.1f}°C")
            metric_humid.metric("💧 Humidity", f"{env.state.humidity:.1f}%")
            metric_reward.metric("🎯 Reward",  f"{cumulative_reward:.2f}")
            metric_step.metric("📍 Step",      f"{step + 1} / {max_steps}")

            progress_bar.progress(min((step + 1) / max_steps, 1.0))
            status_text.markdown(
                f"<span class='step-badge'>Step {step+1}</span>  "
                f"Health: **{env.state.crop_health:.3f}** · "
                f"Temp: **{env.state.temperature:.1f}°C** · "
                f"Reward: **{reward:+.3f}**",
                unsafe_allow_html=True,
            )

            # ── Update live charts every 5 steps (performance) ───────────
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
                    create_live_chart(episode_data, ["fan", "water_sprinter", "light_control", "co2_emitter"], "🛠️ Actuator Intensities", height=180),
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
        final_health = env.state.crop_health
        health_label, health_class = get_health_status(final_health)
        status_text.success(f"✅ Episode complete! Final health: {final_health:.3f} — {health_label}")

        st.markdown("---")
        st.subheader("📊 Episode Summary")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Final Health",   f"{final_health:.3f}")
        s2.metric("Total Steps",    step)
        s3.metric("Total Reward",   f"{cumulative_reward:.2f}")
        s4.metric("Status",         health_label)

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


# ============================================================================
# PAGE: BATCH EVALUATION
# ============================================================================

elif mode == "📈 Batch Evaluation":
    st.title("📈 Batch Evaluation")
    st.caption("Run full multi-episode evaluation across all crops and tasks.")

    col1, col2 = st.columns(2)
    with col1:
        num_episodes = st.slider("Episodes per Crop", min_value=1, max_value=20, value=5)
    with col2:
        show_detailed = st.checkbox("Show Detailed Charts", value=True)

    run_eval_button = st.button("▶️ Start Evaluation", key="run_eval")
    st.markdown("---")

    if run_eval_button:
        agent = get_agent()
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        evaluation_results = {crop: [] for crop in CROPS}

        for crop_idx, crop in enumerate(CROPS):
            for ep in range(num_episodes):
                env = get_environment(difficulty, crop)
                episode_data, final_state = run_episode(env, agent)
                evaluation_results[crop].append({
                    "episode": ep + 1,
                    "health": final_state.crop_health,
                    "reward": episode_data["cumulative_reward"][-1] if episode_data["cumulative_reward"] else 0,
                    "steps": len(episode_data["step"]),
                    "energy": final_state.energy_level,
                    "soil_moisture": final_state.water_level,
                })
                total_progress = (crop_idx * num_episodes + ep + 1) / (len(CROPS) * num_episodes)
                progress_bar.progress(total_progress)
                status_text.text(f"🌱 {crop.title()} — Episode {ep+1}/{num_episodes}")

        progress_bar.progress(1.0)
        status_text.success("✅ Evaluation completed!")

        st.subheader("📊 Results Summary")
        summary_data = []
        for crop in CROPS:
            results = evaluation_results[crop]
            avg_health  = float(np.mean([r["health"] for r in results]))
            avg_reward  = float(np.mean([r["reward"] for r in results]))
            success_rate = sum(1 for r in results if r["health"] > 0.5) / len(results)
            summary_data.append({
                "Crop": crop.title(),
                "Avg Health": f"{avg_health:.3f}",
                "Avg Reward": f"{avg_reward:.2f}",
                "Success Rate": f"{success_rate:.1%}",
                "Episodes": len(results),
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        if show_detailed:
            st.markdown("---")
            st.subheader("📈 Detailed Distributions")
            col1, col2 = st.columns(2)
            health_data = [{"Crop": c.title(), "Health": r["health"]}
                           for c in CROPS for r in evaluation_results[c]]
            reward_data = [{"Crop": c.title(), "Reward": r["reward"]}
                           for c in CROPS for r in evaluation_results[c]]
            with col1:
                fig = px.box(pd.DataFrame(health_data), x="Crop", y="Health",
                             color="Crop", title="Crop Health Distribution",
                             template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.box(pd.DataFrame(reward_data), x="Crop", y="Reward",
                             color="Crop", title="Episode Reward Distribution",
                             template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

        results_df = pd.DataFrame(summary_data)
        st.download_button(
            label="📥 Download Results (CSV)",
            data=results_df.to_csv(index=False),
            file_name="evaluation_results.csv",
            mime="text/csv",
        )


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
