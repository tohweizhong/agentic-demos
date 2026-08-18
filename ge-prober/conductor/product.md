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

### 🎯 Phase 2: No-Code Agents & Agent Designer Probing (Near-Term)
1. **Invoke Built No-Code Agents**:
   - Probe execution of pre-configured, custom no-code enterprise agents in the Gemini Enterprise app.
   - Verify tool dispatch, system prompt adherence, and response quality.
2. **Agent Designer Conversational Creation Probe**:
   - Probe the interactive chat interface of the **Agent Designer** to verify that an agent can be defined and created conversationally (e.g. prompt synthesis, tool binding, and draft generation).

### 🧠 Phase 3: Gemini Enterprise Memory & Personalization Probing (Near-Term)
1. **Save to Memory Verification**:
   - Probe the GE app memory feature by saving structured enterprise user profile attributes (e.g., *"I am a Customer Engineer at Google Cloud"*).
2. **Recall & Context Utilization**:
   - Probe subsequent queries to verify that stored user memory is correctly retrieved and incorporated into downstream reasoning and response generation.
3. **Memory Update & Deletion**:
   - Probe updating and purging stored memory entries to ensure data privacy and freshness.

### 🚀 Phase 4: Extended Observability & Webhook Dispatch (Future)
- Native Google Chat & Slack webhook dispatch for immediate incident alerts.
- BigQuery latency and TTFT telemetry streaming for Grafana/Looker Studio dashboards.
- Multi-region synthetic prober execution (`us-central1`, `europe-west1`, `asia-southeast1`).
