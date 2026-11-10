"""Settings for the agent services starter pack.

The scripts read settings from the process environment first, then from the
gitignored `.env` file in this folder. `.env.example` lists every setting.
"""

import dataclasses
import os
import pathlib

PACK_DIR = pathlib.Path(__file__).resolve().parent
ENV_FILE = PACK_DIR / ".env"

# Default values. Each value can be changed in `.env`.
DEFAULTS = {
    "REGION": "asia-southeast1",
    # gemini-3.5-flash has ML processing in Singapore (Agent Platform data
    # residency table, checked 10 Nov 2026).
    "MODEL": "gemini-3.5-flash",
    "MEMORY_GENERATION_MODEL": "gemini-3.5-flash",
    # No Google embedding model has ML processing in Singapore. This is the
    # Memory Bank default model.
    "EMBEDDING_MODEL": "text-embedding-005",
    # The location in the embedding model resource name. Empty means REGION.
    "EMBEDDING_LOCATION": "",
    "AGENT_DISPLAY_NAME": "svcpack-agent",
    # "true" logs prompts, responses, and user IDs in the traces. Get user
    # consent before you turn it on.
    "CAPTURE_MESSAGE_CONTENT": "false",
    "AGENT_RUNTIME_NAME": "",
}


class SettingsError(Exception):
  """A required setting is missing."""


def read_env_file(path):
  """Returns the KEY=VALUE pairs in a `.env` file. Skips comments."""
  path = pathlib.Path(path)
  if not path.exists():
    return {}
  values = {}
  for line in path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip('"').strip("'")
  return values


def set_env_value(path, key, value):
  """Sets one KEY=VALUE pair in a `.env` file. Keeps the other lines."""
  path = pathlib.Path(path)
  lines = path.read_text().splitlines() if path.exists() else []
  new_line = f"{key}={value}"
  for index, line in enumerate(lines):
    if line.split("=", 1)[0].strip() == key:
      lines[index] = new_line
      break
  else:
    lines.append(new_line)
  path.write_text("\n".join(lines) + "\n")


@dataclasses.dataclass(frozen=True)
class Settings:
  """The settings that the scripts use."""

  project_id: str
  region: str
  staging_bucket: str
  model: str
  memory_generation_model: str
  embedding_model: str
  embedding_location: str
  agent_display_name: str
  capture_message_content: bool
  agent_runtime_name: str

  @property
  def staging_bucket_uri(self):
    return f"gs://{self.staging_bucket}"

  @property
  def generation_model_resource(self):
    return (
        f"projects/{self.project_id}/locations/{self.region}/publishers/google/"
        f"models/{self.memory_generation_model}"
    )

  @property
  def embedding_model_resource(self):
    location = self.embedding_location or self.region
    return (
        f"projects/{self.project_id}/locations/{location}/publishers/google/"
        f"models/{self.embedding_model}"
    )

  @property
  def runtime_id(self):
    return self.agent_runtime_name.rstrip("/").split("/")[-1]

  def require_runtime_name(self):
    """Returns the Agent Runtime name, or fails if the agent is not deployed."""
    if not self.agent_runtime_name:
      raise SettingsError(
          "AGENT_RUNTIME_NAME is not set. Run `python deploy.py` first."
      )
    return self.agent_runtime_name


def load_settings(env_file=ENV_FILE):
  """Loads the settings. The process environment has priority over `.env`."""
  file_values = read_env_file(env_file)

  def get(key):
    if os.environ.get(key):
      return os.environ[key]
    if file_values.get(key):
      return file_values[key]
    return DEFAULTS.get(key, "")

  for key in ("PROJECT_ID", "STAGING_BUCKET"):
    if not get(key):
      raise SettingsError(
          f"{key} is not set. Copy .env.example to .env and set {key}."
      )

  return Settings(
      project_id=get("PROJECT_ID"),
      region=get("REGION"),
      staging_bucket=get("STAGING_BUCKET"),
      model=get("MODEL"),
      memory_generation_model=get("MEMORY_GENERATION_MODEL"),
      embedding_model=get("EMBEDDING_MODEL"),
      embedding_location=get("EMBEDDING_LOCATION"),
      agent_display_name=get("AGENT_DISPLAY_NAME"),
      capture_message_content=get("CAPTURE_MESSAGE_CONTENT").lower() == "true",
      agent_runtime_name=get("AGENT_RUNTIME_NAME"),
  )
