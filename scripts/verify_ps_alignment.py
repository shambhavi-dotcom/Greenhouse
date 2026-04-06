"""Quick verification script — checks all PS-required APIs."""
import sys
import numpy as np

PASS = 0
FAIL = 0

def check(label, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  PASS  {label}")
        PASS += 1
    except Exception as exc:
        print(f"  FAIL  {label} — {exc}")
        FAIL += 1

# ── 1. Pydantic models ────────────────────────────────────────────────────────
from env.models import GreenhouseObservation, GreenhouseAction, GreenhouseReward, GreenhouseStepResult

def test_obs_model():
    obs = GreenhouseObservation(
        temperature=22.5, humidity=65.0, co2=800.0, light_intensity=400.0,
        water_level=75.0, energy_level=180.0, crop_health=0.85,
        mold_presence=0.0, time_of_day_norm=0.5, day_counter_norm=0.03,
    )
    assert 0.0 <= obs.crop_health <= 1.0
    arr = obs.to_array()
    assert len(arr) == 10

def test_action_model():
    a = GreenhouseAction(heating=0.3, irrigation=0.4)
    arr = a.to_array()
    assert len(arr) == 8
    assert arr[0] == 0.3
    a2 = GreenhouseAction.from_array([0.1]*8)
    assert a2.heating == 0.1

def test_action_from_json():
    a = GreenhouseAction.from_llm_text('{"heating":0.5,"irrigation":0.7}')
    assert a.heating == 0.5
    assert a.irrigation == 0.7

def test_reward_model():
    rw = GreenhouseReward.from_dict({"total": 0.72, "component_crop": 0.85}, step=5, done=False)
    assert rw.total == 0.72
    assert rw.step == 5

check("GreenhouseObservation Pydantic model", test_obs_model)
check("GreenhouseAction Pydantic model", test_action_model)
check("GreenhouseAction.from_llm_text() JSON parse", test_action_from_json)
check("GreenhouseReward.from_dict()", test_reward_model)

# ── 2. Environment API ────────────────────────────────────────────────────────
from env.environment import GreenhouseEnv, GreenhouseEasyEnv, GreenhouseMediumEnv, GreenhouseHardEnv

def test_reset():
    e = GreenhouseEnv()
    obs, info = e.reset()
    assert obs.shape == (10,)
    assert "difficulty" in info

def test_step():
    e = GreenhouseEnv()
    e.reset()
    action = np.random.uniform(0, 1, 8).astype(np.float32)
    obs, reward, terminated, truncated, info = e.step(action)
    assert obs.shape == (10,)
    assert isinstance(reward, float)
    assert "reward_breakdown" in info

def test_get_state():
    """OpenEnv mandatory state() API."""
    e = GreenhouseEnv()
    e.reset()
    s = e.get_state()
    assert isinstance(s, GreenhouseObservation)
    assert 0.0 <= s.crop_health <= 1.0
    assert s.step == 0  # no steps taken yet

def test_typed_reset():
    e = GreenhouseEnv()
    obs = e.typed_reset()
    assert isinstance(obs, GreenhouseObservation)

def test_typed_step():
    e = GreenhouseEnv()
    e.typed_reset()
    ga = GreenhouseAction(heating=0.3, irrigation=0.4)
    result = e.typed_step(ga)
    assert isinstance(result, GreenhouseStepResult)
    assert isinstance(result.reward, GreenhouseReward)
    assert isinstance(result.observation, GreenhouseObservation)

def test_backward_compat():
    """env.state.temperature still works (app.py compatibility)."""
    e = GreenhouseEnv()
    e.reset()
    _ = e.state.temperature
    _ = e.state.crop_health
    _ = e.state.humidity

def test_easy_env():
    e = GreenhouseEasyEnv()
    obs, _ = e.reset()
    assert obs.shape == (10,)
    assert e.difficulty == "easy"

def test_medium_env():
    e = GreenhouseMediumEnv()
    obs, _ = e.reset()
    assert e.difficulty == "medium"

def test_hard_env():
    e = GreenhouseHardEnv()
    obs, _ = e.reset()
    assert e.difficulty == "hard"

check("reset() returns (ndarray[10], dict)", test_reset)
check("step() returns (obs, reward, term, trunc, info)", test_step)
check("get_state() — OpenEnv state() API — returns GreenhouseObservation", test_get_state)
check("typed_reset() returns GreenhouseObservation", test_typed_reset)
check("typed_step() returns GreenhouseStepResult", test_typed_step)
check("backward compat: env.state.temperature works (app.py)", test_backward_compat)
check("GreenhouseEasyEnv initialises", test_easy_env)
check("GreenhouseMediumEnv initialises", test_medium_env)
check("GreenhouseHardEnv initialises", test_hard_env)

# ── 3. Inference script imports ───────────────────────────────────────────────
def test_inference_imports():
    from inference import RandomAgent, LLMAgent, GreenhouseAgent, GreenhouseInference
    from inference import log_start, log_step, log_end, run_task_with_logging
    a = RandomAgent()
    obs = np.random.uniform(0, 1, 10).astype(np.float32)
    action = a.select_action(obs)
    assert action.shape == (8,)

check("inference.py imports + RandomAgent.select_action()", test_inference_imports)

# ── 4. Structured log format spot-check ───────────────────────────────────────
import io, contextlib

def test_log_format():
    from inference import log_start, log_step, log_end
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        log_start("easy-stabilization", "greenhouse", "gpt-4o-mini")
        log_step(1, "test_action", 0.42, False, None)
        log_end(True, 5, 0.88, [0.1, 0.2, 0.3, 0.2, 0.18])
    lines = buf.getvalue().strip().splitlines()
    assert lines[0].startswith("[START] task=easy-stabilization")
    assert lines[1].startswith("[STEP] step=1")
    assert "reward=0.42" in lines[1]
    assert "done=false" in lines[1]
    assert "error=null" in lines[1]
    assert lines[2].startswith("[END] success=true")
    assert "score=0.880" in lines[2]
    assert "rewards=0.10,0.20,0.30,0.20,0.18" in lines[2]

check("structured [START]/[STEP]/[END] stdout format", test_log_format)

# ── 5. File existence checks ──────────────────────────────────────────────────
from pathlib import Path

def test_files_exist():
    root = Path(".")
    required = [
        "inference.py", "openenv.yaml", "Dockerfile", "requirements.txt",
        "env/models.py", "env/environment.py",
        "scripts/validate_submission.py", "scripts/validate-submission.sh",
    ]
    missing = [f for f in required if not (root / f).exists()]
    assert not missing, f"Missing files: {missing}"

def test_openenv_yaml_valid():
    import yaml  # not always installed; skip gracefully
    content = Path("openenv.yaml").read_text()
    assert not content.lstrip().startswith('"""'), "openenv.yaml starts with Python docstring!"
    data = yaml.safe_load(content)
    assert data.get("name") == "Greenhouse"
    assert "tasks" in data
    assert len(data["tasks"]) >= 3

def test_dockerfile_valid():
    content = Path("Dockerfile").read_text()
    assert not content.lstrip().startswith('"""'), "Dockerfile starts with Python docstring!"
    assert "EXPOSE 7860" in content
    assert "streamlit" in content.lower()

def test_requirements():
    content = Path("requirements.txt").read_text()
    assert "openai" in content
    assert "pydantic" in content

check("all required files exist", test_files_exist)

try:
    import yaml
    check("openenv.yaml is valid YAML with 3+ tasks", test_openenv_yaml_valid)
except ImportError:
    print("  SKIP  openenv.yaml YAML parse — PyYAML not installed")

check("Dockerfile has no docstring + has EXPOSE 7860 + streamlit CMD", test_dockerfile_valid)
check("requirements.txt has openai + pydantic", test_requirements)

# ── Summary ───────────────────────────────────────────────────────────────────
print()
print(f"{'='*50}")
print(f"  Results: {PASS} passed, {FAIL} failed")
print(f"{'='*50}")
if FAIL > 0:
    sys.exit(1)
