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
| `main.py` | Behind IAP, `/chat`, `/validateUserId`, and `/commit` take the user ID from the `X-Goog-Authenticated-User-Email` header. They ignore the user ID from the form and from cookies. Without the header, the upstream behaviour applies, and the server logs one warning. |
| `main.py` | New `/whoami` endpoint. It returns the IAP user email, or `iap: false` when there is no IAP header. |
| `static/script.js` | The page calls `/whoami`. Behind IAP, it shows the IAP email in the User ID field and disables the field. |
| `Dockerfile` | New file. It runs the client on Cloud Run. |

## Security

Behind IAP, the user ID is the email of the person that IAP verified. Each
person gets a separate token in Auth Manager. Without IAP, the client uses one
user ID from the form (`default_user_id` by default), and every person who can
open the client acts as that user. Do not give the client public access. The
sub-demos deploy it on Cloud Run behind Identity-Aware Proxy (IAP).

The client reads only the IAP email header. For more protection, a production
client must also verify the signed `X-Goog-IAP-JWT-Assertion` header.

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
