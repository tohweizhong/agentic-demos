"""Agent evaluation with the GenAI Evaluation Service.

This module runs in the second virtual environment (`.venv-eval`), because the evaluation SDK
needs `google-genai` < 3 and the main demo uses `google-genai` 3.2.0. The module imports the
SDK only inside `run`, so that the unit tests do not need it.

Two modes:

- `recorded`: score the interaction that `scripts/02_interact.py` saved.
- `generated`: generate scenarios from the agent configuration, run the agent on them, and score
  the conversations. Each scenario runs the agent, so this mode costs more.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from managed_agents_demo import console as out
from managed_agents_demo import interactions
from managed_agents_demo.config import Settings

STATE_PATH = Path("output/last_interaction.json")
OUTPUT_DIR = Path("output/eval")
ANALYST_AGENT_ID = "demo-data-analyst"
GENERATION_INSTRUCTION = (
    "Generate scenarios where a sales manager asks the data analyst questions about the sales "
    "data in /workspace/.agent/data/sales.csv, for example totals, growth, or a ranking."
)


def agent_resource(settings: Settings, agent_id: str) -> str:
    """Return the full resource name of an agent."""
    return f"{settings.parent}/agents/{agent_id}"


def recorded_dataset(types: Any, settings: Settings, state: dict[str, str]) -> Any:
    """Return a dataset with one recorded interaction."""
    agent = agent_resource(settings, state["agent_id"])
    return types.EvaluationDataset(
        eval_cases=[
            types.EvalCase(
                interactions_data_source=types.InteractionsDataSource(
                    interaction=f"{settings.parent}/interactions/{state['interaction_id']}",
                    gemini_agent_config=types.GeminiAgentConfig(gemini_agent=agent),
                )
            )
        ]
    )


def summarize(result: Any) -> tuple[list[tuple], list[tuple]]:
    """Return (case rows, summary rows) from an evaluation result.

    A case row is (case index, metric, score, explanation). A summary row is
    (metric, mean score, pass rate, "valid/total").
    """
    cases = []
    for case in result.eval_case_results or []:
        for candidate in case.response_candidate_results or []:
            for name, metric in (candidate.metric_results or {}).items():
                text = metric.explanation or ""
                if metric.error_message:
                    text = f"Error: {metric.error_message}"
                cases.append((case.eval_case_index, name, metric.score, text))
    summary = [
        (
            item.metric_name,
            item.mean_score,
            item.pass_rate,
            f"{item.num_cases_valid}/{item.num_cases_total}",
        )
        for item in result.summary_metrics or []
    ]
    return cases, summary


def _show(console: Console, result: Any) -> None:
    cases, summary = summarize(result)
    table = Table("Metric", "Mean score", "Pass rate", "Valid cases", title="Summary")
    for metric, mean, rate, valid in summary:
        table.add_row(str(metric), str(mean), str(rate), valid)
    console.print(table)
    detail = Table("Case", "Metric", "Score", "Explanation", title="Cases", show_lines=True)
    for index, metric, score, text in cases:
        detail.add_row(str(index), str(metric), str(score), text)
    console.print(detail)


def _save(result: Any, output_dir: Path, mode: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{mode}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    try:
        data = result.model_dump(mode="json", exclude_none=True)
    except AttributeError:
        data = {"result": str(result)}
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    return path


def run(
    console: Console,
    settings: Settings,
    mode: str = "recorded",
    count: int = 2,
    max_turn: int = 2,
    agent_id: str = ANALYST_AGENT_ID,
    eval_client: Any = None,
    types: Any = None,
    state_path: Path = STATE_PATH,
    output_dir: Path = OUTPUT_DIR,
) -> int:
    """Run one evaluation mode. Return 0 on success and 1 on failure."""
    if eval_client is None or types is None:
        try:
            import agentplatform
            from agentplatform import types as sdk_types
        except ImportError:
            out.error(
                console,
                "The evaluation SDK is not installed in this environment. Make .venv-eval with "
                "requirements-eval.txt, then run: .venv-eval/bin/python scripts/08_evaluate.py",
            )
            return 1

        eval_client = agentplatform.Client(project=settings.project, location=settings.location)
        types = sdk_types
    # FINAL_RESPONSE_QUALITY failed on 13 Nov 2026: its default judge model
    # (gemini-2.5-pro in the global location) was "not found". The demo uses two metrics
    # from the Managed Agents evaluation guide that worked.
    metrics = [types.RubricMetric.MULTI_TURN_TASK_SUCCESS, types.RubricMetric.SAFETY]

    if mode == "recorded":
        try:
            state = interactions.load_state(state_path)
        except FileNotFoundError as exc:
            out.error(console, str(exc))
            return 1
        agent = agent_resource(settings, state["agent_id"])
        out.request(
            console,
            "client.evals.evaluate(...)",
            {
                "interaction": state["interaction_id"],
                "agent": agent,
                "metrics": [str(m) for m in metrics],
            },
        )
        dataset = recorded_dataset(types, settings, state)
    elif mode == "generated":
        agent = agent_resource(settings, agent_id)
        console.print(
            f"[yellow]Cost: this mode runs the agent on {count} generated scenario(s), "
            f"with up to {max_turn} turns each.[/yellow]"
        )
        config = {"count": count, "generation_instruction": GENERATION_INSTRUCTION}
        out.request(console, "client.evals.generate_conversation_scenarios(...)", config)
        inference_config = {"user_simulator_config": {"max_turn": max_turn}}
        try:
            scenarios = eval_client.evals.generate_conversation_scenarios(
                agent=agent, config=config
            )
            out.request(console, "client.evals.run_inference(...)", inference_config)
            dataset = eval_client.evals.run_inference(
                agent=agent, src=scenarios, config=inference_config
            )
        except Exception as exc:  # noqa: BLE001 - the SDK raises many error types.
            out.error(console, f"Scenario generation or inference failed: {exc}")
            return 1
    else:
        out.error(console, f"Unknown mode {mode!r}. Use 'recorded' or 'generated'.")
        return 1

    start = time.monotonic()
    try:
        result = eval_client.evals.evaluate(dataset=dataset, metrics=metrics, agent=agent)
    except Exception as exc:  # noqa: BLE001 - the SDK raises many error types.
        out.error(console, f"Evaluation failed: {exc}")
        return 1
    _show(console, result)
    path = _save(result, output_dir, mode)
    out.result(
        console,
        f"Evaluation done in {out.format_elapsed(time.monotonic() - start)}. "
        f"The full result is in {path}.",
    )
    return 0
