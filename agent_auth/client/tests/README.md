# Client tests

This folder holds the tests for the sample UI client.

| File | What it tests |
|---|---|
| `test_main.py` | Unit tests for the client backend (`main.py`), with the FastAPI test client. |
| `test_playground.py` | Browser tests for the Playground, with Step mode off. |
| `fake_agent_server.py` | Test server. It runs the real client app with a fake agent. |
| `conftest.py` | Fixtures: the fake agent server, headless Chrome, and JavaScript coverage. |

## How the browser tests work

`fake_agent_server.py` runs the real `main.py` app. The static files, the
`/validateUserId` page, `/config`, and `/whoami` are real. Two parts are fake:

- `POST /chat` sends fixed 3LO events. It does not call Agent Runtime.
- The Auth Manager finalize call does nothing. The server counts the calls.

The first word of the chat message selects the scenario:

| Word | Scenario |
|---|---|
| `fast` | Consent request. The fake consent page redirects at once. |
| `slow` | Consent request. The fake consent page redirects after 5 seconds. |
| `stay` | Consent request. The fake consent page never redirects. |
| `md`, `token` | No consent request (token already stored). Tool call, then a Markdown answer. |

The tests do not use Google Cloud, GitHub, or IAP.

## Run the tests

```bash
cd agent_auth/client
python3 -m venv .venv
.venv/bin/pip install uv
.venv/bin/uv pip install --python .venv/bin/python -r tests/requirements.txt
# Skip the next command if Google Chrome is installed.
.venv/bin/playwright install chromium
CI=true .venv/bin/python -m pytest tests -q --cov=main --cov-report=term
```

The run prints the line coverage of `static/script.js`. To write the coverage
of each line to a file, set `JS_COVERAGE_OUT=/path/to/file.json`.
