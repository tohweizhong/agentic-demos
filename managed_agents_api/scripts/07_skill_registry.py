"""Step 7: publish a skill to Skill Registry and use it in a second agent.

The script zips assets/registry-skills/sales-chart-style/, publishes it to Skill Registry in
us-central1, and creates the agent demo-skill-analyst with two sources: the demo bucket and the
registry skill. Then it asks for a chart and checks that the chart file name follows the skill.

Usage:
    python scripts/07_skill_registry.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import client, config, skills, storage


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Skill location: {skills.SKILL_LOCATION}")
    rest = client.RestClient(settings)
    sdk = client.make_genai_client(settings)
    storage_client = storage.make_storage_client(settings.project)
    return skills.run(rest, sdk, storage_client, console, settings)


if __name__ == "__main__":
    sys.exit(main())
