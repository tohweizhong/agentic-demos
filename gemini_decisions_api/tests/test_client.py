"""Tests for the Decisions API client. They use httpx.MockTransport, not the network."""

import json
from pathlib import Path

import httpx
import pytest

from decisions_demo.client import (
    ChoiceAnswer,
    DecisionsAPIError,
    DecisionsClient,
    NoulAnswer,
    ScoreAnswer,
    image_block,
    parse_response,
)
from decisions_demo.config import load_config
from decisions_demo.questions import noul

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "real_response.json").read_text())


def make_client(handler, env=None, token_provider=None):
    config = load_config(env or {"GEMINI_API_KEY": "test-key"})
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return DecisionsClient(config, http_client=http, token_provider=token_provider)


def test_parse_real_response_noul():
    result = parse_response(FIXTURE, latency_ms=12.0)

    answer = result.answers["has_tracking_number"]
    assert isinstance(answer, NoulAnswer)
    assert answer.probability == pytest.approx(0.9748, abs=1e-4)
    assert answer.value is True


def test_parse_real_response_choice():
    result = parse_response(FIXTURE, latency_ms=12.0)

    answer = result.answers["category"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice == "tracking"
    assert answer.probabilities["redelivery"] == pytest.approx(0.000159, abs=1e-6)
    assert list(answer.ranked())[0] == ("tracking", answer.probabilities["tracking"])


def test_parse_real_response_score_uses_int_levels():
    result = parse_response(FIXTURE, latency_ms=12.0)

    answer = result.answers["complexity"]
    assert isinstance(answer, ScoreAnswer)
    assert answer.score == pytest.approx(1.3034, abs=1e-4)
    assert set(answer.probabilities) == {0, 1, 2}
    assert answer.legend[1].startswith("Medium")
    assert answer.most_likely_level == 1


def test_parse_usage_and_latency():
    result = parse_response(FIXTURE, latency_ms=12.5)

    assert result.input_tokens == 391
    assert result.output_tokens == 0
    assert result.latency_ms == 12.5


def test_noul_below_half_is_false():
    result = parse_response(
        {"answers": {"q": {"type": "noul", "noul": 0.2, "confidence": 0.8}}}, latency_ms=1
    )

    assert result.answers["q"].value is False


def test_parse_rejects_unknown_answer_type():
    with pytest.raises(DecisionsAPIError, match="Unknown answer type"):
        parse_response({"answers": {"q": {"type": "other"}}}, latency_ms=1)


def test_gemini_api_request_shape():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=FIXTURE)

    client = make_client(handler)
    client.decide("Where is my parcel?", {"q": noul("x")})

    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/decisions"
    assert seen["key"] == "test-key"
    assert seen["body"] == {
        "model": "models/gemini-decision-1",
        "input": "Where is my parcel?",
        "questions": {"q": {"type": "noul", "instructions": "x"}},
    }


def test_vertex_request_shape():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=FIXTURE)

    client = make_client(
        handler,
        env={"GOOGLE_GENAI_USE_VERTEXAI": "true", "GOOGLE_CLOUD_PROJECT": "demo-p"},
        token_provider=lambda: "token-1",
    )
    client.decide("x", {"q": noul("x")})

    assert seen["url"] == (
        "https://aiplatform.googleapis.com/v1beta1/projects/demo-p/locations/global/decisions"
    )
    assert seen["auth"] == "Bearer token-1"
    # Duckie (12 Nov 2026): Vertex AI needs the bare model ID. Not confirmed by a real call yet.
    assert seen["body"]["model"] == "gemini-decision-exp"


def test_decide_returns_parsed_result_with_latency():
    client = make_client(lambda request: httpx.Response(200, json=FIXTURE))

    result = client.decide("x", {"q": noul("x")})

    assert result.answers["category"].choice == "tracking"
    assert result.latency_ms >= 0


def test_api_error_includes_status_and_message():
    body = {"error": {"code": 402, "message": "Your prepayment credits are depleted."}}
    client = make_client(lambda request: httpx.Response(402, json=body))

    with pytest.raises(DecisionsAPIError) as error:
        client.decide("x", {"q": noul("x")})

    assert error.value.status == 402
    assert "prepayment credits" in str(error.value)


def test_api_error_with_non_json_body():
    client = make_client(lambda request: httpx.Response(500, text="Server error"))

    with pytest.raises(DecisionsAPIError, match="Server error"):
        client.decide("x", {"q": noul("x")})


def test_decide_validates_questions_before_the_call():
    calls = []
    client = make_client(lambda request: calls.append(1) or httpx.Response(200, json=FIXTURE))

    with pytest.raises(ValueError):
        client.decide("x", {"bad key": noul("x")})
    assert calls == []


def test_image_block():
    block = image_block(b"\x89PNG", "image/png")

    assert block == {"type": "image", "data": "iVBORw==", "mime_type": "image/png"}
