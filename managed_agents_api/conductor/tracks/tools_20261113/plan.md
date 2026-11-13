# Plan: Track 2 — Output download and BigQuery MCP tools

## Phase 1: Output download and asset rename

- [ ] Task: Rename the analyst instructions asset (FR3)
    - [ ] Update the test for `bucket_files` to read `analyst-instructions.md`.
    - [ ] Rename the file and update `agent_config.py`.
- [ ] Task: Output download (FR1)
    - [ ] Write failing tests with a fake storage client: paths, sizes, folder object skipped.
    - [ ] Implement `download_output` in `storage.py` and `scripts/05_download.py`.
    - [ ] Run it against the real bucket.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: BigQuery MCP server

- [ ] Task: MCP tool and stream handling (FR2)
    - [ ] Write failing tests: the `mcp_server` tool body, token masking, MCP call steps in the stream.
    - [ ] Implement `mcp.py` (tool body, token, direct `execute_sql_readonly` check).
- [ ] Task: MCP script (FR2)
    - [ ] Implement `scripts/06_mcp_bigquery.py`. Run it against the real API.
- [ ] Task: Documents (FR4)
    - [ ] README, notebook section, `rest_reference.sh mcp` step. Run the new REST step.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
