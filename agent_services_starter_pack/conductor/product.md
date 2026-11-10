# Product Definition: Agent Services Starter Pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed.

## Summary

The agent services starter pack is a set of ADK sample code for three Gemini Enterprise Agent
Platform (GEAP) services: Sessions, Memory Bank, and observability (ADK with OpenTelemetry). One
small ADK agent runs on Agent Runtime in `asia-southeast1`. Three sample scripts show each service
on that agent.

The pack complements [agent_governance_starter_pack](../../agent_governance_starter_pack/). The
governance pack shows the controls (identity, catalog, gateway). This pack shows the services that
an agent uses at run time.

## Problem

An agent factory team must know how to keep conversation state, keep long-term memory, and read
traces for each agent. The public docs show each service on its own, often in `us-central1`. A team
in Singapore must also know which parts of each service stay in Singapore.

## Users

| User | Need |
|---|---|
| Agent developer | Short, runnable ADK code for each service, to copy into their own agent |
| Platform owner | A clear statement of the data residency limits for each service in `asia-southeast1` |
| Operators | A way to find the trace for one request |

## Scope decisions

| # | Decision | Reason |
|---|---|---|
| D1 | In scope: Sessions, Memory Bank, and observability (ADK with OpenTelemetry) | These services are not shown by the governance pack |
| D2 | Out of scope: Agent Registry, Agent Runtime setup, Agent Identity, and Agent Gateway | The governance pack covers them. The README links to that folder. This pack does not copy its code or its requirements |
| D3 | Backlog: Eval (offline) | The Gen AI evaluation service supports only US, EU, and global. Local `adk eval` does not use Agent Runtime |
| D4 | No dependency on the governance pack | The pack must run from a clean clone in a new project (repository `AGENTS.md`, section 2) |
| D5 | Agent Runtime only. No local run path. No Terraform | The samples show the production path. The Python SDK, the ADK, and `gcloud` are sufficient for these three services |
| D6 | The agent uses the default Agent Runtime service agent, not Agent Identity | Agent Identity is out of scope (D2). The default service agent already has permission to read and write memories (Memory Bank setup doc) |
| D7 | Region: `asia-southeast1` for the agent, the models, Sessions, Memory Bank, and the traces | Target region of the source design. Section "Check results" lists the limits |
| D8 | `deploy.py` uses `client.runtimes.create(agent=..., config=...)` from `google-cloud-agentplatform`, not `client.agent_engines.create(...)` | The current Memory Bank and Agent Runtime docs use `agentplatform.Client` and `client.runtimes`. `client.agent_engines` is the older name in the `vertexai` module of `google-cloud-aiplatform` |
| D9 | `bootstrap.sh` sets the project default storage location for observability buckets to `asia-southeast1`. It does not create the `_Trace` bucket | The system creates the `_Trace` bucket. New system-created buckets use the default storage location. See check C3 |

## Components

| # | File | Contents | Status |
|---|---|---|---|
| 1 | `bootstrap.sh` | Turns on the APIs, creates the staging bucket, and sets the observability default storage location to `asia-southeast1` | Not built |
| 2 | `agent/agent.py`, `agent/requirements.txt` | One ADK agent. Sessions: a comment says that Agent Runtime connects `VertexAiSessionService`. Memory Bank: `PreloadMemoryTool` and an `after_agent_callback` that calls `callback_context.add_session_to_memory()`. Observability: built-in ADK traces and one custom span around a tool call | Not built |
| 3 | `deploy.py` | Deploys the agent with `client.runtimes.create`. Sets `context_spec.memory_bank_config` and the telemetry environment variables | Not built |
| 4 | `samples/1_sessions.py` | Creates a session, sends 2 turns, resumes the session, and lists the events | Not built |
| 5 | `samples/2_memory_bank.py` | Writes memories in session A. Recalls them in session B. Prints the residency warning | Not built |
| 6 | `samples/3_o11y.py` | Sends one query. Prints the trace ID and a Cloud Trace link | Not built |
| 7 | `cleanup.sh` | Deletes the agent (with its sessions and memories) and the staging bucket. The system-created `_Trace` bucket and the default storage setting remain. The script says so | Not built |

## Check results (step 6, 10 Nov 2026)

Sources: the current public docs (Agent Platform data residency, agent locations, Memory Bank setup,
Memory Bank ADK quickstart, Agent Runtime tracing, Observability default settings), Duckie, the
`gcloud` reference, and the released package files from PyPI. Nothing was deployed.

### C1. Models for Memory Bank in `asia-southeast1`

