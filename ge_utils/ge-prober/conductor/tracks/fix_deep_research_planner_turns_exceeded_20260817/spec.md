# Specification: Fix Deep Research PLANNER_TURNS_EXCEEDED Error

## Problem Statement
When running on Cloud Run, `ge-prober` failed on the Deep Research probe (`smoke_deep_research_02`) with:
```
HTTP 500: [{
  "error": {
    "code": 500,
    "message": "Too many planner turns for one request. Limit: 10.",
    "status": "INTERNAL",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.ErrorInfo",
        "reason": "PLANNER_TURNS_EXCEEDED",
        "domain": "discoveryengine.googleapis.com"
      }
    ]
  }
}]
```
This caused the Cloud Run container to exit with code 1.

## Root Cause
When `agentsSpec: { agentSpecs: [{ agentId: "deep_research" }] }` is supplied without explicit `toolsSpec` bindings, the Deep Research orchestrator attempts to resolve internal retrieval tools on Turn 1. Without explicit data store and web search scopes, it receives an empty response and replays the agent turn until `kMaxPlannerTurns = 10` is exhausted.

## Remediation Plan
1. Update `BuildStreamAssistRequest` in `ge-prober/client.go` to construct `toolsSpec` containing:
   - `vertexAiSearchSpec.dataStoreSpecs`: full resource paths for all configured engine data stores.
   - `webGroundingSpec`: `{}` for public web grounding.
2. Update unit tests in `client_test.go` to assert that `toolsSpec` is attached when `grounding_type` is `deep_research_agent`.
3. Verify local execution passes cleanly.
4. Redeploy container image to Cloud Run Job `ge-prober-daily` and execute on Cloud Run to verify 4/4 passing probes and exit code 0.

## Acceptance Criteria
- [ ] `client.go` passes `toolsSpec` (data stores + web grounding) alongside `agentsSpec` for `deep_research_agent`.
- [ ] 100% unit tests pass (`go test -v ./...`).
- [ ] Cloud Run Job `ge-prober-daily` passes all 4 probes and terminates with exit code 0.
