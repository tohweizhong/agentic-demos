# Plan: Track 5 — Web UI

## Phase 1: Go backend

- [ ] Task: Server and handlers (FR1)
    - [ ] Write failing Go tests with `httptest` and a fake upstream: agents, interactions stream, outputs, file name check.
    - [ ] Implement `webui/server/` with the standard library and `golang.org/x/oauth2/google`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: TypeScript frontend and delivery

- [ ] Task: Frontend (FR2)
    - [ ] Implement `webui/web/` in plain TypeScript. Compile with `tsc`.
- [ ] Task: Real run and delivery (FR3)
    - [ ] Run the server against the real API. Stream one interaction with curl.
    - [ ] `Dockerfile`, README section, repository checks.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
