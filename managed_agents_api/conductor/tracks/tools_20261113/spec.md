# Spec: Track 2 — Output download and BigQuery MCP tools

Decision: the user delegated all choices on 13 Nov 2026 11:20 SGT ("see to it that this managed api demo is fully built out"). The user was away, so the agent approved the spec and the plan.

## Overview

Add two features to the demo: download the files that the agent wrote, and give the agent the
Google-hosted BigQuery MCP server for one interaction.

## Functional requirements

### FR1. Output download (`scripts/05_download.py`)
- Download every object under `agent/output/` in the demo bucket to the local `output/` folder.
- Print each local path and size. Skip the zero-byte folder object.

### FR2. BigQuery MCP server (`scripts/06_mcp_bigquery.py`)
- Send one interaction to `demo-data-analyst` with a `tools` override: `code_execution` and an
  `mcp_server` tool for `https://bigquery.googleapis.com/mcp`.
- The headers carry a short-lived ADC access token and `X-Goog-User-Project`. The token is not
  stored in the agent configuration and not written to disk. The terminal output masks it.
- The task queries the public table `bigquery-public-data.usa_names.usa_1910_current`.
- Print the MCP tool calls that the stream reports.
- Check the result with a direct BigQuery MCP call (`execute_sql_readonly`) from the script.

### FR3. Asset rename (chore)
- Rename `assets/AGENTS.md` to `assets/analyst-instructions.md`. The bucket object name stays
  `agent/AGENTS.md`. Coding assistants read any `AGENTS.md` file as instructions for the
  folder, so the old name gave them wrong instructions.

### FR4. Documents
- README, notebook, and `scripts/rest_reference.sh` (an `mcp` step) show both features.

## Acceptance criteria
1. Script 05 downloads `report.md` and the PNG chart.
2. Script 06 completes, the stream shows at least one MCP tool call, and the answer agrees
   with the direct query.
3. Unit tests pass with coverage of 70 percent or more. `ruff check` is clean.

## Out of scope
- MCP servers other than BigQuery. Storing MCP credentials in the agent configuration.
