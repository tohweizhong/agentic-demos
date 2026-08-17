# Implementation Plan: Generalize Gemini Enterprise Prober Configuration

## Phase 1: Configuration Layer & TDD
- [x] Task: Implement zero-dependency `.env` loader and hierarchical config resolver in `config.go`.
- [x] Task: [TDD] Write unit tests in `config_test.go` verifying flag precedence, environment variable precedence, `.env` file parsing, and comma-separated Data Store IDs.
- [x] Task: Verify all unit tests pass with `go test -v ./...`.

## Phase 2: CLI Flags & Main Orchestration
- [x] Task: Update `main.go` with full set of CLI flags (`-project`, `-location`, `-region`, `-engine`, `-assistant`, `-datastores`, `-concurrency`, `-timeout`, `-test-cases`, `-output`, `-token`, `-config`).
- [x] Task: Integrate config validation with user-friendly error diagnostics.
- [x] Task: Update `deploy_job.sh` to support dynamic environment variable injection via `gcloud run jobs deploy --set-env-vars`.
- [x] Task: Create `config.example.json`, `.env.example`, and customer-ready `README.md`.

## Phase 3: Live Verification & Checkpoint
- [x] Task: Test CLI flag overrides locally (e.g. overriding project and concurrency via command line).
- [x] Task: Test environment variable overrides.
- [x] Task: Re-deploy and verify Cloud Run execution with dynamic configuration.
- [x] Task: Final Track Verification & Checkpoint.
