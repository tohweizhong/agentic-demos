# Plan: Test the Vertex AI backend

## Phase 1: Vertex AI check (blocked until early access is granted)

- [~] Task: Run `scripts/check_api.py` on Vertex AI and record the result in `tech-stack.md`.
  - Summary (12 Nov 2026): before early access, the result is `404 Method not found` (no
    visibility label). Run again after the grants.
- [x] Task: Fix `client.py` if the request shape or the model name differs
  - [x] Write a failing unit test for the difference.
  - [x] Fix the code.
  - Summary: the model field is now the bare model ID on Vertex AI (from Duckie). A real
    call must confirm it after the grants.
- [ ] Task: Run `triage`, `eval`, and `pytest -m integration` on Vertex AI.
- [ ] Task: Update the README backend table.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)
