"""Step 3: continue the session.

The script sends a follow-up question with the interaction ID and the environment
ID that scripts/02_interact.py saved. The agent answers from the first turn, in the
same sandbox.

Usage:
    python scripts/03_session.py
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
    return interact_demo.run_session(sdk, console)


if __name__ == "__main__":
    sys.exit(main())
