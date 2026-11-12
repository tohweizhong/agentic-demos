"""Tests for the REST client and the operation polling."""

import json

import httpx2 as httpx
import pytest

from managed_agents_demo import client
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")


def make_rest(handler) -> client.RestClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return client.RestClient(SETTINGS, token_provider=lambda: "fake-token", http=http)


def test_request_sends_auth_headers_and_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["project"] = request.headers["X-Goog-User-Project"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"name": "op-1"})

    rest = make_rest(handler)
    data = rest.request("POST", "agents", json={"id": "demo-a"})
    assert data == {"name": "op-1"}
    assert seen["url"] == f"{SETTINGS.base_url}/agents"
    assert seen["auth"] == "Bearer fake-token"
    assert seen["project"] == "test-project"
    assert seen["body"] == {"id": "demo-a"}


def test_request_accepts_full_resource_name():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={})

    rest = make_rest(handler)
    rest.request("GET", "projects/test-project/locations/global/operations/9")
    assert seen["url"] == (
        "https://aiplatform.googleapis.com/v1beta1/projects/test-project/locations/global/operations/9"
    )


def test_request_empty_body_returns_empty_dict():
    rest = make_rest(lambda request: httpx.Response(200, content=b""))
    assert rest.request("DELETE", "agents/demo-a") == {}


def test_request_error_raises_api_error_with_status_and_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "Permission 'aiplatform.agents.create' denied.",
                    "status": "PERMISSION_DENIED",
                }
            },
        )

    rest = make_rest(handler)
    with pytest.raises(client.ApiError) as excinfo:
        rest.request("POST", "agents", json={})
    assert excinfo.value.status == 403
    assert "aiplatform.agents.create" in excinfo.value.message
    assert excinfo.value.permission == "aiplatform.agents.create"


def test_api_error_with_text_body():
    rest = make_rest(lambda request: httpx.Response(500, text="backend error"))
    with pytest.raises(client.ApiError) as excinfo:
        rest.request("GET", "agents")
    assert excinfo.value.status == 500
    assert "backend error" in excinfo.value.message
    assert excinfo.value.permission is None


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def make_poller(responses):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json=responses[min(len(calls) - 1, len(responses) - 1)])

    return make_rest(handler), calls


def test_wait_for_operation_polls_until_done():
    rest, calls = make_poller(
        [{"name": "op"}, {"name": "op"}, {"name": "op", "done": True, "response": {"id": "a"}}]
    )
    clock = FakeClock()
    ticks = []
    result = client.wait_for_operation(
        rest,
        "projects/test-project/locations/global/operations/op",
        interval=5,
        timeout=60,
        clock=clock.time,
        sleep=clock.sleep,
        on_tick=ticks.append,
    )
    assert result["response"] == {"id": "a"}
    assert len(calls) == 3
    assert ticks == [0.0, 5.0, 10.0]


def test_wait_for_operation_raises_on_operation_error():
    rest, _ = make_poller([{"done": True, "error": {"code": 9, "message": "bad config"}}])
    clock = FakeClock()
    with pytest.raises(client.OperationError, match="bad config"):
        client.wait_for_operation(rest, "op", clock=clock.time, sleep=clock.sleep)


def test_wait_for_operation_times_out():
    rest, _ = make_poller([{"name": "op"}])
    clock = FakeClock()
    with pytest.raises(TimeoutError, match="60"):
        client.wait_for_operation(
            rest, "op", interval=10, timeout=60, clock=clock.time, sleep=clock.sleep
        )


def test_operation_name_of_returns_name():
    assert (
        client.operation_name_of({"name": "projects/p/operations/1"}) == "projects/p/operations/1"
    )
    with pytest.raises(ValueError):
        client.operation_name_of({})
