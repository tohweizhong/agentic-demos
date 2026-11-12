"""Tests for the question builders."""

import pytest

from decisions_demo.questions import (
    MAX_QUESTIONS,
    QuestionError,
    choice,
    noul,
    score,
    validate_questions,
)


def test_noul_without_criteria():
    assert noul("The email has a link.") == {
        "type": "noul",
        "instructions": "The email has a link.",
    }


def test_noul_with_criteria():
    question = noul("Has a link.", true_description="A URL is present.", false_description="None.")

    assert question["criteria"] == {
        "true_description": "A URL is present.",
        "false_description": "None.",
    }


def test_noul_rejects_empty_instructions():
    with pytest.raises(QuestionError, match="instructions"):
        noul("  ")


def test_choice():
    question = choice("Which tool?", {"a": "Tool A.", "b": "Tool B."})

    assert question == {
        "type": "choice",
        "instructions": "Which tool?",
        "criteria": {"a": "Tool A.", "b": "Tool B."},
    }


def test_choice_needs_two_options():
    with pytest.raises(QuestionError, match="2 to 255 options"):
        choice("Which?", {"a": "Only one."})


def test_choice_rejects_too_many_options():
    with pytest.raises(QuestionError, match="2 to 255 options"):
        choice("Which?", {f"o{i}": "x" for i in range(256)})


def test_choice_rejects_long_option_key():
    with pytest.raises(QuestionError, match="Option key"):
        choice("Which?", {"a" * 129: "x", "b": "y"})


def test_score():
    question = score("How complex?", ["Low.", "High."])

    assert question == {
        "type": "score",
        "instructions": "How complex?",
        "criteria": ["Low.", "High."],
    }


def test_score_rejects_empty_level():
    with pytest.raises(QuestionError, match="empty"):
        score("How complex?", ["Low.", " "])


def test_score_needs_two_levels():
    with pytest.raises(QuestionError, match="2 to 255 levels"):
        score("How complex?", ["Only."])


def test_validate_accepts_good_keys():
    validate_questions({"has_link": noul("x"), "tool-1": noul("y")})


@pytest.mark.parametrize("key", ["", "has link", "a" * 65, "émail"])
def test_validate_rejects_bad_keys(key):
    with pytest.raises(QuestionError, match="Question key"):
        validate_questions({key: noul("x")})


def test_validate_rejects_empty_map():
    with pytest.raises(QuestionError, match="1 to 1,000"):
        validate_questions({})


def test_validate_rejects_too_many_questions():
    questions = {f"q{i}": noul("x") for i in range(MAX_QUESTIONS + 1)}

    with pytest.raises(QuestionError, match="1 to 1,000"):
        validate_questions(questions)
