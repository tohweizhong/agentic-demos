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

## Architectural Insights & System Topology

### 1. Two-Tier Hybrid Architecture (C++ AssistantServer & Python DolphinServer)
Gemini Enterprise (Agentspace / Discovery Engine) implements a two-tier hybrid architecture:
```
Client / Prober (HTTP/gRPC) ──> ESF (IAM, Quota, Rate Limiting)
                                       │
                                       ▼
                 ┌──────────────────────────────────────────────┐
                 │    Stateful C++ Layer (AssistantServer)      │
                 │ • Session Management (Spanner RichSession)   │
                 │ • Context File Storage (GCS / Bigstore)      │
                 │ • Auth Token Brokering (DataConnectorService)│
                 │ • Pluggable Strategy Selector & Dispatcher   │
                 └──────────────────────┬───────────────────────┘
                                        │ (StreamRunAgent RPC)
                                        ▼
                 ┌──────────────────────────────────────────────┐
                 │     Stateless Reasoning Tier (DolphinServer) │
                 │ • Python Agent Development Kit (ADK)         │
                 │ • Dynamic Agent Tree (Root -> Sub-Agents)    │
                 │ • Query Rewriting (QueryRewriteAgent)        │
                 │ • Local Go MCP Server Proxy                  │
                 └──────────────────────┬───────────────────────┘
                                        │ (gRPC)
                                        ▼
                 ┌──────────────────────────────────────────────┐
                 │ Business Application Platform (BAP Gateway)  │
                 │ • Standard Connectors (MST - Enterprise Ed.) │
                 │ • Managed Connectors (MT - Biz Edition)      │
                 │ • 3P SaaS Integrations (SharePoint, Jira)   │
                 └──────────────────────────────────────────────┘
```

### 2. Delegated Permissions vs. Machine Identities (EUC vs. Service Account)
- **End-User Credentials (EUC)**: When querying federated connectors (e.g., SharePoint, Jira, Salesforce), Gemini Enterprise's `DataConnectorService` requires an End-User Credential (`ya29...` user token) because vaulted 3rd-party OAuth refresh tokens are strictly indexed by the caller's Google Identity (Gaia ID / WIF subject) in Cloud Spanner.
- **Service Account (ADC)**: Background compute service accounts lack interactive 3P consent sessions in `DataConnectorService`, causing calls to 3P connectors to return 0 results, refusals, or `AUTH_REQUIRED` stream payloads ("Broken Delegation" / "Confused Deputy").

### 3. Connector Deployment Models & Toolspec Management
- **BAP Connector Types**:
  - **Standard Connectors (MST)**: Multi-Single-Tenant dedicated deployments for Enterprise Edition (`google3/google/cloud/connectors/v1/connectors_service.proto`).
  - **Managed Connectors (MT)**: Multi-Tenant shared deployments for Biz Edition.
- **Unified GE MCP Server & Toolspecs**:
  - Connectors expose actions and search capabilities via **Model Context Protocol (MCP)**.
  - A local Go MCP proxy inside the Python server forwards `tools/call` RPCs directly to the BAP Gateway with the user's OAuth credentials.
  - Toolspecs are snapshot and periodically synchronized against `google3/cloud/ml/discoveryengine/dolphin/agent_configs/tool_specs/` for drift detection.

