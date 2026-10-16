# Specification: Update Deep Research and Gemini Notebook Probes

## Overview
Align the Deep Research and Gemini Notebook smoke test probe implementations with the exact console API contracts shown in the user screenshots:
1. **Deep Research Agent (Screenshot 1)**: Invokes the dedicated Deep Research agent via `agentsSpec: { agentSpecs: [{ agentId: "deep_research" }] }` with the canonical query `"Project management methodologies"`.
2. **Gemini Notebook (Screenshot 2)**: Queries the `"Model Armor: AI Safety & Security"` notebook directly via natural language prompt without injecting external `toolsSpec.vertexAiSearchSpec` data store bindings.

---

## Technical Specifications

### 1. Deep Research (`deep_research_agent`)
- **Query**: `"Project management methodologies"`
- **Request Payload**:
  ```json
  {
    "query": {
      "text": "Project management methodologies"
    },
    "agentsSpec": {
      "agentSpecs": [
        { "agentId": "deep_research" }
      ]
    }
  }
  ```
- **Expected Behavior**: Backend invokes Deep Research agent strategy, generates `RESEARCH_PLAN` / `Research details` accordions with numbered research sub-questions, and returns session token for the "Start research" action.
- **Assertions**:
  - `must_contain_keywords`: `["Research Plan", "Project Management", "Methodology"]`
  - `forbidden_errors`: `["401", "403", "500", "503", "INVALID_ARGUMENT"]`
  - `slo_targets`: `max_ttft_ms: 10000.0`, `max_ttlt_ms: 25000.0`

### 2. Gemini Notebook (`gemini_notebook`)
- **Query**: `"What is Model Armor's overarching purpose and operational approach to AI protection?"`
- **Request Payload**:
  ```json
  {
    "query": {
      "text": "What is Model Armor's overarching purpose and operational approach to AI protection?"
    }
  }
  ```
- **Expected Behavior**: Direct query against notebook knowledge base without external `toolsSpec.vertexAiSearchSpec`, returning grounded summary citing security policies and proactive screening.
- **Assertions**:
  - `must_contain_keywords`: `["Model Armor", "safety", "security"]`
  - `forbidden_errors`: `["401", "403", "500", "503"]`
  - `slo_targets`: `max_ttft_ms: 15000.0`, `max_ttlt_ms: 30000.0`

---

## Acceptance Criteria
- [ ] Go types (`AgentSpec`) updated to serialize `agentId`.
- [ ] `BuildStreamAssistRequest` in `client.go` properly builds `agentsSpec` for `deep_research_agent` and bare query for `gemini_notebook`.
- [ ] 100% unit test pass rate (`go test -v ./...`).
- [ ] Live execution of `./ge-prober` passes 4/4 probes.
- [ ] Cloud Run Job `ge-prober-daily` updated via `bash deploy_job.sh` and verified.
