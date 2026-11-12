"""Evaluation: measure the accuracy of one choice question on a labeled CSV file.

Dataset format: a CSV file with the columns ``query`` and ``label``. Every label must be
one of the option keys in the question file.

Question file format (JSON):
    {"instructions": "...", "options": {"<key>": "<description>", ...}}
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from decisions_demo.questions import Question, choice

QUESTION_KEY = "label"


class DatasetError(ValueError):
    """The dataset or the question file is not valid. The message states the problem."""


@dataclass(frozen=True)
class EvalRow:
    """One labeled query."""

    query: str
    label: str


@dataclass(frozen=True)
class RowResult:
    """The result for one row."""

    query: str
    label: str
    predicted: str
    confidence: float
    probabilities: dict[str, float]

    @property
    def correct(self) -> bool:
        """True when the selected option equals the label."""
        return self.predicted == self.label


@dataclass(frozen=True)
class Metrics:
    """Summary metrics for one evaluation run."""

    total: int
    accuracy: float
    confusion: dict[str, dict[str, int]]
    mean_confidence_correct: float | None
    mean_confidence_incorrect: float | None


def load_question(path: Path) -> Question:
    """Load the question file and return a choice question."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return choice(data["instructions"], data["options"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise DatasetError(
            f"Cannot read the question file {path}: {error}. "
            'It must be JSON with "instructions" and "options".'
        ) from error


def load_dataset(path: Path, allowed_labels: set[str]) -> list[EvalRow]:
    """Load the CSV file and check that every label is an option key."""
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])
            missing = {"query", "label"} - columns
            if missing:
                raise DatasetError(
                    f"The dataset {path} has no column {', '.join(sorted(missing))}. "
                    "It needs the columns query and label."
                )
            rows = []
            for line_number, record in enumerate(reader, start=2):
                label = (record["label"] or "").strip()
                if label not in allowed_labels:
                    raise DatasetError(
                        f"The dataset {path} has an unknown label at row {line_number}: {label!r}. "
                        f"Use one of: {', '.join(sorted(allowed_labels))}."
                    )
                rows.append(EvalRow(query=record["query"], label=label))
    except OSError as error:
        raise DatasetError(f"Cannot read the dataset {path}: {error}.") from error
    if not rows:
        raise DatasetError(f"The dataset {path} has no rows.")
    return rows


def compute_metrics(results: Iterable[RowResult], labels: list[str]) -> Metrics:
    """Compute accuracy, the confusion matrix, and the mean confidence values."""
    results = list(results)
    confusion = {label: {other: 0 for other in labels} for label in labels}
    for result in results:
        confusion[result.label][result.predicted] = (
            confusion[result.label].get(result.predicted, 0) + 1
        )
    correct = [r.confidence for r in results if r.correct]
    incorrect = [r.confidence for r in results if not r.correct]
    return Metrics(
        total=len(results),
        accuracy=len(correct) / len(results) if results else 0.0,
        confusion=confusion,
        mean_confidence_correct=sum(correct) / len(correct) if correct else None,
        mean_confidence_incorrect=sum(incorrect) / len(incorrect) if incorrect else None,
    )


def write_results(path: Path, results: Iterable[RowResult]) -> None:
    """Write one CSV row for each result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "label", "predicted", "correct", "confidence", "probabilities"])
        for r in results:
            probs = json.dumps({k: round(v, 4) for k, v in r.probabilities.items()})
            writer.writerow(
                [r.query, r.label, r.predicted, r.correct, f"{r.confidence:.4f}", probs]
            )
