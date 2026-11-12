"""Compare one Decisions API call with one generateContent call on the same questions.

The generateContent call asks the same questions in a prompt and gets JSON back
through a response schema. The comparison shows latency, tokens, and estimated cost.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from decisions_demo.questions import Question

# US$ for each 1M tokens: (input, output). Paid tier, read from
# https://ai.google.dev/gemini-api/docs/pricing on 12 Nov 2026.
# gemini-3.8-flash prices are valid until 31 Dec 2026. gemini-4-argon input is valid until
# 30 Nov 2026. Output is the price for output tokens, including thinking tokens.
PRICES_PER_1M: dict[str, tuple[float, float]] = {
    "gemini-decision-1": (0.10, 0.0),
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.8-flash": (0.75, 3.75),
}


@dataclass(frozen=True)
class GenerateResult:
    """Answers and usage from one generateContent call."""

    answers: dict[str, Any]
    input_tokens: int
    output_tokens: int
    latency_ms: float


def build_response_schema(questions: Mapping[str, Question]) -> dict[str, Any]:
    """Return a JSON schema with one property for each question."""
    properties: dict[str, Any] = {}
    for key, question in questions.items():
        if question["type"] == "noul":
            properties[key] = {"type": "boolean"}
        elif question["type"] == "choice":
            properties[key] = {"type": "string", "enum": list(question["criteria"])}
        else:
            properties[key] = {
                "type": "integer",
                "minimum": 0,
                "maximum": len(question["criteria"]) - 1,
            }
    return {"type": "object", "properties": properties, "required": list(questions)}


def build_prompt(email: str, questions: Mapping[str, Question]) -> str:
    """Return a prompt that asks every question about the email."""
    lines = ["Answer each question about the email below. Reply only with JSON.", ""]
    for key, question in questions.items():
        lines.append(f"- {key} ({question['type']}): {question['instructions']}")
        if question["type"] == "choice":
            lines += [f"    {opt}: {desc}" for opt, desc in question["criteria"].items()]
        elif question["type"] == "score":
            lines += [f"    {i}: {level}" for i, level in enumerate(question["criteria"])]
        else:
            lines.append("    true or false")
    lines += ["", "Email:", email]
    return "\n".join(lines)


def parse_generated(text: str) -> dict[str, Any]:
    """Parse the JSON text from the model."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"The model output is not valid JSON: {text[:80]!r}") from error


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Return the estimated cost in US$, or None if the model has no price in the table."""
    if model not in PRICES_PER_1M:
        return None
    price_in, price_out = PRICES_PER_1M[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def run_generate(
    genai_client: Any, model: str, email: str, questions: Mapping[str, Question]
) -> GenerateResult:
    """Ask the questions with one generateContent call and a JSON response schema."""
    from google.genai import types

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_json_schema=build_response_schema(questions),
    )
    start = time.perf_counter()
    response = genai_client.models.generate_content(
        model=model, contents=build_prompt(email, questions), config=config
    )
    latency_ms = (time.perf_counter() - start) * 1000
    usage = response.usage_metadata
    output_tokens = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    return GenerateResult(
        answers=parse_generated(response.text),
        input_tokens=usage.prompt_token_count or 0,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
    )
