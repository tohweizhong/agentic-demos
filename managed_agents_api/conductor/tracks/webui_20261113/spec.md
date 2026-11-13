# Spec: Track 5 — Web UI

Decision: the user delegated all choices on 13 Nov 2026 11:20 SGT ("see to it that this managed api demo is fully built out"). The user was away, so the agent approved the spec and the plan.

## Overview

A small local web UI for the demo. The repository rules select Go (standard library first) for
the backend and TypeScript for the frontend.

## Functional requirements

### FR1. Go backend (`webui/server/`)
- `GET /api/agents`: list the agents (REST).
- `POST /api/interactions`: start an interaction for an agent and pass the server-sent event
  stream to the browser without change.
- `GET /api/outputs`: list the objects under `agent/output/` in the demo bucket.
- `GET /api/outputs/file?name=`: return one output object (Markdown or PNG). Only names under
  `agent/output/` are allowed.
- Credentials: Application Default Credentials with `golang.org/x/oauth2/google`. The token
  never goes to the browser.
- Settings from the environment: `GOOGLE_CLOUD_PROJECT`, `DEMO_BUCKET`, `PORT` (default 8080).
- It serves the built frontend from `webui/web/dist/`.

### FR2. TypeScript frontend (`webui/web/`)
- One page: select an agent, type a task, see the agent steps and text as they stream, then see
  the usage numbers and the output files (report rendered as text, chart as an image).
- Plain TypeScript compiled with `tsc`. No frontend framework.

### FR3. Tests and build
- Go unit tests with `httptest` and a fake upstream. `go vet` is clean.
- `make`-free build steps in the README. A `Dockerfile` with `gcr.io/distroless/static`.

## Acceptance criteria
1. The server runs locally against the real API, and a browser-free check (curl) streams a
   real interaction through it.
2. Go tests pass. `tsc` compiles without errors.

## Out of scope
- Authentication of browser users. Cloud Run deployment.
