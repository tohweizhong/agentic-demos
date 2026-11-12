"""Judge: grade text answers with a rubric of Decisions API checks.

One request holds all checks for one answer. The query and the answer are the shared
input. An answer is "good" when every check passes.

Rubric file (JSON):
    {"checks": [
        {"key": "answers_the_query", "type": "noul", "instructions": "...", "pass_when": true},
        {"key": "tone", "type": "score", "instructions": "...",
         "levels": ["Rude.", "Neutral.", "Polite."], "min_level": 1}
    ]}

Answers file (CSV): columns ``query``, ``answer``, ``label`` (good or bad). Optional
columns ``check:<key>`` hold a human label (yes or no) that says if that check passes.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from decisions_demo.client import DecisionResult, NoulAnswer, ScoreAnswer
from decisions_demo.evaluate import DatasetError
from decisions_demo.questions import Question, noul, score

LABELS = ("good", "bad")
_YES_NO = {"yes": True, "no": False}
CHECK_PREFIX = "check:"


class RubricError(ValueError):
    """The rubric file is not valid. The message states the problem."""


@dataclass(frozen=True)
class Check:
    """One rubric check and its pass rule."""

    key: str
    type: str
    instructions: str
    pass_when: bool | None = None
    levels: tuple[str, ...] = ()
    min_level: int | None = None


@dataclass(frozen=True)
class JudgeRow:
    """One answer to grade, with its human labels."""

    query: str
    answer: str
    label: str
    check_labels: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Verdict:
    """The judge result for one answer."""

    verdict: str
    failed: list[str]
    review: bool
    check_passed: dict[str, bool]
    probabilities: dict[str, float]
    confidences: dict[str, float] = field(default_factory=dict)
    review_checks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Agreement:
    """Agreement between human labels and judge verdicts."""

    total: int
    accuracy: float
    kappa: float | None
    confusion: dict[str, dict[str, int]]


def _parse_check(index: int, data: dict) -> Check:
    key = data.get("key")
    kind = data.get("type")
    instructions = data.get("instructions")
    if not key or not instructions:
        raise RubricError(f"Check {index + 1} needs a key and instructions.")
    if kind == "noul":
        if not isinstance(data.get("pass_when"), bool):
            raise RubricError(f"Check {key!r} needs pass_when: true or false.")
        return Check(key, kind, instructions, pass_when=data["pass_when"])
    if kind == "score":
        levels = tuple(data.get("levels") or ())
        min_level = data.get("min_level")
        if len(levels) < 2:
            raise RubricError(f"Check {key!r} needs 2 or more levels.")
        if not isinstance(min_level, int) or not 0 <= min_level < len(levels):
            raise RubricError(f"Check {key!r}: min_level must be from 0 to {len(levels) - 1}.")
        return Check(key, kind, instructions, levels=levels, min_level=min_level)
    raise RubricError(f"Check {key!r} has type {kind!r}. Use noul or score.")


def load_rubric(path: Path) -> list[Check]:
    """Load and check the rubric file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RubricError(f"Cannot read the rubric file {path}: {error}.") from error
    raw_checks = data.get("checks") if isinstance(data, dict) else None
    if not raw_checks:
        raise RubricError(f"The rubric file {path} has no checks.")
    return [_parse_check(i, c) for i, c in enumerate(raw_checks)]


def rubric_questions(checks: Sequence[Check]) -> dict[str, Question]:
    """Return one Decisions API question for each check."""
    questions: dict[str, Question] = {}
    for check in checks:
        if check.type == "noul":
            questions[check.key] = noul(check.instructions)
        else:
            questions[check.key] = score(check.instructions, list(check.levels))
    return questions


def judge_input(query: str, answer: str) -> str:
    """Return the shared input text: the customer query, then the answer to grade."""
    return f"Customer query:\n{query}\n\nAnswer to grade:\n{answer}"


