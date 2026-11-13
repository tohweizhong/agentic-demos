"""Step 5: download the files that the agent wrote.

The agent writes its report and chart to /workspace/.agent/output/ in the sandbox. These files
are in the demo bucket under agent/output/. The script downloads them to output/agent/.

Usage:
    python scripts/05_download.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from managed_agents_demo import config, interact_demo, storage
from managed_agents_demo import console as out

DESTINATION = Path("output/agent")


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    client = storage.make_storage_client(settings.project)
    files = storage.download_output(
        client, settings.bucket, interact_demo.OUTPUT_PREFIX, DESTINATION
    )
    if not files:
        out.error(
            console,
            f"No files under gs://{settings.bucket}/{interact_demo.OUTPUT_PREFIX}. "
            "Run scripts/02_interact.py first.",
        )
        return 1
    table = Table("Local file", "Size (bytes)")
    for path, size in files:
        table.add_row(str(path), str(size))
    console.print(table)
    out.result(console, f"Downloaded {len(files)} file(s) to {DESTINATION}/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
