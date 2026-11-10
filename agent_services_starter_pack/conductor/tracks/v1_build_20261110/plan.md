# Track plan: version 1 build (v1_build_20261110)

## Phase 1: Code and offline tests

- [x] Task: Settings helper (`config.py`)
  - [x] Write tests for the `.env` reader and writer
  - [x] Write the code
- [x] Task: Agent (`agent/agent.py`)
  - [x] Write tests: tools, callback, custom span, trace ID in the tool result
  - [x] Write the code
- [x] Task: Sample helpers (`samples/common.py`)
  - [x] Write tests: event text, function responses, Cloud Trace link, memory scope
  - [x] Write the code
- [x] Task: `deploy.py`, the three samples, `bootstrap.sh`, and `cleanup.sh`
- [x] Task: README with the run steps
- [x] Task: Phase Verification and Checkpoint (Refer to workflow.md)

## Phase 2: Live run in the approved project (needs approval)

- [x] Task: Run `bootstrap.sh`, and check the observability setting
- [x] Task: Run `deploy.py`, and record the embedding model location result
- [x] Task: Run the three samples, and record the results
- [x] Task: Check the `_Trace` bucket location
- [x] Task: Update product.md, the README status, and the registry
- [x] Task: Phase Verification and Checkpoint (Refer to workflow.md)

## Live run notes (10 Nov 2026, new test project)

1. Deploy 1 failed: the container did not start. `AdkApp.set_up()` imports `google.cloud.aiplatform`.
   Fix: pin `google-cloud-aiplatform` and `google-cloud-resource-manager` in `agent/requirements.txt`.
2. Deploy 2 passed. Sample 1 passed. Stored events use camelCase keys. Fix: the helpers read both forms.
3. Sample 2 found no memories with `add_session_to_memory()` (IngestEvents), with and without an idle
   trigger. A direct GenerateMemories call worked. Fix: the callback selects the GenerateMemories path.
4. Final deploy: samples 1, 2, and 3 passed. `_Trace` is in `asia-southeast1`.
