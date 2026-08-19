# Specification: Automated Cloud E2E Pipeline & Log Artifacts

## Overview
Establish an automated end-to-end cloud pipeline and verification harness for `ge-prober`. This automates container compilation via Cloud Build, deployment to Cloud Run Jobs, Cloud Scheduler synchronization, live Cloud Run execution dispatch, log extraction from Cloud Logging, and dual log persistence for post-track audit trails without relying on manual console screenshots.

## Functional Requirements

### 1. Go Live E2E Test Suite (`e2e_test.go`)
- Guarded with `//go:build e2e` so unit tests remain offline and fast (`go test ./...`).
- Resolves ADC / token credentials and dispatches live queries across all configured test cases.
- Validates that `smoke_prober_results.json` is generated, validates its schema, and asserts 100% functional pass rate.
- Gracefully skips with `t.Skip(...)` when GCP credentials or target project configuration are missing.

### 2. Automated Cloud Pipeline Script (`scripts/e2e_cloud_pipeline.sh`)
- Orchestrates the full lifecycle:
  1. Build container image and deploy/update Cloud Run Job & Cloud Scheduler via `deploy_job.sh`.
  2. Trigger manual execution: `gcloud run jobs execute <job_name> --region=<region> --wait`.
  3. Extract full task execution logs using `gcloud beta run jobs executions logs <execution_id>` or Cloud Logging filter.
  4. Verify return code 0 and assert that `✅ Stream Done` and `📊 TEST SUITE EXECUTION SUMMARY` markers are present.
- Supports CLI flags:
  - `--project`: Target GCP Project ID
  - `--region`: Target GCP Region
  - `--job-name`: Target Cloud Run Job name
  - `--track-id`: Optional Conductor track ID to attach audit logs
  - `--dry-run`: Dry-run simulation mode for test harnesses
  - `--skip-build`: Reuse existing container image

### 3. Dual Log Persistence Architecture
- **Active Local Logs:** Automatically saved to `logs/executions/<timestamp>_<execution_id>.log` for developer inspection.
- **Track Checkpoint Artifact:** When `--track-id=<track_id>` is specified (or auto-detected from active Conductor track), save a copy to `conductor/tracks/<track_id>/execution.log`.

### 4. Repository & Ignore Configuration
- Add `logs/executions/` to `.gitignore` to prevent cluttering version control while preserving permanent track audit logs in `conductor/tracks/`.

## Acceptance Criteria
- [ ] `e2e_test.go` compiles and runs successfully with `go test -v -tags=e2e ./...`.
- [ ] `scripts/test_e2e_cloud_pipeline.sh` test harness validates all flags, dry-run mode, and log destination paths.
- [ ] `scripts/e2e_cloud_pipeline.sh` executes against Cloud Run, captures execution logs, and verifies exit code 0.
- [ ] Execution log is saved to `conductor/tracks/<track_id>/execution.log` and `logs/executions/`.
- [ ] All automated unit and deployment tests pass cleanly.
