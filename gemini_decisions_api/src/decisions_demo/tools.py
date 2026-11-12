"""Tool selection: the Decisions API selects the next tool for an agent.

The six tools return fixed synthetic data. They do not call real systems.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from decisions_demo.client import ChoiceAnswer, DecisionResult, NoulAnswer
from decisions_demo.questions import Question, choice, noul

NONE_OPTION = "none"

TOOLS: dict[str, str] = {
    "lookup_tracking": "Look up the status of one or more tracking numbers.",
    "book_redelivery": "Book a new delivery date or a parcel locker after a missed delivery.",
    "calculate_volumetric_weight": "Calculate the billed weight from the parcel size.",
    "verify_link": "Check if a link or a message sender belongs to the company.",
    "explain_import_tax": "Explain import tax and customs charges for a parcel.",
    "start_damage_claim": "Start a claim for a damaged parcel.",
}

SAMPLE_TOOL_EMAIL = (
    "I got an SMS that says I must pay a 1.99 fee at parcel-fee-pay.example to release my "
    "parcel. Is this message from you?"
)


def tool_questions() -> dict[str, Question]:
    """Return the tool selection questions."""
    options = {**TOOLS, NONE_OPTION: "No tool helps. The email is not about a parcel."}
    return {
        "tool": choice("Which tool must the agent call first for this email?", options),
        "in_scope": noul("The email is about a parcel, a delivery, or a parcel charge."),
    }


def select_tool(result: DecisionResult) -> str | None:
    """Return the tool to call, or None if no tool applies."""
    tool = result.answers["tool"]
    in_scope = result.answers["in_scope"]
    assert isinstance(tool, ChoiceAnswer) and isinstance(in_scope, NoulAnswer)
    if not in_scope.value or tool.choice == NONE_OPTION:
        return None
    return tool.choice


def _lookup_tracking(ref: str) -> dict[str, Any]:
    return {"status": "in_transit", "last_scan": "Sorting centre", "reference": ref}


def _book_redelivery(ref: str) -> dict[str, Any]:
    return {"booked": True, "slot": "next working day, 9:00 to 13:00", "reference": ref}


def _calculate_volumetric_weight(ref: str) -> dict[str, Any]:
    return {"length_cm": 40, "width_cm": 30, "height_cm": 20, "volumetric_kg": 4.8}


def _verify_link(ref: str) -> dict[str, Any]:
    return {"official": False, "advice": "Do not pay. The company does not send fee links by SMS."}


def _explain_import_tax(ref: str) -> dict[str, Any]:
    return {"tax_due": 0.0, "note": "No tax is due on this synthetic parcel.", "reference": ref}


def _start_damage_claim(ref: str) -> dict[str, Any]:
    return {"claim_id": "CLM-0001", "needs": ["photos of the parcel", "proof of value"]}


_TOOL_FUNCTIONS: dict[str, Callable[[str], dict[str, Any]]] = {
    "lookup_tracking": _lookup_tracking,
    "book_redelivery": _book_redelivery,
    "calculate_volumetric_weight": _calculate_volumetric_weight,
    "verify_link": _verify_link,
    "explain_import_tax": _explain_import_tax,
    "start_damage_claim": _start_damage_claim,
}


def run_tool(name: str, reference: str) -> dict[str, Any]:
    """Run one fake tool. Raises KeyError for an unknown tool."""
    output = _TOOL_FUNCTIONS[name](reference)
    return {"tool": name, "synthetic": True, **output}
