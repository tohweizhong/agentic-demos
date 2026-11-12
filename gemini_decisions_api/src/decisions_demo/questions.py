"""Builders for Decisions API questions.

Each builder returns the JSON object that the API expects. The limits come from the
official Decisions API documentation (read on 12 Nov 2026).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

MAX_QUESTIONS = 1000
MIN_OPTIONS = 2
MAX_OPTIONS = 255
MAX_OPTION_KEY_LENGTH = 128
_QUESTION_KEY = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

Question = dict[str, Any]


class QuestionError(ValueError):
    """A question does not obey the API limits."""


def _check_instructions(instructions: str) -> str:
    if not instructions.strip():
        raise QuestionError("The question instructions must not be empty.")
    return instructions


def noul(
    instructions: str,
    *,
    true_description: str | None = None,
    false_description: str | None = None,
) -> Question:
    """Return a yes/no question. The API returns the probability that the statement is true."""
    question: Question = {"type": "noul", "instructions": _check_instructions(instructions)}
    criteria = {}
    if true_description:
        criteria["true_description"] = true_description
    if false_description:
        criteria["false_description"] = false_description
    if criteria:
        question["criteria"] = criteria
    return question


def choice(instructions: str, options: Mapping[str, str]) -> Question:
    """Return a choice question. ``options`` maps each option key to its description."""
    if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
        raise QuestionError(f"A choice question needs 2 to 255 options. It has {len(options)}.")
    for key in options:
        if not 1 <= len(key) <= MAX_OPTION_KEY_LENGTH:
            raise QuestionError(f"Option key {key[:20]!r} must have 1 to 128 characters.")
    return {
        "type": "choice",
        "instructions": _check_instructions(instructions),
        "criteria": dict(options),
    }


def score(instructions: str, levels: Sequence[str]) -> Question:
    """Return a score question. ``levels`` go from the lowest level to the highest level."""
    if not MIN_OPTIONS <= len(levels) <= MAX_OPTIONS:
        raise QuestionError(f"A score question needs 2 to 255 levels. It has {len(levels)}.")
    if any(not level.strip() for level in levels):
        raise QuestionError("A score level must not be empty.")
    return {
        "type": "score",
        "instructions": _check_instructions(instructions),
        "criteria": list(levels),
    }


def validate_questions(questions: Mapping[str, Question]) -> None:
    """Check the question count and the question keys before a request."""
    if not 1 <= len(questions) <= MAX_QUESTIONS:
        raise QuestionError(f"A request needs 1 to 1,000 questions. It has {len(questions)}.")
    for key in questions:
        if not _QUESTION_KEY.match(key):
            raise QuestionError(
                f"Question key {key!r} is not valid. "
                "Use 1 to 64 characters from A-Z, a-z, 0-9, _ and -."
            )
