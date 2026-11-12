"""Cleanup: delete the demo agents and, if the user asks, the demo bucket.

The cleanup deletes only agents whose ID starts with `demo-`. It does not touch
other agents in the project.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from managed_agents_demo import client, lifecycle
from managed_agents_demo import console as out
from managed_agents_demo.config import AGENT_ID_PREFIX, Settings

IDENTITY_NOTICE = (
    "Each deleted agent had its own agent identity. IAM policy bindings that grant access "
    "to that identity remain active after the delete. If you granted access to an agent "
    "identity, remove that principal from the policy."
)


def _ask(confirm: Callable[[str], str], prompt: str) -> bool:
    return confirm(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")


def run(
    rest: client.RestClient,
    sdk: Any,
    storage_client: Any,
    console: Console,
    settings: Settings,
    yes: bool = False,
    delete_bucket: bool = False,
    confirm: Callable[[str], str] = input,
    state_path: Path | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Delete the demo agents, then the bucket if `delete_bucket` is True.

    Returns 0 on success and 1 if a delete failed.
    """
    agents = [lifecycle.agent_id_of(agent) for agent in lifecycle.list_all(sdk, settings.parent)]
    demo_agents = [agent_id for agent_id in agents if agent_id.startswith(AGENT_ID_PREFIX)]
    failed = False

    if not demo_agents:
        console.print(f"No demo agents (ID prefix {AGENT_ID_PREFIX!r}) in {settings.parent}.")
    else:
        table = Table("Demo agent to delete")
        for agent_id in demo_agents:
            table.add_row(agent_id)
        console.print(table)
        if yes or _ask(confirm, f"Delete {len(demo_agents)} demo agent(s)?"):
            for agent_id in demo_agents:
                out.request(console, f"DELETE {rest.url(f'agents/{agent_id}')}")
                try:
                    operation = lifecycle.delete(rest, agent_id)
                    if operation.get("name") and not operation.get("done"):
                        client.wait_for_operation(rest, operation["name"], clock=clock, sleep=sleep)
                    console.print(f"Deleted {agent_id}.")
                except (client.ApiError, client.OperationError, TimeoutError) as exc:
                    out.error(console, f"Delete of {agent_id} failed: {exc}")
                    failed = True
            console.print(f"[yellow]{IDENTITY_NOTICE}[/yellow]")
        else:
            console.print("Nothing deleted.")

    if delete_bucket:
        bucket = storage_client.lookup_bucket(settings.bucket)
        if bucket is None:
            console.print(f"The bucket gs://{settings.bucket} does not exist.")
        elif yes or _ask(confirm, f"Delete gs://{settings.bucket} and all its files?"):
            # `force=True` deletes the objects first. It works for up to 256 objects,
            # which is enough for this demo.
            bucket.delete(force=True)
            console.print(f"Deleted gs://{settings.bucket}.")
        else:
            console.print(f"The bucket gs://{settings.bucket} stays.")

    if state_path is not None and state_path.exists():
        state_path.unlink()
        console.print(f"Removed the local file {state_path}.")

    if failed:
        return 1
    out.result(console, "Cleanup complete.")
    return 0
