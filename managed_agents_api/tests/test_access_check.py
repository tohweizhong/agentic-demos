"""Tests for the access check."""

import io
import json

import httpx2 as httpx
from rich.console import Console

from managed_agents_demo import access_check, client
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")
OP_CREATE = "projects/test-project/locations/global/agents/demo-access-check/operations/1"
OP_DELETE = "projects/test-project/locations/global/operations/2"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def run(handler):
    calls: list[tuple[str, str]] = []

    def recording(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(recording))
    rest = client.RestClient(SETTINGS, token_provider=lambda: "t", http=http)
    buffer = io.StringIO()
    console = Console(file=buffer, width=150, color_system=None)
    clock = FakeClock()
    code = access_check.run(rest, console, clock=clock.time, sleep=clock.sleep, interval=5)
    return code, calls, buffer.getvalue()


def happy_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.method == "POST":
        body = json.loads(request.content)
        assert body["id"] == "demo-access-check"
        assert body["base_agent"] == "antigravity-preview-05-2026"
        return httpx.Response(200, json={"name": OP_CREATE})
    if request.method == "DELETE":
        return httpx.Response(200, json={"name": OP_DELETE})
    if path.endswith("/operations/1") or path.endswith("/operations/2"):
        return httpx.Response(200, json={"done": True, "response": {}})
    raise AssertionError(f"unexpected call {request.method} {path}")


def test_access_check_creates_waits_and_deletes():
    code, calls, text = run(happy_handler)
    assert code == 0
    methods = [method for method, _ in calls]
    assert methods == ["POST", "GET", "DELETE", "GET"]
    assert calls[2][1].endswith("/agents/demo-access-check")
    assert "Access check passed" in text
    assert "Create" in text and "Delete" in text


def test_access_check_permission_denied_names_permission_and_stops():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {"code": 403, "message": "Permission 'aiplatform.agents.create' denied"}
            },
        )

    code, calls, text = run(handler)
    assert code == 1
    assert [method for method, _ in calls] == ["POST"]
    assert "403" in text
    assert "aiplatform.agents.create" in text


def test_access_check_deletes_agent_when_create_operation_fails():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"name": OP_CREATE})
        if request.method == "DELETE":
            return httpx.Response(200, json={"name": OP_DELETE})
        if request.url.path.endswith("/operations/1"):
            return httpx.Response(200, json={"done": True, "error": {"message": "quota"}})
        return httpx.Response(200, json={"done": True})

    code, calls, text = run(handler)
    assert code == 1
    assert ("DELETE", calls[2][1]) == calls[2]
    assert "quota" in text


def test_access_check_existing_agent_is_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(409, json={"error": {"code": 409, "message": "already exists"}})
        raise AssertionError("no other call expected")

    code, calls, text = run(handler)
    assert code == 1
    assert "99_cleanup.py" in text


def test_access_check_skips_polling_when_delete_is_already_done():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"name": OP_CREATE})
        if request.method == "DELETE":
            return httpx.Response(200, json={"name": OP_DELETE, "done": True})
        return httpx.Response(200, json={"done": True})

    code, calls, _ = run(handler)
    assert code == 0
    assert [method for method, _ in calls] == ["POST", "GET", "DELETE"]
