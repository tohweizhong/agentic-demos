"""Terminal output for the demo commands.

Every command prints three blocks in this order: the input, the answers, the decision.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from decisions_demo.client import ChoiceAnswer, DecisionResult, NoulAnswer, ScoreAnswer


def print_input(console: Console, text: str) -> None:
    """Print the input block."""
    console.print(Panel(text, title="Input", expand=False))


def answers_table(result: DecisionResult) -> Table:
    """Return a table with one row for each answer."""
    table = Table(title="Answers")
    table.add_column("Question")
    table.add_column("Type")
    table.add_column("Answer")
    table.add_column("Confidence", justify="right")
    table.add_column("Distribution")
    for key, answer in result.answers.items():
        if isinstance(answer, NoulAnswer):
            text = f"{'yes' if answer.value else 'no'} (p={answer.probability:.2f})"
            table.add_row(key, "noul", text, f"{answer.confidence:.2f}", "")
        elif isinstance(answer, ChoiceAnswer):
            top = ", ".join(f"{k} {p:.2f}" for k, p in answer.ranked()[:3])
            table.add_row(key, "choice", answer.choice, f"{answer.confidence:.2f}", top)
        elif isinstance(answer, ScoreAnswer):
            level = answer.most_likely_level
            label = answer.legend.get(level, str(level))
            dist = ", ".join(f"{k}: {p:.2f}" for k, p in sorted(answer.probabilities.items()))
            text = f"{answer.score:.2f} (level {level}: {label})"
            table.add_row(key, "score", text, f"{answer.confidence:.2f}", dist)
    return table


def print_answers(console: Console, result: DecisionResult) -> None:
    """Print the answers block with usage and latency."""
    console.print(answers_table(result))
    console.print(
        f"Input tokens: {result.input_tokens} | Output tokens: {result.output_tokens} | "
        f"Latency: {result.latency_ms:.0f} ms"
    )


def print_decision(console: Console, lines: list[str]) -> None:
    """Print the decision block."""
    console.print(Panel("\n".join(lines), title="Decision", expand=False))
