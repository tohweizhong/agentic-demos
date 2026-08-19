# Product Definition — Gemini Enterprise Prober (`ge-prober`)

## Overview
`ge-prober` is a simple, lightweight daily smoke test prober deployed on Google Cloud Run. Authenticating via standard service account and Google Cloud API credentials, it executes a curated set of selected smoke test cases once or twice per day to measure Time to First Token (TTFT), track error rates, and verify Gemini Enterprise app stability.

---

## Core Value Proposition & Objectives
1. **App Stability & Vitality**: Detects service degradation, breaking API changes, or unexpected error bursts across Gemini Enterprise.
2. **Deterministic Latency Telemetry**: Accurately tracks **Time to First Token (TTFT)** and total response latency across standard test queries.
3. **Lean & Self-Contained**: Executes on Google Cloud Run via Cloud Scheduler with zero interactive overhead ($0 idle compute).
4. **Actionable Alerts**: Produces structured JSON test reports and automated Cloud Monitoring email alerts on probe failures.

---

## Core Scenarios Tested (Current Baseline)
- **SharePoint & Enterprise Connectors**: Verifies document retrieval and grounding citations.
- **Deep Research Agent**: Validates multi-step research plan generation and synthesis.
- **NotebookLM Integration**: Validates enterprise notebook source Q&A and artifact generation.
- **Web Grounding**: Validates public web search grounding and real-time fact retrieval.

---

## Feature Roadmap

### ✅ Phase 1: Core Foundation & Synthetic Probing (Completed)
- Statically compiled Go binary in minimal Distroless container.
- Automated Cloud Run Job execution via Cloud Scheduler cron.
- Automated Cloud Monitoring log-metric alerting with email dispatch.
- Fully parameterized bash deployment scripts (`deploy_job.sh`).

### 📊 Phase 2: Verbose Cloud Logging & Real-Time Stream Tracing (Immediate / In Progress)
- **Formatted Probe Header & Query**: Output clear probe markers for each test case matching Cloud Run task logs:
  - Probe Header: `[X/N] 🔎 [<grounding_type>] <test_case_id>` (e.g. `[4/4] 🔎 [sharepoint] sharepoint_01`)
  - Query Display: `📜 Query: "<query_text>"` (e.g. `📜 Query: "Search for files about FormSG in our SharePoint site."`)
- **Line-by-Line Response Tracing**:
  - Response Header: `💬 Response:`
  - Emit Gemini Enterprise streamed chunks and complete response line-by-line into standard output so that markdown headings (`### 📌 Primary Document`), bullet points, citations, and grounded document URLs (`* **[Doc.pdf](https://...)**`) are rendered as distinct, readable entries in Cloud Run Log Explorer.
- **Stream Performance & Completion Metric**:
  - Completion Banner: `✅ Stream Done (TTFT: X.X ms | Total: Y.Y ms)`
- **Execution Suite Summary**:
  - Clean, formatted execution summary table (`📊 TEST SUITE EXECUTION SUMMARY`) at the conclusion of the probe run.

### 🤖 Phase 3: Vertex AI LLM-as-a-Judge Semantic Evaluation (Near-Term)
1. **Automated Semantic & Faithfulness Evaluation**:
   - Integrate Vertex AI Gemini (e.g., `gemini-2.5-flash`) as an automated judge to evaluate probe response quality, hallucination detection, and grounding faithfulness beyond deterministic keyword matching.
2. **Structured Scoring & Cloud Telemetry**:
   - Provide rubric scoring (answer relevance, grounding fidelity, citation precision) and stream evaluation logs (`⚖️ Evaluating N test results with Vertex AI LLM Judge (gemini-2.5-flash)...`) into Cloud Run logs and JSON reports.

### 🎯 Phase 4: NotebookLM Grounding & Trigger Verification (Near-Term)
- **Investigate & Resolve Payload Configuration**: Investigate and resolve the NotebookLM probe payload configuration so that the enterprise NotebookLM knowledge base and assistant service are authentically triggered and grounded, rather than falling back to generic ungrounded completions.
- **Refine Assertions & Citation Checks**: Tailor assertions, citation checks, and grounding metadata verifications specifically for NotebookLM source document answers.

### 🤖 Phase 5: No-Code Agents & Agent Designer Probing (Near-Term)
1. **Invoke Built No-Code Agents**:
   - Probe execution of pre-configured, custom no-code enterprise agents in the Gemini Enterprise app.
   - Verify tool dispatch, system prompt adherence, and response quality.
2. **Agent Designer Conversational Creation Probe**:
   - Probe the interactive chat interface of the **Agent Designer** to verify that an agent can be defined and created conversationally (e.g. prompt synthesis, tool binding, and draft generation).

### 🧠 Phase 6: Gemini Enterprise Memory & Personalization Probing (Near-Term)
1. **Save to Memory Verification**:
   - Probe the GE app memory feature by saving structured enterprise user profile attributes (e.g., *"I am a Customer Engineer at Google Cloud"*).
2. **Recall & Context Utilization**:
   - Probe subsequent queries to verify that stored user memory is correctly retrieved and incorporated into downstream reasoning and response generation.
3. **Memory Update & Deletion**:
   - Probe updating and purging stored memory entries to ensure data privacy and freshness.

### 🔐 Phase 7: Identity, Access & Multi-Persona Probing (Near-Term)
1. **Dynamic Token Lifecycle & Reusable TokenSource**:
   - Transition from static one-shot token resolution to goroutine-safe, auto-refreshing `oauth2.TokenSource` for sustained probe executions.
2. **Service Account Impersonation & Multi-Tenant Isolation**:
   - Support CLI/config-driven service account impersonation (`--impersonate-service-account`) to probe access boundaries and tenant isolation across multiple GCP projects.
3. **Document-Level Security & ACL Enforcement Probing**:
   - Probe queries across distinct user personas (e.g. standard employee vs. privileged manager) to verify connector-level ACL filtering, SCIM identity mappings, and SharePoint/Drive security trimming.

### 🚀 Phase 8: Extended Observability & Webhook Dispatch (Future)
- Native Google Chat & Slack webhook dispatch for immediate incident alerts.
- BigQuery latency and TTFT telemetry streaming for Grafana/Looker Studio dashboards.
- Multi-region synthetic prober execution (`us-central1`, `europe-west1`, `asia-southeast1`).
