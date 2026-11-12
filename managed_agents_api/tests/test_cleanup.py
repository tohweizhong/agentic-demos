"""Tests for the cleanup steps."""

import io
from types import SimpleNamespace

import httpx2 as httpx
from rich.console import Console

from managed_agents_demo import cleanup, client
from managed_agents_demo.config import Settings

SETTINGS = Settings(project="test-project")


class FakeAgents:
    def __init__(self, ids):
        self.ids = ids

    def list(self, *, parent=None, page_token=None, page_size=None):
        return SimpleNamespace(
            agents=[SimpleNamespace(id=agent_id) for agent_id in self.ids], next_page_token=None
        )


class FakeBucket:
    def __init__(self):
        self.deleted_with = None

    def delete(self, force=False):
        self.deleted_with = force


class FakeStorage:
    def __init__(self, bucket):
        self.bucket_obj = bucket

    def lookup_bucket(self, name):
        return self.bucket_obj


def run(ids, answers=(), yes=False, bucket=False, storage_bucket=None, state=None):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        return httpx.Response(200, json={"name": "projects/p/operations/1", "done": True})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    rest = client.RestClient(SETTINGS, token_provider=lambda: "t", http=http)
    sdk = SimpleNamespace(agents=FakeAgents(ids))
    storage = FakeStorage(storage_bucket)
    buffer = io.StringIO()
    console = Console(file=buffer, width=160, color_system=None)
    replies = iter(answers)
    code = cleanup.run(
        rest,
        sdk,
        storage,
        console,
        SETTINGS,
        yes=yes,
        delete_bucket=bucket,
        confirm=lambda prompt: next(replies),
        state_path=state,
    )
    return code, calls, buffer.getvalue()


def test_deletes_only_demo_agents_after_confirmation():
    code, calls, text = run(["demo-a", "prod-agent", "demo-b"], answers=["y"])
    assert code == 0
    assert calls == [
        ("DELETE", "/v1beta1/projects/test-project/locations/global/agents/demo-a"),
        ("DELETE", "/v1beta1/projects/test-project/locations/global/agents/demo-b"),
    ]
    assert "prod-agent" not in [path.rsplit("/", 1)[-1] for _, path in calls]
    assert "IAM" in text


def test_no_answer_deletes_nothing():
    code, calls, text = run(["demo-a"], answers=["n"])
    assert code == 0
    assert calls == []
    assert "Nothing deleted" in text


def test_yes_flag_skips_confirmation():
    code, calls, _ = run(["demo-a"], yes=True)
    assert code == 0
    assert len(calls) == 1


def test_no_demo_agents():
    code, calls, text = run(["prod-agent"], answers=[])
    assert code == 0
    assert calls == []
    assert "No demo agents" in text


def test_bucket_is_deleted_only_with_flag_and_second_confirmation():
    bucket = FakeBucket()
    run(["demo-a"], answers=["y", "y"], bucket=True, storage_bucket=bucket)
    assert bucket.deleted_with is True

    kept = FakeBucket()
    run(["demo-a"], answers=["y", "n"], bucket=True, storage_bucket=kept)
    assert kept.deleted_with is None

    not_asked = FakeBucket()
    run(["demo-a"], answers=["y"], bucket=False, storage_bucket=not_asked)
    assert not_asked.deleted_with is None


def test_missing_bucket_is_reported():
    code, _, text = run([], yes=True, bucket=True, storage_bucket=None)
    assert code == 0
    assert "does not exist" in text


def test_local_state_file_is_removed(tmp_path):
    state = tmp_path / "last_interaction.json"
    state.write_text("{}")
    run(["demo-a"], yes=True, state=state)
    assert not state.exists()


def test_delete_error_returns_one():
    def handler(request):
        return httpx.Response(403, json={"error": {"message": "Permission denied"}})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    rest = client.RestClient(SETTINGS, token_provider=lambda: "t", http=http)
    buffer = io.StringIO()
    code = cleanup.run(
        rest,
        SimpleNamespace(agents=FakeAgents(["demo-a"])),
        FakeStorage(None),
        Console(file=buffer, width=160, color_system=None),
        SETTINGS,
        yes=True,
    )
    assert code == 1
    assert "Permission denied" in buffer.getvalue()
