"""Step 2: send the analysis task to the agent.

The agent reads the sales data, makes a chart, and writes a report. The script
streams the agent steps, saves the interaction ID and the environment ID, and
lists the files that the agent wrote to the bucket.

Usage:
    python scripts/02_interact.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import client, config, interact_demo, storage


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    sdk = client.make_genai_client(settings)
    return interact_demo.run_single(
        sdk, storage.make_storage_client(settings.project), console, settings
    )


if __name__ == "__main__":
    sys.exit(main())