| Item | Result | Status |
|---|---|---|
| Memory Bank in `asia-southeast1` | Supported. The agent locations table marks Memory Bank as not supported only in some other regions | Docs |
| Data at rest | Session history and memory bank entries stay in the selected location | Docs |
| Generation model | `gemini-3.5-flash`. The data residency table lists ML processing in Singapore for `gemini-3.5-flash`, `gemini-2.5-flash`, and `gemini-4-argon`. `gemini-3.8-flash` has ML processing only in the US and EU multi-regions | Docs. The governance pack ran `gemini-3.5-flash` in `asia-southeast1` on 09 Nov 2026 |
| Embedding model | No Google embedding model has ML processing in Singapore. `text-embedding-005` (the default): US, EU, India. `text-multilingual-embedding-002`: US, Canada, EU, UK, Japan. `gemini-embedding-001` and `gemini-embedding-2`: US and EU only | Docs |
| `gemini-embedding-2` | Memory Bank accepts it only with the location `global`, `us`, or `eu` in the model resource name | Docs |
| Change the embedding model | You can change it only before the first memory is stored | Docs |
| Global endpoint | Memory Bank and Sessions support `location="global"`. CMEK is not possible with the global endpoint | Docs |
| Delete the agent | Deleting the Agent Runtime instance also deletes its memories | Docs |

**Residency warning for the Memory Bank sample:** memories are stored in `asia-southeast1`, and memory
generation with `gemini-3.5-flash` is processed in Singapore. The embedding step for similarity search
is processed outside Singapore.

**Open item (Not tested):** which location string the embedding model resource name must use when
the instance is in `asia-southeast1`. Test `locations/asia-southeast1/.../text-embedding-005` first at
deploy time, and record the result.

### C2. ADK API to save a session to Memory Bank

| Item | Result | Status |
|---|---|---|
| Callback API | `async def cb(callback_context): await callback_context.add_session_to_memory()`, set as `after_agent_callback` | Docs. Method found in `google/adk/agents/context.py` in `google-adk` 2.14.0 |
| Smaller option | `callback_context.add_events_to_memory(events=...)` sends only some events | Docs and package file |
| Read memories | `PreloadMemoryTool` reads memories at the start of each turn | Docs |
| Service wiring on Agent Runtime | `AdkApp` uses `VertexAiMemoryBankService` and `VertexAiSessionService` when `GOOGLE_CLOUD_AGENT_ENGINE_ID` is set, which Agent Runtime does. Locally it uses in-memory services | Docs. Logic found in `agentplatform/frameworks/adk.py` in 2.7.0 |

### C3. Where the traces are stored

| Item | Result | Status |
|---|---|---|
| Turn on traces | Deploy with `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` and `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` | Docs |
| Prompt and response content | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=EVENT_ONLY` logs prompts, responses, and `user.id`. The sample leaves it off by default, because it needs user consent | Docs |
| APIs | `telemetry.googleapis.com` for traces, `logging.googleapis.com` for logs, and `observability.googleapis.com` for the settings | Docs |
| Default storage | Traces go to the system-created `_Trace` observability bucket. A deploy in `asia-southeast1` does not by itself put this bucket in `asia-southeast1` | Docs and Duckie |
| Config for Singapore | `gcloud observability settings update --project=PROJECT_ID --location=global --update-mask=default_storage_location --default-storage-location=asia-southeast1`. Run it before the first trace. New system-created buckets then use `asia-southeast1` | Docs and `gcloud` reference |
| Existing `_Trace` bucket | The setting does not move it. Use the reprovision procedure in the Observability docs | Docs |
| Trace scopes | They control only which projects a query reads. They do not control storage | Duckie |
| Custom span | `opentelemetry.trace.get_tracer(...)` and `tracer.start_as_current_span(...)` inside a tool add a child span to the same trace | Duckie. Not tested |

**Open item (Not tested):** whether Agent Runtime traces follow the default storage location. Check
the `_Trace` bucket location with `gcloud observability buckets list` after the first trace.

**Known risk:** in the governance pack region test on 09 Nov 2026, the agent log showed repeated
`400 Invalid project id in name!` errors from the OpenTelemetry Cloud Trace exporter. The cause is not
known. The observability sample must check for this error.

### C4. Package versions to pin

| Package | Version | Note |
|---|---|---|
| `google-cloud-agentplatform` | `2.7.0` (latest on 10 Nov 2026) | Use the extras `[agent-engines,adk]`. Version 2.7.0 has no `runtimes` extra, although the docs show `[runtimes,adk]` |
| `google-adk` | `2.14.0` (latest on 10 Nov 2026) | The `adk` extra above needs `>=1.27.0,<3.0.0`. Requires Python 3.11 or later |
| `google-cloud-aiplatform` | Not used | `google-cloud-agentplatform` replaces it for this pack (D8) |
| `opentelemetry-api`, `opentelemetry-sdk` | From the `agent-engines` extra (`opentelemetry-sdk<2`) | Do not pin separately unless a test needs it |

The full dependency install was not completed in the check. Run a clean install before the first
deploy, and record the resolved versions.

## Backlog

| # | Item | Status |
|---|---|---|
| 1 | Eval (offline) with local `adk eval` and an evalset file (D3) | Not started |
| 2 | Agent Identity on the agent, as in the governance pack | Not started. Out of scope for version 1 |
| 3 | CMEK for Sessions and Memory Bank | Not started |

## Repository layout

```
agent_services_starter_pack/
├── bootstrap.sh
├── deploy.py
├── cleanup.sh
├── agent/
│   ├── agent.py
│   └── requirements.txt
├── samples/
│   ├── 1_sessions.py
│   ├── 2_memory_bank.py
│   └── 3_o11y.py
└── conductor/
```
