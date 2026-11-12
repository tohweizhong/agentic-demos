"""Integration test: run the ADK agent against the real APIs.

It runs only with `pytest -m integration` and a real key in .env.
"""

import asyncio
import os

import pytest
from dotenv import dotenv_values

pytestmark = pytest.mark.integration


def test_agent_routes_and_answers_with_real_apis(monkeypatch):
    values = dotenv_values(".env")
    if not values.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY is not set in .env.")
    monkeypatch.setenv("GOOGLE_API_KEY", values["GEMINI_API_KEY"])
    for name, value in values.items():
        if value:
            monkeypatch.setenv(name, value)

    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from decisions_agent.agent import build_root_agent
    from decisions_demo.client import DecisionsClient
    from decisions_demo.config import load_config

    config = load_config(os.environ)
    agent = build_root_agent(DecisionsClient(config), config.tier_models)

    async def run():
        runner = InMemoryRunner(agent=agent, app_name="it")
        session = await runner.session_service.create_session(app_name="it", user_id="u")
        text = "The vase in my parcel arrived broken. I want my money back."
        message = types.Content(role="user", parts=[types.Part(text=text)])
        events = [
            e
            async for e in runner.run_async(user_id="u", session_id=session.id, new_message=message)
        ]
        session = await runner.session_service.get_session(
            app_name="it", user_id="u", session_id=session.id
        )
        return events, session.state

    events, state = asyncio.run(asyncio.wait_for(run(), timeout=120))

    assert state["routed_to"] == "damage_claim_agent"
    assert state["model_tier"] in {"lite", "flash", "pro"}
    replies = [e for e in events if e.author == "damage_claim_agent" and e.content]
    assert replies, "The specialist returned no reply."
    print("STATE", dict(state))
    print("REPLY", replies[-1].content.parts[0].text)
