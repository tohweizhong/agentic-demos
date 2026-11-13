"""Step 6: give the agent the BigQuery MCP server for one interaction.

The script sends a short-lived access token in the `tools` override of one interaction. The
agent queries a public BigQuery table through the Google-hosted MCP server. Then the script
runs the same query directly, and checks the agent answer.

The account needs permission to run BigQuery jobs in the project (`roles/bigquery.jobUser`)
and to call MCP tools (`roles/mcp.toolUser`).

Usage:
    python scripts/06_mcp_bigquery.py
"""

from __future__ import annotations

import sys

from rich.console import Console

from managed_agents_demo import client, config, mcp


def main() -> int:
    console = Console()
    try:
        settings = config.load()
    except config.ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    console.print(f"Project: {settings.project}  Location: {settings.location}")
    sdk = client.make_genai_client(settings)
    return mcp.run(sdk, console, settings, token_provider=client.default_token_provider())


if __name__ == "__main__":
    sys.exit(main())
