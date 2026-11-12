"""Step 0: check that this account can create and delete agents.

The script creates the agent `demo-access-check`, waits for the long-running
operation, and deletes the agent. The first agent in a project can take two to
three minutes to provision.

Usage:
    python scripts/00_access_check.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import access_check, client, config


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    rest = client.RestClient(settings)
    return access_check.run(rest, console)


if __name__ == "__main__":
    sys.exit(main())
