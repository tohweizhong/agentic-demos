# Plan: MVP of the Gemini Decisions API Demo

## Phase 1: Fact check and project frame

- [ ] Task: Make the project frame
  - [ ] Add `requirements.txt`, `.env.example`, `.gitignore`, `pyproject.toml` (ruff, pytest).
  - [ ] Add the package `src/decisions_demo/` with an empty `__main__.py`.
- [ ] Task: Test the Decisions API with a script in `scripts/check_api.py`
  - [ ] Find and pin the `google-genai` version that has `client.decisions.create`.
  - [ ] Send one request with one `noul`, one `choice`, and one `score` question.
  - [ ] Record the response shape in `tech-stack.md`.
- [ ] Task: Record the model IDs and the price
  - [ ] List the models. Record the Flash-Lite, Flash, and Pro IDs in `tech-stack.md`.
  - [ ] Record the price for each 1M input tokens from the official pricing page.
- [ ] Task: Test the ADK callback model change
  - [ ] Write a test agent. Change `llm_request.model` in `before_model_callback`.
  - [ ] Record if ADK calls the new model.
  - [ ] Update `product.md` if a fact is different.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 2: Core module and Part 1 commands

- [ ] Task: Decisions client wrapper
  - [ ] Write tests: question builders, answer parsing, latency measurement, API errors.
  - [ ] Write the fake client.
  - [ ] Implement `client.py` and `questions.py`.
- [ ] Task: Command `triage`
  - [ ] Write tests: answer-to-tier map and answer-to-next-step map.
  - [ ] Implement the command and the rich output (input, answers, decision).
- [ ] Task: Command `tools`
  - [ ] Write tests: tool selection, `none`, and the out-of-scope case.
  - [ ] Implement the six fake tools and the command.
- [ ] Task: Command `multimodal`
  - [ ] Write tests: the image script makes a valid PNG. The request includes the image.
  - [ ] Implement `scripts/make_sample_image.py` and the command.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 3: Evaluation

- [ ] Task: Dataset and question loader
  - [ ] Write tests: valid CSV, empty CSV, missing column, unknown label.
  - [ ] Implement the loader and the label check.
- [ ] Task: Metrics
  - [ ] Write tests: accuracy, confusion matrix, mean confidence for correct and
        incorrect rows.
  - [ ] Implement `metrics.py`.
- [ ] Task: Command `eval` and sample data
  - [ ] Write tests: the results CSV columns and the printed summary.
  - [ ] Write `data/sample_emails.csv` (24 rows) and `data/triage_question.json`.
  - [ ] Implement the command.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 4: Comparison

- [ ] Task: generateContent path
  - [ ] Write tests: the JSON schema matches the triage questions. Parse the response.
  - [ ] Implement the `generateContent` call with the same questions.
- [ ] Task: Command `compare`
  - [ ] Write tests: the cost estimate uses the price constants. The table marks it "estimated".
  - [ ] Implement the command.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 5: ADK agent

- [ ] Task: Router agent
  - [ ] Write tests with the fake client: each category selects the correct sub-agent.
  - [ ] Implement the `BaseAgent` subclass and the six sub-agents.
- [ ] Task: Model-tier callback
  - [ ] Write tests: each complexity level sets the correct model.
  - [ ] Implement the callback, or the fallback from spec FR5.
- [ ] Task: Integration test
  - [ ] Run the agent against the real API with `adk run`. Mark the test as integration.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 6: Notebook and README

- [ ] Task: Notebook
  - [ ] Write `notebooks/decisions_api_demo.ipynb` with one section for each use case.
  - [ ] Run it from top to bottom with `jupyter nbconvert --execute`.
- [ ] Task: README
  - [ ] Write the demo README: setup, commands, known limits.
  - [ ] Add the demo to the top-level `README.md` table.
  - [ ] Change the evaluation example in `product.md` to the six labels.
- [ ] Task: Phase Verification and Checkpoint (refer to workflow.md)
