"""Tests for the interaction demo steps."""

import io
from types import SimpleNamespace

from rich.console import Console

from managed_agents_demo import interact_demo
from managed_agents_demo.config import Settings
from tests.test_interactions import EVENTS

SETTINGS = Settings(project="test-project")


class FakeInteractions:
    def __init__(self):
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return iter(EVENTS)


class FakeAgents:
    def get(self, id):
        return SimpleNamespace(
            model_dump=lambda **kw: {
                "id": id,
                "tools": [{"type": "code_execution"}, {"type": "filesystem"}],
            }
        )


class FakeBlob:
    def __init__(self, name, size):
        self.name = name
        self.size = size


class FakeStorage:
    def __init__(self, blobs):
        self.blobs = blobs
        self.prefixes = []

    def list_blobs(self, bucket, prefix=None):
        self.prefixes.append((bucket, prefix))
        return [blob for blob in self.blobs if blob.name.startswith(prefix)]


def make():
    sdk = SimpleNamespace(interactions=FakeInteractions(), agents=FakeAgents())
    buffer = io.StringIO()
    console = Console(file=buffer, width=160, color_system=None)
    return sdk, console, buffer


def test_single_turn_saves_state_and_lists_output(tmp_path):
    sdk, console, buffer = make()
    storage = FakeStorage([FakeBlob("agent/output/report.md", 900), FakeBlob("agent/AGENTS.md", 1)])
    state = tmp_path / "state.json"
    code = interact_demo.run_single(sdk, storage, console, SETTINGS, state_path=state)
    assert code == 0
    request = sdk.interactions.requests[0]
    assert request["agent"] == "demo-data-analyst"
    assert "report-writer" in request["input"]
    assert state.exists()
    text = buffer.getvalue()
    assert "int-1" in text and "env_1" in text
    assert "list_dir" in text
    assert "agent/output/report.md" in text
    assert "agent/AGENTS.md" not in text
    assert "130" in text  # total tokens


def test_single_turn_reports_missing_output(tmp_path):
    sdk, console, buffer = make()
    code = interact_demo.run_single(
        sdk, FakeStorage([]), console, SETTINGS, state_path=tmp_path / "s.json"
    )
    assert code == 0
    assert "No files under" in buffer.getvalue()


def test_session_uses_saved_ids(tmp_path):
    sdk, console, buffer = make()
    state = tmp_path / "state.json"
    state.write_text(
        '{"agent_id": "demo-data-analyst", "interaction_id": "int-0", "environment_id": "env_0"}'
    )
    code = interact_demo.run_session(sdk, console, state_path=state)
    assert code == 0
    request = sdk.interactions.requests[0]
    assert request["previous_interaction_id"] == "int-0"
    assert request["environment"] == "env_0"


def test_session_without_state_states_the_fix(tmp_path):
    sdk, console, buffer = make()
    code = interact_demo.run_session(sdk, console, state_path=tmp_path / "missing.json")
    assert code == 1
    assert "02_interact.py" in buffer.getvalue()


def test_override_sends_tools_and_shows_stored_tools_unchanged():
    sdk, console, buffer = make()
    code = interact_demo.run_override(sdk, console)
    assert code == 0
    request = sdk.interactions.requests[0]
    assert request["tools"] == interact_demo.OVERRIDE_TOOLS
    text = buffer.getvalue()
    assert "filesystem" in text
    assert "did not change" in text
    assert "Search citations in this turn: none" in text


def test_failed_interaction_returns_error():
    sdk, console, buffer = make()
    sdk.interactions.create = lambda **kwargs: iter(
        [{"event_type": "error", "error": {"message": "sandbox failed"}}]
    )
    code = interact_demo.run_override(sdk, console)
    assert code == 1
    assert "sandbox failed" in buffer.getvalue()


def test_list_output_skips_folder_placeholder():
    storage = FakeStorage([FakeBlob("agent/output/", 0), FakeBlob("agent/output/a.png", 5)])
    assert interact_demo.list_output(storage, "b") == [("agent/output/a.png", 5)]


def test_sdk_error_is_printed_not_raised():
    sdk, console, buffer = make()

    def fail(**kwargs):
        raise RuntimeError("Error code: 400 - bad tool type")

    sdk.interactions.create = fail
    assert interact_demo.run_override(sdk, console) == 1
    assert "bad tool type" in buffer.getvalue()
