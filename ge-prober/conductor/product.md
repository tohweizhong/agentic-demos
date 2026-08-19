# Product Definition — Gemini Enterprise Prober (`ge-prober`)

## Overview
`ge-prober` is a simple, lightweight daily synthetic prober and regression testing suite deployed on Google Cloud Run. Scheduled via Cloud Scheduler, it executes a curated set of smoke tests once or twice per day to measure Time to First Token (TTFT), track error rates, evaluate semantic quality with Vertex AI LLM-as-a-Judge, and verify Gemini Enterprise app stability and connector health.

---

## Core Value Proposition & Objectives
1. **Connector & App Vitality**: Detects service degradation, breaking API changes, or authentication failures across Gemini Enterprise and enterprise data connectors (starting with Google Drive).
2. **Deterministic Latency Telemetry**: Accurately tracks **Time to First Token (TTFT)** and total response latency across standard test queries.
3. **Lean & Self-Contained**: Executes on Google Cloud Run via Cloud Scheduler with zero interactive overhead ($0 idle compute).
4. **Automated Semantic Validation**: Evaluates answer faithfulness, contract fulfillment, and refusal detection via Vertex AI LLM-as-a-Judge (`gemini-2.5-flash`).
5. **Actionable Alerts**: Produces structured JSON test reports and automated Cloud Monitoring email alerts on probe failures.

---

## Core Scenarios Tested (Current Baseline)
- **Google Drive Connector Grounding (Primary Focus)**:
  - **Query**: `"Tell me about the helicopter racing league"`
  - **Connectors**: Google Drive enabled (Google Search disabled, SharePoint disabled).
  - **Expected Behavior**: Validates authentication and connector tool routing, retrieves internal Google Drive document excerpts, and returns a grounded response with citations.
- **Deep Research Agent**: Validates multi-step research plan generation and synthesis.
- **Gemini Notebook Integration**: Validates enterprise notebook source Q&A and artifact generation.
- **Web Grounding**: Validates public web search grounding and real-time fact retrieval.

---

## Architectural Insights & Authentication Foundations

### 1. Delegated Permissions vs. Machine Identities (EUC vs. Service Account)
- **End-User Credentials (EUC)**: When querying federated connectors (e.g., SharePoint, Jira, Salesforce), Gemini Enterprise's `DataConnectorService` requires an End-User Credential (`ya29...` user token) because vaulted 3rd-party OAuth refresh tokens are strictly indexed by the caller's Google Identity (Gaia ID / WIF subject).
- **Service Account (ADC)**: Background compute service accounts lack interactive 3P consent sessions in `DataConnectorService`, causing calls to 3P connectors to return 0 results, refusals, or `AUTH_REQUIRED` stream payloads ("Broken Delegation" / "Confused Deputy").

### 2. First-Party (1P) Google Workspace vs. Third-Party (3P) Connectors
| Dimension | Third-Party (SharePoint, Jira, Salesforce) | First-Party Google Workspace (Google Drive, Gmail) |
| :--- | :--- | :--- |
| **Identity Namespace** | Heterogeneous (External IDs / Entra GUIDs) | Unified (Native Google Cloud Identity / Gaia) |
| **Initial Consent** | Interactive 3P OAuth consent popup required | Zero interactive 3P consent required (Native 1P auth / 3LO) |
| **Token Brokering** | `DataConnectorService` vaults & refreshes 3P tokens | Direct Google-internal authorization |
| **ACL Evaluation** | Ingested ACLs or real-time Microsoft Graph evaluation | Native Google Drive ACLs and Google Groups |

### 3. API Selection: `StreamAssist` (FiberDag) vs. `Assist`
- **FiberDag Runtime**: `AssistantService.StreamAssist` executes queries through a Directed Acyclic Graph (DAG) runtime with dynamic intent classification (`query_classifier` node), query reformulation / DRIP (`query_rewriter` node), and Manta tool selector (`MantaSkillSelector`).
- **Prober Target**: `ge-prober` exclusively targets `StreamAssist` to accurately benchmark Time to First Token (TTFT), trace streamed chunk progression, and validate true production tool dispatch.

### 4. Headless Auth Patterns for Synthetic Probing
1. **Application Default Credentials (ADC)**: Direct service account authentication for Web Grounding, Deep Research Agent, Gemini Notebook, Vertex AI LLM Judge, and ingested data stores.
2. **Headless OAuth 2.0 Refresh Token Pattern (Non-WIF)**: A dedicated synthetic test user (e.g., `prober-robot@domain.com`) whose Google OAuth refresh token is securely vaulted in GCP Secret Manager. At runtime, Cloud Run exchanges the refresh token for a fresh EUC token without human intervention.
3. **Workforce Identity Federation (WIF) with Entra ID**: Exchanging Entra ID ROPC tokens at Google Cloud STS (`sts.googleapis.com`) for federated Google access tokens.

