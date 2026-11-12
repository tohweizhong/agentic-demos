"""Steps of the interaction scripts (`scripts/02` to `scripts/04`)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from managed_agents_demo import agent_config, interactions, storage
from managed_agents_demo import console as out
from managed_agents_demo.config import Settings

STATE_PATH = Path("output/last_interaction.json")
OUTPUT_PREFIX = f"{agent_config.BUCKET_PREFIX}/output/"

FIRST_TASK = (
    "Analyse the sales data in /workspace/.agent/data/sales.csv. "
    "Calculate the total revenue for each region in each quarter of 2025. "
    "Find the region with the highest revenue growth from Q1 to Q4, as a percentage. "
    "Make one bar chart of the revenue by region and quarter. "
    "Write the report with the report-writer skill. "
    "Save all files in /workspace/.agent/output/."
)

FOLLOW_UP = (
    "In your previous answer, which region had the highest growth from Q1 to Q4, and by what "
    "percentage? Use your earlier result. Do not calculate it again. "
    "Then list the files in /workspace/.agent/output/ with their sizes."
)

OVERRIDE_TASK = (
    "List the names of the tools that you can use in this turn. "
    "If you have a Google Search tool, use it to find the year of the first Python 3.0 "
    "release, and say which tool gave you the answer."
)

# For one interaction, the agent also gets Google Search. The stored agent keeps its
# two tools. A test on 12 Nov 2026 showed that an override with only `code_execution`
# does not remove the file tools of the harness, so the demo adds a tool instead.
# The interaction `tools` field does not accept `filesystem` (HTTP 400), so the list
# has only the types that the Interactions API accepts.
OVERRIDE_TOOLS = [{"type": "code_execution"}, {"type": "google_search"}]


def _run_turn(sdk: Any, console: Console, request: dict[str, Any]) -> interactions.StreamSummary:
    shown = {key: value for key, value in request.items() if key != "input"}
    shown["input"] = request["input"]
    out.request(console, "client.interactions.create(...)", shown)
    console.rule("Agent stream")
    start = time.monotonic()

    def on_step(name: str) -> None:
        console.print(f"\n[dim]-> tool call: {name}[/dim]")

    def on_text(text: str) -> None:
        console.print(text, end="", markup=False, highlight=False)

    try:
        summary = interactions.consume(
            interactions.start(sdk, request), on_text=on_text, on_step=on_step
        )
    except Exception as exc:  # noqa: BLE001 - the SDK raises many error types.
        # Show the API error to the user. Do not hide it in a traceback.
        return interactions.StreamSummary(status="failed", errors=[str(exc)])
    console.print()
    elapsed = time.monotonic() - start
    usage = summary.usage or {}
    out.response(
        console,
        {
            "interaction_id": summary.interaction_id,
            "environment_id": summary.environment_id,
            "status": summary.status,
            "elapsed": out.format_elapsed(elapsed),
            "tool_calls": len(summary.tool_calls),
            "tool_errors": summary.tool_errors,
            "search_citations": summary.citations,
            "total_input_tokens": usage.get("total_input_tokens"),
            "total_output_tokens": usage.get("total_output_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    )
    return summary


def _failed(console: Console, summary: interactions.StreamSummary) -> bool:
    if summary.errors or summary.status not in (None, "completed"):
        message = "; ".join(summary.errors) or f"The interaction status is {summary.status}."
        out.error(console, message)
        return True
    return False


def list_output(storage_client: Any, bucket: str) -> list[tuple[str, int]]:
    """Return the files that the agent wrote to the bucket, as (name, size)."""
    blobs = storage_client.list_blobs(bucket, prefix=OUTPUT_PREFIX)
    # The sandbox creates a zero-byte object for the folder itself. Skip it.
    return [(blob.name, blob.size or 0) for blob in blobs if not blob.name.endswith("/")]


def run_single(
    sdk: Any,
    storage_client: Any,
    console: Console,
    settings: Settings,
    agent_id: str = agent_config.ANALYST_AGENT_ID,
    state_path: Path = STATE_PATH,
) -> int:
    """Send the analysis task, save the IDs, and list the output files in the bucket."""
    summary = _run_turn(sdk, console, interactions.build_request(agent_id, FIRST_TASK))
    if _failed(console, summary):
        return 1
    if summary.interaction_id and summary.environment_id:
        interactions.save_state(
            state_path, agent_id, summary.interaction_id, summary.environment_id
        )
        console.print(f"Saved the IDs for the next script in {state_path}.")

    files = list_output(storage_client, settings.bucket)
    if files:
        table = Table("Object in the bucket", "Size (bytes)")
        for name, size in files:
            table.add_row(f"gs://{settings.bucket}/{name}", str(size))
        console.print(table)
    else:
        console.print(
            f"No files under gs://{settings.bucket}/{OUTPUT_PREFIX}. "
            "The files are only in the sandbox."
        )
    out.result(
        console,
        f"Console: {storage.console_url(settings.bucket, OUTPUT_PREFIX)}\n"
        "Next step: python scripts/03_session.py",
    )
    return 0


def run_session(sdk: Any, console: Console, state_path: Path = STATE_PATH) -> int:
    """Send a follow-up question in the same session and the same sandbox."""
    try:
        state = interactions.load_state(state_path)
    except FileNotFoundError as exc:
        out.error(console, str(exc))
        return 1
    request = interactions.build_request(
        state["agent_id"],
        FOLLOW_UP,
        previous_interaction_id=state["interaction_id"],
        environment_id=state["environment_id"],
    )
    summary = _run_turn(sdk, console, request)
    if _failed(console, summary):
        return 1
    out.result(
        console,
        "The agent answered from the first turn, in the same sandbox.\n"
        "Next step: python scripts/04_override.py",
    )
    return 0


def run_override(sdk: Any, console: Console, agent_id: str = agent_config.ANALYST_AGENT_ID) -> int:
    """Send one interaction with other tools, then show that the stored agent did not change."""
    request = interactions.build_request(agent_id, OVERRIDE_TASK, tools=OVERRIDE_TOOLS)
    summary = _run_turn(sdk, console, request)
    if _failed(console, summary):
        return 1
    stored = sdk.agents.get(id=agent_id)
    stored = (
        stored if isinstance(stored, dict) else stored.model_dump(mode="json", exclude_none=True)
    )
    out.request(console, f"client.agents.get(id={agent_id!r})")
    out.response(console, {"tools": stored.get("tools")})
    cited = ", ".join(summary.citations) or "none"
    out.result(
        console,
        f"This interaction sent the tools {[tool['type'] for tool in OVERRIDE_TOOLS]}.\n"
        f"Search citations in this turn: {cited}.\n"
        "The stored agent configuration did not change.\n"
        "To delete the demo resources: python scripts/99_cleanup.py",
    )
    return 0
