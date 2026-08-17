# Product Definition — Gemini Enterprise Prober (`ge-prober`)

## Overview
`ge-prober` is a simple, lightweight daily smoke test prober deployed on Google Cloud Run. Authenticating via standard service account and Google Cloud API credentials, it executes a curated set of selected smoke test cases once per day to measure Time to First Token (TTFT), track error rates, and verify Gemini Enterprise app stability.

---

## Core Value Proposition & Objectives
1. **App Stability & Vitality**: Detects service degradation, breaking API changes, or unexpected error bursts across Gemini Enterprise.
2. **Deterministic Latency Telemetry**: Accurately tracks **Time to First Token (TTFT)** and total response latency across standard test queries.
3. **Lean & Self-Contained**: Executes daily on Google Cloud Run via Cloud Scheduler with zero interactive overhead.
4. **Actionable Alerts**: Produces structured JSON test reports and logs for monitoring and dashboards.

---

## Core Scenarios Tested
- **SharePoint & Enterprise Connectors**: Verifies document retrieval and grounding citations.
- **Deep Research Agent**: Validates multi-step research plan generation and synthesis.
- **NotebookLM Integration**: Validates enterprise notebook source Q&A and artifact generation.
- **Web Grounding**: Validates public web search grounding and real-time fact retrieval.
