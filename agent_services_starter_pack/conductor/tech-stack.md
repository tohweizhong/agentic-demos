# Technology Stack: Agent Services Starter Pack

| Layer | Technology |
|---|---|
| Language | Python 3.11 or later (`google-adk` 2.14.0 requires 3.11) |
| Agent framework | Google ADK, `google-adk==2.14.0` |
| Platform SDK | `google-cloud-agentplatform[agent-engines,adk]==2.7.0`. `agentplatform.Client`, `client.runtimes`, and `agentplatform.frameworks.AdkApp` |
| Agent hosting | Agent Runtime in `asia-southeast1`, deployed by `deploy.py` with `client.runtimes.create(agent=AdkApp(...), config=...)` |
| Sessions | Agent Runtime Sessions. `AdkApp` uses `VertexAiSessionService` on Agent Runtime |
| Memory | Memory Bank on the same Agent Runtime instance. `context_spec.memory_bank_config` in the deploy config. `PreloadMemoryTool` and `callback_context.add_session_to_memory()` in the agent |
| Model | `gemini-3.5-flash` in `asia-southeast1` for the agent and for memory generation |
| Embedding model | `text-embedding-005` (the Memory Bank default). ML processing is outside Singapore |
| Observability | Built-in ADK OpenTelemetry traces on Agent Runtime (`GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`). Telemetry API. Cloud Trace to view. One custom span with `opentelemetry-api` |
| Trace storage | System-created `_Trace` observability bucket. The project default storage location is `asia-southeast1` |
| Scripts | Bash with `gcloud` and `gsutil` or `gcloud storage`. Settings in a gitignored `.env` file, with `.env.example` |
| Tests | `pytest` for the agent and the helper functions, offline. Live runs of the samples in an approved project |
| Infrastructure as code | None. No Terraform (product decision D5) |

## Decisions

- No Terraform. The three services need only the SDK, the ADK, and `gcloud`.
- The default Agent Runtime service agent runs the agent. Agent Identity is out of scope.
- The deploy code uses `google-cloud-agentplatform`. The agent also needs `google-cloud-aiplatform` at run time, because `AdkApp.set_up()` imports it on Agent Runtime.

## Exceptions

- None. All code is Python, as the repository rules ask for ADK agents.
