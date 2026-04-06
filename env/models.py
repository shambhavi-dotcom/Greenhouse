"""
env/models.py

Pydantic v2 typed models for the Greenhouse OpenEnv environment.
Satisfies the OpenEnv spec requirement for typed Observation, Action, and Reward models.

These are the canonical typed interfaces between the environment and agents/evaluators.
The gymnasium-compatible env methods (step/reset/state) return/accept these types.
"""

from typing import Annotated, Dict, Any, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# OBSERVATION MODEL
# ==============================================================================

class GreenhouseObservation(BaseModel):
    """
    Typed observation returned by reset() and step().

    All environmental sensor readings at a single time-step.
    This is what the agent sees — the full (non-hidden) state.
    """

    # Environmental sensors
    temperature: float = Field(..., description="Greenhouse air temperature (°C)")
    humidity: float = Field(..., description="Relative humidity (%)")
    co2: float = Field(..., description="CO₂ concentration (ppm)")
    light_intensity: float = Field(..., description="Light intensity (µmol/m²/s)")

    # Resource levels
    water_level: float = Field(..., description="Available water in reservoir (units, 0–100)")
    energy_level: float = Field(..., description="Available energy (units, 0–200)")

    # Crop state
    crop_health: float = Field(..., ge=0.0, le=1.0, description="Crop health score (0.0=dead, 1.0=thriving)")
    mold_presence: float = Field(..., ge=0.0, le=1.0, description="Mold presence level (0.0=none, 1.0=severe)")

    # Temporal features (normalised to [0, 1])
    time_of_day_norm: float = Field(..., ge=0.0, le=1.0, description="Time of day normalised (0=midnight, 1=midnight)")
    day_counter_norm: float = Field(..., ge=0.0, description="Day number normalised by 365")

    # Episode metadata
    step: int = Field(default=0, description="Current step number within episode")
    difficulty: str = Field(default="easy", description="Task difficulty (easy/medium/hard)")
    crop: str = Field(default="tomato", description="Crop type being grown")

    def to_array(self) -> list[float]:
        """Return flat list matching gymnasium observation order."""
        return [
            self.temperature,
            self.humidity,
            self.co2,
            self.light_intensity,
            self.water_level,
            self.energy_level,
            self.crop_health,
            self.mold_presence,
            self.time_of_day_norm,
            self.day_counter_norm,
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 22.5,
                "humidity": 65.0,
                "co2": 800.0,
                "light_intensity": 400.0,
                "water_level": 75.0,
                "energy_level": 180.0,
                "crop_health": 0.85,
                "mold_presence": 0.0,
                "time_of_day_norm": 0.5,
                "day_counter_norm": 0.03,
                "step": 10,
                "difficulty": "medium",
                "crop": "tomato",
            }
        }


# ==============================================================================
# ACTION MODEL
# ==============================================================================

