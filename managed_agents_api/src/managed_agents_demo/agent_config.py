"""Configuration of the data analyst agent.

The Managed Agents API accepts only `gcs` and `skill_registry` sources. The demo
uploads three files to a Cloud Storage bucket under the `agent/` prefix, and mounts
that prefix at `/.agent` in the sandbox:

- `/.agent/AGENTS.md`: the agent instructions.
- `/.agent/skills/report-writer/SKILL.md`: one skill.
- `/.agent/data/sales.csv`: the synthetic sales data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from managed_agents_demo import data
from managed_agents_demo.config import AGENT_ID_PREFIX, BASE_AGENT

ANALYST_AGENT_ID = "demo-data-analyst"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
BUCKET_PREFIX = "agent"
MOUNT_TARGET = "/.agent"
# The Preview API needs an allowlist when a data source is set, and it accepts only "*".
# The user accepted this for the demo on 12 Nov 2026. The data is synthetic.
NETWORK_ALLOWLIST = ("*",)

SYSTEM_INSTRUCTION = (
    "Read /.agent/AGENTS.md before you start, and follow it. "
    "Write all output files to /.agent/output/."
)

# Agent ID rules from the docs: 1 to 63 characters, lowercase letters, numbers, and
# hyphens, start with a letter, end with a letter or a number.
_AGENT_ID = re.compile(r"^[a-z]([a-z0-9-]{0,61}[a-z0-9])?$")


def load_asset(name: str) -> str:
    """Return the text of a file in the `assets/` folder."""
    return (ASSETS / name).read_text(encoding="utf-8")


def check_agent_id(agent_id: str) -> None:
    """Raise ValueError if the agent ID breaks the API rules or the demo prefix rule."""
    if not agent_id.startswith(AGENT_ID_PREFIX):
        raise ValueError(f"The agent ID must start with {AGENT_ID_PREFIX!r}: {agent_id!r}")
    if not _AGENT_ID.match(agent_id) or agent_id == AGENT_ID_PREFIX:
        raise ValueError(
            "The agent ID must have 1 to 63 lowercase letters, numbers, or hyphens. "
            f"It must start with a letter and end with a letter or a number: {agent_id!r}"
        )


def bucket_files() -> dict[str, str]:
    """Return the files to upload to the demo bucket, as {object name: content}."""
    return {
        f"{BUCKET_PREFIX}/AGENTS.md": load_asset("AGENTS.md"),
        f"{BUCKET_PREFIX}/skills/report-writer/SKILL.md": load_asset("report-writer/SKILL.md"),
        f"{BUCKET_PREFIX}/data/sales.csv": data.make_sales_csv(),
    }


def build_agent_body(
    bucket: str,
    agent_id: str = ANALYST_AGENT_ID,
    description: str = "Data analyst for the Managed Agents API demo. Synthetic data only.",
) -> dict[str, Any]:
    """Return the request body that creates the data analyst agent.

    The Preview API needs a network allowlist when a data source is set, and it accepts
    only `*`. Thus the sandbox can reach all internet hosts.
    """
    check_agent_id(agent_id)
    return {
        "id": agent_id,
        "base_agent": BASE_AGENT,
        "description": description,
        "system_instruction": SYSTEM_INSTRUCTION,
        "tools": [{"type": "code_execution"}, {"type": "filesystem"}],
        "base_environment": {
            "type": "remote",
            "sources": [
                {
                    "type": "gcs",
                    "source": f"gs://{bucket}/{BUCKET_PREFIX}",
                    "target": MOUNT_TARGET,
                }
            ],
            "network": {"allowlist": [{"domain": d} for d in NETWORK_ALLOWLIST]},
        },
    }
