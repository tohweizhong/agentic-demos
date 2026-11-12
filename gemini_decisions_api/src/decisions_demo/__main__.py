"""Command-line entry point: python -m decisions_demo <command>.

Commands:
    triage      Classify one email and select the model tier and the next step.
    tools       Select the next tool for an agent.
    multimodal  Ask several questions about one synthetic image.
    eval        Measure accuracy of one choice question on a labeled CSV file.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from rich.console import Console

from decisions_demo import render
from decisions_demo.client import DecisionInput, DecisionResult, DecisionsAPIError, image_block
from decisions_demo.config import ConfigError, load_config
from decisions_demo.evaluate import DatasetError
from decisions_demo.questions import Question
from decisions_demo.sample_image import make_delivery_slip, multimodal_questions
from decisions_demo.scenario import SAMPLE_EMAIL, decide_triage, triage_questions
from decisions_demo.tools import SAMPLE_TOOL_EMAIL, run_tool, select_tool, tool_questions


class Decider(Protocol):
    """Any object with a decide method: the real client or the fake client."""

    def decide(self, input: DecisionInput, questions: dict[str, Question]) -> DecisionResult: ...


def _cmd_triage(args: argparse.Namespace, client: Decider, console: Console) -> None:
    email = args.email or SAMPLE_EMAIL
    render.print_input(console, email)
    result = client.decide(email, triage_questions())
    render.print_answers(console, result)
    decision = decide_triage(result)
    render.print_decision(
        console,
        [
            f"Category: {decision.category}",
            f"Model tier: {decision.tier}",
            f"Next step: {decision.next_step.value}",
            *[f"Reason: {reason}" for reason in decision.reasons],
        ],
    )


def _cmd_tools(args: argparse.Namespace, client: Decider, console: Console) -> None:
    email = args.email or SAMPLE_TOOL_EMAIL
    render.print_input(console, email)
    result = client.decide(email, tool_questions())
    render.print_answers(console, result)
    tool = select_tool(result)
    if tool is None:
        render.print_decision(console, ["Selected tool: none", "The agent replies without a tool."])
        return
    output = run_tool(tool, reference="AB123456789XX")
    render.print_decision(console, [f"Selected tool: {tool}", f"Tool output: {output}"])


def _cmd_multimodal(args: argparse.Namespace, client: Decider, console: Console) -> None:
    image = make_delivery_slip()
    render.print_input(console, f"Synthetic missed-delivery slip (PNG, {len(image)} bytes)")
    result = client.decide([image_block(image, "image/png")], multimodal_questions())
    render.print_answers(console, result)
    slip = result.answers["is_missed_delivery_slip"]
    step = result.answers["next_step"]
    lines = [f"Missed-delivery slip: {'yes' if slip.value else 'no'}"]  # type: ignore[union-attr]
    lines.append(f"Next step for the customer: {step.choice}")  # type: ignore[union-attr]
    render.print_decision(console, lines)


COMMANDS = {"triage": _cmd_triage, "tools": _cmd_tools, "multimodal": _cmd_multimodal}


def _cmd_eval(args: argparse.Namespace, client: Decider, console: Console) -> None:
    from rich.table import Table

    from decisions_demo import evaluate
    from decisions_demo.client import ChoiceAnswer

    question = evaluate.load_question(Path(args.question))
    labels = list(question["criteria"])
    rows = evaluate.load_dataset(Path(args.dataset), allowed_labels=set(labels))
    console.print(f"Dataset: {args.dataset} ({len(rows)} rows) | Labels: {', '.join(labels)}")

    results = []
    input_tokens = 0
    latencies = []
    for row in rows:
        result = client.decide(row.query, {evaluate.QUESTION_KEY: question})
        answer = result.answers[evaluate.QUESTION_KEY]
        assert isinstance(answer, ChoiceAnswer)
        results.append(
            evaluate.RowResult(
                row.query, row.label, answer.choice, answer.confidence, answer.probabilities
            )
        )
        input_tokens += result.input_tokens
        latencies.append(result.latency_ms)

    metrics = evaluate.compute_metrics(results, labels)
    evaluate.write_results(Path(args.output), results)

    console.print(
        f"Accuracy: {metrics.accuracy:.1%} ({sum(r.correct for r in results)}/{metrics.total})"
    )
    for name, value in (
        ("correct", metrics.mean_confidence_correct),
        ("incorrect", metrics.mean_confidence_incorrect),
    ):
        console.print(f"Mean confidence, {name} rows: {'n/a' if value is None else f'{value:.2f}'}")
    median = sorted(latencies)[len(latencies) // 2]
    console.print(
        f"Input tokens: {input_tokens} | Output tokens: 0 | Median latency: {median:.0f} ms"
    )

    table = Table(title="Confusion matrix (rows: label, columns: predicted)")
    table.add_column("label")
    for label in labels:
        table.add_column(label, justify="right")
    for label in labels:
        table.add_row(label, *[str(metrics.confusion[label].get(p, 0)) for p in labels])
    console.print(table)
    console.print(f"Results CSV: {args.output}")


COMMANDS["eval"] = _cmd_eval


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser."""
    parser = argparse.ArgumentParser(prog="python -m decisions_demo", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("triage", "tools"):
        p = sub.add_parser(name)
        p.add_argument("--email", help="Email text. Default: a sample email.")
    sub.add_parser("multimodal")
    p = sub.add_parser("eval", help="Measure accuracy on a labeled CSV file.")
    p.add_argument("--dataset", default="data/sample_emails.csv", help="CSV with query,label.")
    p.add_argument("--question", default="data/triage_question.json", help="Question JSON.")
    p.add_argument("--output", default="results/eval_results.csv", help="Results CSV path.")
    return parser


def _make_client(console: Console) -> Decider:
    from decisions_demo.client import DecisionsClient

    load_dotenv()
    config = load_config(os.environ)
    console.print(config.describe(), style="dim")
    return DecisionsClient(config)


def main(argv: Sequence[str] | None = None, client: Decider | None = None) -> int:
    """Run one command. Returns 0 on success, 1 on an API error, 2 on a config error."""
    args = build_parser().parse_args(argv)
    console = Console()
    err = Console(stderr=True)
    try:
        if client is None:
            client = _make_client(console)
        COMMANDS[args.command](args, client, console)
    except ConfigError as error:
        err.print(f"Configuration error: {error}")
        return 2
    except DatasetError as error:
        err.print(f"Dataset error: {error}")
        return 2
    except DecisionsAPIError as error:
        err.print(f"Decisions API error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
