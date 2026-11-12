"""The email triage scenario: a fictional parcel-delivery company.

All emails, categories, and rules are synthetic. They show how application code can
branch on Decisions API answers.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field

from decisions_demo.client import ChoiceAnswer, DecisionResult, NoulAnswer, ScoreAnswer
from decisions_demo.questions import Question, choice, noul, score

CATEGORIES: dict[str, str] = {
    "tracking": "Where is my parcel. One or more tracking numbers.",
    "redelivery": "Missed delivery. Book a new delivery or a locker.",
    "weight_dispute": "The customer disputes the billed parcel weight.",
    "scam_check": "The customer asks if a message or a link is real.",
    "import_tax": "A question about import tax or customs charges.",
    "damage_claim": "The parcel arrived damaged. The customer wants money.",
}

COMPLEXITY_LEVELS = [
    "Low: one simple fact answers it.",
    "Medium: needs a lookup and a short explanation.",
    "High: needs a policy decision or a human.",
]

TIER_BY_LEVEL = {0: "lite", 1: "flash", 2: "pro"}

# Categories where a request for money needs a person to approve the reply.
MONEY_CATEGORIES = {"damage_claim", "import_tax", "weight_dispute"}

# Below this confidence, the category is not certain enough for an automatic reply.
MIN_CATEGORY_CONFIDENCE = 0.6

SAMPLE_EMAIL = (
    "Hello, my parcel AB123456789XX was due on Monday. The tracking page has shown "
    "'in transit' for five days. Where is it? I need it before Friday."
)


class NextStep(enum.Enum):
    """What the support system does with the email."""

    AUTO_REPLY = "AUTO_REPLY"
    HUMAN_DRAFT = "HUMAN_DRAFT"


@dataclass(frozen=True)
class TriageDecision:
    """The result of the triage rules."""

    category: str
    tier: str
    next_step: NextStep
    reasons: list[str] = field(default_factory=list)


def triage_questions() -> dict[str, Question]:
    """Return all triage questions. One request asks all of them."""
    return {
        "category": choice("Which enquiry category does this email belong to?", CATEGORIES),
        "complexity": score("Rate how complex this email is to answer.", COMPLEXITY_LEVELS),
        "has_tracking_number": noul(
            "The email contains a parcel tracking number.",
            true_description="A tracking number is present in the email.",
            false_description="No tracking number is present in the email.",
        ),
        "has_link": noul("The email contains a web link or a URL."),
        "asks_for_money": noul(
            "The customer asks for a refund, compensation, or a waiver of a charge."
        ),
        "customer_is_angry": noul("The customer is angry or threatens to complain."),
    }


def decide_triage(result: DecisionResult) -> TriageDecision:
    """Apply the triage rules to the answers. This is plain code, not a model call."""
    category = result.answers["category"]
    complexity = result.answers["complexity"]
    money = result.answers["asks_for_money"]
    angry = result.answers["customer_is_angry"]
    assert isinstance(category, ChoiceAnswer)
    assert isinstance(complexity, ScoreAnswer)
    assert isinstance(money, NoulAnswer) and isinstance(angry, NoulAnswer)

    level = complexity.most_likely_level
    tier = TIER_BY_LEVEL.get(level, "pro")
    reasons: list[str] = []

    if category.confidence < MIN_CATEGORY_CONFIDENCE:
        reasons.append(f"Category confidence {category.confidence:.2f} is below 0.60.")
    if category.choice in MONEY_CATEGORIES and money.value:
        reasons.append(f"The customer asks for money in a {category.choice} email.")
    if angry.value:
        reasons.append("The customer is angry.")
    if level >= 2:
        reasons.append("The complexity is high.")

    if reasons:
        return TriageDecision(category.choice, tier, NextStep.HUMAN_DRAFT, reasons)
    return TriageDecision(
        category.choice,
        tier,
        NextStep.AUTO_REPLY,
        ["No rule needs a person. The model tier writes the reply."],
    )
