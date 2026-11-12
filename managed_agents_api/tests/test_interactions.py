"""Tests for the interaction helpers.

The events in this file copy the shape of real stream events that the API sent on
12 Nov 2026. The IDs and the text are shortened.
"""

from types import SimpleNamespace

from managed_agents_demo import interactions

EVENTS = [
    {"event_type": "interaction.created", "interaction": {"id": "int-1", "status": "in_progress"}},
    {"event_type": "interaction.status_update", "interaction_id": "int-1", "status": "in_progress"},
    {
        "event_type": "step.start",
        "index": 0,
        "step": {"id": "call_1", "name": "list_dir", "type": "function_call"},
    },
    {
        "event_type": "step.delta",
        "index": 0,
        "event_id": "e0",
        "delta": {"type": "arguments_delta", "arguments": '{"DirectoryPath":"/workspace/.agent"}'},
    },
    {"event_type": "step.stop", "index": 0},
    {
        "event_type": "step.start",
        "index": 1,
        "step": {"call_id": "call_1", "name": "list_dir", "type": "function_result"},
    },
    {
        "event_type": "step.delta",
        "index": 1,
        "event_id": "e1",
        "delta": {
            "type": "function_result",
            "name": "list_dir",
            "is_error": False,
            "result": {"results": [{"name": "AGENTS.md"}]},
        },
    },
    {"event_type": "step.stop", "index": 1},
    {"event_type": "step.start", "index": 2, "step": {"type": "model_output"}},
    {
        "event_type": "step.delta",
        "index": 2,
        "event_id": "e2",
        "delta": {"type": "text", "text": "I will"},
    },
    {
        "event_type": "step.delta",
        "index": 2,
        "event_id": "e3",
        "delta": {"type": "text", "text": " read."},
    },
    # The API repeats the full text of a step in one delta without an event ID.
    {"event_type": "step.delta", "index": 2, "delta": {"type": "text", "text": "I will read."}},
    {"event_type": "step.stop", "index": 2},
    {"event_type": "step.start", "index": 3, "step": {"type": "model_output"}},
    {
        "event_type": "step.delta",
        "index": 3,
        "event_id": "e4",
        "delta": {"type": "text", "text": "Done"},
    },
    {
        "event_type": "step.delta",
        "index": 3,
        "event_id": "e5",
        "delta": {"type": "text", "text": "."},
    },
    {"event_type": "step.stop", "index": 3},
    {
        "event_type": "interaction.completed",
        "interaction": {
            "id": "int-1",
            "status": "completed",
            "environment_id": "env_1",
            "usage": {"total_input_tokens": 100, "total_output_tokens": 20, "total_tokens": 130},
        },
    },
]


def test_consume_collects_ids_usage_and_text():
    texts, steps = [], []
    summary = interactions.consume(EVENTS, on_text=texts.append, on_step=steps.append)
    assert summary.interaction_id == "int-1"
    assert summary.environment_id == "env_1"
    assert summary.status == "completed"
    assert summary.usage["total_tokens"] == 130
    assert "".join(texts) == "I will read.Done."
    assert summary.final_text == "Done."
    assert summary.tool_calls == ["list_dir"]
    assert steps == ["list_dir"]


def test_consume_accepts_sdk_models():
    models = [SimpleNamespace(model_dump=lambda event=event, **kw: event) for event in EVENTS]
    assert interactions.consume(models).environment_id == "env_1"


def test_consume_records_tool_errors_and_error_events():
    events = [
        {
            "event_type": "step.delta",
            "index": 0,
            "event_id": "x",
            "delta": {"type": "function_result", "name": "run_command", "is_error": True},
        },
        {"event_type": "error", "error": {"code": 500, "message": "sandbox failed"}},
    ]
    summary = interactions.consume(events)
    assert summary.tool_errors == ["run_command"]
    assert summary.errors == ["sandbox failed"]


def test_consume_uses_aggregate_when_chunks_are_missing():
    events = [
        {"event_type": "step.start", "index": 0, "step": {"type": "model_output"}},
        {"event_type": "step.delta", "index": 0, "delta": {"type": "text", "text": "All text."}},
    ]
    texts = []
    summary = interactions.consume(events, on_text=texts.append)
    assert summary.final_text == "All text."
    assert texts == ["All text."]


def test_build_request_first_turn():
    request = interactions.build_request("demo-a", "Analyse the data.")
    assert request == {
        "agent": "demo-a",
        "input": "Analyse the data.",
        "stream": True,
        "background": True,
        "store": True,
    }


def test_build_request_next_turn_and_override():
    request = interactions.build_request(
        "demo-a",
        "Next question.",
        previous_interaction_id="int-1",
        environment_id="env_1",
        tools=[{"type": "code_execution"}],
    )
    assert request["previous_interaction_id"] == "int-1"
    assert request["environment"] == "env_1"
    assert request["tools"] == [{"type": "code_execution"}]


def test_start_calls_sdk():
    calls = []
    sdk = SimpleNamespace(
        interactions=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or iter(EVENTS))
    )
    stream = interactions.start(sdk, interactions.build_request("demo-a", "hi"))
    assert list(stream) == EVENTS
    assert calls[0]["agent"] == "demo-a"


def test_state_round_trip(tmp_path):
    path = tmp_path / "output" / "last_interaction.json"
    interactions.save_state(path, "demo-a", "int-1", "env_1")
    assert interactions.load_state(path) == {
        "agent_id": "demo-a",
        "interaction_id": "int-1",
        "environment_id": "env_1",
    }


def test_load_state_missing_file_states_the_fix(tmp_path):
    try:
        interactions.load_state(tmp_path / "missing.json")
    except FileNotFoundError as exc:
        assert "02_interact.py" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_consume_records_built_in_tool_calls():
    events = [
        {"event_type": "step.start", "index": 0, "step": {"type": "google_search_call"}},
        {
            "event_type": "step.start",
            "index": 1,
            "step": {"type": "mcp_server_tool_call", "name": "query"},
        },
    ]
    steps = []
    summary = interactions.consume(events, on_step=steps.append)
    assert summary.tool_calls == ["google_search", "mcp_server_tool:query"]
    assert steps == summary.tool_calls


def test_consume_collects_search_citations():
    events = [
        {
            "event_type": "step.delta",
            "index": 3,
            "event_id": "c1",
            "delta": {
                "type": "text_annotation_delta",
                "text": "",
                "annotations": [
                    {"type": "url_citation", "title": "python.org", "url": "https://a"},
                    {"type": "url_citation", "title": "wikipedia.org", "url": "https://b"},
                    {"type": "url_citation", "title": "python.org", "url": "https://a"},
                ],
            },
        }
    ]
    summary = interactions.consume(events)
    assert summary.citations == ["python.org", "wikipedia.org"]
