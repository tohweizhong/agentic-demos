# Specification: Generalize Gemini Enterprise Prober Configuration

## Overview
Generalize `ge-prober` so it is fully dynamic, portable, and decoupled from any hardcoded project, engine, or regional parameters. It must support execution across local developer workstations, multi-region GCP environments, Cloud Run Jobs, and CI/CD pipelines.

## Functional Requirements

### 1. 12-Factor Configuration Precedence Hierarchy
Configuration parameters are resolved in the following strict order of priority:
1. **Command-Line Flags** (Explicit overrides)
   - `-project`: Target GCP project ID.
   - `-location` / `-region`: Target Discovery Engine location (`global`, `us`, `eu`, `asia-southeast1`, etc.).
   - `-engine`: Target Engine / App ID.
   - `-assistant`: Assistant ID (defaults to `default_assistant`).
   - `-datastores`: Comma-separated list of Data Store IDs (e.g. `ds1,ds2,ds3`).
   - `-concurrency`: Number of concurrent workers (default: `4`).
   - `-timeout`: Overall timeout in seconds per probe (default: `180`).
   - `-test-cases`: Path to custom test cases JSON file (default: `test_cases/smoke_test_cases.json`).
   - `-output`: Path to export JSON results report (default: `smoke_prober_results.json`).
   - `-config`: Path to custom JSON configuration file (default: `config.json`).
   - `-token`: Direct GCP Access Token override (fallback to ADC / WIF).
2. **OS Environment Variables** (Production Container Runtime)
   - `GCP_PROJECT_ID` or `PROJECT_ID`
   - `GE_LOCATION` or `LOCATION` or `REGION`
   - `GE_ENGINE_ID` or `ENGINE_ID`
   - `GE_ASSISTANT_ID` or `ASSISTANT_ID`
   - `GE_DATA_STORE_IDS` or `DATA_STORE_IDS` (comma-separated or JSON list)
   - `GE_MAX_CONCURRENCY` or `CONCURRENCY`
   - `GE_TIMEOUT_SECONDS` or `TIMEOUT_SECONDS`
   - `GE_TEST_CASES_PATH`
   - `GE_OUTPUT_FILE`
   - `GCP_ACCESS_TOKEN`
3. **Local `.env` File** (Local Developer Emulation)
   - Automatically parsed on startup if `.env` exists in the local working directory (zero external dependencies).
4. **JSON Configuration File** (`config.json`)
   - Structured fallback file.
5. **Built-in Sensible Defaults**
   - Location: `global`
   - Assistant ID: `default_assistant`
   - Concurrency: `4`
   - Timeout: `180`
   - Output File: `smoke_prober_results.json`

### 2. Validation & Error Handling
- Validate that `project_id` and `engine_id` are non-empty after resolving the hierarchy.
- Output clear, actionable error messages with flag/env guidance if required parameters are missing.

## Acceptance Criteria
- [ ] `config.go` implements the 4-tier resolution hierarchy.
- [ ] 100% unit test coverage for config resolution, env overrides, flag parsing, and comma-separated datastore parsing.
- [ ] Prober can be run purely with CLI flags: `./ge-prober -project=my-proj -engine=my-eng -region=global`.
- [ ] Cloud Run Job `deploy_job.sh` supports injecting `PROJECT_ID`, `ENGINE_ID`, `LOCATION`, and `DATA_STORE_IDS` via `--set-env-vars`.
