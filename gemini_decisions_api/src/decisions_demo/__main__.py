"""Command-line entry point: python -m decisions_demo <command>.

Commands:
    triage      Classify one email and select the model tier and the next step.
    tools       Select the next tool for an agent.
    multimodal  Ask several questions about one synthetic image.
    eval        Measure accuracy of one choice question on a labeled CSV file.
    compare     Compare one Decisions API call with one generateContent call.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv
from rich.console import Console

from decisions_demo import render
from decisions_demo.client import DecisionInput, DecisionResult, DecisionsAPIError, image_block
from decisions_demo.config import DEFAULT_TIER_MODELS, Backend, Config, ConfigError, load_config
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


def _decision_value(answer: Any) -> Any:
    """Return the answer in the same form as the generateContent JSON."""
    from decisions_demo.client import ChoiceAnswer, NoulAnswer

    if isinstance(answer, NoulAnswer):
        return answer.value
    if isinstance(answer, ChoiceAnswer):
        return answer.choice
    return answer.most_likely_level


def _cmd_compare(
    args: argparse.Namespace, client: Decider, console: Console, genai_client: Any
) -> None:
    from rich.table import Table

    from decisions_demo import compare

    email = args.email or SAMPLE_EMAIL
    questions = triage_questions()
    model = args.model
    render.print_input(console, email)

    decision = client.decide(email, questions)
    generated = compare.run_generate(genai_client, model, email, questions)
    decision_model = getattr(
        getattr(client, "config", None), "decisions_model", "gemini-decision-1"
    )

    table = Table(title="One request, same questions")
    for column in ("Method", "Model", "Latency (ms)", "Input tokens", "Output tokens"):
        table.add_column(column, justify="right" if "(" in column or "tokens" in column else "left")
    table.add_column("Cost US$ (estimated)", justify="right")
    rows = [
        ("Decisions API", decision_model, decision.latency_ms, decision.input_tokens, 0),
        (
            "generateContent",
            model,
            generated.latency_ms,
            generated.input_tokens,
            generated.output_tokens,
        ),
    ]
    for method, name, latency, tokens_in, tokens_out in rows:
        cost = compare.estimate_cost(name, tokens_in, tokens_out)
        cost_text = "no price in table" if cost is None else f"{cost:.6f}"
        table.add_row(method, name, f"{latency:.0f}", str(tokens_in), str(tokens_out), cost_text)
    console.print(table)

    answers = Table(title="Answers")
    for column in ("Question", "Decisions API", "generateContent", "Same"):
        answers.add_column(column)
    same = 0
    for key in questions:
        left = _decision_value(decision.answers[key])
        right = generated.answers.get(key)
        same += left == right
        answers.add_row(key, str(left), str(right), "yes" if left == right else "no")
    console.print(answers)
    console.print(f"Agreement: {same} of {len(questions)} answers")
    console.print(
        "Costs are estimated from the price table in compare.py (12 Nov 2026). "
        "The Decisions API also gives probabilities. generateContent gives only the labels."
    )


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
    p = sub.add_parser("compare", help="Compare with one generateContent call.")
    p.add_argument("--email", help="Email text. Default: a sample email.")
    p.add_argument("--model", default=None, help="generateContent model. Default: the lite tier.")
    return parser


def _make_client(console: Console) -> Decider:
    from decisions_demo.client import DecisionsClient

    config = _load_env_config()
    console.print(config.describe(), style="dim")
    return DecisionsClient(config)


def _load_env_config() -> Config:
    load_dotenv()
    return load_config(os.environ)


def _make_genai_client(config: Config) -> Any:
    from google import genai

    # Stop a slow call after 60 seconds, so the command does not wait without end.
    http_options = {"timeout": 60_000}
    if config.backend is Backend.VERTEX_AI:
        return genai.Client(
            vertexai=True,
            project=config.project,
            location=config.location,
            http_options=http_options,
        )
    return genai.Client(api_key=config.api_key, http_options=http_options)


def main(
    argv: Sequence[str] | None = None,
    client: Decider | None = None,
    genai_client: Any = None,
) -> int:
    """Run one command. Returns 0 on success, 1 on an API error, 2 on a config error."""
    args = build_parser().parse_args(argv)
    console = Console()
    err = Console(stderr=True)
    try:
        if client is None:
            client = _make_client(console)
        if args.command == "compare":
            if args.model is None:
                tiers = getattr(getattr(client, "config", None), "tier_models", None)
                args.model = (tiers or DEFAULT_TIER_MODELS)["lite"]
            if genai_client is None:
                genai_client = _make_genai_client(_load_env_config())
            _cmd_compare(args, client, console, genai_client)
        else:
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
    except Exception as error:  # noqa: BLE001 - show any generateContent error with its type.
        if type(error).__module__.startswith(("google.genai", "httpx")):
            err.print(f"generateContent error: {type(error).__name__}: {str(error)[:300]}")
            return 1
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
