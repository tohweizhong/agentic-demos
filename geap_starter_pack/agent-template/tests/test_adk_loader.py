"""`adk api_server` must find the agent in the container layout."""

import pathlib

from google.adk.cli.utils.agent_loader import AgentLoader


def test_adk_loader_finds_the_root_agent():
  agents_dir = pathlib.Path(__file__).resolve().parents[1]
  loaded = AgentLoader(str(agents_dir)).load_agent("work_items")
  assert getattr(loaded, "name", None) == "work_items_assistant"
