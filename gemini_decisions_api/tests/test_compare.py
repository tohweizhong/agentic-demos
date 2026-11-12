"""Tests for the comparison between the Decisions API and generateContent."""

import json
from types import SimpleNamespace

import pytest

from decisions_demo.__main__ import main
from decisions_demo.compare import (
    PRICES_PER_1M,
    GenerateResult,
    build_prompt,
    build_response_schema,
    estimate_cost,
    parse_generated,
    run_generate,
)
from decisions_demo.fake import FakeDecisionsClient
from decisions_demo.questions import choice, noul, score

QUESTIONS = {
    "has_link": noul("The email has a link."),
    "category": choice(
        "Which category?", {"tracking": "Where is it.", "scam_check": "Is it real."}
    ),
    "complexity": score("How complex?", ["Low.", "Medium.", "High."]),
}


def test_schema_has_one_property_for_each_question():
    schema = build_response_schema(QUESTIONS)

    assert schema["type"] == "object"
    assert schema["required"] == ["has_link", "category", "complexity"]
    assert schema["properties"]["has_link"] == {"type": "boolean"}
    assert schema["properties"]["category"] == {
        "type": "string",
        "enum": ["tracking", "scam_check"],
    }
    assert schema["properties"]["complexity"] == {"type": "integer", "minimum": 0, "maximum": 2}


def test_prompt_lists_every_question_and_the_email():
    prompt = build_prompt("Where is my parcel?", QUESTIONS)

    assert "Where is my parcel?" in prompt
    for key in QUESTIONS:
        assert key in prompt
    assert "0: Low." in prompt
    assert "tracking: Where is it." in prompt


def test_parse_generated():
    parsed = parse_generated('{"has_link": false, "category": "tracking", "complexity": 1}')

    assert parsed == {"has_link": False, "category": "tracking", "complexity": 1}


def test_parse_generated_rejects_bad_json():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_generated("not json")


def test_estimate_cost_uses_price_table():
    price_in, price_out = PRICES_PER_1M["gemini-3.8-flash"]

    cost = estimate_cost("gemini-3.8-flash", input_tokens=1_000_000, output_tokens=2_000_000)

    assert cost == pytest.approx(price_in + 2 * price_out)


def test_estimate_cost_for_decision_model_has_no_output_price():
    assert estimate_cost("gemini-decision-1", 1_000_000, 0) == pytest.approx(0.10)


def test_estimate_cost_unknown_model_is_none():
    assert estimate_cost("unknown-model", 10, 10) is None


class FakeModels:
    def __init__(self, text):
        self.text = text
        self.kwargs = None

    def generate_content(self, **kwargs):
        self.kwargs = kwargs
        usage = SimpleNamespace(
            prompt_token_count=300, candidates_token_count=20, thoughts_token_count=80
        )
        return SimpleNamespace(text=self.text, usage_metadata=usage)


def test_run_generate_sends_json_schema_and_counts_thinking_as_output():
    models = FakeModels(json.dumps({"has_link": False, "category": "tracking", "complexity": 0}))
    genai_client = SimpleNamespace(models=models)

    result = run_generate(genai_client, "gemini-3.8-flash", "Where?", QUESTIONS)

    assert isinstance(result, GenerateResult)
    assert result.answers["category"] == "tracking"
    assert result.input_tokens == 300
    assert result.output_tokens == 100
    assert models.kwargs["model"] == "gemini-3.8-flash"
    config = models.kwargs["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema["required"] == list(QUESTIONS)


def test_compare_command_prints_both_rows_and_marks_estimates(capsys):
    from decisions_demo.scenario import triage_questions

    keys = list(triage_questions())
    answers = {k: False for k in keys}
    answers.update({"category": "tracking", "complexity": 1})
    models = FakeModels(json.dumps(answers))

    code = main(
        ["compare"],
        client=FakeDecisionsClient(),
        genai_client=SimpleNamespace(models=models),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "Decisions API" in out and "generateContent" in out
    assert "estimated" in out.lower()
    assert "Agreement" in out


def test_compare_command_reports_generate_error(capsys):
    from google.genai import errors

    class FailingModels:
        def generate_content(self, **kwargs):
            raise errors.ServerError(504, {"error": {"message": "Deadline expired."}})

    code = main(
        ["compare"],
        client=FakeDecisionsClient(),
        genai_client=SimpleNamespace(models=FailingModels()),
    )

    assert code == 1
    assert "generateContent error" in capsys.readouterr().err


def test_compare_default_model_is_lite_tier(capsys):
    from decisions_demo.config import DEFAULT_TIER_MODELS
    from decisions_demo.scenario import triage_questions

    answers = {k: False for k in triage_questions()}
    answers.update({"category": "tracking", "complexity": 0})
    models = FakeModels(json.dumps(answers))

    main(["compare"], client=FakeDecisionsClient(), genai_client=SimpleNamespace(models=models))

    assert models.kwargs["model"] == DEFAULT_TIER_MODELS["lite"]
