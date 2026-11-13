# Plan: Track 5 — Web UI

## Phase 1: Go backend [checkpoint: d5d1a2e]

- [x] Task: Server and handlers (FR1)
    - Summary: `webui/server/main.go` with five endpoints. 10 Go tests with `httptest` and a fake
      upstream: token never sent to the browser, file names limited to `agent/output/`.
    - [x] Write failing Go tests with `httptest` and a fake upstream: agents, interactions stream, outputs, file name check.
    - [x] Implement `webui/server/` with the standard library and `golang.org/x/oauth2/google`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: TypeScript frontend and delivery [checkpoint: d5d1a2e]

- Verification: `go vet`, `go test`, `tsc`, Node.js tests, and real runs passed. The user
  delegated checkpoints.

- [x] Task: Frontend (FR2)
    - Summary: `webui/web/` in plain TypeScript. `sse.ts` parses the stream (3 Node.js tests).
      Headless Chrome loaded agents and outputs, and showed the registry chart.
    - [x] Implement `webui/web/` in plain TypeScript. Compile with `tsc`.
- [x] Task: Real run and delivery (FR3)
    - Summary: curl and headless Chrome streamed real interactions through the server. Answers
      were correct (144 rows, South 488,846.67). `Dockerfile` and `webui/README.md` added.
    - [x] Run the server against the real API. Stream one interaction with curl.
    - [x] `Dockerfile`, README section, repository checks.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
