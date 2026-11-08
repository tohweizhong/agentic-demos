"""DevOps assistant that reads GitHub data on behalf of the signed-in user."""

from __future__ import annotations

from functools import cached_property
import os

import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import Client
from google.genai import types

from .tools import github_toolset

# The Gemini model is available in the "global" location. The agent itself
# runs in a region (for example us-central1). This model client always uses
# "global", and it does not change GOOGLE_CLOUD_LOCATION for the rest of ADK.
MODEL_ID = os.environ.get("MODEL_ID", "gemini-3.8-flash")
MODEL_LOCATION = os.environ.get("MODEL_LOCATION", "global")


class GlobalGemini(Gemini):
  """Gemini model that calls the Vertex AI endpoint in MODEL_LOCATION."""

  @cached_property
  def api_client(self) -> Client:
    _, project_id = google.auth.default()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", project_id)
    return Client(vertexai=True, project=project_id, location=MODEL_LOCATION)


INSTRUCTION = """You are the DevOps Assistant. You help developers list and triage their GitHub issues, pull requests, and repositories.
You have a GitHub MCP toolset. Use it to do what the user asks.

Rules:
- Never write, update, or delete. You have read access only.
- Act on behalf of the signed-in user.
- If a tool returns an authentication or authorization error, tell the user to sign in.
- Never make up information. Report only real data that the tools return.
"""

root_agent = Agent(
    name="root_agent",
    model=GlobalGemini(
        model=MODEL_ID,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[github_toolset()],
)

app = App(
    root_agent=root_agent,
    name="agent",
)
