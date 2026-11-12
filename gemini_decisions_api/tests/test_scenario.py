"""Tests for the triage scenario: questions and the decision rules."""

import pytest

from decisions_demo.client import ChoiceAnswer, DecisionResult, NoulAnswer, ScoreAnswer
from decisions_demo.scenario import (
    CATEGORIES,
    NextStep,
    decide_triage,
    triage_questions,
)


def result(category="tracking", category_conf=0.95, level=0, money=0.1, angry=0.1, link=0.1):
    probabilities = {k: 0.0 for k in CATEGORIES}
    probabilities[category] = category_conf
    score_probs = {0: 0.0, 1: 0.0, 2: 0.0}
    score_probs[level] = 0.9
    return DecisionResult(
        answers={
            "category": ChoiceAnswer(category, category_conf, probabilities),
            "complexity": ScoreAnswer(float(level), 0.9, score_probs, {}),
            "has_tracking_number": NoulAnswer(0.9, 0.9),
            "has_link": NoulAnswer(link, max(link, 1 - link)),
            "asks_for_money": NoulAnswer(money, max(money, 1 - money)),
            "customer_is_angry": NoulAnswer(angry, max(angry, 1 - angry)),
        },
        input_tokens=100,
        output_tokens=0,
        latency_ms=200.0,
    )


def test_six_categories():
    assert list(CATEGORIES) == [
        "tracking",
        "redelivery",
        "weight_dispute",
        "scam_check",
        "import_tax",
        "damage_claim",
    ]


def test_triage_questions_have_expected_keys_and_types():
    questions = triage_questions()

    assert {k: q["type"] for k, q in questions.items()} == {
        "category": "choice",
        "complexity": "score",
        "has_tracking_number": "noul",
        "has_link": "noul",
        "asks_for_money": "noul",
        "customer_is_angry": "noul",
    }
    assert set(questions["category"]["criteria"]) == set(CATEGORIES)
    assert len(questions["complexity"]["criteria"]) == 3


@pytest.mark.parametrize(("level", "tier"), [(0, "lite"), (1, "flash"), (2, "pro")])
def test_complexity_level_selects_tier(level, tier):
    assert decide_triage(result(level=level)).tier == tier


def test_simple_tracking_email_is_auto_reply():
    decision = decide_triage(result())

    assert decision.next_step is NextStep.AUTO_REPLY
    assert decision.category == "tracking"


def test_damage_claim_with_money_needs_human():
    decision = decide_triage(result(category="damage_claim", money=0.9))

    assert decision.next_step is NextStep.HUMAN_DRAFT
    assert any("money" in reason for reason in decision.reasons)


def test_angry_customer_needs_human():
    assert decide_triage(result(angry=0.8)).next_step is NextStep.HUMAN_DRAFT


def test_high_complexity_needs_human():
    assert decide_triage(result(level=2)).next_step is NextStep.HUMAN_DRAFT


def test_low_category_confidence_needs_human():
    decision = decide_triage(result(category_conf=0.4))

    assert decision.next_step is NextStep.HUMAN_DRAFT
    assert any("confidence" in reason for reason in decision.reasons)


def test_money_on_tracking_email_stays_auto_reply():
    assert decide_triage(result(category="tracking", money=0.9)).next_step is NextStep.AUTO_REPLY


def test_auto_reply_has_a_reason():
    assert decide_triage(result()).reasons
