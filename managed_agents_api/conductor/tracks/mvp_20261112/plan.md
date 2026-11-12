# Plan: Track 1 — MVP (lifecycle, interactions, inline skills)

## Phase 1: Project base and access check [checkpoint: 395ba83]

- Verification: `pytest --cov=src` 30 passed, coverage 92 percent. `ruff check` clean.
  Real access check passed in the test project. User confirmed on 12 Nov 2026 22:12 SGT.

- [x] Task: Make the project files
    - Summary: Added `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.env.example`,
      and `.gitignore`. The SDK installs `httpx2`, so the demo uses it instead of `httpx`.
    - [x] Add `requirements.txt` (pinned), `requirements-dev.txt`, `pyproject.toml` (ruff, pytest).
    - [x] Add `.env.example` and `.gitignore` (`.env`, `.venv/`, `output/`).
    - [x] Add an empty package `src/managed_agents_demo/` and `tests/`.
- [x] Task: Configuration module (FR1)
    - Summary: `config.py` reads `GOOGLE_CLOUD_PROJECT` and rejects the placeholder value.
      It holds the base agent, the location, and the `demo-` prefix.
    - [x] Write failing tests: project ID read from the environment, error text when it is missing.
    - [x] Implement `config.py`.
- [x] Task: Terminal output module
    - Summary: `console.py` prints the request, response, result, and error blocks.
      It masks every `Authorization` value at any depth.
    - [x] Write failing tests: the request, response, and result blocks, and token masking.
    - [x] Implement `console.py` with `rich`.
- [x] Task: Client module and operation polling
    - Summary: `client.py` has a REST client with ADC tokens, `ApiError` with the denied
      permission, and `wait_for_operation` with a time limit. Tests use `MockTransport`.
    - [x] Write failing tests with a fake client: poll until `done`, a time limit, an error result.
    - [x] Implement `client.py`: the SDK client, a REST helper with `httpx`, and `wait_for_operation`.
- [x] Task: Access check script (FR2)
    - Summary: `access_check.py` and `scripts/00_access_check.py`. Real run in the test project:
      create 373.2 s, delete 6.5 s, passed. Times recorded in `tech-stack.md`.
    - Note: the tests and the code for Phase 1 were written in the same step while the
      package install ran. The red phase was not run separately.
    - Fix: a unit test in `test_scripts.py` read the real `.env` file and called the real API
      two times. `python-dotenv` searched from the script folder, not the current folder.
      Both runs deleted their agent. `config.load` now uses `find_dotenv(usecwd=True)`, and
      `tests/conftest.py` blocks real credentials and the SDK client in all unit tests.
    - [x] Write failing tests: create, wait, delete, and the HTTP 403 message.
    - [x] Implement `scripts/00_access_check.py`.
    - [x] Run it against the real API. Record the times and any error in `tech-stack.md`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Agent lifecycle and Cloud Storage source [checkpoint: 59b8e53]

- Verification: `pytest --cov=src` 64 passed, coverage 93 percent. `ruff check` clean.
  Real bucket setup and lifecycle run passed. User confirmed on 12 Nov 2026 22:28 SGT.

- [x] Task: Synthetic data (FR4)
    - Summary: `data.py` makes 144 rows of seeded monthly sales (12 months, 4 regions,
      3 products). Revenue is units times price.
    - [x] Write failing tests: fixed seed, column names, row count.
    - [x] Implement `data.py`, which makes the sales CSV text.
- [x] Task: Agent configuration (FR4)
    - Summary: `agent_config.py` mounts `gs://BUCKET/agent` at `/.agent` with one `gcs` source,
      a system instruction that points to `/.agent/AGENTS.md`, and the `*` network allowlist.
    - Change: the real API rejects `inline` sources (HTTP 400). The user selected a Cloud
      Storage bucket on 12 Nov 2026 22:19 SGT.
    - Change: the API needs a network allowlist with a data source, and accepts only `*`.
      The user accepted `*` on 12 Nov 2026 22:25 SGT.
    - [x] Write failing tests: one `gcs` source, `gs://BUCKET/agent` mounted at `/.agent`.
    - [x] Change `agent_config.py` to the `gcs` source.
- [x] Task: Demo bucket setup (FR4)
    - Summary: `storage.py` and `scripts/00b_setup_bucket.py` create the bucket with uniform
      access in `US` and upload three files. Real run: bucket created, three files uploaded.
    - [x] Write failing tests with a fake storage client: create if missing, uniform access,
      upload paths, and an existing bucket in the same project.
    - [x] Implement `storage.py` and `scripts/00b_setup_bucket.py`.
    - [x] Run it against the real API.
