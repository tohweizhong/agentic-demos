# Implementation Plan: Vertex AI LLM-as-a-Judge Semantic Evaluation

## Phase 1: Semantic Contracts & Vertex AI LLM Judge Client (TDD) [checkpoint: ec41655]
- [x] Task: Define `semantic_contract` for all test cases in `test_cases/smoke_test_cases.json`. ec41655
- [x] Task: Define `JudgeConfig`, `SemanticEvaluation`, and judge prompt templates in `types.go`. ec41655
- [x] Task: [TDD] Create `judge_test.go` with mock Vertex AI endpoint testing contract fulfillment, refusal detection, scoring, and JSON parsing. ec41655
- [x] Task: Implement `judge.go` with Vertex AI client and structured schema extraction. ec41655
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) ec41655

## Phase 2: Prober Integration, CLI Controls & Data Store Deployment Fix (TDD) [checkpoint: 4e8fada]
- [x] Task: [TDD] Write unit tests in `prober_test.go` and `logger_test.go` for probe judge evaluation and summary table formatting. 4e8fada
- [x] Task: Update `prober.go`, `logger.go`, `config.go`, and `main.go` to wire up `-judge` (`default: true`), `-judge-model`, and formatted log banners. 4e8fada
- [x] Task: Update `deploy_job.sh` and `scripts/e2e_cloud_pipeline.sh` to pass `GE_DATA_STORE_IDS` into Cloud Run environment variables. 4e8fada
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) 4e8fada

## Phase 3: Live Verification & Cloud Pipeline Execution [checkpoint: 8361040]
- [x] Task: Execute `./ge-prober` locally to verify live LLM judge scoring and refusal detection. 8361040
- [x] Task: Run live `scripts/e2e_cloud_pipeline.sh` to deploy and capture verified Cloud Run execution logs. 8361040
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) 8361040