### 4. Pluggable `AssistantStrategy` Implementations
- **`CorePlannerStrategy` (C++)**: Native "plan-execute-observe" reasoning loop managed by the C++ Orchestrator with pre-emptive parallel search and ECHO mode optimizations.
- **`DolphinStrategy` (Python)**: Hierarchical agent-as-a-tool reasoning tree managed by ADK.
- **`ResearchAssistantStrategy`**: Multi-step Deep Research plan generation followed by iterative Grounded Generation.
- **`DirectAgentAssistantStrategy`**: Direct execution of user-configured No-Code agents (strictly constrained to a subset of the parent assistant's tools and data sources).

### 5. Grounding & Citation Architecture
- **Vertex Grounding API**: Grounding citation metadata is extracted by a post-processor at the conclusion of the stream.
- **Evaluation Invariant**: Probers must separate structured JSON citation metadata verification (`must_have_citations`) from pure semantic text quality evaluation by the LLM Judge.

---

## Feature Roadmap

### ✅ Phase 1: Core Foundation & Synthetic Probing (Completed)
- Statically compiled Go binary in minimal Alpine container.
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
- Prompt guidelines for temporal neutrality and separation of API citations vs synthesized text.

### ✅ Phase 4: Expanded Multi-Probe Suite: Google Drive, Deep Research & Web Grounding (Completed)
- **Multi-Probe Test Catalog**: Configured authentic queries for 1P Google Drive (`"Tell me about the helicopter racing league"`), Deep Research Agent (`"Project management methodologies"`), and Web Grounding (`"What are the latest announced Google Cloud Singapore regional capabilities this year?"`).
- **Authentication & Tool Routing**: Validated caller EUC token resolution, service account discovery (`ge-regression-runner-sa`), and appropriate tool/agent routing.
- **Pure Semantic Evaluation**: 100% pure semantic evaluation via Vertex AI Gemini 2.5 Flash judge with zero brittle keyword assertions.
- **Automated Cloud Run E2E Verification**: 100% Functional, Semantic, and SLO compliance across all probes in Cloud Run.

### 🔐 Phase 5: Microsoft SharePoint Online & 3P Federated Connectors (Near-Term)
- **Headless EUC OAuth Token Brokering**: Implement Secret Manager Google OAuth refresh token exchange for synthetic user EUC tokens (`ya29...`) to enable `DataConnectorService` 3P token lookup.
- **BAP Standard Connector (MST) Integration**: Validate document search across SharePoint Online data stores (`vertexAiSearchSpec.dataStoreSpecs`).
- **PKCE & `AUTH_REQUIRED` Interception**: Detect `auth_required` stream states and trigger automated runbook alerts for Microsoft OAuth re-consent.

### 📓 Phase 6: Gemini Notebook Enterprise (NotebookLM) Probing (Near-Term)
- **`QueryNotebookTool` Invocation**: Verify assistant tool routing to user-attached notebook knowledge bases.
- **RAG Context Window & Chunk Grounding**: Validate citation metadata and source chunk assertions for notebook sources.

### 🤖 Phase 7: Custom No-Code Enterprise Agents & Agent Designer Probing (Near-Term)
- **`DirectAgentAssistantStrategy` Invariant Verification**: Probe execution of custom agents via `agentsSpec: [{agentId: "..."}]` and ensure data store / tool scoping constraints are enforced.
- **Agent Designer Conversational Creation**: Probe the `create_conversational_agent` meta-tool.

### ⚡ Phase 8: Quick Search Fast-Path & HITL Mutating Actions Probing (Near-Term)
- **Quick Search Low-Latency Fast-Path**: Validate simple queries triggering `quick_search=True` (bypassing multi-turn reasoning loops for minimal latency).
- **Mutating Actions & HITL State**: Probe write tools (e.g. Jira issue creation, Calendar events) to verify that `action_invocation` confirmation events are emitted to the client before execution.

### 🧠 Phase 9: Gemini Enterprise Memory & Personalization Probing (Near-Term)
- Probe Save, Recall, Update, and Purge of user memory profile context across conversation turns.

### 👥 Phase 10: Multi-Persona ACL Security Trimming & Identity Federation (Near-Term)
- Multi-persona probing (Standard Employee vs. Privileged Manager) to verify connector ACL filtering and prevent data leakage.
- Support for Workforce Identity Federation (WIF) and Microsoft Entra ID ROPC token exchange.

### 🚀 Phase 11: Extended Observability & BigQuery Telemetry (Future)
- Stream continuous probe telemetry into BigQuery for Looker Studio latency percentiles and failure heatmaps.
- Native Google Chat & Slack interactive webhook cards on probe regressions.
