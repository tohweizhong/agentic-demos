"""Skill Registry: publish one skill and attach it to an agent.

Skill Registry is regional (for example `us-central1`). The agent is in `global`, and it
mounts the skill with a `skill_registry` source. A skill ID stays reserved after a delete.
"""

from __future__ import annotations

import base64
import io
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from managed_agents_demo import agent_config, client, interactions, lifecycle, storage
from managed_agents_demo import console as out
from managed_agents_demo.config import BASE_AGENT, Settings

SKILL_LOCATION = "us-central1"
SKILL_ID = "sales-chart-style"
SKILL_FOLDER = agent_config.ASSETS / "registry-skills" / SKILL_ID
DISPLAY_NAME = "Sales chart style"
DESCRIPTION = (
    "Sets the house style for sales charts: horizontal sorted bars, value labels, "
    "a source footnote, and a fixed file name."
)
SKILL_AGENT_ID = "demo-skill-analyst"
SKILL_TARGET = "skills"

SKILL_TASK = (
    "Make one chart of the total 2025 revenue by region from /workspace/.agent/data/sales.csv. "
    "Use the sales-chart-style skill from /workspace/skills/. "
    "Save the chart in /workspace/.agent/output/."
)


def skill_url(project: str, location: str = SKILL_LOCATION) -> str:
    """Return the regional REST URL of the skills collection."""
    return (
        f"https://{location}-aiplatform.googleapis.com/v1beta1/"
        f"projects/{project}/locations/{location}/skills"
    )


def skill_resource(project: str, location: str = SKILL_LOCATION) -> str:
    """Return the resource name that a `skill_registry` source uses."""
    return f"projects/{project}/locations/{location}/skills/{SKILL_ID}"


def zip_skill(folder: Path) -> bytes:
    """Return a zip archive of the skill folder, with SKILL.md at the root."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(folder).as_posix())
    return buffer.getvalue()


def _body() -> dict[str, str]:
    return {
        "displayName": DISPLAY_NAME,
        "description": DESCRIPTION,
        "zippedFilesystem": base64.b64encode(zip_skill(SKILL_FOLDER)).decode("ascii"),
    }


def _wait(rest: client.RestClient, operation: dict[str, Any], sleep: Callable) -> None:
    if operation.get("name") and not operation.get("done"):
        regional = f"https://{SKILL_LOCATION}-aiplatform.googleapis.com/v1beta1/{operation['name']}"
        client.wait_for_operation(rest, regional, sleep=sleep)


def publish(rest: client.RestClient, project: str, sleep: Callable = time.sleep) -> str:
    """Create the skill, or update it if it exists. Return "created" or "updated"."""
    url = f"{skill_url(project)}/{SKILL_ID}"
    try:
        rest.request("GET", url)
        exists = True
    except client.ApiError as exc:
        if exc.status != 404:
            raise
        exists = False
    if exists:
        operation = rest.request(
            "PATCH",
            url,
            json=_body(),
            params={"updateMask": "displayName,description,zippedFilesystem"},
        )
        _wait(rest, operation, sleep)
        return "updated"
    operation = rest.request("POST", skill_url(project), json=_body(), params={"skillId": SKILL_ID})
    _wait(rest, operation, sleep)
    return "created"


def delete(rest: client.RestClient, project: str, sleep: Callable = time.sleep) -> None:
    """Delete the skill. The skill ID stays reserved."""
    operation = rest.request("DELETE", f"{skill_url(project)}/{SKILL_ID}")
    _wait(rest, operation, sleep)


def build_skill_agent_body(bucket: str, project: str) -> dict[str, Any]:
    """Return the body for an agent with the demo bucket and the registry skill."""
    agent_config.check_agent_id(SKILL_AGENT_ID)
    return {
        "id": SKILL_AGENT_ID,
        "base_agent": BASE_AGENT,
        "description": "Data analyst with a skill from Skill Registry. Synthetic data only.",
        "system_instruction": (
            agent_config.SYSTEM_INSTRUCTION
            + " Skills from Skill Registry are in /workspace/skills/."
            + " Read a skill before you use it."
        ),
        "tools": [{"type": "code_execution"}, {"type": "filesystem"}],
        "base_environment": {
            "type": "remote",
            "sources": [
                {
                    "type": "gcs",
                    "source": f"gs://{bucket}/{agent_config.BUCKET_PREFIX}",
                    "target": agent_config.MOUNT_TARGET,
                },
                {
                    "type": "skill_registry",
                    "source": skill_resource(project),
                    "target": SKILL_TARGET,
                },
            ],
            "network": {"allowlist": [{"domain": d} for d in agent_config.NETWORK_ALLOWLIST]},
        },
    }


def follows_skill_name(names: list[str]) -> bool:
    """Return True if a file name follows the skill rule `chart_<metric>_by_<category>.png`."""
    return any(
        Path(name).name.startswith("chart_") and "_by_" in name and name.endswith(".png")
        for name in names
    )


def run(
    rest: client.RestClient,
    sdk: Any,
    storage_client: Any,
    console: Console,
    settings: Settings,
    sleep: Callable = time.sleep,
) -> int:
    """Publish the skill, create the skill agent, send one task, and check the chart name."""
    console.rule("Step 1: publish the skill to Skill Registry")
    result = publish(rest, settings.project, sleep=sleep)
    console.print(f"Skill {skill_resource(settings.project)}: {result}.")

    console.rule("Step 2: create the agent with a skill_registry source")
    body = build_skill_agent_body(settings.bucket, settings.project)
    out.request(console, f"POST {rest.url('agents')}", body)
    try:
        operation = lifecycle.create(rest, body)
        if operation.get("name") and not operation.get("done"):
            client.wait_for_operation(rest, operation["name"], sleep=sleep)
        console.print(f"Created {SKILL_AGENT_ID}.")
    except client.ApiError as exc:
        if exc.status != 409:
            out.error(console, exc.message, status=exc.status)
            return 1
        console.print(f"The agent {SKILL_AGENT_ID} already exists. The script uses it.")

    console.rule("Step 3: send the chart task")
    request = interactions.build_request(SKILL_AGENT_ID, SKILL_TASK)
    out.request(console, "client.interactions.create(...)", request)

    def on_step(name: str) -> None:
        console.print(f"\n[dim]-> tool call: {name}[/dim]")

    def on_text(text: str) -> None:
        console.print(text, end="", markup=False, highlight=False)

    try:
        summary = interactions.consume(
            interactions.start(sdk, request), on_text=on_text, on_step=on_step
        )
    except Exception as exc:  # noqa: BLE001 - the SDK raises many error types.
        out.error(console, str(exc))
        return 1
    console.print()
    if summary.errors or summary.status not in (None, "completed"):
        out.error(console, "; ".join(summary.errors) or f"Status: {summary.status}")
        return 1

    names = [
        blob.name
        for blob in storage_client.list_blobs(settings.bucket, prefix="agent/output/")
        if not blob.name.endswith("/")
    ]
    table = Table("Object in the bucket")
    for name in names:
        table.add_row(f"gs://{settings.bucket}/{name}")
    console.print(table)
    if not follows_skill_name(names):
        out.error(console, "No chart file follows the skill rule chart_<metric>_by_<category>.png.")
        return 1
    out.result(
        console,
        "A chart file name follows the skill rule, so the agent used the registry skill.\n"
        f"Console: {storage.console_url(settings.bucket, 'agent/output/')}",
    )
    return 0
