import os
import numpy as np
from typing import Optional

# ENV IMPORTS (unchanged)
from env.environment import GreenhouseEasyEnv

# =========================
# ENV VARIABLES (MANDATORY)
# =========================
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

HF_TOKEN = os.getenv("HF_TOKEN")
API_KEY = HF_TOKEN or os.getenv("OPENAI_API_KEY") or None

MAX_STEPS = 50

# =========================
# AGENTS
# =========================
class RandomAgent:
    def select_action(self, obs: np.ndarray) -> np.ndarray:
        return np.random.uniform(0.0, 1.0, 8).astype(np.float32)


class LLMAgent:
    def __init__(self, client, fallback):
        self.client = client
        self.fallback = fallback

    def select_action(self, obs: np.ndarray) -> np.ndarray:
        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": f"Observation: {obs.tolist()}. Give 8 float actions between 0 and 1."}
                ],
                max_tokens=50,
                temperature=0.3,
            )
            text = response.choices[0].message.content

            # VERY simple parsing fallback-safe
            nums = [float(x) for x in text.replace("[", "").replace("]", "").split() if x.replace('.', '', 1).isdigit()]
            if len(nums) >= 8:
                return np.array(nums[:8], dtype=np.float32)

        except Exception:
            pass

        return self.fallback.select_action(obs)


# =========================
# LOGGING (FIXED)
# =========================
def log_start(task: str):
    print(f"[START] task={task}", flush=True)


def log_step(step: int, reward: float):
    print(f"[STEP] step={step} reward={reward:.4f}", flush=True)


def log_end(task: str, score: float, steps: int):
    print(f"[END] task={task} score={score:.4f} steps={steps}", flush=True)


# =========================
# MAIN RUN
# =========================
def main():

    # --- agent setup ---
    if API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
            agent = LLMAgent(client, RandomAgent())
        except Exception:
            agent = RandomAgent()
    else:
        agent = RandomAgent()

    # --- environment ---
    env = GreenhouseEasyEnv()
    task_name = "greenhouse"

    log_start(task_name)

    obs, _ = env.reset()

    rewards = []
    steps_taken = 0

    for step in range(1, MAX_STEPS + 1):
        action = agent.select_action(obs)
        obs, reward, terminated, truncated, _ = env.step(action)

        rewards.append(float(reward))
        steps_taken = step

        log_step(step, reward)

        if terminated or truncated:
            break

    # score normalization
    score = float(np.clip(sum(rewards) / MAX_STEPS, 0.0, 1.0))

    log_end(task_name, score, steps_taken)


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    main()