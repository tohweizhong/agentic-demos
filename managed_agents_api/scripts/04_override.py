"""Step 4: override the tools for one interaction.

The script sends one interaction with only the code execution tool. Then it gets
the agent again, to show that the stored configuration did not change.

Usage:
    python scripts/04_override.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import client, config, interact_demo


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    sdk = client.make_genai_client(settings)
    return interact_demo.run_override(sdk, console)


if __name__ == "__main__":
    sys.exit(main())
