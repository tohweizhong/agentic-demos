"""Tests for the reference agent setup."""

from unittest import mock

import pytest


@pytest.fixture(name="agent_module")
def fixture_agent_module(monkeypatch):
  monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.run.app/mcp")
  monkeypatch.setenv(
      "MCP_INVOKER_SERVICE_ACCOUNT",
      "invoker@example-project.iam.gserviceaccount.com",
  )
  monkeypatch.setenv("MODEL_ID", "test-model")
  monkeypatch.setenv("MODEL_LOCATION", "global")
  import importlib  # pylint: disable=g-import-not-at-top

  import agent  # pylint: disable=g-import-not-at-top

  return importlib.reload(agent)


def test_root_agent_has_the_work_items_toolset(agent_module):
  from google.adk.tools.mcp_tool import McpToolset  # pylint: disable=g-import-not-at-top

  assert any(isinstance(t, McpToolset) for t in agent_module.root_agent.tools)


def test_root_agent_uses_the_model_from_the_environment(agent_module):
  assert agent_module.root_agent.model.model == "test-model"


def test_instruction_tells_the_agent_to_report_denied_calls(agent_module):
  assert "denied" in agent_module.root_agent.instruction


def test_model_client_uses_the_model_location(agent_module):
  with mock.patch.object(
      agent_module.google.auth,
      "default",
      return_value=(object(), "example-project"),
  ), mock.patch.object(agent_module, "Client") as client:
    _ = agent_module.root_agent.model.api_client
  client.assert_called_once_with(
      vertexai=True, project="example-project", location="global"
  )


def test_agent_engine_app_wraps_the_root_agent(agent_module):
  del agent_module
  import agent_engine_app  # pylint: disable=g-import-not-at-top

  assert agent_engine_app.app is not None
