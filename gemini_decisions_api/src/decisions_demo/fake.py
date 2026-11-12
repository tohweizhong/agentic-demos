"""A fake Decisions API client for unit tests and offline runs.

It returns answers with the same shape as the real API (see tests/fixtures). The values
are not model output. Use the fake only for tests.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from decisions_demo.client import (
    Answer,
    ChoiceAnswer,
    DecisionInput,
    DecisionResult,
    NoulAnswer,
    ScoreAnswer,
)
from decisions_demo.questions import Question

Responder = Callable[[DecisionInput, Mapping[str, Question]], DecisionResult]


def _default_answer(question: Mapping[str, Any]) -> Answer:
    """Return a fixed answer: the first option, the lowest level, and 'no'."""
    kind = question["type"]
    if kind == "noul":
        return NoulAnswer(probability=0.1, confidence=0.9)
    if kind == "choice":
        keys = list(question["criteria"])
        rest = 0.1 / max(len(keys) - 1, 1)
        probabilities = {key: (0.9 if i == 0 else rest) for i, key in enumerate(keys)}
        return ChoiceAnswer(choice=keys[0], confidence=0.9, probabilities=probabilities)
    levels = list(question["criteria"])
    probabilities = {i: (0.9 if i == 0 else 0.1 / (len(levels) - 1)) for i in range(len(levels))}
    return ScoreAnswer(
        score=sum(i * p for i, p in probabilities.items()),
        confidence=0.9,
        probabilities=probabilities,
        legend=dict(enumerate(levels)),
    )


def default_responder(input: DecisionInput, questions: Mapping[str, Question]) -> DecisionResult:
    """Answer every question with a fixed default answer."""
    answers = {key: _default_answer(question) for key, question in questions.items()}
    return DecisionResult(answers=answers, input_tokens=0, output_tokens=0, latency_ms=0.0)


class FakeDecisionsClient:
    """Records each call and returns the responder output."""

    def __init__(self, responder: Responder | None = None) -> None:
        self._responder = responder or default_responder
        self.calls: list[tuple[DecisionInput, Mapping[str, Question]]] = []

    def decide(self, input: DecisionInput, questions: Mapping[str, Question]) -> DecisionResult:
        """Record the call and return the responder output."""
        self.calls.append((input, questions))
        return self._responder(input, questions)
