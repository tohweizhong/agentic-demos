# Implementation Plan: Parameterize Cloud Scheduler and Deployment for `ge-prober`

## Phase 1: Deployment & Scheduler Parameterization (TDD & Implementation)
- [x] Task: Create test harness (`test_deploy_job.sh`) validating CLI flags, `--help`, `--dry-run`, and environment variable overrides d5d20b0
- [~] Task: Implement full parameterization in `deploy_job.sh` (supporting `--project`, `--region`, `--engine-id`, `--location`, `--job-name`, `--scheduler-name`, `--schedule`, `--time-zone`, `--service-account`, `--dry-run`, `--skip-build`, `--only-scheduler`)
- [ ] Task: Verify test harness passes with dry-run executions, flag precedence, and invalid input rejection
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: IAM Diagnostics, Trigger Verification & Documentation
- [ ] Task: Add pre-flight IAM role check (`roles/run.invoker`) and advisory warnings in `deploy_job.sh`
- [ ] Task: Update `README.md` and `PROBER_SPECIFICATION.md` with the new Cloud Scheduler parameters, CLI usage, environment variables table, and standalone trigger examples
- [ ] Task: Run end-to-end regression validation on Go test suite and deployment scripts
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
