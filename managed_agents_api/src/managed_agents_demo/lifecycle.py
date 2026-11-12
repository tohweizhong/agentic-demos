"""Agent lifecycle: create, get, list, update, and delete.

- `get` and `list_all` use the `google-genai` SDK.
- `create`, `update`, and `delete` use REST. The SDK has no `update` method, and
  its `create` and `delete` methods hide the long-running operation.
"""

from __future__ import annotations

from typing import Any

from managed_agents_demo.client import RestClient


def create(rest: RestClient, body: dict[str, Any]) -> dict[str, Any]:
    """Send `CreateAgent`. Return the long-running operation."""
    return rest.request("POST", "agents", json=body)


def update(rest: RestClient, agent_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Send `UpdateAgent` for the given fields. Return the long-running operation.

    The update mask contains the names of the fields, in the given order.
    """
    if not fields:
        raise ValueError("Give at least one field to update.")
    body = {"name": agent_id, **fields}
    params = {"update_mask": ",".join(fields)}
    return rest.request("PATCH", f"agents/{agent_id}", json=body, params=params)


def delete(rest: RestClient, agent_id: str) -> dict[str, Any]:
    """Send `DeleteAgent`. Return the long-running operation."""
    return rest.request("DELETE", f"agents/{agent_id}")


def get(sdk: Any, agent_id: str) -> Any:
    """Return one agent from the SDK."""
    return sdk.agents.get(id=agent_id)


def list_all(sdk: Any, parent: str) -> list[Any]:
    """Return all agents in `parent`. Follow every page."""
    agents: list[Any] = []
    token = None
    while True:
        page = sdk.agents.list(parent=parent, page_token=token)
        agents.extend(page.agents or [])
        token = page.next_page_token
        if not token:
            return agents


def agent_id_of(agent: Any) -> str:
    """Return the agent ID of an SDK agent or a REST agent dictionary."""
    if isinstance(agent, dict):
        return agent.get("id") or agent["name"].rsplit("/", 1)[-1]
    return getattr(agent, "id", None) or agent.name.rsplit("/", 1)[-1]
