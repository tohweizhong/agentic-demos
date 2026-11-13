"""Tests for the BigQuery MCP helpers."""

import io
import json
from types import SimpleNamespace

import httpx2 as httpx
from rich.console import Console

from managed_agents_demo import mcp
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")

ROWS_TEXT = json.dumps(
    {
        "schema": {"fields": [{"name": "name"}, {"name": "total"}]},
        "rows": [
            {"f": [{"v": "Liam"}, {"v": "19777"}]},
            {"f": [{"v": "Noah"}, {"v": "18630"}]},
        ],
        "jobComplete": True,
    }
)


def test_bigquery_tool_has_url_name_and_headers():
    tool = mcp.bigquery_tool("tok", "test-project")
    assert tool == {
        "type": "mcp_server",
        "name": "bigquery",
        "url": "https://bigquery.googleapis.com/mcp",
        "headers": {"Authorization": "Bearer tok", "X-Goog-User-Project": "test-project"},
    }


def test_override_tools_keep_code_execution():
    tools = mcp.override_tools("tok", "p")
    assert tools[0] == {"type": "code_execution"}
    assert tools[1]["type"] == "mcp_server"


def test_direct_query_parses_rows():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["Authorization"]
        result = {"content": [{"type": "text", "text": ROWS_TEXT}], "isError": False}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    rows = mcp.direct_query(http, "tok", "test-project", "SELECT 1")
    assert rows == [{"name": "Liam", "total": "19777"}, {"name": "Noah", "total": "18630"}]
    assert seen["body"]["method"] == "tools/call"
    assert seen["body"]["params"]["name"] == "execute_sql_readonly"
    assert seen["body"]["params"]["arguments"] == {"projectId": "test-project", "query": "SELECT 1"}
    assert seen["auth"] == "Bearer tok"


def test_direct_query_raises_on_tool_error():
    def handler(request):
        result = {"content": [{"type": "text", "text": "invalid credentials"}], "isError": True}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        mcp.direct_query(http, "tok", "p", "SELECT 1")
    except mcp.McpError as exc:
        assert "invalid credentials" in str(exc)
    else:
        raise AssertionError("expected McpError")


def stream_events():
    return [
        {"event_type": "interaction.created", "interaction": {"id": "int-1"}},
        {
            "event_type": "step.start",
            "index": 0,
            "step": {"name": "bigquery:execute_sql_readonly", "type": "function_call"},
        },
        {"event_type": "step.start", "index": 1, "step": {"type": "model_output"}},
        {
            "event_type": "step.delta",
            "index": 1,
            "event_id": "e1",
            "delta": {"type": "text", "text": "Liam 19,777, Noah 18,630"},
        },
        {
            "event_type": "interaction.completed",
            "interaction": {"id": "int-1", "status": "completed", "environment_id": "env"},
        },
    ]


def run_demo(events, rows):
    requests = []
    sdk = SimpleNamespace(
        interactions=SimpleNamespace(
            create=lambda **kwargs: requests.append(kwargs) or iter(events)
        )
    )
    buffer = io.StringIO()
    console = Console(file=buffer, width=160, color_system=None)
    code = mcp.run(
        sdk,
        console,
        SETTINGS,
        token_provider=lambda: "secret-token",
        query=lambda token, project, sql: rows,
    )
    return code, requests, buffer.getvalue()


def test_run_sends_override_masks_token_and_checks_answer():
    rows = [{"name": "Liam", "total": "19777"}, {"name": "Noah", "total": "18630"}]
    code, requests, text = run_demo(stream_events(), rows)
    assert code == 0
    tools = requests[0]["tools"]
    assert tools[1]["headers"]["Authorization"] == "Bearer secret-token"
    assert "secret-token" not in text
    assert "bigquery:execute_sql_readonly" in text
    assert "The agent answer contains all 2 names" in text


def test_run_reports_missing_mcp_calls_and_mismatch():
    events = [event for event in stream_events() if event.get("index") != 0]
    rows = [{"name": "Olivia", "total": "1"}]
    code, _, text = run_demo(events, rows)
    assert code == 1
    assert "No MCP tool call" in text
    assert "Olivia" in text
