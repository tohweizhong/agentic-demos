# Agent services starter pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed. **Nothing is built yet.** This folder holds only
> the product definition in [conductor/](conductor/index.md).

The agent services starter pack is a set of ADK sample code for three Gemini Enterprise Agent
Platform services: **Sessions**, **Memory Bank**, and **observability** (ADK with OpenTelemetry).
One small ADK agent runs on Agent Runtime in `asia-southeast1`. Three sample scripts show each
service on that agent. No Terraform is used.

## Relation to the governance starter pack

This pack complements [agent_governance_starter_pack](../agent_governance_starter_pack/). The two
packs do not depend on each other.

| Service | Shown in |
|---|---|
| Agent Registry, Agent Identity, Agent Gateway, Agent Runtime setup | [agent_governance_starter_pack](../agent_governance_starter_pack/) |
| Sessions, Memory Bank, observability | This pack |
| Eval (offline) | Backlog |

## Planned contents

| File | Contents |
|---|---|
| `bootstrap.sh` | Turns on the APIs, creates the staging bucket, and sets the observability default storage location to `asia-southeast1` |
| `agent/agent.py` | One ADK agent that uses Sessions, Memory Bank, and traces |
| `deploy.py` | Deploys the agent to Agent Runtime with the Memory Bank config and telemetry on |
| `samples/1_sessions.py` | Create a session, send 2 turns, resume the session, and list the events |
| `samples/2_memory_bank.py` | Write memories in session A, and recall them in session B |
| `samples/3_o11y.py` | Send one query, and print the trace ID and a Cloud Trace link |
| `cleanup.sh` | Deletes the agent and the staging bucket |

## Data residency in `asia-southeast1`

| Service | Data at rest in Singapore | ML processing in Singapore |
|---|---|---|
| Sessions | Yes | Not applicable |
| Memory Bank, memory generation (`gemini-3.5-flash`) | Yes | Yes |
| Memory Bank, embedding for similarity search | Yes (the stored memories) | **No.** No Google embedding model has ML processing in Singapore |
| Traces | Yes, when the project default storage location is `asia-southeast1` before the first trace | Not applicable |

The sources and the open items are in [conductor/product.md](conductor/product.md#check-results-step-6-10-nov-2026).
