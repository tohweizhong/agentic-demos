"""One ADK agent that uses Sessions, Memory Bank, and traces on Agent Runtime.

Sessions: Agent Runtime connects `VertexAiSessionService` to `AdkApp`
automatically. This file has no session code. Each call to the agent with a
`session_id` reads and writes the events of that session.

Memory Bank: `PreloadMemoryTool` reads the memories of the user at the start
of each turn. `save_session_to_memory` sends the session events to Memory Bank
after each turn, with the GenerateMemories API. Memory Bank generates the
memories in the background. On Agent Runtime, `AdkApp`
connects `VertexAiMemoryBankService` automatically.

Traces: the environment variable `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY`
turns on the built-in ADK traces. `get_service_status` adds one custom span
to the same trace.
"""

import logging
import os

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("agent_services_starter_pack")

# Sample data only. A real agent calls a real system here.
_SAMPLE_STATUS = {
    "payments": "degraded",
    "search": "operational",
    "notifications": "operational",
}


def model_name():
  """Returns the model ID. `deploy.py` sets MODEL on Agent Runtime."""
  return os.environ.get("MODEL", "gemini-3.5-flash")


def get_service_status(service_name: str) -> dict:
  """Returns the status of an internal service.

  Args:
    service_name: The name of the service, for example "payments" or "search".

  Returns:
    The service name, its status, and the trace ID of this call.
  """
  name = service_name.strip().lower()
  # Custom span. It is a child of the active ADK tool span, so it shows in
  # the same trace in Cloud Trace.
  with tracer.start_as_current_span("get_service_status") as span:
    status = _SAMPLE_STATUS.get(name, "not_found")
    span.set_attribute("starter_pack.service", name)
    span.set_attribute("starter_pack.status", status)
    trace_id = format(span.get_span_context().trace_id, "032x")
  # The trace ID lets samples/3_o11y.py print a link to this trace.
  return {
      "service": name,
      "status": status,
      "sample_data": True,
      "trace_id": trace_id,
  }


# Selects the GenerateMemories API path in ADK. The value False means that the
# callback does not wait for memory generation to finish.
MEMORY_GENERATE_METADATA = {"wait_for_completion": False}


async def save_session_to_memory(callback_context: CallbackContext):
  """Sends the session events to Memory Bank after each turn.

  ADK 2.14 has two paths. The default path (IngestEvents) starts the call as a
  background task and does not wait for it. On Agent Runtime, that call did
  not reach Memory Bank in the live test (10 Nov 2026), and ADK logged no
  error. The metadata key "wait_for_completion" selects the GenerateMemories
  path. ADK waits for the API call, and Memory Bank generates the memories in
  the background. Memory Bank merges new facts with the existing memories of
  the user, so the callback can send the full session each time.

  An error here does not stop the turn.
  """
  try:
    await callback_context.add_events_to_memory(
        events=callback_context.session.events,
        custom_metadata=MEMORY_GENERATE_METADATA,
    )
  except Exception:  # pylint: disable=broad-exception-caught
    logger.exception("Could not send the session to Memory Bank.")
  return None


root_agent = Agent(
    name="services_agent",
    model=model_name(),
    description="Sample agent for Sessions, Memory Bank, and traces.",
    instruction=(
        "You are a helpful assistant for a team that runs internal services. "
        "Use get_service_status when the user asks about the status of a "
        "service. Use what you remember about the user, if it is relevant. "
        "Keep each answer short."
    ),
    tools=[PreloadMemoryTool(), get_service_status],
    after_agent_callback=save_session_to_memory,
)
