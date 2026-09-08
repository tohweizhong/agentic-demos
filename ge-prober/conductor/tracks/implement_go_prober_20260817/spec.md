# Specification: Implement Go Synthetic Prober

## Overview
A lightweight, compiled Go 1.22+ CLI and Google Cloud Run batch job executing the 4 canonical smoke test cases (SharePoint document retrieval, Deep Research Agent, NotebookLM, and Google Web Grounding) against the Discovery Engine `streamAssist` API.

---

## Functional Requirements
1. **Config & Test Case Loading**:
   - Parse `config.json` (Project ID, Region, Engine ID, Timeout, Concurrency) with safe environment overrides.
   - Parse `test_cases/smoke_test_cases.json` with strict schema validation.
2. **Authentication**:
   - Resolve Application Default Credentials (ADC) / Cloud Run Service Account tokens via `golang.org/x/oauth2/google`.
   - Fall back to `GCP_ACCESS_TOKEN` environment variable if present.
3. **Concurrent StreamAssist Client**:
   - Construct HTTP `POST` requests to `https://{location}-discoveryengine.googleapis.com/v1alpha/projects/{project}/locations/{location}/collections/default_collection/engines/{engine}/assistants/default_assistant:streamAssist`.
   - Format `toolsSpec` dynamically for `vertexAiSearchSpec` (SharePoint/OneDrive data stores) and `webGroundingSpec`.
   - Stream and parse response JSON chunks asynchronously using goroutines and worker pools.
4. **Telemetry & SLO Evaluation**:
   - Measure **TTFT** (latency to first non-thought text token), **TTFA**, and **TTLT** (total roundtrip latency).
   - Evaluate keyword assertions, verify absence of forbidden error codes (`401`, `403`, `500`, `503`, `USER_PROJECT_DENIED`).
   - Flag SLO breaches when `TTFT > max_ttft_ms` or `TTLT > max_ttlt_ms`.
5. **Output & Reporting**:
   - Display formatted terminal progress with status icons (`✅`, `⚠️`, `❌`).
   - Export structured JSON telemetry report to a specified output path.
6. **Containerization**:
   - Multi-stage Dockerfile (`golang:1.22-alpine` builder $\rightarrow$ `gcr.io/distroless/static-debian12` runner) resulting in a minimal, secure container image (<20MB).

---

## Non-Functional Requirements
- Memory consumption $\le 20\text{MB}$.
- Zero external CGo dependencies.
- Sub-second binary cold start time on Cloud Run.

---

## Acceptance Criteria
- [ ] 100% unit test coverage for config parsing, auth resolution, mock streaming, and SLO evaluation (`go test -v ./...`).
- [ ] Successful execution against live Discovery Engine endpoint with `--concurrency 4`.
- [ ] Successful Docker container build and clean dry-run execution.
