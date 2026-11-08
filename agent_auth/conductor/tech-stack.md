# Technology Stack: Agent Auth Demos

| Layer | Technology |
|---|---|
| Agent language | Python 3.12 or later |
| Agent framework | Google ADK, `google-adk[agent-identity,gcp,mcp]`, version 2.5 or later and below 3.0 |
| Agent hosting | Agent Runtime, deployed with `adk deploy agent_engine` (Python object, named methods) |
| Model | Gemini (for example `gemini-3.8-flash`), called in the `global` location |
| Agent tools | GitHub MCP server through `McpToolset`, with tokens from Auth Manager |
| Identity and credentials | Agent Identity (SPIFFE principal) and Auth Manager auth providers (3LO) |
| Client backend | Python, FastAPI, Uvicorn, `google-auth`, `httpx`, `google-cloud-aiplatform[agent-engines]` |
| Client frontend | HTML, CSS, plain JavaScript, Material web components, inline SVG, stored libraries `marked` and `DOMPurify` |
| Client hosting | Cloud Run with IAP, one build service account, one runtime service account |
| Deploy and clean-up | Bash scripts with `gcloud` and `curl`. Settings in a gitignored `.env` |
| Database | None. The client keeps state in cookies and in browser memory |
| Client tests | `pytest` and `pytest-cov` for `main.py`. Playwright with headless Chrome for browser tests against a fake agent server. JavaScript coverage of `script.js` through the Chrome DevTools Protocol |

## Exceptions

- The repository rules ask for Go for production backends. The FastAPI client is a
  documented exception, because it is a copy of the ADK sample client and it is a
  demo, not a production backend.
