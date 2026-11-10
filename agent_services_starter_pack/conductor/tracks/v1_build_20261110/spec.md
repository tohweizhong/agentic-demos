# Track spec: version 1 build (v1_build_20261110)

Type: MVP. Created 10 Nov 2026.

## Overview

Build the seven components in [product.md](../../product.md#components): one ADK agent on Agent
Runtime in `asia-southeast1`, a deploy script, three samples (Sessions, Memory Bank, observability),
and the bootstrap and clean-up scripts.

## Functional requirements

| # | Requirement |
|---|---|
| F1 | `bootstrap.sh` turns on the APIs, sets the observability default storage location to the region, and creates the staging bucket. It is safe to run again |
| F2 | `agent/agent.py` defines one ADK agent with `PreloadMemoryTool`, an `after_agent_callback` that calls `callback_context.add_session_to_memory()`, and one tool that makes a custom OpenTelemetry span |
| F3 | The tool returns the trace ID of its span, so that the observability sample can print it |
| F4 | `deploy.py` creates the Agent Runtime instance, or updates it when it exists. It sets the Memory Bank config and the telemetry environment variables. It writes the instance name to `.env` |
| F5 | `deploy.py --delete` deletes the instance with its sessions and memories |
| F6 | `samples/1_sessions.py` creates a session, sends 2 turns, resumes the session with a third turn, lists the events, and lists the sessions for the user |
| F7 | `samples/2_memory_bank.py` sends facts in session A, waits for Memory Bank to generate memories, prints them, and asks about them in a new session B. It prints the residency warning |
| F8 | `samples/3_o11y.py` sends one query that uses the tool. It prints the trace ID, a Cloud Trace link, and the command to check the `_Trace` bucket location |
| F9 | `cleanup.sh` deletes the instance and the staging bucket after the user types the project ID |

## Non-functional requirements

- All settings come from a gitignored `.env` file. `.env.example` has placeholders only.
- Offline tests with `pytest` cover the agent and the helper functions. They do not call Google Cloud.
- All text is in Simplified Technical English.

## Acceptance criteria

1. `pytest` passes offline, and coverage for `agent/` and `samples/common.py` is more than 60 percent.
2. After approval, the three samples run against the deployed agent in the approved project.
3. The results for the open items in product.md are recorded.

## Out of scope

Eval, Agent Identity, Agent Gateway, Agent Registry, CMEK, and Terraform.
