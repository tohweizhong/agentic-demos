"""Tests for the sample helpers. These tests run offline."""

from samples import common


def _event(parts, author="services_agent"):
  return {"author": author, "content": {"role": "model", "parts": parts}}


def test_event_text_joins_the_text_parts():
  event = _event([{"text": "Hello"}, {"function_call": {"name": "x"}}, {"text": " there"}])
  assert common.event_text(event) == "Hello there"


def test_event_text_handles_an_event_with_no_content():
  assert common.event_text({"author": "user"}) == ""


def test_final_text_returns_the_text_of_the_last_event_with_text():
  events = [
      _event([{"text": "first"}]),
      _event([{"function_response": {"name": "x", "response": {}}}]),
      _event([{"text": "last"}]),
  ]
  assert common.final_text(events) == "last"


def test_function_responses_returns_name_and_response():
  events = [
      _event([{"function_call": {"name": "get_service_status", "args": {}}}]),
      _event([
          {
              "function_response": {
                  "name": "get_service_status",
                  "response": {"status": "operational", "trace_id": "ab"},
              }
          }
      ]),
  ]
  assert common.function_responses(events) == [
      ("get_service_status", {"status": "operational", "trace_id": "ab"})
  ]


def test_function_responses_ignores_events_without_a_response():
  assert common.function_responses([_event([{"text": "x"}]), {"author": "user"}]) == []


def test_trace_ids_from_events_reads_the_tool_result():
  events = [
      _event([
          {
              "function_response": {
                  "name": "get_service_status",
                  "response": {"trace_id": "0af7651916cd43dd8448eb211c80319c"},
              }
          }
      ])
  ]
  assert common.trace_ids_from_events(events) == ["0af7651916cd43dd8448eb211c80319c"]


def test_cloud_trace_link():
  assert common.cloud_trace_link("my-project", "abc") == (
      "https://console.cloud.google.com/traces/explorer;traceId=abc"
      "?project=my-project"
  )


def test_memory_scope_uses_the_runtime_id_as_app_name():
  assert common.memory_scope("42", "user-1") == {"app_name": "42", "user_id": "user-1"}


def test_memory_fact_reads_the_fact_field():
  retrieved = {"memory": {"fact": "The user prefers window seats."}}
  assert common.memory_fact(retrieved) == "The user prefers window seats."


def test_memory_fact_reads_an_object_with_attributes():
  class Memory:
    fact = "fact text"

  class Retrieved:
    memory = Memory()

  assert common.memory_fact(Retrieved()) == "fact text"


def test_event_summary_names_the_author_and_the_part_types():
  event = _event([{"text": "Hi"}, {"function_call": {"name": "get_service_status"}}])
  assert common.event_summary(event) == (
      "services_agent: text, function_call(get_service_status)"
  )


def test_session_id_reads_dict_and_object_forms():
  assert common.session_id({"id": "s1"}) == "s1"

  class Session:
    id = "s2"

  assert common.session_id(Session()) == "s2"
