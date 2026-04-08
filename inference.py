# ===================== inference.py (FINAL FIXED) =====================

from __future__ import annotations

import os
import sys
import textwrap
import numpy as np
from typing import List, Optional, Dict, Any

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from env.environment import (
    GreenhouseEnv,
    GreenhouseEasyEnv,
    GreenhouseMediumEnv,
    GreenhouseHardEnv,
)
from env.models import GreenhouseAction

# ================= CONFIG =================

API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")

# ✅ REQUIRED FIX
HF_TOKEN = os.getenv("HF_TOKEN")

API_KEY: Optional[str] = (
    HF_TOKEN or os.getenv("OPENAI_API_KEY") or None
)

MAX_STEPS_PER_EPISODE = 50
TEMPERATURE = 0.3
MAX_TOKENS = 200
SUCCESS_SCORE_THRESHOLD = 0.1


# ================= AGENTS =================

class GreenhouseAgent:
    def select_action(self, obs: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class RandomAgent(GreenhouseAgent):
    def select_action(self, obs: np.ndarray) -> np.ndarray:
        return np.random.uniform(0.0, 1.0, 8).astype(np.float32)


class LLMAgent(GreenhouseAgent):
    SYSTEM_PROMPT = textwrap.dedent("""
        Control greenhouse optimally.
        Return ONLY JSON with 8 actuator values.
    """).strip()

    def __init__(self, client, fallback):
        self.client = client
        self.fallback = fallback
        self.last_error = None

    def select_action(self, obs: np.ndarray) -> np.ndarray:
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": str(obs.tolist())}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            text = response.choices[0].message.content
            action = GreenhouseAction.from_llm_text(text)
            return np.array(action.to_array(), dtype=np.float32)
        except Exception as e:
            self.last_error = str(e)
            return self.fallback.select_action(obs)


# ================= LOGGING (FIXED) =================

def log_start(task, env, model):
    print(f"START task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error):
    error_val = error if error else "null"
    print(
        f"STEP step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error_val}",
        flush=True
    )


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"END success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True
    )


# ================= CORE LOOP =================

def run_task(task_name, env, agent):
    log_start(task_name, "greenhouse", MODEL_NAME)

    rewards = []
    steps = 0

    obs, _ = env.reset()

    for step in range(1, MAX_STEPS_PER_EPISODE + 1):
        action = agent.select_action(obs)
        obs, reward, terminated, truncated, _ = env.step(action)

        done = terminated or truncated
        rewards.append(float(reward))
        steps = step

        action_str = str(list(map(float, action)))

        log_step(step, action_str, reward, done, None)

        if done:
            break

    score = sum(rewards) / MAX_STEPS_PER_EPISODE
    success = score >= SUCCESS_SCORE_THRESHOLD

    log_end(success, steps, score, rewards)

    return score


# ================= MAIN =================

def main():
    if API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
            agent = LLMAgent(client, RandomAgent())
        except:
            agent = RandomAgent()
    else:
        agent = RandomAgent()

    run_task("easy", GreenhouseEasyEnv(), agent)
    run_task("medium", GreenhouseMediumEnv(), agent)
    run_task("hard", GreenhouseHardEnv(), agent)


if __name__ == "__main__":
    main()
