# Plan: Decisions API judge

## Phase 1: Judge logic [checkpoint: 94e53f6]

- [x] Task: Rubric loader
  - [x] Write tests: valid rubric, missing pass rule, bad type, bad min_level.
  - [x] Implement `judge.py`: load the rubric and build the questions.
- [x] Task: Answer loader
  - [x] Write tests: valid CSV, bad label, optional check columns, empty file.
  - [x] Implement the loader.
- [x] Task: Verdict and review flag
  - [x] Write tests: all pass, one fail, low confidence gives review.
  - [x] Implement the verdict rules.
- [x] Task: Agreement metrics
  - [x] Write tests: accuracy, Cohen's kappa (known values), confusion matrix,
        agreement for each check.
  - [x] Implement the metrics with the standard library.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 2: Command and sample data [checkpoint: 94e53f6]

- [x] Task: Command `judge`
  - [x] Write tests with the fake client: printed summary, results CSV, error codes.
  - [x] Implement the command.
- [x] Task: Sample data
  - [x] Write `data/judge_answers.csv` (20 rows) and `data/judge_rubric.json`.
  - [x] Write a test that checks 10 good rows and 10 bad rows.
- [x] Task: Real run
  - [x] Run the command against the real API. Record accuracy, kappa, and cost.
  - Summary: 20 of 20 correct, kappa 1.00, 3 rows for review, 8,020 input tokens.
    The first run marked 16 rows for review. The fix uses the pass-decision probability
    for score checks (see the tech-stack change log).
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 3: Documentation [checkpoint: 6287181]

- [x] Task: README
  - [x] Add the "Judge" section, the formats, a Mermaid diagram, and the real results.
  - [x] Validate the diagram.
- [x] Task: Conductor docs
  - [x] Add use case 6 to `product.md`. Add the method and results to `tech-stack.md`.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)
