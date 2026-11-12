"""Access check: create one agent, wait for it, and delete it.

The check proves that the project and the account can create agents. It uses
REST calls, so that the output shows each long-running operation.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from rich.console import Console

from managed_agents_demo import client
from managed_agents_demo import console as out
from managed_agents_demo.config import BASE_AGENT

AGENT_ID = "demo-access-check"


def run(
    rest: client.RestClient,
    console: Console,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    interval: float = 5,
    timeout: float = 600,
) -> int:
    """Run the access check. Return 0 on success and 1 on failure."""
    body = {
        "id": AGENT_ID,
        "base_agent": BASE_AGENT,
        "description": "Access check for the Managed Agents API demo. Safe to delete.",
    }

    def tick(elapsed: float) -> None:
        console.print(f"  Waiting for the operation: {out.format_elapsed(elapsed)}")

    out.request(console, f"POST {rest.url('agents')}", body)
    start = clock()
    try:
        created = rest.request("POST", "agents", json=body)
    except client.ApiError as exc:
        _report_api_error(console, exc)
        return 1
    out.response(console, created)

    failed = False
    try:
        client.wait_for_operation(
            rest,
            client.operation_name_of(created),
            interval=interval,
            timeout=timeout,
            clock=clock,
            sleep=sleep,
            on_tick=tick,
        )
        create_seconds = clock() - start
        console.print(f"Create: done in {out.format_elapsed(create_seconds)}")
    except (client.OperationError, TimeoutError, client.ApiError) as exc:
        out.error(console, f"Create failed: {exc}")
        failed = True

    path = f"agents/{AGENT_ID}"
    out.request(console, f"DELETE {rest.url(path)}")
    start = clock()
    try:
        deleted = rest.request("DELETE", path)
        out.response(console, deleted)
        # The delete operation can be done in the first response. Poll only if it is not done.
        if deleted.get("name") and not deleted.get("done"):
            client.wait_for_operation(
                rest,
                client.operation_name_of(deleted),
                interval=interval,
                timeout=timeout,
                clock=clock,
                sleep=sleep,
                on_tick=tick,
            )
        console.print(f"Delete: done in {out.format_elapsed(clock() - start)}")
    except (client.ApiError, client.OperationError, TimeoutError) as exc:
        out.error(console, f"Delete failed: {exc}. Run scripts/99_cleanup.py to delete the agent.")
        return 1

    if failed:
        return 1
    out.result(console, "Access check passed. This account can create and delete agents.")
    return 0


def _report_api_error(console: Console, exc: client.ApiError) -> None:
    lines = [exc.message]
    if exc.status == 403:
        if exc.permission:
            lines.append(f"The account needs the permission {exc.permission}.")
        lines.append("Ask a project owner to grant a role that contains this permission.")
    elif exc.status == 409:
        lines.append(
            f"The agent {AGENT_ID} already exists. Run scripts/99_cleanup.py, then try again."
        )
    out.error(console, "\n".join(lines), status=exc.status)
