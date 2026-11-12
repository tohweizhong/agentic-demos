"""Step 1: the agent lifecycle.

The script creates the agent `demo-data-analyst`, gets it, lists the agents, and
updates the agent description. The agent stays in the project, so that the next
scripts can use it. Run `scripts/99_cleanup.py` to delete it.

Usage:
    python scripts/01_lifecycle.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import client, config, lifecycle_demo


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    rest = client.RestClient(settings)
    sdk = client.make_genai_client(settings)
    return lifecycle_demo.run(rest, sdk, console, settings)


if __name__ == "__main__":
    sys.exit(main())
