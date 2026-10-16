# Implementation Plan: Implement Go Synthetic Prober

## Phase 1: Go Project Setup, Models & Config Loading (TDD)
- [x] Task: Initialize Go module (`go.mod`) with oauth2 and google dependencies.
- [x] Task: Define Go data models (`types.go`) for `Config`, `TestCase`, `SLOTargets`, `Assertions`, and `ProbeResult`.
- [x] Task: [TDD] Write unit tests (`config_test.go`) for configuration loading, test case parsing, and default fallbacks.
- [x] Task: Implement configuration & test case loader (`config.go`).
- [x] Task: Phase 1 Verification & Checkpoint (Run `go test ./...` and verify green passes).

## Phase 2: Token Resolution & StreamAssist Client (TDD)
- [x] Task: [TDD] Write unit tests (`auth_test.go`) for ADC token source resolution and environment fallback.
- [x] Task: Implement authentication provider (`auth.go`).
- [x] Task: [TDD] Write unit tests (`client_test.go`) with mock HTTP server simulating StreamAssist chunked SSE responses.
- [x] Task: Implement StreamAssist HTTP client & streaming chunk parser (`client.go`).
- [x] Task: Phase 2 Verification & Checkpoint (Run `go test ./...` and verify green passes).

## Phase 3: Prober Concurrency Engine & Assertions (TDD)
- [x] Task: [TDD] Write unit tests (`prober_test.go`) for goroutine worker pool, keyword matching, forbidden error detection, and SLO latency evaluation.
- [x] Task: Implement concurrency engine, timer calculations, and assertion evaluator (`prober.go`).
- [x] Task: Implement CLI entrypoint (`main.go`) with flags, terminal output, and JSON export.
- [x] Task: Phase 3 Verification & Checkpoint (Run `go test ./...` and verify green passes).

## Phase 4: Docker Containerization & Cloud Run Runbook
- [x] Task: Create multi-stage `Dockerfile` (`golang:1.22-alpine` builder -> `gcr.io/distroless/static-debian12` runner).
- [x] Task: Test local Docker container build & execution.
- [x] Task: Add Cloud Run Job deployment script (`deploy_job.sh`).
- [x] Task: Final Track Verification & Checkpoint.
