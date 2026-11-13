# Spec: Track 4 — Evaluation

Decision: the user delegated all choices on 13 Nov 2026 11:20 SGT ("see to it that this managed api demo is fully built out"). The user was away, so the agent approved the spec and the plan.

## Overview

Evaluate the data analyst agent with the GenAI Evaluation Service, as the Managed Agents
evaluation guide describes.

## Functional requirements

### FR1. Evaluate a recorded interaction (`scripts/08_evaluate.py --recorded`)
- Read the interaction ID that `scripts/02_interact.py` saved.
- Score it with `MULTI_TURN_TASK_SUCCESS` and `FINAL_RESPONSE_QUALITY`.

### FR2. Generated scenarios (`scripts/08_evaluate.py --generate N`)
- Generate N scenarios (default 2) from the agent configuration, run inference, and score them.
- Print the cost warning before the run: each scenario runs the agent.

### FR3. Output
- Print a table with the metric, the score, and the rationale for each case.
- Save the results as JSON in `output/eval/`.

### FR4. Dependencies
- The evaluation SDK is large, so it goes in `requirements-eval.txt`, not in the base file.

## Acceptance criteria
1. Both modes run against the real API and print scores.
2. Unit tests pass without the evaluation SDK installed.

## Out of scope
- Custom metrics. Evaluation dashboards.
