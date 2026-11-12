"""ADK agent with Decisions API routing and model-tier selection.

Two uses of the Decisions API inside ADK:

1. Router. ``DecisionRouterAgent`` asks one ``choice`` question and gives the email to the
   selected specialist. The routing is plain code, not an LLM transfer.
2. Model tier. Each specialist has a ``before_model_callback``. The callback asks one
   ``score`` question about complexity and sets ``llm_request.model`` for that turn.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from pydantic import ConfigDict

from decisions_demo.client import ChoiceAnswer, DecisionsClient, ScoreAnswer
from decisions_demo.config import load_config
from decisions_demo.questions import choice, score
from decisions_demo.scenario import CATEGORIES, COMPLEXITY_LEVELS, TIER_BY_LEVEL

CATEGORY_QUESTION = {
    "category": choice("Which enquiry category does this email belong to?", CATEGORIES)
}
COMPLEXITY_QUESTION = {
    "complexity": score("Rate how complex this email is to answer.", COMPLEXITY_LEVELS)
}

SPECIALIST_INSTRUCTION = (
    "You are a support agent for a fictional parcel-delivery company. The customer email is "
    "about this topic: {topic} Write a short, polite draft reply of at most five sentences. "
    "Do not promise money or dates. Say that a person will confirm any claim."
)


def _text_of(content: types.Content | None) -> str:
    """Return the joined text parts of one content object."""
    if content is None or not content.parts:
        return ""
    return "\n".join(part.text for part in content.parts if part.text)


def make_tier_callback(decider: Any, tier_models: Mapping[str, str]) -> Callable[..., None]:
    """Return a before_model_callback that sets the model from the complexity answer."""

    def tier_callback(callback_context: Any, llm_request: LlmRequest) -> None:
        user_texts = [_text_of(c) for c in llm_request.contents if c.role == "user"]
        text = next((t for t in reversed(user_texts) if t), "")
        if not text:
            return None
        result = decider.decide(text, COMPLEXITY_QUESTION)
        answer = result.answers["complexity"]
        assert isinstance(answer, ScoreAnswer)
        tier = TIER_BY_LEVEL.get(answer.most_likely_level, "pro")
        llm_request.model = tier_models[tier]
        callback_context.state["model_tier"] = tier
        callback_context.state["complexity_score"] = round(answer.score, 2)
        return None

    return tier_callback


class DecisionRouterAgent(BaseAgent):
    """Routes the user email to one specialist with one Decisions API choice question."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    decider: Any = None

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        text = _text_of(ctx.user_content)
        result = await asyncio.to_thread(self.decider.decide, text, CATEGORY_QUESTION)
        answer = result.answers["category"]
        assert isinstance(answer, ChoiceAnswer)
        target_name = f"{answer.choice}_agent"
        target = next(agent for agent in self.sub_agents if agent.name == target_name)

        note = (
            f"Decisions API: category {answer.choice} (confidence {answer.confidence:.2f}, "
            f"{result.latency_ms:.0f} ms). Routing to {target_name}."
        )
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(text=note)]),
            actions=EventActions(
                state_delta={
                    "category": answer.choice,
                    "category_confidence": round(answer.confidence, 4),
                    "routed_to": target_name,
                }
            ),
        )
        async for event in target.run_async(ctx):
            yield event


def build_root_agent(decider: Any, tier_models: Mapping[str, str] | None = None) -> BaseAgent:
    """Build the router and its six specialists."""
    from decisions_demo.config import DEFAULT_TIER_MODELS

    tiers = dict(tier_models or DEFAULT_TIER_MODELS)
    callback = make_tier_callback(decider, tiers)
    specialists = [
        LlmAgent(
            name=f"{category}_agent",
            model=tiers["flash"],
            description=f"Writes draft replies for {category} emails.",
            instruction=SPECIALIST_INSTRUCTION.format(topic=topic),
            before_model_callback=callback,
        )
        for category, topic in CATEGORIES.items()
    ]
    return DecisionRouterAgent(
        name="decisions_router",
        description="Routes parcel support emails with the Gemini Decisions API.",
        sub_agents=specialists,
        decider=decider,
    )


def _build_from_env() -> BaseAgent:
    """Build the agent from .env. `adk web` and `adk run` load this module."""
    load_dotenv()
    config = load_config(os.environ)
    if config.api_key and not os.environ.get("GOOGLE_API_KEY"):
        # ADK reads GOOGLE_API_KEY for the Gemini Developer API backend.
        os.environ["GOOGLE_API_KEY"] = config.api_key
    return build_root_agent(DecisionsClient(config), config.tier_models)


root_agent = _build_from_env() if os.environ.get("DECISIONS_AGENT_SKIP_BUILD") != "1" else None
