# Implementation Plan: Expand Prober Suite with Deep Research and Web Grounding

## Phase 1: Multi-Probe Test Catalog & Unit Test Verification (TDD) [checkpoint: c86f148]
- [x] Task: Update `test_cases/smoke_test_cases.json` to define all 3 smoke probes (`smoke_gdrive_01`, `smoke_deep_research_02`, `smoke_web_grounding_03`) with zero keywords and pure semantic contracts. a1fe69f
- [x] Task: [TDD] Update `config_test.go` and `client_test.go` to verify 3-probe parsing and payload construction. c86f148
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) c86f148

## Phase 2: Local Concurrent Live Prober Verification
- [~] Task: Execute `./ge-prober -concurrency 4 -verbose` locally to verify 3 parallel probes (Drive, Deep Research, Web Grounding) with live Vertex AI LLM Judge scoring.
- [ ] Task: Verify `smoke_prober_results.json` exports accurate telemetry and verdicts for all 3 probes.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Cloud Run Deployment & Live E2E Pipeline Verification
- [ ] Task: Execute `scripts/e2e_cloud_pipeline.sh --track-id expand_suite_deep_research_and_web_grounding_20260819` to build, deploy, run in Cloud Run, and capture live execution logs.
- [ ] Task: Verify Cloud Run execution logs confirm 3/3 passing probes (100% functional & semantic pass rates) and persistence of dual log artifacts.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
