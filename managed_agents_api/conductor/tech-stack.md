# Tech Stack: Managed Agents API Demo

## Language

- Python 3.11 or later.

## Libraries

| Library                | Purpose                                                                   |
|------------------------|---------------------------------------------------------------------------|
| `google-genai`         | `client.agents` and `client.interactions`. Version 3.2.0.                 |
| `httpx2`               | REST calls that the SDK does not have: update an agent, get an operation. |
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

## Change log

### 12 Nov 2026: `httpx2`, not `httpx`

- `google-genai` 3.2.0 installs `httpx2` 2.16.0, not `httpx`. The SDK imports `httpx` if it is
  present, and uses `httpx2` if it is not.
- The demo REST client uses `httpx2` (`import httpx2 as httpx`). Thus the demo installs no
  second HTTP library. `httpx2` has the same API, including `MockTransport` for the unit tests.

### 12 Nov 2026: SDK facts from the docs and the package

- The docs say that the Python SDK has no `update` method. Use REST `PATCH` with `update_mask`.
- The docs say that SDK `agents.create()` and `agents.delete()` return the final result.
  They do not show the long-running operation. The demo uses REST to show the operation.
- The SDK source type allows `gcs`, `inline`, `repository`, and `skill_registry`. An `inline`
  source has `content`, `target`, and an optional `encoding`. The Agent Platform docs show only
  `gcs` and `skill_registry`. Phase 2 tests `inline` against the real API.
- The interaction `curl` examples in the docs send the header `Api-Revision: 2026-05-20`.

### 12 Nov 2026: first real access check (test project)

- Create operation for the first agent in the project: 373.2 s. The docs say two to three
  minutes. The access check timeout is 600 s.
- Delete operation: the first response already had `"done": true`. Total time 6.5 s.
- The delete operation name uses the numeric agent ID, not the custom ID.
- The `admin@` account of the Argolis organization had enough access. The role that a
  user with fewer permissions needs is still not confirmed.

### 12 Nov 2026: the `inline` source type is rejected

- The real API rejects an inline source with HTTP 400:
  "Invalid `base_environment.sources.type`: inline. Must be one of: [`gcs`, `skill_registry`]".
- The SDK type allows `inline` and `repository`, but the Agent Platform API accepts only `gcs`
  and `skill_registry`. This agrees with the Agent Platform docs.

### 12 Nov 2026: a data source needs the `*` network allowlist

- With a `gcs` source and no `network` field, the API returns HTTP 400:
  "Network allowlist domain must be set when data source is set."
- With `{"domain": "storage.googleapis.com"}`, the API returns HTTP 400:
  "Only domain: '*' is supported now. Found: `storage.googleapis.com`."
- Thus, in this Preview, a sandbox with a Cloud Storage source must have unrestricted network
  access.
- The user accepted the `*` allowlist for this demo on 12 Nov 2026 22:25 SGT. The data is
  synthetic. The lifecycle script prints a warning before it creates the agent.

### 12 Nov 2026: lifecycle run in the test project

- Create of the second agent in the project: 13.3 s. The first agent took 373.2 s.
- `UpdateAgent` (REST `PATCH`) returns a long-running operation. It was done after one poll.
- SDK `agents.get` returns the configuration, `created`, `updated`, and `effectiveIdentity`.
  `effectiveIdentity` is the agent identity principal
  (`agents.global.org-<ORG_NUMBER>.system.id.goog/resources/aiplatform/projects/<PROJECT_NUMBER>/...`).
- The SDK prints `UserWarning: Agents usage is experimental` on each call. The demo hides it.
- Cloud Audit Logs: no `aiplatform.googleapis.com` entries were found for the create, update,
  or delete calls, 20 minutes after the calls.
