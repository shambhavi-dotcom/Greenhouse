from typing import Annotated, Any, Dict, List
import logging
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import numpy as np
from env.environment import GreenhouseEnv

app = FastAPI(title="Greenhouse OpenEnv API")

logger = logging.getLogger(__name__)

# Initialize ONE global environment instance
# We default to medium difficulty to provide a standard challenge for evaluators
env = GreenhouseEnv(difficulty="medium")
env_lock = threading.Lock()


def _to_jsonable(value: Any) -> Any:
    """Recursively convert NumPy values/containers into JSON-safe Python types."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


ActionVector = Annotated[List[float], Field(min_length=8, max_length=8)]

class StepRequest(BaseModel):
    action: ActionVector

@app.get("/")
async def health_check():
    """Health check endpoint required by OpenEnv."""
    return {"status": "running"}

@app.post("/reset")
async def reset():
    """Reset the environment and return the initial observation."""
    try:
        with env_lock:
            obs_array, info = env.reset()
        return {
            "observation": _to_jsonable(obs_array),
            "info": _to_jsonable(info),
        }
    except Exception as exc:
        logger.exception("Failed to reset environment")
        raise HTTPException(status_code=500, detail="Failed to reset environment") from exc

@app.post("/step")
async def step(request: StepRequest):
    """Execute a step in the environment with the provided action."""
    try:
        action = np.array(request.action, dtype=np.float32)
        with env_lock:
            obs_array, reward, terminated, truncated, info = env.step(action)

        return {
            "observation": _to_jsonable(obs_array),
            "reward": float(reward),
            "done": bool(terminated or truncated),
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "info": _to_jsonable(info),
        }
    except Exception as exc:
        logger.exception("Failed to execute environment step")
        raise HTTPException(status_code=500, detail="Failed to execute step") from exc

@app.get("/state")
async def get_state():
    """Return the current high-fidelity state of the greenhouse."""
    try:
        with env_lock:
            state = env.get_state()
        return state.model_dump(mode="json")
    except Exception as exc:
        logger.exception("Failed to retrieve environment state")
        raise HTTPException(status_code=500, detail="Failed to read state") from exc
