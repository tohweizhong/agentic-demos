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

## Phase 2: Agent lifecycle and inline sources

- [ ] Task: Synthetic data (FR4)
    - [ ] Write failing tests: fixed seed, column names, row count.
    - [ ] Implement `data.py`, which makes the sales CSV text.
- [ ] Task: Agent configuration (FR4)
    - [ ] Write failing tests: three inline sources, the target paths, the `demo-` ID prefix.
    - [ ] Add `assets/AGENTS.md` and `assets/report-writer/SKILL.md`.
    - [ ] Implement `agent_config.py`.
- [ ] Task: Lifecycle functions (FR3)
    - [ ] Write failing tests: create, get, list, and update with the fake client.
    - [ ] Check if the SDK has an update method. Use REST `PATCH` if it does not.
    - [ ] Implement `lifecycle.py`. Record the update result in `tech-stack.md`.
- [ ] Task: Lifecycle script
    - [ ] Implement `scripts/01_lifecycle.py`.
    - [ ] Run it against the real API.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Interactions

- [ ] Task: Event stream handling (FR5)
    - [ ] Write failing tests with recorded events: agent text, the final event, the interaction ID, the environment ID.
    - [ ] Implement `interactions.py`.
- [ ] Task: Single-turn script (FR5, FR8)
    - [ ] Implement `scripts/02_interact.py`. Save the IDs to `output/last_interaction.json`.
    - [ ] Run it against the real API. Check that the agent writes a chart and a report.
- [ ] Task: Multi-turn session (FR6)
    - [ ] Write failing tests: `previous_interaction_id` and the environment ID go in the request.
    - [ ] Implement `scripts/03_session.py`.
    - [ ] Run it against the real API.
- [ ] Task: Configuration override (FR7)
    - [ ] Write failing tests: the override `tools` list goes in the request, and the stored agent is not changed.
    - [ ] Implement `scripts/04_override.py`.
    - [ ] Run it against the real API.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Cleanup, reference, and documents

- [ ] Task: Cleanup script (FR9)
    - [ ] Write failing tests: only `demo-` agents are deleted, the confirmation, `--yes`.
    - [ ] Implement `scripts/99_cleanup.py` with the agent identity notice.
- [ ] Task: REST reference (FR10)
    - [ ] Write `scripts/rest_reference.sh`. Run each command once against the real API.
- [ ] Task: Notebook (FR11)
    - [ ] Write `notebook.ipynb` with the same steps as the scripts.
    - [ ] Run it from top to bottom.
- [ ] Task: Integration test
    - [ ] Write one test for create, interact, and delete. Mark it `integration`.
- [ ] Task: README and repository index
    - [ ] Write `README.md`: the Preview notice, setup, scripts, cost, and what is not built.
    - [ ] Add one line for `managed_agents_api/` to the top-level `README.md`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
