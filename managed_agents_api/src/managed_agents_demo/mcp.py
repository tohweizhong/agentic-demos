"""The Google-hosted BigQuery MCP server as a tool for one interaction.

The demo does not store MCP credentials in the agent configuration. It sends a short-lived
access token in the `tools` override of one interaction. The token is not written to disk,
and the terminal output masks it.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx2 as httpx
from rich.console import Console
from rich.table import Table

from managed_agents_demo import agent_config, interactions
from managed_agents_demo import console as out
from managed_agents_demo.config import Settings

BIGQUERY_MCP_URL = "https://bigquery.googleapis.com/mcp"
TOP_NAMES_SQL = (
    "SELECT name, SUM(number) AS total "
    "FROM `bigquery-public-data.usa_names.usa_1910_current` "
    "WHERE year = 2020 GROUP BY name ORDER BY total DESC LIMIT 3"
)


class McpError(RuntimeError):
    """The MCP server returned an error."""


def bigquery_tool(token: str, project: str) -> dict[str, Any]:
    """Return the `mcp_server` tool for the BigQuery MCP server."""
    return {
        "type": "mcp_server",
        "name": "bigquery",
        "url": BIGQUERY_MCP_URL,
        "headers": {"Authorization": f"Bearer {token}", "X-Goog-User-Project": project},
    }


def override_tools(token: str, project: str) -> list[dict[str, Any]]:
    """Return the tools for the interaction.

    The override replaces the tools in the agent configuration for this turn. The harness file
    tools stay available.
    """
    return [{"type": "code_execution"}, bigquery_tool(token, project)]


def direct_query(http: httpx.Client, token: str, project: str, sql: str) -> list[dict[str, str]]:
    """Run `sql` with the MCP tool `execute_sql_readonly`, outside the agent. Return the rows."""
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "execute_sql_readonly",
            "arguments": {"projectId": project, "query": sql},
        },
    }
    reply = http.post(
        BIGQUERY_MCP_URL,
        json=body,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Goog-User-Project": project,
            "Accept": "application/json, text/event-stream",
        },
        timeout=60,
    )
    reply.raise_for_status()
    result = reply.json().get("result", {})
    text = "".join(part.get("text", "") for part in result.get("content", []))
    if result.get("isError"):
        raise McpError(text)
    data = json.loads(text)
    names = [field["name"] for field in data.get("schema", {}).get("fields", [])]
    return [
        {name: cell.get("v") for name, cell in zip(names, row.get("f", []), strict=False)}
        for row in data.get("rows", [])
    ]


TASK = (
    "Use the BigQuery tools to find the 3 most common baby names in 2020 in the public table "
    "bigquery-public-data.usa_names.usa_1910_current. Run the query in project {project}. "
    "Show the SQL and the result as a table with the name and the total."
)


def run(
    sdk: Any,
    console: Console,
    settings: Settings,
    token_provider: Callable[[], str],
    query: Callable[[str, str, str], list[dict[str, str]]] | None = None,
    agent_id: str = agent_config.ANALYST_AGENT_ID,
) -> int:
    """Send one interaction with the BigQuery MCP server, then check the answer directly."""
    token = token_provider()
    request = interactions.build_request(
        agent_id,
        TASK.format(project=settings.project),
        tools=override_tools(token, settings.project),
    )
    out.request(console, "client.interactions.create(...)", request)
    console.rule("Agent stream")
    start = time.monotonic()

    def on_step(name: str) -> None:
        console.print(f"\n[dim]-> tool call: {name}[/dim]")

    def on_text(text: str) -> None:
        console.print(text, end="", markup=False, highlight=False)

    try:
        summary = interactions.consume(
            interactions.start(sdk, request), on_text=on_text, on_step=on_step
        )
    except Exception as exc:  # noqa: BLE001 - the SDK raises many error types.
        out.error(console, str(exc))
        return 1
    console.print()
    mcp_calls = [name for name in summary.tool_calls if name.startswith("bigquery:")]
    out.response(
        console,
        {
            "interaction_id": summary.interaction_id,
            "status": summary.status,
            "elapsed": out.format_elapsed(time.monotonic() - start),
            "mcp_tool_calls": mcp_calls,
            "total_tokens": (summary.usage or {}).get("total_tokens"),
        },
    )
    if summary.errors or summary.status not in (None, "completed"):
        out.error(console, "; ".join(summary.errors) or f"Status: {summary.status}")
        return 1

    if query is None:
        http = httpx.Client()

        def query(token: str, project: str, sql: str) -> list[dict[str, str]]:
            return direct_query(http, token, project, sql)

    rows = query(token, settings.project, TOP_NAMES_SQL)
    table = Table("Name", "Total", title="Direct check with execute_sql_readonly")
    for row in rows:
        table.add_row(row.get("name", ""), row.get("total", ""))
    console.print(table)

    failed = False
    if not mcp_calls:
        out.error(console, "No MCP tool call in the stream. The agent did not use BigQuery.")
        failed = True
    missing = [row["name"] for row in rows if row.get("name") not in summary.final_text]
    if missing:
        out.error(console, f"The agent answer does not contain: {', '.join(missing)}")
        failed = True
    if failed:
        return 1
    out.result(
        console,
        f"The agent answer contains all {len(rows)} names from the direct query.\n"
        "The token was sent for this interaction only. The stored agent has no MCP credentials.",
    )
    return 0
