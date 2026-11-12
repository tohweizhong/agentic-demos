"""Backend configuration for the demo.

The demo supports two backends:

* Gemini Developer API (default). It uses an API key.
* Vertex AI. It uses Application Default Credentials. The Decisions API is in early
  access on Vertex AI, so the project must be on the allowlist.

All settings come from environment variables. This keeps the demo code the same for
both backends. Only the model IDs and the endpoint change.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_DECISIONS_MODEL_GEMINI_API = "gemini-decision-1"
DEFAULT_DECISIONS_MODEL_VERTEX = "gemini-decision-exp"
DEFAULT_VERTEX_LOCATION = "global"

# Tier models. Recorded from the Gemini Developer API model list on 12 Nov 2026.
DEFAULT_TIER_MODELS: dict[str, str] = {
    "lite": "gemini-3.5-flash-lite",
    "flash": "gemini-3.8-flash",
    "pro": "gemini-4-argon",
}

_TRUE_VALUES = {"1", "true", "yes"}
_TIER_ENV_VARS = {"lite": "MODEL_TIER_LITE", "flash": "MODEL_TIER_FLASH", "pro": "MODEL_TIER_PRO"}


class Backend(enum.Enum):
    """The API that the demo calls."""

    GEMINI_API = "Gemini Developer API"
    VERTEX_AI = "Vertex AI"


class ConfigError(ValueError):
    """A required setting is missing. The message states the fix."""


@dataclass(frozen=True)
class Config:
    """Settings for one run of the demo."""

    backend: Backend
    decisions_model: str
    tier_models: dict[str, str] = field(default_factory=dict)
    api_key: str | None = None
    project: str | None = None
    location: str | None = None

    def describe(self) -> str:
        """Return one line that names the backend and the model. It never includes the key."""
        text = f"Backend: {self.backend.value} | Decisions model: {self.decisions_model}"
        if self.backend is Backend.VERTEX_AI:
            text += f" | Project: {self.project} | Location: {self.location}"
        return text


def _get(env: Mapping[str, str], name: str) -> str | None:
    """Return the value of a variable, or None if it is missing or empty."""
    value = env.get(name, "").strip()
    return value or None


def load_config(env: Mapping[str, str]) -> Config:
    """Build a Config from environment variables.

    Args:
        env: The environment, for example ``os.environ``.

    Raises:
        ConfigError: A required variable for the selected backend is missing.
    """
    use_vertex = (_get(env, "GOOGLE_GENAI_USE_VERTEXAI") or "").lower() in _TRUE_VALUES
    tier_models = {
        tier: _get(env, var) or DEFAULT_TIER_MODELS[tier] for tier, var in _TIER_ENV_VARS.items()
    }

    if use_vertex:
        project = _get(env, "GOOGLE_CLOUD_PROJECT")
        if project is None:
            raise ConfigError(
                "GOOGLE_CLOUD_PROJECT is not set. Set it in .env to use the Vertex AI backend."
            )
        return Config(
            backend=Backend.VERTEX_AI,
            decisions_model=_get(env, "DECISIONS_MODEL") or DEFAULT_DECISIONS_MODEL_VERTEX,
            tier_models=tier_models,
            project=project,
            location=_get(env, "GOOGLE_CLOUD_LOCATION") or DEFAULT_VERTEX_LOCATION,
        )

    api_key = _get(env, "GEMINI_API_KEY")
    if api_key is None:
        raise ConfigError("GEMINI_API_KEY is not set. Copy .env.example to .env and set the key.")
    return Config(
        backend=Backend.GEMINI_API,
        decisions_model=_get(env, "DECISIONS_MODEL") or DEFAULT_DECISIONS_MODEL_GEMINI_API,
        tier_models=tier_models,
        api_key=api_key,
    )
