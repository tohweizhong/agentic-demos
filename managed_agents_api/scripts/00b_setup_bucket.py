"""Step 0b: create the demo bucket and upload the agent files.

The Managed Agents API reads files from Cloud Storage. This script creates the
bucket if it does not exist, and uploads `AGENTS.md`, the `report-writer` skill,
and the synthetic sales data under the `agent/` prefix.

Usage:
    python scripts/00b_setup_bucket.py
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from managed_agents_demo import agent_config, config, storage
from managed_agents_demo import console as out


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Bucket: gs://{settings.bucket}")
    client = storage.make_storage_client(settings.project)
    result = storage.setup_bucket(
        client, settings.bucket, settings.project, agent_config.bucket_files()
    )
    console.print(
        f"Bucket {'created' if result.created else 'exists'}: gs://{result.bucket} "
        f"(location {storage.LOCATION} for a new bucket)"
    )
    table = Table("Object", "Size (bytes)")
    for name, size in result.uploaded:
        table.add_row(f"gs://{result.bucket}/{name}", str(size))
    console.print(table)
    out.result(
        console,
        f"The agent files are in the bucket.\n"
        f"Console: {storage.console_url(result.bucket, agent_config.BUCKET_PREFIX)}\n"
        "Next step: python scripts/01_lifecycle.py",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
