# Implementation Plan: Google Drive Connector Grounding & Authentication Probe

## Phase 1: Test Case Catalog & TDD Client Tool Routing
- [x] Task: Update `test_cases/smoke_test_cases.json` to configure `smoke_gdrive_01` ("Tell me about the helicopter racing league", `grounding_type: "google_drive"`, `must_have_citations: true`, zero keyword assertions `must_contain_keywords: []`, and semantic contract). e00901a
- [~] Task: [TDD] Update `client_test.go` with unit tests verifying `BuildStreamAssistRequest` payload for `google_drive` grounding.
- [ ] Task: Implement `BuildStreamAssistRequest` in `client.go` to construct Google Drive 1P tool routing payload.
- [ ] Task: [TDD] Update `prober_test.go` and `config_test.go` to verify test case parsing and LLM Judge evaluation without keyword assertions.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Authentication Resolution & Local Live Probing
- [ ] Task: Verify `auth.go` resolves user token (`admin@weizhongt.altostrat.com`) and configure `deploy_job.sh` to use dedicated SA `ge-regression-runner-sa@weizhong-project03.iam.gserviceaccount.com`.
- [ ] Task: Execute `./ge-prober` locally to verify live Google Drive connector query, citation capture, and Vertex AI LLM Judge score.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Cloud Run Deployment, E2E Pipeline & Log Artifacts
- [ ] Task: Execute `scripts/e2e_cloud_pipeline.sh` with `--track-id google_drive_connector_probe_20260819` to build, deploy, execute in Cloud Run, and capture execution logs.
- [ ] Task: Verify Cloud Run execution logs confirm Google Drive document retrieval, citations, and LLM Judge verdict.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