### 5. Error Taxonomy & Stream Failure Modes
- **Transport / API Errors**: Non-200 HTTP codes (401, 403, 500, 503).
- **Planner Errors**: `PLANNER_TURNS_EXCEEDED`, missing tools, or query timeout.
- **`AUTH_REQUIRED` Stream State**: Emitted when vaulted 3P tokens expire or are revoked, accompanied by an `authorizationUri`. Triggers dedicated alerts and token re-consent runbooks.
- **Silent Refusal / Ungrounded Fallback**: Model produces a generic completion or refusal without triggering connector retrieval; detected and failed by Vertex AI LLM-as-a-Judge semantic contract verification.

---

## Feature Roadmap

### ✅ Phase 1: Core Foundation & Synthetic Probing (Completed)
- Statically compiled Go binary in minimal Distroless container.
- Automated Cloud Run Job execution via Cloud Scheduler cron.
- Automated Cloud Monitoring log-metric alerting with email dispatch.
- Fully parameterized bash deployment scripts (`deploy_job.sh`).

### ✅ Phase 2: Verbose Cloud Logging & Real-Time Stream Tracing (Completed)
- **Formatted Probe Header & Query**: Output clear probe markers for each test case matching Cloud Run task logs.
- **Line-by-Line Response Tracing**: Emit Gemini Enterprise streamed chunks and markdown response line-by-line into Cloud Run Log Explorer.
- **Stream Performance & Completion Metric**: Real-time TTFT and total latency banners.
- **Execution Suite Summary**: Clean, formatted execution summary table (`📊 TEST SUITE EXECUTION SUMMARY`).

### ✅ Phase 3: Vertex AI LLM-as-a-Judge Semantic Evaluation (Completed)
- Integrated Vertex AI Gemini (`gemini-2.5-flash`) as an automated judge.
- Rubric scoring (1-5), refusal detection (`detected_refusal_or_unconnected`), and stream evaluation logs.
- Test suite summary with semantic pass rates alongside functional pass rates.

### ✅ Phase 4: Expanded Multi-Probe Suite: Google Drive, Deep Research & Web Grounding (Completed)
- **Multi-Probe Test Catalog**: Configured authentic queries for 1P Google Drive (`"Tell me about the helicopter racing league"`), Deep Research Agent (`"Project management methodologies"`), and Web Grounding (`"What are the latest announced Google Cloud Singapore regional capabilities this year?"`).
- **Authentication & Tool Routing**: Validated caller EUC token resolution, service account discovery (`ge-regression-runner-sa`), and appropriate tool/agent routing.
- **Pure Semantic Evaluation**: 100% pure semantic evaluation via Vertex AI Gemini 2.5 Flash judge (zero brittle keyword assertions) with robust prompt instructions for temporal neutrality and separation of API citation metadata vs synthesized text.
- **Automated Cloud Run E2E Verification**: 100% Functional, Semantic, and SLO compliance across all probes in Cloud Run.

### 🔐 Phase 5: Microsoft SharePoint Online & 3P Federated Connectors (Near-Term)
- **Headless EUC OAuth Token Brokering**: Implement Secret Manager Google OAuth refresh token exchange for synthetic user EUC tokens (`ya29...`) to enable `DataConnectorService` 3P token lookup.
- **`AUTH_REQUIRED` Detection & Alerts**: Intercept `auth_required` stream states with dedicated runbook alerts for Microsoft re-consent.
- **SharePoint Canary Site Probing**: Validate security-trimmed document retrieval from dedicated SharePoint sites (`/sites/CanaryProberSite`).

### 📓 Phase 6: NotebookLM Grounding & Trigger Verification (Near-Term)
- Investigate payload configuration and prompt triggers for authentic enterprise NotebookLM assistant tool invocation.
- Refine assertions, citation checks, and grounding metadata verifications for notebook sources.

### 🤖 Phase 7: No-Code Agents & Agent Designer Probing (Near-Term)
- Probe execution of pre-configured custom no-code enterprise agents.
- Probe interactive chat interface of Agent Designer for conversational agent creation.

### 🧠 Phase 8: Gemini Enterprise Memory & Personalization Probing (Near-Term)
- Probe Save, Recall, Update, and Purge of user memory profile context.

### 👥 Phase 9: Multi-Persona ACL Security Trimming & Identity Federation (Near-Term)
- Multi-persona probing (Standard Employee vs. Privileged Manager) to verify connector ACL filtering.
- Support for Workforce Identity Federation (WIF) and Microsoft Entra ID ROPC token exchange.

### 🚀 Phase 10: Extended Observability & Webhook Dispatch (Future)
- Native Google Chat & Slack webhook alerts, BigQuery telemetry export, and multi-region execution.