- [x] Task: Lifecycle functions (FR3)
    - Summary: `lifecycle.py`: REST create, update (`PATCH` with `update_mask`), and delete.
      SDK get and list with pages. The docs confirm that the SDK has no update method.
    - [x] Write failing tests: create, get, list, and update with the fake client.
    - [x] Check if the SDK has an update method. Use REST `PATCH` if it does not.
    - [x] Implement `lifecycle.py`. Record the update result in `tech-stack.md`.
- [x] Task: Lifecycle script
    - Summary: `lifecycle_demo.py` and `scripts/01_lifecycle.py`. It reuses an agent that
      exists (HTTP 409). Real run: create 13.3 s, get, list, and update passed.
    - [x] Implement `scripts/01_lifecycle.py`.
    - [x] Run it against the real API.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Interactions [checkpoint: 4e43aec]

- Verification: `pytest --cov=src` 86 passed, coverage 94 percent. `ruff check` clean.
  Real runs of scripts 02, 03, and 04 passed. User confirmed on 12 Nov 2026 22:45 SGT.

- [x] Task: Event stream handling (FR5)
    - Summary: `interactions.py` reads the real event shapes, skips the repeated full text,
      and records harness and built-in tool calls. Test events copy a real recording.
    - [x] Write failing tests with recorded events: agent text, the final event, the interaction ID, the environment ID.
    - [x] Implement `interactions.py`.
- [x] Task: Single-turn script (FR5, FR8)
    - Summary: real run: 230.6 s, 16 tool calls. The agent wrote `report.md` and a PNG chart,
      and both are in the bucket. Its numbers agree with an independent calculation.
    - Fix: the mount target `/.agent` failed in the sandbox. The target is now `.agent`.
    - [x] Implement `scripts/02_interact.py`. Save the IDs to `output/last_interaction.json`.
    - [x] Run it against the real API. Check that the agent writes a chart and a report.
- [x] Task: Multi-turn session (FR6)
    - Summary: real run: 11.1 s, no tool calls. The agent repeated North, 95.3 percent, from
      the first turn.
    - [x] Write failing tests: `previous_interaction_id` and the environment ID go in the request.
    - [x] Implement `scripts/03_session.py`.
    - [x] Run it against the real API.
- [x] Task: Configuration override (FR7)
    - Summary: the override adds `google_search` for one turn. The agent used search, and the
      stored tools stayed `code_execution` and `filesystem`. SDK errors now print, not raise.
    - [x] Write failing tests: the override `tools` list goes in the request, and the stored agent is not changed.
    - [x] Implement `scripts/04_override.py`.
    - [x] Run it against the real API.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Cleanup, reference, and documents [checkpoint: a738101]

- Verification: `pytest --cov=src` 95 passed, coverage 95 percent. `ruff check` clean.
  Real runs passed: cleanup, REST reference (7 steps), notebook (top to bottom), and the
  integration test (107.5 s). The user delegated this checkpoint on 12 Nov 2026 22:45 SGT
  ("steer and build this out completely").

- [x] Task: Cleanup script (FR9)
    - Summary: `cleanup.py` and `scripts/99_cleanup.py`. Deletes only `demo-` agents, asks
      first, `--bucket` asks again. Real run deleted the agent, the bucket, and the state file.
    - [x] Write failing tests: only `demo-` agents are deleted, the confirmation, `--yes`,
      and `--bucket`, which deletes the demo bucket after a second confirmation.
    - [x] Implement `scripts/99_cleanup.py` with the agent identity notice.
- [x] Task: REST reference (FR10)
    - Summary: `scripts/rest_reference.sh` with its own agent. Real run: all seven steps passed.
      Fix: `tee /dev/stderr` truncated a redirected log file. The script now uses `tee >(cat >&2)`.
    - [x] Write `scripts/rest_reference.sh`. Run each command once against the real API.
- [x] Task: Notebook (FR11)
    - Summary: `notebook.ipynb` with the same steps, plus a cell that shows the report and the
      chart from the bucket. Executed from top to bottom with `nbclient` against the real API.
      The repository copy has no outputs, so that it has no project ID.
    - [x] Write `notebook.ipynb` with the same steps as the scripts.
    - [x] Run it from top to bottom.
- [x] Task: Integration test
    - Summary: `tests/test_integration.py` creates `demo-integration-test`, asks for the row count
      (144), and deletes the agent in `finally`. It runs only with `RUN_INTEGRATION=1`.
    - [x] Write one test for create, interact, and delete. Mark it `integration`.
- [x] Task: README and repository index
    - Summary: `README.md` with the Preview notice, setup, steps, test results, Preview limits,
      and what is not built. One line in the top-level `README.md`.
    - [x] Write `README.md`: the Preview notice, setup, scripts, cost, and what is not built.
    - [x] Add one line for `managed_agents_api/` to the top-level `README.md`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
