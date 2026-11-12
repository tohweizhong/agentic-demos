"""Tests for the lifecycle functions."""

import json
from types import SimpleNamespace

import httpx2 as httpx
import pytest

from managed_agents_demo import client, lifecycle
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")


def make_rest(handler):
    calls = []

    def recording(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, dict(request.url.params), body))
        return handler(request)

    http = httpx.Client(transport=httpx.MockTransport(recording))
    return client.RestClient(SETTINGS, token_provider=lambda: "t", http=http), calls


class FakeAgents:
    def __init__(self, pages):
        self.pages = pages
        self.list_calls = []
        self.get_calls = []

    def list(self, *, parent=None, page_token=None, page_size=None):
        self.list_calls.append((parent, page_token))
        return self.pages[page_token]

    def get(self, id):
        self.get_calls.append(id)
        return SimpleNamespace(id=id, name=f"projects/p/locations/global/agents/{id}")


def test_create_posts_body_and_returns_operation():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={"name": "op/1"}))
    operation = lifecycle.create(rest, {"id": "demo-a"})
    assert operation == {"name": "op/1"}
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/locations/global/agents")
    assert calls[0][3] == {"id": "demo-a"}


def test_update_sends_patch_with_update_mask_and_name():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={"name": "op/2"}))
    lifecycle.update(rest, "demo-a", {"description": "new"})
    method, path, params, body = calls[0]
    assert method == "PATCH"
    assert path.endswith("/agents/demo-a")
    assert params == {"update_mask": "description"}
    assert body == {"name": "demo-a", "description": "new"}


def test_update_mask_joins_many_fields():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={}))
    lifecycle.update(rest, "demo-a", {"description": "d", "system_instruction": "s"})
    assert calls[0][2] == {"update_mask": "description,system_instruction"}


def test_update_without_fields_is_an_error():
    rest, _ = make_rest(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValueError):
        lifecycle.update(rest, "demo-a", {})


def test_delete_sends_delete():
    rest, calls = make_rest(lambda request: httpx.Response(200, json={"done": True}))
    assert lifecycle.delete(rest, "demo-a") == {"done": True}
    assert calls[0][0] == "DELETE"
    assert calls[0][1].endswith("/agents/demo-a")


def test_get_uses_sdk():
    agents = FakeAgents({})
    sdk = SimpleNamespace(agents=agents)
    agent = lifecycle.get(sdk, "demo-a")
    assert agent.id == "demo-a"
    assert agents.get_calls == ["demo-a"]


def test_list_all_follows_pages():
    first = SimpleNamespace(agents=[SimpleNamespace(id="demo-a")], next_page_token="t2")
    second = SimpleNamespace(agents=[SimpleNamespace(id="other")], next_page_token=None)
    agents = FakeAgents({None: first, "t2": second})
    sdk = SimpleNamespace(agents=agents)
    result = lifecycle.list_all(sdk, SETTINGS.parent)
    assert [agent.id for agent in result] == ["demo-a", "other"]
    assert agents.list_calls == [(SETTINGS.parent, None), (SETTINGS.parent, "t2")]


def test_list_all_handles_empty_list():
    agents = FakeAgents({None: SimpleNamespace(agents=None, next_page_token=None)})
    assert lifecycle.list_all(SimpleNamespace(agents=agents), SETTINGS.parent) == []


def test_agent_id_of_prefers_id_then_name():
    assert lifecycle.agent_id_of(SimpleNamespace(id="demo-a", name="x/y")) == "demo-a"
    assert lifecycle.agent_id_of(SimpleNamespace(id=None, name="p/agents/demo-b")) == "demo-b"
    assert lifecycle.agent_id_of({"name": "p/agents/demo-c"}) == "demo-c"
