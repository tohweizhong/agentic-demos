"""Reference agent of the GEAP starter pack mini build.

The agent factory uses this agent as its output template. The agent reads and
changes work items through one MCP server. All of its calls go through the
egress Agent Gateway.
"""

from __future__ import annotations

from functools import cached_property
import os

import google.auth
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import Client
from google.genai import types

from .tools import work_items_toolset

MODEL_ID = os.environ.get("MODEL_ID", "gemini-3.8-flash")
MODEL_LOCATION = os.environ.get("MODEL_LOCATION", "global")


class LocationGemini(Gemini):
  """Gemini model that calls the Vertex AI endpoint in MODEL_LOCATION.

  The agent runs in a region. The model can be in another location, for
  example "global". This client does not change GOOGLE_CLOUD_LOCATION for the
  rest of ADK.
  """

  @cached_property
  def api_client(self) -> Client:
    _, project_id = google.auth.default()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", project_id)
    return Client(vertexai=True, project=project_id, location=MODEL_LOCATION)


INSTRUCTION = """You are the Work Items Assistant. You help an operator read and change the status of work items.
You have a work items MCP toolset. Use it to do what the user asks.

Rules:
- To read a status, use get_status. To change a status, use update_status.
- If a tool call fails, or the connection to the tools is lost, tell the user that the call was denied or failed. Give the tool name. Do not try a different tool to get the same result.
- Never make up information. Report only real data that the tools return.
"""

root_agent = Agent(
    name="work_items_assistant",
    model=LocationGemini(
        model=MODEL_ID,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[work_items_toolset()],
)
