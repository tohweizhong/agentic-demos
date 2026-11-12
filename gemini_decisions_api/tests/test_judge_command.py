"""Tests for the judge command and its sample data."""

import csv
import json
from pathlib import Path

from decisions_demo.__main__ import main
from decisions_demo.client import DecisionResult, NoulAnswer, ScoreAnswer
from decisions_demo.fake import FakeDecisionsClient
from decisions_demo.judge import load_answers, load_rubric

DATA = Path(__file__).parent.parent / "data"

RUBRIC = {
    "checks": [
        {
            "key": "answers_the_query",
            "type": "noul",
            "instructions": "Answers it.",
            "pass_when": True,
        },
        {
            "key": "tone",
            "type": "score",
            "instructions": "Tone.",
            "levels": ["Rude.", "Neutral.", "Polite."],
            "min_level": 1,
        },
    ]
}


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def responder(bad_answers):
    """Fail the tone check for answers in bad_answers. Pass all checks for the rest."""

    def respond(text, questions):
        is_bad = any(answer in text for answer in bad_answers)
        level = 0 if is_bad else 2
        probs = {0: 0.05, 1: 0.05, 2: 0.05}
        probs[level] = 0.9
        return DecisionResult(
            answers={
                "answers_the_query": NoulAnswer(0.95, 0.95),
                "tone": ScoreAnswer(float(level), 0.9, probs, {}),
            },
            input_tokens=120,
            output_tokens=0,
            latency_ms=8.0,
        )

    return respond


def test_judge_command_prints_agreement_and_writes_csv(tmp_path, capsys):
    answers = write(
        tmp_path,
        "a.csv",
        "query,answer,label,check:tone\n"
        "q1,Kind reply,good,yes\n"
        "q2,Rude reply,bad,no\n"
        "q3,Another kind reply,bad,yes\n",
    )
    rubric = write(tmp_path, "r.json", json.dumps(RUBRIC))
    output = tmp_path / "out.csv"
    client = FakeDecisionsClient(responder({"Rude reply"}))

    code = main(
        [
            "judge",
            "--answers",
            str(answers),
            "--rubric",
            str(rubric),
            "--output",
            str(output),
        ],
        client=client,
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "Accuracy: 66.7% (2/3)" in out
    assert "Cohen's kappa:" in out
    assert "Review rows: 0" in out
    assert "tone: 100.0% (3/3)" in out
    assert "Input tokens: 360" in out
    with output.open() as f:
        rows = list(csv.DictReader(f))
    assert rows[1]["verdict"] == "bad"
    assert rows[1]["failed_checks"] == "tone"
    assert set(rows[0]) >= {"query", "label", "verdict", "review", "p:answers_the_query", "p:tone"}
    assert rows[0]["c:tone"] == "0.9500"  # Pass probability: levels 1 and 2.


def test_judge_sends_query_and_answer_in_one_request(tmp_path, capsys):
    answers = write(tmp_path, "a.csv", "query,answer,label\nWhere is it?,In transit.,good\n")
    rubric = write(tmp_path, "r.json", json.dumps(RUBRIC))
    client = FakeDecisionsClient(responder(set()))

    main(
        [
            "judge",
            "--answers",
            str(answers),
            "--rubric",
            str(rubric),
            "--output",
            str(tmp_path / "o.csv"),
        ],
        client=client,
    )

    sent_input, sent_questions = client.calls[0]
    assert "Where is it?" in sent_input and "In transit." in sent_input
    assert set(sent_questions) == {"answers_the_query", "tone"}


def test_judge_with_bad_rubric_returns_2(tmp_path, capsys):
    answers = write(tmp_path, "a.csv", "query,answer,label\nq,a,good\n")
    rubric = write(tmp_path, "r.json", json.dumps({"checks": []}))

    code = main(
        ["judge", "--answers", str(answers), "--rubric", str(rubric)], client=FakeDecisionsClient()
    )

    assert code == 2
    assert "no checks" in capsys.readouterr().err


def test_sample_data_has_10_good_and_10_bad_rows():
    checks = load_rubric(DATA / "judge_rubric.json")
    rows = load_answers(DATA / "judge_answers.csv", {c.key for c in checks})

    assert len(rows) == 20
    assert sum(r.label == "good" for r in rows) == 10
    assert sum(r.label == "bad" for r in rows) == 10


def test_sample_bad_rows_fail_exactly_one_check_and_good_rows_pass_all():
    checks = load_rubric(DATA / "judge_rubric.json")
    keys = {c.key for c in checks}
    rows = load_answers(DATA / "judge_answers.csv", keys)

    for row in rows:
        assert set(row.check_labels) == keys
        failed = [k for k, passed in row.check_labels.items() if not passed]
        assert len(failed) == (0 if row.label == "good" else 1), row.answer
