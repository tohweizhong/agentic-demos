"""Tests for the judge: rubric, answers, verdict, and agreement metrics."""

import json

import pytest

from decisions_demo.client import DecisionResult, NoulAnswer, ScoreAnswer
from decisions_demo.evaluate import DatasetError
from decisions_demo.judge import (
    Check,
    RubricError,
    agreement,
    cohen_kappa,
    decide_verdict,
    judge_input,
    load_answers,
    load_rubric,
    rubric_questions,
)

RUBRIC = {
    "checks": [
        {
            "key": "answers_the_query",
            "type": "noul",
            "instructions": "The answer addresses the customer's question.",
            "pass_when": True,
        },
        {
            "key": "promises_money",
            "type": "noul",
            "instructions": "The answer promises a refund or compensation.",
            "pass_when": False,
        },
        {
            "key": "tone",
            "type": "score",
            "instructions": "Rate the tone of the answer.",
            "levels": ["Rude.", "Neutral.", "Polite."],
            "min_level": 1,
        },
    ]
}


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def checks(tmp_path):
    return load_rubric(write(tmp_path, "r.json", json.dumps(RUBRIC)))


# --- Rubric ---------------------------------------------------------------


def test_load_rubric(tmp_path):
    loaded = checks(tmp_path)

    assert [c.key for c in loaded] == ["answers_the_query", "promises_money", "tone"]
    assert loaded[1].pass_when is False
    assert loaded[2].min_level == 1


def test_rubric_questions_use_the_decisions_types(tmp_path):
    questions = rubric_questions(checks(tmp_path))

    assert questions["answers_the_query"] == {
        "type": "noul",
        "instructions": "The answer addresses the customer's question.",
    }
    assert questions["tone"]["criteria"] == ["Rude.", "Neutral.", "Polite."]


def test_noul_check_needs_pass_when(tmp_path):
    bad = {"checks": [{"key": "a", "type": "noul", "instructions": "x"}]}

    with pytest.raises(RubricError, match="pass_when"):
        load_rubric(write(tmp_path, "r.json", json.dumps(bad)))


def test_unknown_check_type(tmp_path):
    bad = {"checks": [{"key": "a", "type": "choice", "instructions": "x"}]}

    with pytest.raises(RubricError, match="type"):
        load_rubric(write(tmp_path, "r.json", json.dumps(bad)))


def test_min_level_must_be_a_level(tmp_path):
    bad = {
        "checks": [
            {"key": "a", "type": "score", "instructions": "x", "levels": ["L", "H"], "min_level": 2}
        ]
    }

    with pytest.raises(RubricError, match="min_level"):
        load_rubric(write(tmp_path, "r.json", json.dumps(bad)))


def test_empty_rubric(tmp_path):
    with pytest.raises(RubricError, match="no checks"):
        load_rubric(write(tmp_path, "r.json", json.dumps({"checks": []})))


def test_judge_input_holds_query_and_answer():
    text = judge_input("Where is it?", "It is in transit.")

    assert "Where is it?" in text and "It is in transit." in text
    assert text.index("Where is it?") < text.index("It is in transit.")


# --- Answers --------------------------------------------------------------


def test_load_answers_with_check_columns(tmp_path):
    path = write(
        tmp_path,
        "a.csv",
        "query,answer,label,check:tone\nq1,a1,good,yes\nq2,a2,bad,no\n",
    )

    rows = load_answers(path, check_keys={"answers_the_query", "promises_money", "tone"})

    assert rows[0].label == "good"
    assert rows[0].check_labels == {"tone": True}
    assert rows[1].check_labels == {"tone": False}


def test_load_answers_without_check_columns(tmp_path):
    rows = load_answers(write(tmp_path, "a.csv", "query,answer,label\nq,a,bad\n"), {"x"})

    assert rows[0].check_labels == {}


def test_bad_label_gives_row_number(tmp_path):
    path = write(tmp_path, "a.csv", "query,answer,label\nq,a,good\nq,a,maybe\n")

    with pytest.raises(DatasetError, match=r"row 3.*maybe"):
        load_answers(path, {"x"})


def test_unknown_check_column(tmp_path):
    path = write(tmp_path, "a.csv", "query,answer,label,check:nope\nq,a,good,yes\n")

    with pytest.raises(DatasetError, match="nope"):
        load_answers(path, {"tone"})


