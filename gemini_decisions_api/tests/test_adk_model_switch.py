"""Check that before_model_callback can change the model that ADK calls.

The test replaces the google-genai client inside the ADK Gemini model with a fake.
The fake records the model name of each generate_content call. No network call occurs.
"""

import asyncio
from unittest import mock

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

START_MODEL = "gemini-3.5-flash-lite"
NEW_MODEL = "gemini-4-argon"


class _FakeModels:
    def __init__(self):
        self.models_called = []

    async def generate_content(self, *, model, contents, config=None, **kwargs):
        self.models_called.append(model)
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(role="model", parts=[types.Part(text="ok")]),
                    finish_reason=types.FinishReason.STOP,
                )
            ]
        )


def _run_agent(callback):
    fake_models = _FakeModels()
    fake_client = mock.MagicMock()
    fake_client.aio.models = fake_models
    fake_client.vertexai = False

    agent = LlmAgent(
        name="switch_test",
        model=START_MODEL,
        instruction="Reply with ok.",
        before_model_callback=callback,
    )

    async def run():
        runner = InMemoryRunner(agent=agent, app_name="switch_test")
        session = await runner.session_service.create_session(app_name="switch_test", user_id="u")
        message = types.Content(role="user", parts=[types.Part(text="hello")])
        async for _ in runner.run_async(user_id="u", session_id=session.id, new_message=message):
            pass

    with mock.patch.object(Gemini, "api_client", new=fake_client):
        asyncio.run(run())
    return fake_models.models_called


def test_without_callback_adk_calls_the_agent_model():
    assert _run_agent(None) == [START_MODEL]


def test_callback_change_to_llm_request_model_changes_the_called_model():
    def switch_model(callback_context, llm_request):
        llm_request.model = NEW_MODEL
        return None

    assert _run_agent(switch_model) == [NEW_MODEL]
