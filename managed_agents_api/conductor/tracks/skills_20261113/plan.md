# Plan: Track 3 — Skill Registry skill

## Phase 1: Skill Registry [checkpoint: 059c724]

- Verification: unit tests pass, `ruff check` clean, real run of script 07 passed. The user
  delegated checkpoints.

- [x] Task: Skill client (FR1)
    - Summary: `skills.py` zips the skill, creates or updates it with the regional REST host,
      and polls the regional operation. `RestClient.url` now accepts an absolute URL.
    - [x] Write failing tests: zip content, create body, update when the skill exists, regional URL.
    - [x] Implement `skills.py` with REST calls and operation polling.
- [x] Task: Agent with the registry skill (FR2)
    - Summary: real run: skill updated, `demo-skill-analyst` created, and the agent wrote
      `chart_revenue_by_region.png` as the skill requires.
    - [x] Write failing tests: agent body with a `gcs` source and a `skill_registry` source.
    - [x] Implement `scripts/07_skill_registry.py`. Run it against the real API.
- [x] Task: Cleanup and documents (FR3, FR4)
    - Summary: `--skills` in the cleanup, README section with a diagram, notebook section 9,
      and the REST `skill` step (passed against the real API).
    - [x] Write failing tests for `--skills`. Implement it.
    - [x] README, notebook section, `rest_reference.sh skill` step.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
