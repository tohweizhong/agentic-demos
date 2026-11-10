"""Tests for the agent definition. These tests run offline."""

import asyncio
from unittest import mock

from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import pytest

from agent import agent as agent_module

_EXPORTER = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def _tracer_provider():
  provider = TracerProvider()
  provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
  trace.set_tracer_provider(provider)
  yield


@pytest.fixture(autouse=True)
def _clear_spans():
  _EXPORTER.clear()
  yield


def test_agent_has_preload_memory_tool_and_status_tool():
  tools = agent_module.root_agent.tools
  assert any(isinstance(t, PreloadMemoryTool) for t in tools)
  assert agent_module.get_service_status in tools


def test_agent_uses_the_memory_callback():
  assert (
      agent_module.root_agent.after_agent_callback
      is agent_module.save_session_to_memory
  )


def test_agent_model_comes_from_the_environment(monkeypatch):
  monkeypatch.setenv("MODEL", "gemini-test")
  assert agent_module.model_name() == "gemini-test"
  monkeypatch.delenv("MODEL")
  assert agent_module.model_name() == "gemini-3.5-flash"


def test_get_service_status_returns_sample_data_for_a_known_service():
  result = agent_module.get_service_status("payments")
  assert result["service"] == "payments"
  assert result["status"] == "degraded"
  assert result["sample_data"] is True


def test_get_service_status_handles_an_unknown_service():
  result = agent_module.get_service_status("Unknown Service")
  assert result["service"] == "unknown service"
  assert result["status"] == "not_found"


def test_get_service_status_makes_a_custom_span_with_attributes():
  result = agent_module.get_service_status("search")
  spans = _EXPORTER.get_finished_spans()
  assert len(spans) == 1
  span = spans[0]
  assert span.name == "get_service_status"
  assert span.attributes["starter_pack.service"] == "search"
  assert span.attributes["starter_pack.status"] == "operational"
  # The tool returns the trace ID of its span. The O11y sample prints it.
  assert result["trace_id"] == format(span.context.trace_id, "032x")


def test_save_session_to_memory_calls_the_adk_api():
  callback_context = mock.MagicMock()
  callback_context.add_session_to_memory = mock.AsyncMock()
  result = asyncio.run(agent_module.save_session_to_memory(callback_context))
  callback_context.add_session_to_memory.assert_awaited_once_with()
  assert result is None


def test_save_session_to_memory_does_not_stop_the_turn_on_error():
  callback_context = mock.MagicMock()
  callback_context.add_session_to_memory = mock.AsyncMock(
      side_effect=ValueError("memory service is not available")
  )
  assert asyncio.run(agent_module.save_session_to_memory(callback_context)) is None
