"""Settings for the demo.

The demo reads the project ID from the environment or from a `.env` file.
The Managed Agents API supports only the `global` location.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

BASE_AGENT = "antigravity-preview-05-2026"
AGENT_ID_PREFIX = "demo-"
LOCATION = "global"
API_ROOT = "https://aiplatform.googleapis.com/v1beta1"

_PLACEHOLDER = "your-project-id"


class ConfigError(RuntimeError):
    """A required setting is missing."""


@dataclass(frozen=True)
class Settings:
    """Project settings for all API calls."""

    project: str
    location: str = LOCATION

    @property
    def parent(self) -> str:
        """Return the parent resource name for agents and interactions."""
        return f"projects/{self.project}/locations/{self.location}"

    @property
    def base_url(self) -> str:
        """Return the REST URL of the parent resource."""
        return f"{API_ROOT}/{self.parent}"


def load(dotenv: bool = True) -> Settings:
    """Load the settings.

    Args:
        dotenv: If True, read the `.env` file in the current folder first.

    Raises:
        ConfigError: If `GOOGLE_CLOUD_PROJECT` is not set.
    """
    if dotenv:
        from dotenv import find_dotenv, load_dotenv

        # Search from the current folder. Without `usecwd=True`, python-dotenv searches
        # from the folder of the calling file, and it can find a `.env` file that the
        # user did not select.
        load_dotenv(find_dotenv(usecwd=True))
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project or project == _PLACEHOLDER:
        raise ConfigError(
            "GOOGLE_CLOUD_PROJECT is not set. Copy .env.example to .env and set the project ID."
        )
    return Settings(project=project)
