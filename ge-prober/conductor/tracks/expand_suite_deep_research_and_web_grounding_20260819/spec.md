# Specification: Expand Prober Suite with Deep Research and Web Grounding

## Overview
Expand `ge-prober` from a single Google Drive probe into a robust 3-probe synthetic smoke test suite encompassing:
1. **1P Google Drive Connector Grounding** (`smoke_gdrive_01`)
2. **Deep Research Autonomous Agent** (`smoke_deep_research_02`)
3. **Public Web Grounding** (`smoke_web_grounding_03`)

All test cases enforce **100% pure semantic evaluation via Vertex AI LLM-as-a-Judge** (`gemini-2.5-flash`), eliminating brittle keyword dependencies while asserting strict refusal detection, contract fulfillment, and citation presence where required.

## Functional Requirements

### 1. `smoke_gdrive_01` (1P Google Workspace Google Drive)
- **Query:** `"Tell me about the helicopter racing league"`
- **Grounding Type:** `google_drive`
- **Semantic Contract:** *"The response must synthesize and present factual information about the helicopter racing league retrieved from Google Drive documents. It must NOT be a refusal message, an error, or an ungrounded generic answer."*
- **Assertions:** `must_contain_keywords: []`, `must_have_citations: true`, zero `401`/`403`/`AUTH_REQUIRED`.

### 2. `smoke_deep_research_02` (Deep Research Agent)
- **Query:** `"Project management methodologies"`
- **Grounding Type:** `deep_research_agent`
- **Payload:** `agentsSpec: [{agentId: "deep_research"}]`, `toolsSpec: {webGroundingSpec: {}}`
- **Semantic Contract:** *"The response must demonstrate authentic execution of the Deep Research Agent by generating a structured, comprehensive multi-step research plan and in-depth synthesis exploring project management methodologies (such as Agile, Waterfall, Scrum, Kanban, Lean). It must NOT be a shallow one-paragraph answer, a refusal message, or a planner/turns error."*
- **Assertions:** `must_contain_keywords: []`, `must_have_citations: false`, zero `PLANNER_TURNS_EXCEEDED`/`INVALID_ARGUMENT`.

### 3. `smoke_web_grounding_03` (Public Web Grounding)
- **Query:** `"What are the latest announced Google Cloud Singapore regional capabilities this year?"`
- **Grounding Type:** `web_search`
- **Payload:** `toolsSpec: {webGroundingSpec: {}}`
- **Semantic Contract:** *"The response must provide specific, factual regional capabilities announced for Google Cloud Singapore (such as data residency, model availability, or regional ML processing) grounded with factual web search citations."*
- **Assertions:** `must_contain_keywords: []`, `must_have_citations: true`, zero `401`/`403`/`500`/`503`.

## Acceptance Criteria
- [ ] `smoke_test_cases.json` contains all 3 smoke test cases with zero keyword assertions and explicit semantic contracts.
- [ ] Go unit tests (`go test -v ./...`) validate JSON loading and payload builders for all 3 grounding types.
- [ ] Local execution (`./ge-prober -concurrency 4 -verbose`) runs all 3 probes in parallel with 100% functional and semantic pass rate.
- [ ] `scripts/e2e_cloud_pipeline.sh` executes the 3-probe suite on Cloud Run and records dual log artifacts.
