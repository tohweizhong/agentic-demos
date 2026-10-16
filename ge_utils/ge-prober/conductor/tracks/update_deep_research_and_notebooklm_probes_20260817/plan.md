# Implementation Plan: Update Deep Research and Gemini Notebook Probes

## Phase 1: Update Go Types & Payload Builder (TDD)
- [x] Task: Update `types.go` struct tag: `AgentSpec { AgentID string json:"agentId" }`.
- [x] Task: Update `client.go` `BuildStreamAssistRequest` for `deep_research_agent` (`agentsSpec`) and `gemini_notebook` (direct query).
- [x] Task: [TDD] Update unit tests in `client_test.go` and verify with `go test ./...`.

## Phase 2: Update Test Cases Catalog
- [x] Task: Update `test_cases/smoke_test_cases.json` with new queries, grounding types, and assertions.
- [x] Task: Run unit tests to verify JSON schema parsing (`config_test.go`).

## Phase 2: Live Verification & Cloud Run Deployment
- [x] Task: Run live `./ge-prober` locally to verify 4/4 passing probes.
- [x] Task: Re-deploy container to Cloud Run Job via `bash deploy_job.sh`.
- [x] Task: Execute Cloud Run Job `ge-prober-daily` and verify clean execution.
- [x] Task: Final Track Verification & Checkpoint.
