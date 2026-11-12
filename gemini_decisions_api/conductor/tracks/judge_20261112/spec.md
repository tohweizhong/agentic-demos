# Spec: Decisions API judge

## Overview

Add a `judge` command. It grades text answers with a rubric of yes/no and score checks,
in one Decisions API request for each answer. It then measures agreement with human labels.
The judge works for answers from any system. All sample data is synthetic.

## Functional requirements

### FR1. Input

- A CSV file with the columns `query`, `answer`, and `label` (good or bad).
- Optional columns `check:<check_key>` hold a human label for one check (yes or no).
- The command stops with the row number if a label is not valid.

### FR2. Rubric file (JSON)

- A list of checks. Each check has a key, a type (`noul` or `score`), the instructions,
  and a pass rule:
  - `noul`: `pass_when` is `true` or `false`.
  - `score`: `levels` (lowest first) and `min_level` to pass.
- The query and the answer go into the input text. All checks go into one request.

### FR3. Verdict

- An answer is "good" when every check passes. Otherwise it is "bad".
- The result lists the checks that failed.
- An answer is marked "review" when any check has a confidence below a threshold
  (default 0.70, set with `--min-confidence`).

### FR4. Agreement

- Accuracy, Cohen's kappa, and a confusion matrix of the verdict against `label`.
- When `check:` columns exist, the agreement for each check.
- A results CSV with the verdict, the failed checks, the review flag, and each probability.

### FR5. Sample data

- `data/judge_answers.csv`: 20 synthetic answers to parcel-support queries. 10 good, and
  10 with one planted defect each (wrong topic, unsupported promise, missing step,
  rude tone, wrong tracking number).
- `data/judge_rubric.json`: about 5 checks that can find those defects.

### FR6. Documentation

- README: a "Judge" section, the CSV and rubric formats, a diagram, and the real results.
- `product.md`: the judge as use case 6. `tech-stack.md`: Cohen's kappa method and results.
- The README states the limits: no reasons in the output, and a golden set is still needed.

## Non-functional requirements

- Unit tests with the fake client. No network. Coverage 70 percent or more.
- Standard library only for the metrics (no scikit-learn).

## Acceptance criteria

- `python -m decisions_demo judge` runs on the sample data with real calls and prints
  accuracy, kappa, and the review count.
- The README and the docs describe the judge and show the measured result.

## Out of scope

- An LLM judge that writes reasons.
- Real customer answers in the repository.
