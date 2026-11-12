# Plan: Track 1 — MVP (lifecycle, interactions, inline skills)

## Phase 1: Project base and access check

- [ ] Task: Make the project files
    - [ ] Add `requirements.txt` (pinned), `requirements-dev.txt`, `pyproject.toml` (ruff, pytest).
    - [ ] Add `.env.example` and `.gitignore` (`.env`, `.venv/`, `output/`).
    - [ ] Add an empty package `src/managed_agents_demo/` and `tests/`.
- [ ] Task: Configuration module (FR1)
    - [ ] Write failing tests: project ID read from the environment, error text when it is missing.
    - [ ] Implement `config.py`.
- [ ] Task: Terminal output module
    - [ ] Write failing tests: the request, response, and result blocks, and token masking.
    - [ ] Implement `console.py` with `rich`.
- [ ] Task: Client module and operation polling
    - [ ] Write failing tests with a fake client: poll until `done`, a time limit, an error result.
    - [ ] Implement `client.py`: the SDK client, a REST helper with `httpx`, and `wait_for_operation`.
- [ ] Task: Access check script (FR2)
    - [ ] Write failing tests: create, wait, delete, and the HTTP 403 message.
    - [ ] Implement `scripts/00_access_check.py`.
    - [ ] Run it against the real API. Record the times and any error in `tech-stack.md`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

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
