"""
inference.py

Greenhouse OpenEnv — Baseline Inference Script
===============================================

MANDATORY STDOUT FORMAT (PS-compliant):
    [START] task=<task_name> env=greenhouse model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Environment variables used:
    API_BASE_URL  - LLM API endpoint   (default: https://api.openai.com/v1)
    MODEL_NAME    - Model identifier   (default: gpt-4o-mini)
    HF_TOKEN      - Hugging Face / API key (checked first)
    OPENAI_API_KEY - OpenAI API key   (fallback)

When no API key is available the script falls back to RandomAgent so it always
produces valid structured output and completes without error.

Run:
    python inference.py

Classes kept for app.py backward compatibility:
    - GreenhouseAgent
    - RandomAgent
    - GreenhouseInference
"""

from __future__ import annotations

import os
import sys
import json
import textwrap
import numpy as np
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Load .env if present (python-dotenv is optional — graceful fallback)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; env vars must be pre-set

# ---------------------------------------------------------------------------
# Env + task imports
# ---------------------------------------------------------------------------
from env.environment import (
    GreenhouseEnv,
    GreenhouseEasyEnv,
    GreenhouseMediumEnv,
    GreenhouseHardEnv,
)
from env.models import GreenhouseAction
from tasks.task_easy import EasyTask
from tasks.task_medium import MediumTask
from tasks.task_hard import HardTask
from tasks.graders import (
    grade_easy_task,
    grade_medium_task,
    grade_hard_task,
    grade_overall_performance,
    print_grading_report,
)

# ===========================================================================
# CONFIGURATION — read from environment variables (PS-mandated)
# ===========================================================================

API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
# PS mandates HF_TOKEN; also accept OPENAI_API_KEY as fallback
API_KEY: Optional[str] = (
    os.getenv("HF_TOKEN")
    or os.getenv("OPENAI_API_KEY")
    or None
)

BENCHMARK_NAME = "greenhouse"
MAX_STEPS_PER_EPISODE = 50   # Capped for inference speed (<20 min total)
TEMPERATURE = 0.3
MAX_TOKENS = 200
SUCCESS_SCORE_THRESHOLD = 0.1   # Normalised score in [0, 1]


# ===========================================================================
# AGENT CLASSES  (kept for app.py backward compatibility)
# ===========================================================================

class GreenhouseAgent:
    """Base agent interface for greenhouse control."""

    def select_action(self, observation: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def reset(self):
        pass


class RandomAgent(GreenhouseAgent):
    """Agent that takes random actions (baseline / fallback when no API key)."""

    def select_action(self, observation: np.ndarray) -> np.ndarray:
        return np.random.uniform(0, 1, 8).astype(np.float32)


class LLMAgent(GreenhouseAgent):
    """
    LLM-backed agent using OpenAI client.

    Sends the current observation to the LLM and parses the response
    into a GreenhouseAction. Gracefully falls back to RandomAgent on failure.
    """

    SYSTEM_PROMPT = textwrap.dedent("""
        You are an expert greenhouse control system.
        Your task is to control a greenhouse to maximise crop health.
        
        You control 8 actuators (each 0.0–1.0, where 0=off, 1=full power):
          heating, cooling, humidifying, dehumidifying,
          ventilation, irrigation, lighting, co2_enrichment
        
        Current observation (numpy array, index order):
          [0] temperature (°C)   [1] humidity (%)      [2] co2 (ppm)
          [3] light (µmol/m²/s)  [4] water_level       [5] energy_level
          [6] crop_health (0–1)  [7] mold presence     [8] time_of_day_norm
          [9] day_counter_norm
        
        Optimal conditions (tomato): temp=22°C, humidity=65%, co2=800ppm,
        light=600µmol/m²/s. Keep crop_health above 0.7.
        
        Respond ONLY with a JSON object containing the 8 actuator values, e.g.:
        {"heating":0.2,"cooling":0.0,"humidifying":0.1,"dehumidifying":0.0,
         "ventilation":0.3,"irrigation":0.4,"lighting":0.5,"co2_enrichment":0.3}
        No explanation, no markdown, just JSON.
    """).strip()

    def __init__(self, client, fallback: RandomAgent):
        self._client = client
        self._fallback = fallback
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def select_action(self, observation: np.ndarray) -> np.ndarray:
        """Query LLM and parse action; fall back to random on failure."""
        self._last_error = None
        obs_str = ", ".join(f"{v:.3f}" for v in observation)
        user_msg = f"Current observation: [{obs_str}]\nProvide greenhouse control actions:"

        try:
            completion = self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system",  "content": self.SYSTEM_PROMPT},
                    {"role": "user",    "content": user_msg},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            text = (completion.choices[0].message.content or "").strip()
            action = GreenhouseAction.from_llm_text(text)
            return np.array(action.to_array(), dtype=np.float32)
        except Exception as exc:
            self._last_error = str(exc)[:120]
            return self._fallback.select_action(observation)

    def reset(self):
        self._last_error = None


# ===========================================================================
# STRUCTURED LOGGING  (PS-mandated format)
# ===========================================================================

def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] line to stdout."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    """Emit [STEP] line to stdout."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={done_val} error={error_val}",
        flush=True,
    )


