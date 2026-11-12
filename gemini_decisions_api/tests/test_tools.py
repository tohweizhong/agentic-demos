"""Tests for tool selection and the fake tools."""

import pytest

from decisions_demo.client import ChoiceAnswer, DecisionResult, NoulAnswer
from decisions_demo.tools import NONE_OPTION, TOOLS, run_tool, select_tool, tool_questions


def result(tool, in_scope=0.9):
    probabilities = {k: 0.01 for k in [*TOOLS, NONE_OPTION]}
    probabilities[tool] = 0.9
    return DecisionResult(
        answers={
            "tool": ChoiceAnswer(tool, 0.9, probabilities),
            "in_scope": NoulAnswer(in_scope, max(in_scope, 1 - in_scope)),
        },
        input_tokens=10,
        output_tokens=0,
        latency_ms=1.0,
    )


def test_one_tool_for_each_category():
    assert len(TOOLS) == 6


def test_tool_question_includes_none_option():
    questions = tool_questions()

    assert set(questions["tool"]["criteria"]) == {*TOOLS, NONE_OPTION}
    assert questions["in_scope"]["type"] == "noul"


def test_select_tool_returns_the_chosen_tool():
    assert select_tool(result("lookup_tracking")) == "lookup_tracking"


def test_select_tool_returns_none_for_none_option():
    assert select_tool(result(NONE_OPTION)) is None


def test_select_tool_returns_none_when_out_of_scope():
    assert select_tool(result("lookup_tracking", in_scope=0.2)) is None


@pytest.mark.parametrize("tool", list(TOOLS))
def test_every_fake_tool_returns_synthetic_data(tool):
    output = run_tool(tool, "AB123456789XX")

    assert output["tool"] == tool
    assert output["synthetic"] is True


def test_run_tool_rejects_unknown_tool():
    with pytest.raises(KeyError):
        run_tool("delete_everything", "x")
