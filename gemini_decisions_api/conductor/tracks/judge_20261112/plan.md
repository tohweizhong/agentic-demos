# Plan: Decisions API judge

## Phase 1: Judge logic

- [ ] Task: Rubric loader
  - [ ] Write tests: valid rubric, missing pass rule, bad type, bad min_level.
  - [ ] Implement `judge.py`: load the rubric and build the questions.
- [ ] Task: Answer loader
  - [ ] Write tests: valid CSV, bad label, optional check columns, empty file.
  - [ ] Implement the loader.
- [ ] Task: Verdict and review flag
  - [ ] Write tests: all pass, one fail, low confidence gives review.
  - [ ] Implement the verdict rules.
- [ ] Task: Agreement metrics
  - [ ] Write tests: accuracy, Cohen's kappa (known values), confusion matrix,
        agreement for each check.
  - [ ] Implement the metrics with the standard library.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 2: Command and sample data

- [ ] Task: Command `judge`
  - [ ] Write tests with the fake client: printed summary, results CSV, error codes.
  - [ ] Implement the command.
- [ ] Task: Sample data
  - [ ] Write `data/judge_answers.csv` (20 rows) and `data/judge_rubric.json`.
  - [ ] Write a test that checks 10 good rows and 10 bad rows.
- [ ] Task: Real run
  - [ ] Run the command against the real API. Record accuracy, kappa, and cost.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 3: Documentation

- [ ] Task: README
  - [ ] Add the "Judge" section, the formats, a Mermaid diagram, and the real results.
  - [ ] Validate the diagram.
- [ ] Task: Conductor docs
  - [ ] Add use case 6 to `product.md`. Add the method and results to `tech-stack.md`.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)