def log_end(
    success: bool,
    steps: int,
    score: float,
    rewards: List[float],
) -> None:
    """Emit [END] line to stdout."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ===========================================================================
# CORE: run one task with full structured logging
# ===========================================================================

def run_task_with_logging(
    task_name: str,
    env: GreenhouseEnv,
    agent: GreenhouseAgent,
    max_steps: int = MAX_STEPS_PER_EPISODE,
) -> Dict[str, Any]:
    """
    Run a single episode on `env` with `agent`, emitting PS-structured logs.

    Returns a dict with:
        score, success, steps, rewards, final_crop_health, resource_efficiency
    """
    log_start(task=task_name, env=BENCHMARK_NAME, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    last_error: Optional[str] = None

    try:
        obs, info = env.reset()

        for step in range(1, max_steps + 1):
            # Agent selects action
            action_array = agent.select_action(obs)

            # Capture any LLM error for [STEP] logging
            if isinstance(agent, LLMAgent):
                last_error = agent.last_error
            else:
                last_error = None

            # Format action string for logging (compact JSON-like)
            action_str = (
                "{h:%.2f,c:%.2f,hu:%.2f,d:%.2f,v:%.2f,ir:%.2f,l:%.2f,co2:%.2f}"
                % tuple(float(x) for x in action_array)
            )

            # Step environment
            obs, reward, terminated, truncated, info = env.step(action_array)
            done = terminated or truncated

            rewards.append(float(reward))
            steps_taken = step

            log_step(
                step=step,
                action=action_str,
                reward=float(reward),
                done=done,
                error=last_error,
            )

            if done:
                break

        # Normalise score to [0, 1]
        # Max theoretical reward per step ≈ 1.0 * crop_health_weight = 1.0
        max_possible = max_steps * 1.0
        raw_score = sum(rewards)
        score = float(np.clip(raw_score / max_possible if max_possible > 0 else 0.0, 0.0, 1.0))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        last_error = str(exc)[:200]
        # Always emit [END] even on exception
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    # Return structured result for grader
    return {
        "episode_return": sum(rewards),
        "final_crop_health": float(env._state.crop_health),
        "steps": steps_taken,
        "success": success,
        "score": score,
        "rewards": rewards,
        # Medium task extra field
        "max_weather_disturbance": float(env._state.external_weather.get("temp_shift", 0.0)),
        # Hard task extra fields
        "resource_efficiency": (
            float(env._state.crop_health) / (sum(rewards) + 1e-6)
            if sum(rewards) > 0 else 0.0
        ),
    }


# ===========================================================================
# GreenhouseInference class (kept for app.py backward compatibility)
# ===========================================================================

class GreenhouseInference:
    """
    Main inference orchestrator.
    Runs agent through all three tasks and generates grading report.
    Used by app.py for batch evaluation display.
    """

    def __init__(self, agent: GreenhouseAgent):
        self.agent = agent
        self.easy_results = []
        self.medium_results = []
        self.hard_results = []

    def run_all_tasks(self) -> dict:
        """Run agent through all three tasks and return scores."""
        print("\n" + "=" * 60)
        print("STARTING GREENHOUSE ENVIRONMENT EVALUATION")
        print("=" * 60)

        # Easy task
        print("\n[EASY TASK] Running 10 episodes (stabilization)...")
        easy_task = EasyTask(num_episodes=10)
        self.easy_results = easy_task.run(self.agent)
        easy_score = grade_easy_task(self.easy_results)
        print(f"Easy Task Score: {easy_score:.3f}\n")

        # Medium task
        print("[MEDIUM TASK] Running 20 episodes (adaptation)...")
        medium_task = MediumTask(num_episodes=20)
        self.medium_results = medium_task.run(self.agent)
        medium_score = grade_medium_task(self.medium_results)
        print(f"Medium Task Score: {medium_score:.3f}\n")

        # Hard task
        print("[HARD TASK] Running 30 episodes (optimization)...")
        hard_task = HardTask(num_episodes=30)
        self.hard_results = hard_task.run(self.agent)
        hard_score = grade_hard_task(self.hard_results)
        print(f"Hard Task Score: {hard_score:.3f}\n")

        # Overall
        overall_score = grade_overall_performance(easy_score, medium_score, hard_score)
        print_grading_report(easy_score, medium_score, hard_score, overall_score)

        return {
            "easy_score": easy_score,
            "medium_score": medium_score,
            "hard_score": hard_score,
            "overall_score": overall_score,
            "easy_results": self.easy_results,
            "medium_results": self.medium_results,
            "hard_results": self.hard_results,
        }

    def run_single_episode(self, difficulty: str = "easy") -> dict:
        """Run single episode at specified difficulty."""
        if difficulty == "easy":
            env = GreenhouseEasyEnv()
        elif difficulty == "medium":
            env = GreenhouseMediumEnv()
        elif difficulty == "hard":
            env = GreenhouseHardEnv()
        else:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        obs, info = env.reset()
        done = False
        episode_return = 0.0
        steps = 0

        while not done:
            action = self.agent.select_action(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_return += reward
            done = terminated or truncated
            steps += 1

        return {
            "difficulty": difficulty,
            "episode_return": episode_return,
            "final_crop_health": env._state.crop_health,
            "steps": steps,
        }


# ===========================================================================
# MAIN  — PS-compliant entry point
# ===========================================================================

def main() -> None:
    """
    PS-compliant main: runs LLM agent (or RandomAgent fallback) through all
    3 tasks and emits structured [START]/[STEP]/[END] logs to stdout.

    Task order: easy → medium → hard
    Each task runs a SINGLE representative episode with structured logging.
    """

    # -----------------------------------------------------------------------
    # Build OpenAI client (PS-mandated)
    # -----------------------------------------------------------------------
    use_llm = bool(API_KEY)

    if use_llm:
        try:
            from openai import OpenAI
            client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
            fallback = RandomAgent()
            agent = LLMAgent(client=client, fallback=fallback)
        except ImportError:
            print("[DEBUG] openai package not installed; using RandomAgent", flush=True)
            agent = RandomAgent()
            use_llm = False
    else:
        print("[DEBUG] No API key found (HF_TOKEN / OPENAI_API_KEY); using RandomAgent", flush=True)
        agent = RandomAgent()

    # -----------------------------------------------------------------------
    # Task 1: Easy — Stabilization (static environment, no weather)
    # -----------------------------------------------------------------------
    easy_env = GreenhouseEasyEnv()
    easy_result = run_task_with_logging(
        task_name="easy-stabilization",
        env=easy_env,
        agent=agent,
        max_steps=MAX_STEPS_PER_EPISODE,
    )

    # -----------------------------------------------------------------------
    # Task 2: Medium — Adaptation (weather disturbances, resource limits)
    # -----------------------------------------------------------------------
    if isinstance(agent, LLMAgent):
        agent.reset()
    medium_env = GreenhouseMediumEnv()
    medium_result = run_task_with_logging(
        task_name="medium-adaptation",
        env=medium_env,
        agent=agent,
        max_steps=MAX_STEPS_PER_EPISODE,
    )

    # -----------------------------------------------------------------------
    # Task 3: Hard — Optimization (all constraints, long horizon)
    # -----------------------------------------------------------------------
    if isinstance(agent, LLMAgent):
        agent.reset()
    hard_env = GreenhouseHardEnv()
    hard_result = run_task_with_logging(
        task_name="hard-optimization",
        env=hard_env,
        agent=agent,
        max_steps=MAX_STEPS_PER_EPISODE,
    )

    # -----------------------------------------------------------------------
    # Final summary (to stderr so it doesn't pollute structured stdout)
    # -----------------------------------------------------------------------
    easy_score   = easy_result["score"]
    medium_score = medium_result["score"]
    hard_score   = hard_result["score"]
    overall      = (easy_score + medium_score + hard_score) / 3.0

    print(
        f"\n[SUMMARY] easy={easy_score:.3f} medium={medium_score:.3f} "
        f"hard={hard_score:.3f} overall={overall:.3f}",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    main()
