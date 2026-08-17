# Implementation Plan: Fix Deep Research PLANNER_TURNS_EXCEEDED Error

## Phase 1: Update StreamAssist Client & Unit Tests (TDD)
- [x] Task: Update `client.go` `BuildStreamAssistRequest` to construct `toolsSpec` (`webGroundingSpec`) for `deep_research_agent`.
- [x] Task: [TDD] Update unit tests in `client_test.go` and verify with `go test ./...`.

## Phase 2: Local Verification & Checkpoint
- [x] Task: Run live `./ge-prober -concurrency 4` locally to verify 4/4 passing probes.

## Phase 3: Cloud Run Deployment & Verification
- [x] Task: Re-deploy container image via `bash deploy_job.sh`.
- [x] Task: Execute Cloud Run Job `ge-prober-daily` and verify 4/4 passing probes with exit code 0 (`ge-prober-daily-rdf45`).
- [x] Task: Final Track Verification & Checkpoint.