def load_answers(path: Path, check_keys: set[str]) -> list[JudgeRow]:
    """Load the answers CSV and check every label."""
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = list(reader.fieldnames or [])
            missing = {"query", "answer", "label"} - set(columns)
            if missing:
                raise DatasetError(
                    f"The answers file {path} has no column {', '.join(sorted(missing))}. "
                    "It needs the columns query, answer, and label."
                )
            check_columns = [c for c in columns if c.startswith(CHECK_PREFIX)]
            for column in check_columns:
                if column[len(CHECK_PREFIX) :] not in check_keys:
                    raise DatasetError(
                        f"Column {column!r} names no rubric check. "
                        f"Use one of: {', '.join(sorted(check_keys))}."
                    )
            rows = []
            for line, record in enumerate(reader, start=2):
                label = (record["label"] or "").strip().lower()
                if label not in LABELS:
                    raise DatasetError(
                        f"The answers file {path} has a bad label at row {line}: {label!r}. "
                        "Use good or bad."
                    )
                check_labels = {}
                for column in check_columns:
                    value = (record[column] or "").strip().lower()
                    if value == "":
                        continue
                    if value not in _YES_NO:
                        raise DatasetError(
                            f"Row {line}, column {column!r}: {value!r} is not yes or no."
                        )
                    check_labels[column[len(CHECK_PREFIX) :]] = _YES_NO[value]
                rows.append(JudgeRow(record["query"], record["answer"], label, check_labels))
    except OSError as error:
        raise DatasetError(f"Cannot read the answers file {path}: {error}.") from error
    if not rows:
        raise DatasetError(f"The answers file {path} has no rows.")
    return rows


def _decision_confidence(check: Check, answer: NoulAnswer | ScoreAnswer) -> float:
    """Return the probability of the pass or fail decision for one check.

    For a score check, the levels at or above min_level all pass. Their probabilities are
    added, so a split between two passing levels does not lower the confidence.
    """
    if isinstance(answer, NoulAnswer):
        return answer.confidence
    assert check.min_level is not None
    p_pass = sum(p for level, p in answer.probabilities.items() if level >= check.min_level)
    return max(p_pass, 1 - p_pass)


def decide_verdict(
    checks: Sequence[Check], result: DecisionResult, min_confidence: float
) -> Verdict:
    """Apply the pass rules to the answers and return the verdict."""
    check_passed: dict[str, bool] = {}
    probabilities: dict[str, float] = {}
    confidences: dict[str, float] = {}
    for check in checks:
        answer = result.answers[check.key]
        if check.type == "noul":
            assert isinstance(answer, NoulAnswer)
            check_passed[check.key] = answer.value == check.pass_when
            probabilities[check.key] = answer.probability
        else:
            assert isinstance(answer, ScoreAnswer)
            assert check.min_level is not None
            check_passed[check.key] = answer.most_likely_level >= check.min_level
            probabilities[check.key] = answer.score
        confidences[check.key] = _decision_confidence(check, answer)
    failed = [key for key, passed in check_passed.items() if not passed]
    review_checks = [key for key, conf in confidences.items() if conf < min_confidence]
    return Verdict(
        verdict="bad" if failed else "good",
        failed=failed,
        review=bool(review_checks),
        check_passed=check_passed,
        probabilities=probabilities,
        confidences=confidences,
        review_checks=review_checks,
    )


def cohen_kappa(first: Sequence[str], second: Sequence[str]) -> float | None:
    """Return Cohen's kappa for two label lists, or None when kappa is not defined."""
    total = len(first)
    if total == 0 or total != len(second):
        return None
    labels = sorted(set(first) | set(second))
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / total
    expected = sum((first.count(lab) / total) * (second.count(lab) / total) for lab in labels)
    if expected == 1.0:
        return None
    return (observed - expected) / (1 - expected)


def agreement(human: Sequence[str], judge: Sequence[str]) -> Agreement:
    """Return accuracy, kappa, and the confusion matrix (rows: human, columns: judge)."""
    confusion = {h: {j: 0 for j in LABELS} for h in LABELS}
    for h, j in zip(human, judge, strict=True):
        confusion[h][j] += 1
    correct = sum(h == j for h, j in zip(human, judge, strict=True))
    return Agreement(
        total=len(human),
        accuracy=correct / len(human) if human else 0.0,
        kappa=cohen_kappa(human, judge),
        confusion=confusion,
    )