class GreenhouseAction(BaseModel):
    """
    Typed action sent by agent to env.step().

    All intensities are normalised to [0.0, 1.0]:
      0.0 = off / minimum
      1.0 = full power / maximum
    """

    heating: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Heating system intensity (0=off, 1=full)"
    )
    cooling: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Cooling system intensity (0=off, 1=full)"
    )
    humidifying: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Humidifier intensity"
    )
    dehumidifying: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Dehumidifier intensity"
    )
    ventilation: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Ventilation fan intensity"
    )
    irrigation: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Water irrigation intensity"
    )
    lighting: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="Supplemental lighting intensity"
    )
    co2_enrichment: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        default=0.0, description="CO₂ enrichment system intensity"
    )

    def to_array(self) -> list[float]:
        """Return flat 8-element list in canonical gymnasium action order."""
        return [
            self.heating,
            self.cooling,
            self.humidifying,
            self.dehumidifying,
            self.ventilation,
            self.irrigation,
            self.lighting,
            self.co2_enrichment,
        ]

    @classmethod
    def from_array(cls, arr: list[float]) -> "GreenhouseAction":
        """Construct from 8-element float array (gymnasium action_space output)."""
        if len(arr) != 8:
            raise ValueError(f"Expected 8 action values, got {len(arr)}")
        return cls(
            heating=float(arr[0]),
            cooling=float(arr[1]),
            humidifying=float(arr[2]),
            dehumidifying=float(arr[3]),
            ventilation=float(arr[4]),
            irrigation=float(arr[5]),
            lighting=float(arr[6]),
            co2_enrichment=float(arr[7]),
        )

    @classmethod
    def from_llm_text(cls, text: str) -> "GreenhouseAction":
        """
        Parse LLM-generated action text into a GreenhouseAction.

        LLM can respond with either:
          - JSON: {"heating": 0.3, "cooling": 0.0, ...}
          - Key=value pairs: heating=0.3 cooling=0.0 ...
          - Fallback: random values if parse fails
        """
        import json
        import re
        import numpy as np

        text = text.strip()

        # Try JSON first
        try:
            data = json.loads(text)
            return cls(**{k: float(v) for k, v in data.items() if k in cls.model_fields})
        except Exception:
            pass

        # Try key=value pairs
        fields: Dict[str, float] = {}
        for field_name in cls.model_fields:
            pattern = rf"{field_name}\s*[=:]\s*([0-9.]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fields[field_name] = min(1.0, max(0.0, float(match.group(1))))

        if fields:
            return cls(**fields)

        # Fallback: random action
        arr = np.random.uniform(0.0, 1.0, 8).tolist()
        return cls.from_array(arr)

    class Config:
        json_schema_extra = {
            "example": {
                "heating": 0.3,
                "cooling": 0.0,
                "humidifying": 0.2,
                "dehumidifying": 0.0,
                "ventilation": 0.1,
                "irrigation": 0.4,
                "lighting": 0.5,
                "co2_enrichment": 0.6,
            }
        }


# ==============================================================================
# REWARD MODEL
# ==============================================================================

class GreenhouseReward(BaseModel):
    """
    Typed reward returned alongside each step.

    The total reward is a weighted combination of components minus penalties.
    All sub-components are included for interpretability and grader use.
    """

    total: float = Field(..., description="Total step reward (sum of components minus penalties)")

    # Positive components
    component_crop: float = Field(default=0.0, description="Reward for high crop health")
    component_stability: float = Field(default=0.0, description="Reward for environmental stability (negative if unstable)")
    component_resource: float = Field(default=0.0, description="Reward for resource efficiency (negative = wasteful)")

    # Penalties (always <= 0.0)
    penalty_mold: float = Field(default=0.0, description="Penalty for mold presence")
    penalty_freeze: float = Field(default=0.0, description="Penalty for freeze risk")
    penalty_heat: float = Field(default=0.0, description="Penalty for heat stress")
    penalty_death: float = Field(default=0.0, description="Large penalty if crop dies")

    # Metadata
    step: int = Field(default=0, description="Step number this reward was computed at")
    done: bool = Field(default=False, description="Whether this step ended the episode")

    @classmethod
    def from_dict(cls, d: Dict[str, Any], step: int = 0, done: bool = False) -> "GreenhouseReward":
        """Construct from the dict returned by env/rewards.py compute_reward()."""
        return cls(
            total=float(d.get("total", 0.0)),
            component_crop=float(d.get("component_crop", 0.0)),
            component_stability=float(d.get("component_stability", 0.0)),
            component_resource=float(d.get("component_resource", 0.0)),
            penalty_mold=float(d.get("penalty_mold", 0.0)),
            penalty_freeze=float(d.get("penalty_freeze", 0.0)),
            penalty_heat=float(d.get("penalty_heat", 0.0)),
            penalty_death=float(d.get("penalty_death", 0.0)),
            step=step,
            done=done,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "total": 0.72,
                "component_crop": 0.85,
                "component_stability": -0.05,
                "component_resource": -0.08,
                "penalty_mold": 0.0,
                "penalty_freeze": 0.0,
                "penalty_heat": 0.0,
                "penalty_death": 0.0,
                "step": 42,
                "done": False,
            }
        }


# ==============================================================================
# STEP RESULT (composite return from env.step())
# ==============================================================================

class GreenhouseStepResult(BaseModel):
    """
    Composite result returned by the typed env.typed_step() method.
    Bundles observation + reward + done flag + info.
    """

    observation: GreenhouseObservation
    reward: GreenhouseReward
    done: bool
    truncated: bool
    info: Dict[str, Any] = Field(default_factory=dict)
