# Plan: Track 2 — Output download and BigQuery MCP tools

## Phase 1: Output download and asset rename [checkpoint: dd1d0b9]

- Verification: 98 unit tests passed, `ruff check` clean, real download passed. The user
  delegated checkpoints on 13 Nov 2026 11:20 SGT.

- [x] Task: Rename the analyst instructions asset (FR3)
    - Summary: `assets/AGENTS.md` is now `assets/analyst-instructions.md`. The bucket object is
      still `agent/AGENTS.md`. A test checks that no `AGENTS.md` file is in `assets/`.
    - [x] Update the test for `bucket_files` to read `analyst-instructions.md`.
    - [x] Rename the file and update `agent_config.py`.
- [x] Task: Output download (FR1)
    - Summary: `storage.download_output` and `scripts/05_download.py`. Real run: 3 files
      downloaded to `output/agent/`.
    - [x] Write failing tests with a fake storage client: paths, sizes, folder object skipped.
    - [x] Implement `download_output` in `storage.py` and `scripts/05_download.py`.
    - [x] Run it against the real bucket.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: BigQuery MCP server

- [ ] Task: MCP tool and stream handling (FR2)
    - [ ] Write failing tests: the `mcp_server` tool body, token masking, MCP call steps in the stream.
    - [ ] Implement `mcp.py` (tool body, token, direct `execute_sql_readonly` check).
- [ ] Task: MCP script (FR2)
    - [ ] Implement `scripts/06_mcp_bigquery.py`. Run it against the real API.
- [ ] Task: Documents (FR4)
    - [ ] README, notebook section, `rest_reference.sh mcp` step. Run the new REST step.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
