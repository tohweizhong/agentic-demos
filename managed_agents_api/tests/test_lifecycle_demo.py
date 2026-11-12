"""Tests for the lifecycle demo steps."""

import io
import json
from types import SimpleNamespace

import httpx2 as httpx
from rich.console import Console

from managed_agents_demo import client, lifecycle_demo
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeAgents:
    def __init__(self) -> None:
        self.description = "Data analyst"

    def get(self, id):
        return SimpleNamespace(
            model_dump=lambda **kwargs: {
                "id": id,
                "description": self.description,
                "base_environment": {
                    "sources": [
                        {"type": "inline", "target": "data/sales.csv", "content": "a\nb\nc"}
                    ]
                },
            },
            id=id,
            description=self.description,
        )

    def list(self, *, parent=None, page_token=None, page_size=None):
        return SimpleNamespace(
            agents=[SimpleNamespace(id="demo-data-analyst"), SimpleNamespace(id="other-agent")],
            next_page_token=None,
        )


def run(handler, agents=None):
    calls = []

    def recording(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        return handler(request, agents)

    http = httpx.Client(transport=httpx.MockTransport(recording))
    rest = client.RestClient(SETTINGS, token_provider=lambda: "t", http=http)
    agents = agents or FakeAgents()
    sdk = SimpleNamespace(agents=agents)
    buffer = io.StringIO()
    console = Console(file=buffer, width=160, color_system=None)
    clock = FakeClock()
    code = lifecycle_demo.run(
        rest, sdk, console, SETTINGS, clock=clock.time, sleep=clock.sleep, interval=1
    )
    return code, calls, buffer.getvalue()


def happy(request: httpx.Request, agents) -> httpx.Response:
    if request.method == "POST":
        return httpx.Response(200, json={"name": "projects/p/operations/1"})
    if request.method == "PATCH":
        body = json.loads(request.content)
        if agents is not None:
            agents.description = body["description"]
        return httpx.Response(200, json={"name": "projects/p/operations/2", "done": True})
    return httpx.Response(200, json={"done": True})


def test_run_creates_waits_gets_lists_and_updates():
    agents = FakeAgents()
    code, calls, text = run(happy, agents)
    assert code == 0
    assert [method for method, _ in calls] == ["POST", "GET", "PATCH"]
    assert "demo-data-analyst" in text
    assert "other-agent" in text
    assert agents.description.startswith("Data analyst")
    assert "updated" in agents.description
    assert "02_interact.py" in text
    assert "99_cleanup.py" in text


def test_run_mounts_the_demo_bucket():
    _, _, text = run(happy)
    assert "gs://test-project-managed-agents-demo/agent" in text


def test_shorten_sources_cuts_long_content():
    body = {"base_environment": {"sources": [{"content": "1\n2\n3\n4\n5"}]}}
    shown = lifecycle_demo.shorten_sources(body)
    assert "lines in total" in shown["base_environment"]["sources"][0]["content"]


def test_run_reuses_existing_agent():
    def handler(request, agents):
        if request.method == "POST":
            return httpx.Response(409, json={"error": {"code": 409, "message": "already exists"}})
        return happy(request, agents)

    code, calls, text = run(handler)
    assert code == 0
    # The script sends the current configuration to the agent that exists, then the
    # description update.
    assert [method for method, _ in calls] == ["POST", "PATCH", "PATCH"]
    assert "already exists" in text


def test_run_stops_on_other_error():
    def handler(request, agents):
        return httpx.Response(400, json={"error": {"code": 400, "message": "bad source type"}})

    code, calls, text = run(handler)
    assert code == 1
    assert "bad source type" in text


def test_shorten_sources_keeps_short_content():
    body = {"base_environment": {"sources": [{"content": "one line"}]}}
    assert lifecycle_demo.shorten_sources(body) == body
