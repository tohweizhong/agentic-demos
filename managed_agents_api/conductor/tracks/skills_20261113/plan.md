# Plan: Track 3 — Skill Registry skill

## Phase 1: Skill Registry

- [ ] Task: Skill client (FR1)
    - [ ] Write failing tests: zip content, create body, update when the skill exists, regional URL.
    - [ ] Implement `skills.py` with REST calls and operation polling.
- [ ] Task: Agent with the registry skill (FR2)
    - [ ] Write failing tests: agent body with a `gcs` source and a `skill_registry` source.
    - [ ] Implement `scripts/07_skill_registry.py`. Run it against the real API.
- [ ] Task: Cleanup and documents (FR3, FR4)
    - [ ] Write failing tests for `--skills`. Implement it.
    - [ ] README, notebook section, `rest_reference.sh skill` step.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
