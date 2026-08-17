# Technology Stack — Gemini Enterprise Prober (`ge-prober`)

## Core Runtime & Architecture
- **Language**: Go 1.22+
- **Execution Model**: Compiled single static binary with concurrent goroutines for parallel probe execution.
- **Footprint**: Minimal memory footprint (~15MB RAM) and near-instant cold start (<100ms).

---

## Libraries & Protocols
- **HTTP & Streaming**: Go standard library `net/http`, `bufio.Scanner`, `encoding/json`.
- **Concurrency**: `sync.WaitGroup`, `golang.org/x/sync/errgroup`.
- **Authentication**: `golang.org/x/oauth2/google` (automatic Application Default Credentials resolution for Cloud Run Service Account).
- **Configuration**: JSON file parsing (`config.json`, `smoke_test_cases.json`).

---

## Containerization & Deployment
- **Container Build**: Multi-stage Docker build (`golang:1.22-alpine` builder $\rightarrow$ `gcr.io/distroless/static-debian12` runner).
- **Orchestration**: Google Cloud Run Job (Daily scheduled batch execution via Cloud Scheduler).
- **Telemetry**: Structured stdout JSON logging to Google Cloud Logging & Monitoring.
