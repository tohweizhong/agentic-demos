"""Tests for the evaluation loader, the metrics, and the eval command."""

import csv
import json
from pathlib import Path

import pytest

from decisions_demo.__main__ import main
from decisions_demo.client import ChoiceAnswer, DecisionResult
from decisions_demo.evaluate import (
    DatasetError,
    EvalRow,
    RowResult,
    compute_metrics,
    load_dataset,
    load_question,
)
from decisions_demo.fake import FakeDecisionsClient

DATA = Path(__file__).parent.parent / "data"


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


QUESTION = {
    "instructions": "Which queue?",
    "options": {"billing": "Money questions.", "tracking": "Where is my parcel."},
}


def test_load_question(tmp_path):
    path = write(tmp_path, "q.json", json.dumps(QUESTION))

    question = load_question(path)

    assert question["type"] == "choice"
    assert set(question["criteria"]) == {"billing", "tracking"}


def test_load_dataset(tmp_path):
    path = write(tmp_path, "d.csv", 'query,label\n"Double charge",billing\nWhere is it,tracking\n')

    rows = load_dataset(path, allowed_labels={"billing", "tracking"})

    assert rows == [EvalRow("Double charge", "billing"), EvalRow("Where is it", "tracking")]


def test_empty_dataset_is_an_error(tmp_path):
    path = write(tmp_path, "d.csv", "query,label\n")

    with pytest.raises(DatasetError, match="no rows"):
        load_dataset(path, allowed_labels={"billing"})


def test_missing_column_is_an_error(tmp_path):
    path = write(tmp_path, "d.csv", "text,label\nx,billing\n")

    with pytest.raises(DatasetError, match="query"):
        load_dataset(path, allowed_labels={"billing"})


def test_unknown_label_is_an_error_with_row_number(tmp_path):
    path = write(tmp_path, "d.csv", "query,label\nx,billing\ny,refunds\n")

    with pytest.raises(DatasetError, match=r"row 3.*refunds"):
        load_dataset(path, allowed_labels={"billing", "tracking"})


def test_metrics():
    results = [
        RowResult("a", "billing", "billing", 0.9, {}),
        RowResult("b", "billing", "tracking", 0.6, {}),
        RowResult("c", "tracking", "tracking", 0.8, {}),
        RowResult("d", "tracking", "tracking", 0.7, {}),
    ]

    metrics = compute_metrics(results, labels=["billing", "tracking"])

    assert metrics.accuracy == pytest.approx(0.75)
    assert metrics.confusion["billing"]["tracking"] == 1
    assert metrics.confusion["tracking"]["tracking"] == 2
    assert metrics.mean_confidence_correct == pytest.approx(0.8)
    assert metrics.mean_confidence_incorrect == pytest.approx(0.6)
    assert metrics.total == 4


def test_metrics_with_no_incorrect_rows():
    metrics = compute_metrics([RowResult("a", "x", "x", 0.9, {})], labels=["x"])

    assert metrics.mean_confidence_incorrect is None


def test_sample_data_has_24_rows_and_4_for_each_label():
    question = load_question(DATA / "triage_question.json")
    rows = load_dataset(DATA / "sample_emails.csv", allowed_labels=set(question["criteria"]))

    assert len(rows) == 24
    for label in question["criteria"]:
        assert sum(1 for row in rows if row.label == label) == 4


def responder_from_label_map(label_by_query):
    def respond(email, questions):
        options = list(questions["label"]["criteria"])
        chosen = label_by_query[email]
        probs = {o: (0.9 if o == chosen else 0.1 / (len(options) - 1)) for o in options}
        return DecisionResult(
            answers={"label": ChoiceAnswer(chosen, 0.9, probs)},
            input_tokens=100,
            output_tokens=0,
            latency_ms=10.0,
        )

    return respond


def test_eval_command_writes_results_csv_and_prints_summary(tmp_path, capsys):
    dataset = write(tmp_path, "d.csv", "query,label\nq1,billing\nq2,tracking\n")
    question = write(tmp_path, "q.json", json.dumps(QUESTION))
    output = tmp_path / "out" / "results.csv"
    client = FakeDecisionsClient(responder_from_label_map({"q1": "billing", "q2": "billing"}))

    code = main(
        ["eval", "--dataset", str(dataset), "--question", str(question), "--output", str(output)],
        client=client,
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "Accuracy: 50.0%" in out
    assert "Confusion matrix" in out
    assert "Input tokens: 200" in out
    with output.open() as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == [
        "query",
        "label",
        "predicted",
        "correct",
        "confidence",
        "probabilities",
    ]
    assert rows[1]["correct"] == "False"


def test_eval_command_with_bad_label_returns_2(tmp_path, capsys):
    dataset = write(tmp_path, "d.csv", "query,label\nq1,refunds\n")
    question = write(tmp_path, "q.json", json.dumps(QUESTION))

    code = main(
        ["eval", "--dataset", str(dataset), "--question", str(question)],
        client=FakeDecisionsClient(),
    )

    assert code == 2
    assert "refunds" in capsys.readouterr().err
