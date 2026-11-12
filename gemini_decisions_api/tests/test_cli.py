"""Tests for the command-line interface. They use the fake client."""

import json
from pathlib import Path

import pytest

from decisions_demo.__main__ import main
from decisions_demo.client import parse_response
from decisions_demo.fake import FakeDecisionsClient

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "real_response.json").read_text())


@pytest.fixture
def fake_client():
    return FakeDecisionsClient()


def test_triage_prints_answers_and_decision(fake_client, capsys):
    code = main(["triage", "--email", "Where is my parcel AB123456789XX?"], client=fake_client)

    out = capsys.readouterr().out
    assert code == 0
    assert "Input" in out and "Answers" in out and "Decision" in out
    assert "Model tier" in out
    assert fake_client.calls[0][0] == "Where is my parcel AB123456789XX?"


def test_triage_uses_sample_email_when_none_given(fake_client, capsys):
    assert main(["triage"], client=fake_client) == 0
    assert "parcel" in fake_client.calls[0][0].lower()


def test_tools_prints_selected_tool(fake_client, capsys):
    code = main(["tools", "--email", "Is this SMS link real?"], client=fake_client)

    out = capsys.readouterr().out
    assert code == 0
    assert "Selected tool" in out


def test_multimodal_sends_image_block(fake_client, capsys):
    code = main(["multimodal"], client=fake_client)

    sent_input = fake_client.calls[0][0]
    assert code == 0
    assert isinstance(sent_input, list)
    assert sent_input[0]["type"] == "image"
    assert sent_input[0]["mime_type"] == "image/png"


def test_fake_client_answers_every_question_type(fake_client):
    from decisions_demo.scenario import triage_questions

    result = fake_client.decide("x", triage_questions())

    assert set(result.answers) == set(triage_questions())


def test_fake_client_can_return_a_fixed_response():
    client = FakeDecisionsClient(responder=lambda _input, _q: parse_response(FIXTURE, 5.0))

    assert client.decide("x", {}).answers["category"].choice == "tracking"


def test_missing_key_prints_fix_and_returns_2(monkeypatch, capsys):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.setattr("decisions_demo.__main__.load_dotenv", lambda *a, **k: None)

    code = main(["triage"])

    assert code == 2
    assert "GEMINI_API_KEY is not set" in capsys.readouterr().err


def test_api_error_prints_status_and_returns_1(capsys):
    from decisions_demo.client import DecisionsAPIError

    def fail(_input, _questions):
        raise DecisionsAPIError("Your prepayment credits are depleted.", status=402)

    code = main(["triage"], client=FakeDecisionsClient(responder=fail))

    err = capsys.readouterr().err
    assert code == 1
    assert "402" in err and "prepayment" in err
