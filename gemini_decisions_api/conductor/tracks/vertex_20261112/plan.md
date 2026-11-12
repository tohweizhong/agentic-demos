# Plan: Test the Vertex AI backend

## Phase 1: Vertex AI check (blocked until early access is granted)

- [ ] Task: Run `scripts/check_api.py` on Vertex AI and record the result in `tech-stack.md`.
- [ ] Task: Fix `client.py` if the request shape or the model name differs
  - [ ] Write a failing unit test for the difference.
  - [ ] Fix the code.
- [ ] Task: Run `triage`, `eval`, and `pytest -m integration` on Vertex AI.
- [ ] Task: Update the README backend table.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)
