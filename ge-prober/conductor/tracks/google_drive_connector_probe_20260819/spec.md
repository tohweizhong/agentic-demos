# Specification: Google Drive Connector Grounding & Authentication Probe

## Overview
Implement and configure a dedicated probe for the **1P Google Workspace Google Drive Connector** within `ge-prober`. The objective is to verify authentication (`admin@weizhongt.altostrat.com`) and ensure `StreamAssist` routes queries to Google Drive, retrieves internal enterprise documents, returns source citations, and produces a grounded response without auth errors, permission blocks, or ungrounded refusals.

## Functional Requirements

### 1. Single Focused Test Case (`test_cases/smoke_test_cases.json`)
- Configure `smoke_gdrive_01` replacing legacy SharePoint placeholder:
  - **ID:** `smoke_gdrive_01`
  - **Module:** `1P Google Workspace Connectors`
  - **Subsystem:** `google_drive`
  - **Title:** `Google Drive Document Retrieval`
  - **Query:** `"Tell me about the helicopter racing league"`
  - **Grounding Type:** `google_drive`
  - **Expected Behavior:** Queries the Google Drive 1P connector, retrieves relevant documents from the connected Drive knowledge base, and returns a grounded summary with source citations.
  - **Semantic Contract:** *"The response must retrieve and synthesize factual information about the helicopter racing league from internal Google Drive documents. It must NOT be a refusal message, an error, or a generic ungrounded completion."*
  - **Zero Keyword Matching:** Pure semantic evaluation (`must_contain_keywords: []`).
  - **Assertions:**
    - `must_have_citations`: `true`
    - `forbidden_errors`: `["401", "403", "500", "503", "USER_PROJECT_DENIED", "AUTH_REQUIRED"]`

### 2. Tool Specification & Payload Builder (`client.go`, `types.go`)
- Support `grounding_type: "google_drive"` in `BuildStreamAssistRequest`:
  - Route directly to the Google Drive 1P connector tool while keeping external search and 3P connectors disabled.
  - Extract Google Drive citation URLs and metadata from `StreamAssistResponse` chunks.

### 3. Authentication & Identity (`auth.go`, `deploy_job.sh`)
- Seamlessly resolve user access token for `admin@weizhongt.altostrat.com` (from local ADC or `GCP_ACCESS_TOKEN`).
- Ensure Discovery Engine correctly evaluates Drive permissions without `401`/`403` or `AUTH_REQUIRED`.
- Set default scheduler/invocation service account in `deploy_job.sh` to `ge-regression-runner-sa@weizhong-project03.iam.gserviceaccount.com`.

### 4. 100% LLM-as-a-Judge Evaluation (`judge.go`)
- Use Vertex AI `gemini-2.5-flash` to evaluate the response against the semantic contract (detecting ungrounded fallbacks or refusals, score $\ge 4/5$).

## Acceptance Criteria
- [ ] `client_test.go` and `config_test.go` validate `google_drive` payload construction and test case schema.
- [ ] `smoke_test_cases.json` includes `smoke_gdrive_01`.
- [ ] `./ge-prober` executes `smoke_gdrive_01` locally and passes both functional assertions and LLM Judge evaluation.
- [ ] `scripts/e2e_cloud_pipeline.sh` executes the suite in Cloud Run and verifies dual log persistence.
