"""Step 8: evaluate the agent with the GenAI Evaluation Service.

Run this script with the evaluation environment (.venv-eval). See requirements-eval.txt.

Usage:
    .venv-eval/bin/python scripts/08_evaluate.py                # Score the interaction from step 2.
    .venv-eval/bin/python scripts/08_evaluate.py --generate 2   # Generate 2 scenarios, run, score.
"""

from __future__ import annotations

import argparse
import sys
import warnings

from rich.console import Console

from managed_agents_demo import config, evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the demo agent.")
    parser.add_argument(
        "--generate",
        type=int,
        metavar="N",
        help="Generate N scenarios and run the agent on them. Without it, score the saved one.",
    )
    parser.add_argument("--max-turn", type=int, default=2, help="Turns for each scenario.")
    args = parser.parse_args(argv)

    console = Console(width=140)
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    warnings.filterwarnings("ignore", category=UserWarning)
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    if args.generate:
        return evaluation.run(
            console, settings, mode="generated", count=args.generate, max_turn=args.max_turn
        )
    return evaluation.run(console, settings, mode="recorded")


if __name__ == "__main__":
    sys.exit(main())
