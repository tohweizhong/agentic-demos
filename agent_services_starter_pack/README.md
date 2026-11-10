# Agent services starter pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed. The code is written and the offline tests
> pass. **The live run on Agent Runtime is not done yet.** Each step below is "Not tested" until
> the live run.

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

## Contents

| File | Contents |
|---|---|
| `bootstrap.sh` | Turns on the APIs, sets the observability default storage location to the region, and creates the staging bucket |
| `agent/agent.py` | One ADK agent. It uses `PreloadMemoryTool`, a callback that sends each session to Memory Bank, and a tool with a custom trace span |
| `deploy.py` | Deploys the agent to Agent Runtime with the Memory Bank config and telemetry on. `--delete` deletes it |
| `samples/1_sessions.py` | Creates a session, sends 2 turns, resumes the session, and lists the events |
| `samples/2_memory_bank.py` | Writes memories in session A, and recalls them in session B |
| `samples/3_o11y.py` | Sends one query, and prints the trace ID and a Cloud Trace link |
| `cleanup.sh` | Deletes the agent and the staging bucket |
| `tests/` | Offline tests. They do not call Google Cloud |

## Before you start

- A Google Cloud project with billing. Use a new project if you want the traces in the region.
  The reason is in [Traces](#traces).
- The roles to turn on APIs, create a bucket, and create an Agent Runtime instance in the project.
- `gcloud`, authenticated with `gcloud auth login` and `gcloud auth application-default login`.
- Python 3.11 or later.

## Steps

1. Make the settings file. Set `PROJECT_ID` and `STAGING_BUCKET`.

   ```bash
   cp .env.example .env
   ```

2. Make a virtual environment for this folder.

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Prepare the project. Do this before the first deploy, so that the first trace goes to the region.

   ```bash
   ./bootstrap.sh
   ```

4. Deploy the agent. This takes some minutes. The script saves `AGENT_RUNTIME_NAME` in `.env`.

   ```bash
   .venv/bin/python deploy.py
   ```

5. Run the samples.

   ```bash
   .venv/bin/python samples/1_sessions.py
   .venv/bin/python samples/2_memory_bank.py
   .venv/bin/python samples/3_o11y.py
   ```

6. Delete the resources when you finish.

   ```bash
   ./cleanup.sh
   ```

## Data residency in `asia-southeast1`

| Service | Data at rest in Singapore | ML processing in Singapore |
|---|---|---|
| Sessions | Yes | Not applicable |
| Memory Bank, memory generation (`gemini-3.5-flash`) | Yes | Yes |
| Memory Bank, embedding for similarity search | Yes (the stored memories) | **No.** No Google embedding model has ML processing in Singapore |
| Traces | Yes, when the project default storage location is `asia-southeast1` before the first trace | Not applicable |

## Traces

The system creates the `_Trace` observability bucket when the first trace arrives. It uses the
default storage location of the project at that time. `bootstrap.sh` sets this location to the
region. The setting does not move a bucket that exists already. For an existing bucket, use the
reprovision procedure in the Google Cloud Observability docs ("Remediate data residency and CMEK
requirements").

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## More detail

The decisions, the sources, and the open items are in [conductor/product.md](conductor/product.md).
