# Plan: Track 4 — Evaluation

## Phase 1: Evaluation [checkpoint: cb75cf1]

- Verification: 126 unit tests pass without the SDK, `ruff check` clean, real runs of both
  modes passed. The user delegated checkpoints.

- [x] Task: Dependencies (FR4)
    - Summary: `requirements-eval.txt` for a second environment (`.venv-eval`). The evaluation
      SDK needs `google-genai` < 3, and generated mode needs `google-adk`.
    - [x] Add `requirements-eval.txt` with pinned versions. Install it in the demo venv.
- [x] Task: Evaluation module (FR1, FR2, FR3)
    - Summary: `evaluation.py` and `scripts/08_evaluate.py`. Real runs: recorded mode and generated
      mode (1 scenario) both scored task success 1.0 and safety 1.0. `final_response_quality_v1`
      failed (judge model not found), so the demo does not use it.
    - [x] Write failing tests with a fake evaluation client: recorded mode, generated mode, result table.
    - [x] Implement `evaluation.py` and `scripts/08_evaluate.py`.
    - [x] Run both modes against the real API.
- [x] Task: Documents
    - Summary: README section with a diagram, and a notebook note with the shell command.
    - [x] README and notebook section.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
