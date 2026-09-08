# Specification: Vertex AI LLM-as-a-Judge Semantic Evaluation

## Overview
Implement an automated semantic evaluation engine using Vertex AI Generative AI models (`gemini-2.5-flash` / `gemini-2.0-flash`) as an LLM judge. The judge evaluates whether retrieved Gemini Enterprise responses fulfill an explicit test case contract, accurately detecting ungrounded responses, refusals, missing connectors, or hallucinations that bypass deterministic keyword assertions.

## Functional Requirements

### 1. Test Case Semantic Contracts (`smoke_test_cases.json`)
- Augment each test case with an explicit `semantic_contract` string specifying exact criteria for fulfilling the user's objective:
  - Distinguish successful document retrieval from refusal messages or setup instructions.
  - Require factual grounding and relevance to the specific prompt.

### 2. Vertex AI LLM Judge Engine (`judge.go`)
- Connects to Vertex AI `generateContent` REST API using standard GCP ADC tokens:
  `https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{judge_model}:generateContent`
- Sends structured evaluation prompts containing:
  - User Query
  - Retrieved Response Text
  - Test Case Expected Behavior & Semantic Contract
- Enforces strict JSON response schema:
  - `fulfilled` (bool): Whether the response satisfies the semantic contract.
  - `score` (int 1-5): Semantic score (5 = Perfect fulfillment, 1 = Refusal / completely ungrounded).
  - `reasoning` (string): Concise explanation of the verdict.
  - `detected_refusal_or_unconnected` (bool): True if the model returned a refusal or setup guide.

### 3. Prober Integration & Stream Logging (`prober.go`, `logger.go`)
- Runs semantic judging concurrently after response streaming completes.
- Emits real-time judge verdict in verbose logs:
  - `⚖️ Judge Verdict: ✅ FULFILLED (Score: 5/5 | Gemini 2.5 Flash)`
  - `⚖️ Judge Verdict: ❌ UNFULFILLED (Score: 1/5 | Reason: Response is a setup guide rather than retrieved policy documents)`
- Displays `Semantic Pass Rate : X/N (YY.Y%)` in `📊 TEST SUITE EXECUTION SUMMARY`.
- Exports judge evaluations into `smoke_prober_results.json`.

### 4. Configuration & CLI Controls (`config.go`, `main.go`)
- Flags:
  - `-judge`: Enable/disable LLM-as-a-Judge (default: `true`).
  - `-judge-model`: Model name (default: `gemini-2.5-flash`, fallback: `gemini-2.0-flash`).
- Environment variables: `GE_ENABLE_JUDGE`, `GE_JUDGE_MODEL`.

### 5. Cloud Deployment Data Store Propagation Fix (`deploy_job.sh`, `scripts/e2e_cloud_pipeline.sh`)
- Extract `data_store_ids` from `config.json` and inject `GE_DATA_STORE_IDS` into Cloud Run Job environment variables (`--set-env-vars`).

## Acceptance Criteria
- [ ] `judge_test.go` verifies contract evaluation, refusal detection, scoring, and error handling with 100% test coverage.
- [ ] `smoke_test_cases.json` includes `semantic_contract` for all 4 smoke tests.
- [ ] `./ge-prober` evaluates responses semantically and displays `⚖️ Judge Verdict` and `Semantic Pass Rate`.
- [ ] `deploy_job.sh` passes `GE_DATA_STORE_IDS` to Cloud Run Job.
- [ ] `scripts/e2e_cloud_pipeline.sh` runs in Cloud Run and captures execution logs containing LLM judge evaluations.
