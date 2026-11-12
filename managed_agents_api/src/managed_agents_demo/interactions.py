"""Interactions: send a task to an agent and read the event stream.

The demo uses the SDK method `client.interactions.create` with `stream=True`. The
stream sends these event types:

- `interaction.created`: the interaction ID.
- `step.start`, `step.delta`, `step.stop`: one step of the agent. A step is a harness
  tool call (`function_call`), a built-in tool call (for example `google_search_call`),
  a tool result, or text (`model_output`).
- `interaction.completed`: the status, the token usage, and the environment ID.

Each text chunk has an `event_id`. At the end of a text step, the API can send the
full text again in one delta without an `event_id`. The code does not print it again.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StreamSummary:
    """What the stream returned."""

    interaction_id: str | None = None
    environment_id: str | None = None
    status: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    final_text: str = ""
    tool_calls: list[str] = field(default_factory=list)
    tool_errors: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


def _as_dict(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return event
    return event.model_dump(mode="json", exclude_none=True)


def consume(
    events: Iterable[Any],
    on_text: Callable[[str], None] | None = None,
    on_step: Callable[[str], None] | None = None,
) -> StreamSummary:
    """Read all events. Call `on_text` for each new text chunk and `on_step` for each tool call."""
    summary = StreamSummary()
    step_text: dict[int, str] = {}
    last_text_step: int | None = None
    for raw in events:
        event = _as_dict(raw)
        kind = event.get("event_type")
        if kind in ("interaction.created", "interaction.completed"):
            interaction = event.get("interaction", {})
            summary.interaction_id = interaction.get("id", summary.interaction_id)
            summary.status = interaction.get("status", summary.status)
            summary.environment_id = interaction.get("environment_id", summary.environment_id)
            summary.usage = interaction.get("usage", summary.usage)
        elif kind == "step.start":
            step = event.get("step", {})
            step_type = step.get("type", "")
            name = None
            if step_type == "function_call":
                # A harness tool, for example `run_command` or `view_file`.
                name = step.get("name", "unknown")
            elif step_type.endswith("_call"):
                # A built-in tool, for example `google_search_call` or `mcp_server_tool_call`.
                name = step_type.removesuffix("_call")
                if step.get("name"):
                    name = f"{name}:{step['name']}"
            if name:
                summary.tool_calls.append(name)
                if on_step:
                    on_step(name)
        elif kind == "step.delta":
            delta = event.get("delta", {})
            index = event.get("index", -1)
            if delta.get("type") == "text":
                text = delta.get("text", "")
                last_text_step = index
                if "event_id" in event:
                    step_text[index] = step_text.get(index, "") + text
                    if on_text:
                        on_text(text)
                elif not step_text.get(index):
                    # The full text arrived without chunks. Print it one time.
                    step_text[index] = text
                    if on_text:
                        on_text(text)
            elif delta.get("type") == "text_annotation_delta":
                # Google Search grounding does not come as a step. It comes as URL
                # citations on the text.
                for note in delta.get("annotations", []):
                    title = note.get("title") or note.get("url")
                    if note.get("type") == "url_citation" and title not in summary.citations:
                        summary.citations.append(title)
            elif delta.get("type") == "function_result" and delta.get("is_error"):
                summary.tool_errors.append(delta.get("name", "unknown"))
        elif kind == "error":
            error = event.get("error", {})
            summary.errors.append(str(error.get("message", error)))
    if last_text_step is not None:
        summary.final_text = step_text.get(last_text_step, "")
    return summary


def build_request(
    agent_id: str,
    text: str,
    previous_interaction_id: str | None = None,
    environment_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the keyword arguments for `client.interactions.create`.

    Args:
        agent_id: The agent to call.
        text: The user message.
        previous_interaction_id: Continue the conversation of this interaction.
        environment_id: Use this sandbox again, with its files.
        tools: Replace the agent tools for this interaction only.
    """
    request: dict[str, Any] = {
        "agent": agent_id,
        "input": text,
        "stream": True,
        "background": True,
        "store": True,
    }
    if previous_interaction_id:
        request["previous_interaction_id"] = previous_interaction_id
    if environment_id:
        request["environment"] = environment_id
    if tools is not None:
        request["tools"] = tools
    return request


def start(sdk: Any, request: dict[str, Any]) -> Iterable[Any]:
    """Send the interaction. Return the event stream."""
    return sdk.interactions.create(**request)


def save_state(path: Path, agent_id: str, interaction_id: str, environment_id: str) -> None:
    """Save the IDs that the next script needs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "agent_id": agent_id,
        "interaction_id": interaction_id,
        "environment_id": environment_id,
    }
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_state(path: Path) -> dict[str, str]:
    """Load the IDs that `scripts/02_interact.py` saved."""
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run scripts/02_interact.py first.")
    return json.loads(path.read_text(encoding="utf-8"))
