# Sample UI client for Agent Identity and Auth Manager

This folder holds a copy of the sample UI client from the open source
[adk-python](https://github.com/google/adk-python/tree/main/contributing/samples/integrations/gcp_auth/client)
repository. The original files keep their Apache 2.0 license header.

The client does three things:

1. It sends chat messages to a remote agent on Agent Runtime.
2. When the agent sends an `adk_request_credential` event, it opens the consent
   popup and stores the consent nonce in a cookie.
3. It hosts the `/validateUserId` callback. Auth Manager sends the browser to
   this URL after the user gives consent. The client then calls
   `credentials:finalize`, and Auth Manager stores the user token in its vault.

> [!NOTE]
> This client uses FastAPI. The repository rule says "no FastAPI for a
> production-shaped backend". This folder is an exception. It is a copy of the
> upstream sample, and it is a test harness only. It is not a production
> backend.

## Changes from the upstream sample

| File | Change |
|---|---|
| `main.py` | The `/chat` endpoint uses the `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `AGENT_ID` environment values when the UI sends empty values. |
| `main.py` | The `__main__` block reads `HOST` and `PORT`. |
| `Dockerfile` | New file. It runs the client on Cloud Run. |

## Security

The client uses one fixed user ID (`default_user_id`) for every browser.
Every person who can open the client acts as that user. Do not give the client
public access. The sub-demos deploy it on Cloud Run behind Identity-Aware Proxy
(IAP).

## Run on your machine

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1
export AGENT_ID=YOUR_ENGINE_ID
.venv/bin/uvicorn main:app --port 8080
```

Open `http://localhost:8080`. Use `localhost`, not `127.0.0.1`. The agent
continue URI must match the client URL.