def test_missing_answer_column(tmp_path):
    with pytest.raises(DatasetError, match="answer"):
        load_answers(write(tmp_path, "a.csv", "query,label\nq,good\n"), {"x"})


def test_empty_answers_file(tmp_path):
    with pytest.raises(DatasetError, match="no rows"):
        load_answers(write(tmp_path, "a.csv", "query,answer,label\n"), {"x"})


# --- Verdict --------------------------------------------------------------


def result(addresses=0.95, money=0.05, tone_level=2, tone_conf=0.9):
    tone_probs = {0: 0.05, 1: 0.05, 2: 0.05}
    tone_probs[tone_level] = tone_conf
    return DecisionResult(
        answers={
            "answers_the_query": NoulAnswer(addresses, max(addresses, 1 - addresses)),
            "promises_money": NoulAnswer(money, max(money, 1 - money)),
            "tone": ScoreAnswer(float(tone_level), tone_conf, tone_probs, {}),
        },
        input_tokens=100,
        output_tokens=0,
        latency_ms=10.0,
    )


def test_all_checks_pass_gives_good(tmp_path):
    verdict = decide_verdict(checks(tmp_path), result(), min_confidence=0.7)

    assert verdict.verdict == "good"
    assert verdict.failed == []
    assert verdict.review is False
    assert verdict.check_passed == {"answers_the_query": True, "promises_money": True, "tone": True}


def test_noul_with_pass_when_false_fails_when_true(tmp_path):
    verdict = decide_verdict(checks(tmp_path), result(money=0.9), min_confidence=0.7)

    assert verdict.verdict == "bad"
    assert verdict.failed == ["promises_money"]


def test_score_below_min_level_fails(tmp_path):
    verdict = decide_verdict(checks(tmp_path), result(tone_level=0), min_confidence=0.7)

    assert verdict.failed == ["tone"]


def test_low_confidence_marks_review(tmp_path):
    verdict = decide_verdict(checks(tmp_path), result(addresses=0.6), min_confidence=0.7)

    assert verdict.review is True
    assert verdict.verdict == "good"
    assert verdict.review_checks == ["answers_the_query"]
    assert verdict.confidences["answers_the_query"] == pytest.approx(0.6)


# --- Agreement ------------------------------------------------------------


def test_cohen_kappa_perfect_agreement():
    assert cohen_kappa(["good", "bad", "good"], ["good", "bad", "good"]) == pytest.approx(1.0)


def test_cohen_kappa_known_value():
    # Observed agreement 0.7. Expected agreement 0.5. Kappa = (0.7 - 0.5) / (1 - 0.5) = 0.4.
    human = ["good"] * 5 + ["bad"] * 5
    judge = ["good"] * 4 + ["bad"] + ["bad"] * 3 + ["good"] * 2

    assert cohen_kappa(human, judge) == pytest.approx(0.4)


def test_cohen_kappa_single_class_is_none():
    assert cohen_kappa(["good", "good"], ["good", "good"]) is None


def test_agreement_metrics():
    human = ["good", "good", "bad", "bad"]
    judge = ["good", "bad", "bad", "bad"]

    metrics = agreement(human, judge)

    assert metrics.accuracy == pytest.approx(0.75)
    assert metrics.confusion == {"good": {"good": 1, "bad": 1}, "bad": {"good": 0, "bad": 2}}
    assert metrics.kappa == pytest.approx(0.5)


def test_check_dataclass_is_frozen():
    check = Check("k", "noul", "x", pass_when=True)

    with pytest.raises(AttributeError):
        check.key = "other"  # type: ignore[misc]


def test_score_review_uses_the_probability_of_the_pass_decision(tmp_path):
    # Neutral 0.45 and Polite 0.50 both pass (min_level 1). Pass probability is 0.95.
    split = DecisionResult(
        answers={
            "answers_the_query": NoulAnswer(0.95, 0.95),
            "promises_money": NoulAnswer(0.05, 0.95),
            "tone": ScoreAnswer(1.45, 0.50, {0: 0.05, 1: 0.45, 2: 0.50}, {}),
        },
        input_tokens=1,
        output_tokens=0,
        latency_ms=1.0,
    )

    verdict = decide_verdict(checks(tmp_path), split, min_confidence=0.7)

    assert verdict.review is False
    assert verdict.confidences["tone"] == pytest.approx(0.95)
