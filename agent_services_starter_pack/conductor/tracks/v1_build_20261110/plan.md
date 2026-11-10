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
- [ ] Task: Phase Verification and Checkpoint (Refer to workflow.md)

## Phase 2: Live run in the approved project (needs approval)

- [ ] Task: Run `bootstrap.sh`, and check the observability setting
- [ ] Task: Run `deploy.py`, and record the embedding model location result
- [ ] Task: Run the three samples, and record the results
- [ ] Task: Check the `_Trace` bucket location
- [ ] Task: Update product.md, the README status, and the registry
- [ ] Task: Phase Verification and Checkpoint (Refer to workflow.md)
