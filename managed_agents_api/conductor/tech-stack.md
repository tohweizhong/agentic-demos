# Tech Stack: Managed Agents API Demo

## Language

- Python 3.11 or later.

## Libraries

| Library                | Purpose                                                                   |
|------------------------|---------------------------------------------------------------------------|
| `google-genai`         | `client.agents` and `client.interactions`. Version 3.2.0.                 |
| `httpx`                | REST calls that the SDK does not have: update an agent, get an operation. |
| `google-auth`          | Application Default Credentials and short-lived access tokens.            |
| `google-cloud-storage` | Upload the input CSV file. Download the files that the agent writes.      |
| `python-dotenv`        | Reads the project ID and the bucket name from the `.env` file.            |
| `rich`                 | Tables, JSON, and colour in the terminal output.                          |
| `jupyter`              | The step-by-step notebook.                                                |
| `pytest`               | Unit tests.                                                               |

## API

- Endpoint: `https://aiplatform.googleapis.com/v1beta1/projects/PROJECT_ID/locations/global/agents`.
- Location: `global`. This is the only supported location.
- Base agent: `antigravity-preview-05-2026`. This is the only supported value.
- Authentication: Application Default Credentials (`gcloud auth application-default login`).
- The SDK client uses `vertexai=True`, the project ID, and `location="global"`.

## SDK facts (checked 12 Nov 2026)

- `google-genai` 3.2.0 and 2.34.0 both have `client.agents` and `client.interactions`.
- `client.agents` has `create`, `get`, `list`, and `delete`. It has no `update` method.
  The demo sends the update as a REST `PATCH` request with `httpx`.
- The demo does not use ADK. Thus the ADK limit on `google-genai` 3.x does not apply.

## Google Cloud resources

| Resource                 | Use                                                        |
|--------------------------|------------------------------------------------------------|
| A Cloud Storage bucket   | Input CSV file and agent output. Mounted into the sandbox. |
| BigQuery public datasets | Data for the MCP feature. No dataset to create.            |
| BigQuery MCP server      | `https://bigquery.googleapis.com/mcp`.                     |

## IAM roles

- The user needs permission to create agents in the project.
  Track 1 confirms the exact role name from the docs.
- `roles/mcp.toolUser` for the user and for the associated service account (MCP feature).
- Read and write access to the bucket for the agent service identity.
  Track 1 confirms which identity the sandbox uses.

## Environment

- A local virtual environment in the demo folder (`.venv/`). It is not shared with other demos.
- `requirements.txt` with pinned versions.

## Tests

- Unit tests use a fake client. They do not call the network.
- Integration tests call the real API. They run only when `GOOGLE_CLOUD_PROJECT`
  and `RUN_INTEGRATION=1` are set.

## Later tracks

- Web UI: TypeScript frontend (Vite) and a Go backend with the standard library.
  The Go backend calls the REST API. Container base image: `gcr.io/distroless/static`.

## Not used

- No ADK, no backend framework, no frontend framework, and no database in the first version.
