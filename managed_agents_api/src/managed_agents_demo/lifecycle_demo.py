"""Steps of the lifecycle script (`scripts/01_lifecycle.py`).

1. Create the data analyst agent with REST, and wait for the operation.
2. Get the agent with the SDK.
3. List the agents with the SDK.
4. Update the description with REST `PATCH`, and get the agent again.
"""

from __future__ import annotations

import copy
import time
from collections.abc import Callable
from typing import Any

from rich.console import Console
from rich.table import Table

from managed_agents_demo import agent_config, client, lifecycle
from managed_agents_demo import console as out
from managed_agents_demo.config import AGENT_ID_PREFIX, Settings

_MAX_LINES = 3
_CONFIG_FIELDS = ("description", "system_instruction", "tools", "base_environment")


def shorten_sources(body: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `body` with long inline content cut to a few lines, for display."""
    shown = copy.deepcopy(body)
    for source in shown.get("base_environment", {}).get("sources", []) or []:
        content = source.get("content")
        if isinstance(content, str):
            lines = content.splitlines()
            if len(lines) > _MAX_LINES:
                source["content"] = (
                    "\n".join(lines[:_MAX_LINES]) + f"\n... ({len(lines)} lines in total)"
                )
    return shown


def _as_dict(agent: Any) -> dict[str, Any]:
    if isinstance(agent, dict):
        return agent
    return agent.model_dump(mode="json", exclude_none=True)


def run(
    rest: client.RestClient,
    sdk: Any,
    console: Console,
    settings: Settings,
    agent_id: str = agent_config.ANALYST_AGENT_ID,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    interval: float = 5,
    timeout: float = 600,
) -> int:
    """Run the lifecycle steps. Return 0 on success and 1 on failure."""

    def tick(elapsed: float) -> None:
        console.print(f"  Waiting for the operation: {out.format_elapsed(elapsed)}")

    def wait(operation: dict[str, Any]) -> None:
        if operation.get("name") and not operation.get("done"):
            client.wait_for_operation(
                rest,
                operation["name"],
                interval=interval,
                timeout=timeout,
                clock=clock,
                sleep=sleep,
                on_tick=tick,
            )

    # Step 1: create.
    console.rule("Step 1: create the agent (REST)")
    body = agent_config.build_agent_body(bucket=settings.bucket, agent_id=agent_id)
    domains = ", ".join(agent_config.NETWORK_ALLOWLIST)
    console.print(
        f"[yellow]Warning: the network allowlist is {domains!r}. The sandbox can reach all "
        "internet hosts. The Preview API needs this when a Cloud Storage source is set. "
        "Use only data that is safe to expose.[/yellow]"
    )
    out.request(console, f"POST {rest.url('agents')}", shorten_sources(body))
    start = clock()
    try:
        operation = lifecycle.create(rest, body)
        out.response(console, operation)
        wait(operation)
        console.print(f"Create: done in {out.format_elapsed(clock() - start)}")
    except client.ApiError as exc:
        if exc.status != 409:
            out.error(console, exc.message, status=exc.status)
            return 1
        console.print(
            f"The agent {agent_id} already exists. "
            "The script sends the current configuration to it."
        )
        fields = {key: body[key] for key in _CONFIG_FIELDS}
        try:
            operation = lifecycle.update(rest, agent_id, fields)
            out.response(console, operation)
            wait(operation)
        except (client.ApiError, client.OperationError, TimeoutError) as update_exc:
            out.error(console, f"Update failed: {update_exc}")
            return 1
    except (client.OperationError, TimeoutError) as exc:
        out.error(console, f"Create failed: {exc}")
        return 1

    # Step 2: get.
    console.rule("Step 2: get the agent (SDK)")
    out.request(console, f"client.agents.get(id={agent_id!r})")
    out.response(console, shorten_sources(_as_dict(lifecycle.get(sdk, agent_id))))

    # Step 3: list.
    console.rule("Step 3: list the agents (SDK)")
    out.request(console, f"client.agents.list(parent={settings.parent!r})")
    table = Table("Agent ID", "Created by this demo")
    for agent in lifecycle.list_all(sdk, settings.parent):
        found_id = lifecycle.agent_id_of(agent)
        table.add_row(found_id, "yes" if found_id.startswith(AGENT_ID_PREFIX) else "no")
    console.print(table)

    # Step 4: update.
    console.rule("Step 4: update the description (REST PATCH)")
    new_description = f"{body['description']} Description updated by 01_lifecycle.py."
    fields = {"description": new_description}
    out.request(console, f"PATCH {rest.url(f'agents/{agent_id}')}?update_mask=description", fields)
    try:
        operation = lifecycle.update(rest, agent_id, fields)
        out.response(console, operation)
        wait(operation)
    except (client.ApiError, client.OperationError, TimeoutError) as exc:
        out.error(console, f"Update failed: {exc}")
        return 1
    updated = lifecycle.get(sdk, agent_id)
    console.print(f"Description after the update: {_as_dict(updated).get('description')}")

    out.result(
        console,
        f"The agent {agent_id} is ready.\n"
        "Next step: python scripts/02_interact.py\n"
        "To delete the demo agents: python scripts/99_cleanup.py",
    )
    return 0
