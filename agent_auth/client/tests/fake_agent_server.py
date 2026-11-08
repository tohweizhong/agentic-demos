"""Fake agent server for the client browser tests.

The server runs the real client app (client/main.py): the real static files,
the real /validateUserId page, and the real /config and /whoami endpoints.
Only two parts are fake:

- POST /chat sends fixed 3LO events instead of calling Agent Runtime.
- The Auth Manager finalize call does nothing.

The first word of the chat message selects the scenario:

- "fast": consent request. The fake consent page redirects at once.
- "slow": consent request. The fake consent page redirects after 5 seconds.
- "stay": consent request. The fake consent page never redirects.
- "md" or "token": no consent request (the token is already stored). The
  agent calls a tool and answers with Markdown.

Usage: python fake_agent_server.py --port 8093
"""

import argparse
import asyncio
import json
import os
import sys

CLIENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLIENT_DIR)
os.chdir(CLIENT_DIR)  # main.py serves "static/" from the working directory.

from fastapi import Request  # pylint: disable=g-import-not-at-top
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
import uvicorn

import main  # pylint: disable=g-import-not-at-top

STATS = {"chat": 0, "resume": 0, "finalize": 0, "no_session": 0}

# Markdown answer. It also holds unsafe HTML, to test the sanitizer.
ANSWER_MD = (
    "Here are your **three** repos:\n\n"
    "1. repo-a\n2. repo-b\n3. *private-repo-c*\n\n"
    "See [GitHub](https://github.com/) and `inline code`.\n\n"
    "| Name | Private |\n|---|---|\n| repo-a | no |\n"
    "| private-repo-c | yes |\n\n"
    "```\ncode block line\n```\n\n"
    "<script>window.__xss = 1</script>\n\n"
    '<img src=x onerror="window.__xss = 2">\n\n'
    "[bad](javascript:window.__xss=3)\n"
)

CONSENT_DELAY_SECONDS = {"fast": 0, "slow": 5, "stay": 3600}


class FakeCredentialsClient:
  """Replaces AuthProviderCredentialsServiceClient. Counts finalize calls."""

  def __init__(self, **unused_kwargs):
    pass

  def finalize_credentials(self, unused_request):
    STATS["finalize"] += 1


main.AuthProviderCredentialsServiceClient = FakeCredentialsClient
main.app.router.routes = [
    r for r in main.app.router.routes if getattr(r, "path", "") != "/chat"
]


def _event(obj: dict) -> str:
  return "data: " + json.dumps(obj) + "\n\n"


@main.app.post("/chat")
async def fake_chat(request: Request):
  """Sends the 3LO events of the selected scenario as server-sent events."""
  body = await request.json()
  STATS["chat"] += 1
  if not body.get("session_id"):
    STATS["no_session"] += 1
  resume = bool(body.get("is_auth_resume"))
  if resume:
    STATS["resume"] += 1
  words = (body.get("message") or "").split()
  mode = words[0] if words else "fast"

  async def generate():
    yield _event({"session_id": f"session-{STATS['chat']}"})
    await asyncio.sleep(1.5)
    if resume or mode in ("md", "token"):
      yield _event({"content": {"parts": [{"function_call": {
          "name": "search_repositories", "id": "tool-1"}}]}})
      await asyncio.sleep(1.5)
      yield _event({"content": {"parts": [{"function_response": {
          "name": "search_repositories", "id": "tool-1"}}]}})
      await asyncio.sleep(0.5)
      yield _event({"content": {"parts": [{"text": ANSWER_MD}]}})
    else:
      # Like the real agent: the model calls the tool first. The tool then
      # asks for consent.
      yield _event({"content": {"parts": [{"function_call": {
          "name": "search_repositories", "id": "tool-1"}}]}})
      await asyncio.sleep(0.3)
      yield _event({
          "content": {"parts": [{"function_call": {
              "name": "adk_request_credential", "id": "fc-1"}}]},
          "popup_auth_uri": f"/fake_consent?mode={mode}",
          "consent_nonce": "nonce-1234567890",
          "auth_request_function_call_id": "fc-1",
          "auth_config": {"fake": True},
      })

  return StreamingResponse(generate(), media_type="text/event-stream")


@main.app.get("/fake_consent")
async def fake_consent(mode: str = "fast"):
  """Fake GitHub consent page. It redirects to the real /validateUserId."""
  target = ("/validateUserId?user_id_validation_state=YWJj"
            "&auth_provider_name=projects/p/locations/l/authProviders/a")
  delay = CONSENT_DELAY_SECONDS.get(mode, 5)
  return HTMLResponse(
      f'<html><head><meta http-equiv="refresh" content="{delay};url={target}">'
      f"</head><body>Fake GitHub consent ({mode})</body></html>")


@main.app.get("/test/stats")
async def stats():
  """Returns the request counters."""
  return STATS


@main.app.post("/test/stats/reset")
async def stats_reset():
  """Sets all request counters to zero."""
  for key in STATS:
    STATS[key] = 0
  return STATS


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--port", type=int, default=8093)
  args = parser.parse_args()
  uvicorn.run(main.app, host="127.0.0.1", port=args.port, log_level="warning")
