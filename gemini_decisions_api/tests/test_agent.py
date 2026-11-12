"""Tests for the ADK agent: the Decisions router and the model-tier callback.

A fake decider replaces the Decisions API. A fake genai client replaces the Gemini API.
No network call occurs.
"""

import asyncio
from types import SimpleNamespace
from unittest import mock

import pytest
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.runners import InMemoryRunner
from google.genai import types

from decisions_agent.agent import build_root_agent, make_tier_callback
from decisions_demo.client import ChoiceAnswer, DecisionResult, ScoreAnswer
from decisions_demo.config import DEFAULT_TIER_MODELS
from decisions_demo.scenario import CATEGORIES


class FakeDecider:
    """Answers the category question and the complexity question with fixed values."""

    def __init__(self, category="tracking", level=0):
        self.category = category
        self.level = level
        self.calls = []

    def decide(self, input, questions):
        self.calls.append((input, set(questions)))
        answers = {}
        if "category" in questions:
            probs = {k: (0.95 if k == self.category else 0.01) for k in CATEGORIES}
            answers["category"] = ChoiceAnswer(self.category, 0.95, probs)
        if "complexity" in questions:
            probs = {i: (0.9 if i == self.level else 0.05) for i in range(3)}
            answers["complexity"] = ScoreAnswer(float(self.level), 0.9, probs, {})
        return DecisionResult(answers, input_tokens=50, output_tokens=0, latency_ms=5.0)


class FakeModels:
    def __init__(self):
        self.models_called = []

    async def generate_content(self, *, model, contents, config=None, **kwargs):
        self.models_called.append(model)
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(role="model", parts=[types.Part(text="Draft reply.")]),
                    finish_reason=types.FinishReason.STOP,
                )
            ]
        )


def run(agent, text):
    fake_models = FakeModels()
    fake_client = mock.MagicMock()
    fake_client.aio.models = fake_models
    fake_client.vertexai = False

    async def go():
        runner = InMemoryRunner(agent=agent, app_name="t")
        session = await runner.session_service.create_session(app_name="t", user_id="u")
        message = types.Content(role="user", parts=[types.Part(text=text)])
        events = [
            e
            async for e in runner.run_async(user_id="u", session_id=session.id, new_message=message)
        ]
        session = await runner.session_service.get_session(
            app_name="t", user_id="u", session_id=session.id
        )
        return events, session.state

    with mock.patch.object(Gemini, "api_client", new=fake_client):
        events, state = asyncio.run(go())
    return events, state, fake_models.models_called


def test_root_agent_has_one_specialist_for_each_category():
    agent = build_root_agent(decider=FakeDecider())

    assert {sub.name for sub in agent.sub_agents} == {f"{c}_agent" for c in CATEGORIES}


@pytest.mark.parametrize("category", list(CATEGORIES))
def test_router_sends_the_email_to_the_selected_specialist(category):
    agent = build_root_agent(decider=FakeDecider(category=category))

    events, state, _ = run(agent, "Some customer email.")

    authors = [e.author for e in events]
    assert f"{category}_agent" in authors
    assert state["routed_to"] == f"{category}_agent"
    assert state["category"] == category


def test_router_asks_the_category_question_with_the_user_text():
    decider = FakeDecider()
    agent = build_root_agent(decider=decider)

    run(agent, "Where is my parcel?")

    assert decider.calls[0] == ("Where is my parcel?", {"category"})


@pytest.mark.parametrize(("level", "tier"), [(0, "lite"), (1, "flash"), (2, "pro")])
def test_specialist_uses_the_model_tier_from_the_callback(level, tier):
    agent = build_root_agent(decider=FakeDecider(level=level))

    _, state, models_called = run(agent, "Some customer email.")

    assert models_called == [DEFAULT_TIER_MODELS[tier]]
    assert state["model_tier"] == tier


def test_callback_sets_model_on_the_request():
    callback = make_tier_callback(FakeDecider(level=2), DEFAULT_TIER_MODELS)
    request = LlmRequest(
        model="start-model",
        contents=[types.Content(role="user", parts=[types.Part(text="Complex claim.")])],
    )
    context = SimpleNamespace(state={})

    assert callback(context, request) is None
    assert request.model == DEFAULT_TIER_MODELS["pro"]
    assert context.state["model_tier"] == "pro"


def test_callback_without_user_text_keeps_the_model():
    callback = make_tier_callback(FakeDecider(level=2), DEFAULT_TIER_MODELS)
    request = LlmRequest(model="start-model", contents=[])
    context = SimpleNamespace(state={})

    callback(context, request)

    assert request.model == "start-model"
