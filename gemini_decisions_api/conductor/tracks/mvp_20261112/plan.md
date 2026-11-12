# Plan: MVP of the Gemini Decisions API Demo

## Phase 1: Fact check and project frame [checkpoint: 0ade250]

  - Verification: `pytest --cov=src` passed (93 tests, 98 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 21:50 SGT.
  - Open: the Vertex AI task is blocked until the project gets early access.

- [x] Task: Make the project frame
  - [x] Add `requirements.txt`, `.env.example`, `.gitignore`, `pyproject.toml` (ruff, pytest).
  - [x] Add the package `src/decisions_demo/`.
  - Summary: all frame files exist. `requirements.txt` pins `google-adk` 2.14.0 and
    `google-genai` 2.34.0. A plain `pip install google-adk` took about 2 minutes.
- [x] Task: Backend config module (spec FR0)
  - [x] Write tests: default backend, Vertex AI backend, model ID override, and a
        missing variable for each backend.
  - [x] Implement `src/decisions_demo/config.py`.
  - [x] Show both backends in `.env.example`.
  - Summary: `config.py` reads the environment and selects the backend. 16 tests, 100 percent
    coverage. `describe()` never prints the key.
- [x] Task: Test the Decisions API with a script in `scripts/check_api.py`
  - [x] Find the `google-genai` version that has `client.decisions.create` (3.2.0).
  - [x] Send one request with one `noul`, one `choice`, and one `score` question.
  - [x] Record the response shape in `tech-stack.md`.
  - Summary: 3.2.0 conflicts with `google-adk`, so the demo uses REST (see the tech-stack
    change log). The REST call returned 200 with all three answer types.
- [x] Task: Record the model IDs and the price
  - [x] List the models. Record the Flash-Lite, Flash, and Pro IDs in `tech-stack.md`.
  - [x] Record the price for each 1M input tokens from the official pricing page.
  - Summary: tiers are `gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-4-argon`.
    The official pricing page gives US$0.10 for each 1M input tokens for `gemini-decision-1`.
- [ ] Task: Test the Vertex AI backend (BLOCKED: waiting for early access)
  - [ ] Run `scripts/check_api.py` with `GOOGLE_GENAI_USE_VERTEXAI=true`.
  - [ ] Record the result. If access is not granted yet, mark the task as blocked
        and continue. Do not block phase 1 on this task.
- [x] Task: Test the ADK callback model change
  - [x] Write a test agent. Change `llm_request.model` in `before_model_callback`.
  - [x] Record if ADK calls the new model.
  - [x] Update `product.md` if a fact is different.
  - Summary: `tests/test_adk_model_switch.py` proves it with a fake genai client. ADK 2.14.0
    sends `llm_request.model` to `generate_content`. The spec FR5 fallback is not needed.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 2: Core module and Part 1 commands [checkpoint: 6c24f9b]

  - Verification: `pytest --cov=src` passed (93 tests, 98 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 21:50 SGT.

- [x] Task: Decisions client wrapper
  - [x] Write tests: question builders, answer parsing, latency measurement, API errors.
  - [x] Write the fake client.
  - [x] Implement `client.py` and `questions.py`.
  - Summary: REST client for both backends, tested with `httpx.MockTransport` and the real
    response in `tests/fixtures/real_response.json`. `questions.py` checks the API limits.
- [x] Task: Command `triage`
  - [x] Write tests: answer-to-tier map and answer-to-next-step map.
  - [x] Implement the command and the rich output (input, answers, decision).
  - Summary: `scenario.py` holds 6 questions and the rules. Real run: `tracking`, tier
    `flash`, `AUTO_REPLY`, 543 input tokens, 399 ms.
- [x] Task: Command `tools`
  - [x] Write tests: tool selection, `none`, and the out-of-scope case.
  - [x] Implement the six fake tools and the command.
  - Summary: real run on the fake-fee SMS email selected `verify_link` (p=1.00), 302 tokens.
- [x] Task: Command `multimodal`
  - [x] Write tests: the image code makes a valid PNG. The request includes the image.
  - [x] Implement `sample_image.py` and the command.
  - Summary: the image is drawn in code, so no image file is stored. Real run: slip yes
    (0.89), `collect_at_locker` (0.99), 1,375 tokens, 1,171 ms.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 3: Evaluation [checkpoint: ed95bd2]

  - Verification: `pytest --cov=src` passed (93 tests, 98 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 21:50 SGT.

- [x] Task: Dataset and question loader
  - [x] Write tests: valid CSV, empty CSV, missing column, unknown label.
  - [x] Implement the loader and the label check.
  - Summary: `evaluate.py` loads the CSV and the question JSON. Errors give the row number.
- [x] Task: Metrics
  - [x] Write tests: accuracy, confusion matrix, mean confidence for correct and
        incorrect rows.
  - [x] Implement the metrics (in `evaluate.py`, not a separate `metrics.py`).
- [x] Task: Command `eval` and sample data
  - [x] Write tests: the results CSV columns and the printed summary.
  - [x] Write `data/sample_emails.csv` (24 rows) and `data/triage_question.json`.
  - [x] Implement the command.
  - Summary: real run: 24/24 correct, mean confidence 0.99, 4,876 input tokens, median
    469 ms. The synthetic emails are easy. This result is not a benchmark.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 4: Comparison [checkpoint: 4eac7fc]

  - Verification: `pytest --cov` passed (117 tests, 96 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 22:08 SGT.

- [x] Task: generateContent path
  - [x] Write tests: the JSON schema matches the triage questions. Parse the response.
  - [x] Implement the `generateContent` call with the same questions.
  - Summary: `compare.py` builds a JSON schema and a prompt from the same questions. Thinking
    tokens count as output tokens.
- [x] Task: Command `compare`
  - [x] Write tests: the cost estimate uses the price constants. The table marks it "estimated".
  - [x] Implement the command.
  - Summary: default model is the lite tier, with a 60 s limit. Real run: Decisions 396 ms,
    543 tokens. Flash-Lite 46,122 ms (service slow on 12 Nov), 333 + 60 tokens. 5 of 6 agree.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 5: ADK agent [checkpoint: c9bad5d]

  - Verification: `pytest --cov` passed (117 tests, 96 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 22:08 SGT.

- [x] Task: Router agent
  - [x] Write tests with the fake client: each category selects the correct sub-agent.
  - [x] Implement the `BaseAgent` subclass and the six sub-agents.
  - Summary: `decisions_agent/agent.py`. The router writes `category`, `routed_to` to state.
- [x] Task: Model-tier callback
  - [x] Write tests: each complexity level sets the correct model.
  - [x] Implement the callback, or the fallback from spec FR5.
  - Summary: the callback sets `llm_request.model`. No fallback needed.
- [x] Task: Integration test
  - [x] Run the agent against the real API. Mark the test as integration.
  - Summary: real run passed in 6.3 s: `damage_claim` (0.9975), tier `pro` (score 1.76).
    `gemini-3.8-flash` and `gemini-4-argon` returned 504 on 12 Nov, so a local `.env`
    override set flash and pro to `gemini-3-flash-preview` for this run only.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)

## Phase 6: Notebook and README [checkpoint: a71807b]

  - Verification: `pytest --cov` passed (117 tests, 96 percent coverage) and `ruff check`
    passed. Real API runs checked. User approved on 12 Nov 2026 22:08 SGT.

- [x] Task: Notebook
  - [x] Write `notebooks/decisions_api_demo.ipynb` with one section for each use case.
  - [x] Run it from top to bottom with `jupyter nbconvert --execute`.
  - Summary: 6 sections. Executed with real calls. The saved outputs contain no key.
- [x] Task: README
  - [x] Write the demo README: setup, commands, known limits.
  - [x] Add the demo to the top-level `README.md` list.
  - [x] Change the evaluation example in `product.md` to the six labels.
- [x] Task: Phase Verification and Checkpoint (refer to workflow.md)
