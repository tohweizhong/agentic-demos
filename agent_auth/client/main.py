# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A FastAPI client for interacting with ADK remote agents and handling GCP authentication."""

import asyncio
import base64
import importlib
import json
import os
import sys
import traceback
import uuid

import agentplatform
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.auth import AuthConfig
from google.adk.runners import InMemoryRunner
from google.api_core.client_options import ClientOptions
import google.auth
import google.auth.transport.requests
from google.cloud.agentidentitycredentials_v1 import AuthProviderCredentialsServiceClient
from google.cloud.agentidentitycredentials_v1 import FinalizeCredentialsRequest
from google.genai import types
from pydantic import BaseModel
import uvicorn

# Add agent project directory to path to allow importing local agents
AGENT_PROJECT_DIR = os.environ.get("AGENT_PROJECT_DIR") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if AGENT_PROJECT_DIR not in sys.path:
  sys.path.append(AGENT_PROJECT_DIR)

app = FastAPI()

# Global cache for local runners to persist session history
local_runners = {}

# Mount static files
try:
  app.mount("/static", StaticFiles(directory="static"), name="static")
  print("Successfully mounted /static")
except Exception as e:
  print(f"Error mounting /static: {e}")


# Serve the index page for the root path
@app.get("/")
async def get_index():
  try:
    return FileResponse("static/index.html")
  except Exception as e:
    print(f"Error serving static/index.html: {e}")
    return {"error": str(e)}, 500


# Helper function to stream SSE error messages
def stream_error(msg: str, tb: str = None):
  async def err_gen():
    payload = {"error": msg}
    if tb:
      payload["traceback"] = tb
    yield f"data: {json.dumps(payload)}\n\n"

  return StreamingResponse(err_gen(), media_type="text/event-stream")


# List local agents in the agent project directory (e.g. agent.py)
@app.get("/list_local_agents")
async def list_local_agents():
  try:
    agents = [
        {
            "id": f[:-3],
            "name": f[:-3].replace("_", " ").title(),
            "import_path": f[:-3],
        }
        for f in os.listdir(AGENT_PROJECT_DIR)
        if f.endswith(".py") and not f.startswith(".") and f != "__init__.py"
    ]
    return {"agents": agents}
  except Exception as e:
    return {"error": str(e)}


# List remote agents in the given project and location.
@app.get("/list_agents")
async def list_remote_agents(project_id: str, location: str):
  try:
    client = agentplatform.Client(project=project_id, location=location)
    return {
        "agents": [
            {
                "id": a.api_resource.name.split("/")[-1],
                "name": a.api_resource.display_name,
                "full_name": a.api_resource.name,
            }
            for a in client.runtimes.list()
        ]
    }
  except Exception as e:
    return {"error": str(e)}


# Helper function to extract the auth URI and nonce from the auth config
def handle_adk_request_credential(auth_config):
  if (
      auth_config.exchanged_auth_credential
      and auth_config.exchanged_auth_credential.oauth2
  ):
    oauth2 = auth_config.exchanged_auth_credential.oauth2
    return oauth2.auth_uri, oauth2.nonce
  return None, None


try:
  _, default_project = google.auth.default()
except Exception:
  default_project = ""


# agentic-demos change: take the Auth Manager user ID from the IAP login.
# IAP verifies the user and sets this header on each request. Its value has
# the format "accounts.google.com:user@example.com". The client uses only this
# header. If the header is absent (local run without IAP), the client keeps
# the upstream behaviour: the user ID comes from the form or a cookie.
IAP_EMAIL_HEADER = "X-Goog-Authenticated-User-Email"
_iap_warning_logged = False


def iap_user_id(http_request: Request) -> str | None:
  """Returns the IAP user email, or None when the request has no IAP header."""
  global _iap_warning_logged
  value = http_request.headers.get(IAP_EMAIL_HEADER)
  if not value:
    if not _iap_warning_logged:
      print(
          f"WARNING: no {IAP_EMAIL_HEADER} header. The client uses the user ID"
          " from the form. Do not expose this client without IAP."
      )
      _iap_warning_logged = True
    return None
  return value.split(":", 1)[1] if ":" in value else value


@app.get("/whoami")
async def whoami(http_request: Request):
  user_id = iap_user_id(http_request)
  return {"iap": user_id is not None, "user_id": user_id}


# agentic-demos change: "Demo controls" endpoints. DEMO ONLY.
# These endpoints let a presenter reset the Auth Manager consent of the
# signed-in user and show the access summaries. A production client must not
# expose these actions. Each endpoint acts only for the IAP user, and returns
# 403 when there is no IAP header. No endpoint runs a shell or a subprocess.
AGENT_IDENTITY_API = "https://agentidentity.googleapis.com/v1"
# Full resource name: projects/P/locations/L/authProviders/A
DEMO_AUTH_PROVIDER_NAME = os.environ.get("AUTH_PROVIDER_NAME", "")
DEMO_GITHUB_APP_URL = os.environ.get(
    "GITHUB_APP_URL", "https://github.com/settings/developers"
)


def _demo_call(method: str, url: str, body: dict | None = None):
  """Calls the Agent Identity API with the client service account."""
  credentials, _ = google.auth.default(
      scopes=["https://www.googleapis.com/auth/cloud-platform"]
  )
  session = google.auth.transport.requests.AuthorizedSession(credentials)
  resp = session.request(method, url, json=body, timeout=30)
  try:
    data = resp.json()
  except ValueError:
    data = {"text": resp.text}
  return resp.status_code, data


def _demo_provider_parts():
  # projects/P/locations/L/authProviders/A -> (P, L, A)
  parts = DEMO_AUTH_PROVIDER_NAME.split("/")
  if len(parts) != 6 or parts[0] != "projects" or parts[4] != "authProviders":
    return None
  return parts[1], parts[3], parts[5]


@app.get("/demo/config")
async def demo_config():
  parts = _demo_provider_parts()
  return {
      "github_app_url": DEMO_GITHUB_APP_URL,
      "auth_provider": parts[2] if parts else None,
      "ingressAgentId": os.environ.get("INGRESS_AGENT_ID", ""),
      "egressAgentId": os.environ.get("EGRESS_AGENT_ID", ""),
  }


LOGGING_API = "https://logging.googleapis.com/v2"
_SHORT_INFO_TYPES = {
    "US_SOCIAL_SECURITY_NUMBER": "SSN",
}


def _parse_ingress_entry(entry: dict) -> dict:
  """Normalizes one Model Armor sanitize_operations log entry."""
  payload = entry.get("jsonPayload") or {}
  result = payload.get("sanitizationResult") or payload.get("filterResult") or {}
  meta = (
      result.get("sanitizationMetadata")
      or payload.get("sanitizationMetadata")
      or {}
  )
  verdict = str(
      result.get("sanitizationVerdict")
      or payload.get("sanitizationVerdict")
      or ""
  )
  match_state = str(
      result.get("filterMatchState") or payload.get("filterMatchState") or ""
  )
  blocked = (
      "BLOCK" in verdict.upper() or match_state.upper() == "MATCH_FOUND"
  )
  decision = "Blocked" if blocked else "Allowed"

  op = str(
      payload.get("operationType")
      or (entry.get("labels") or {}).get(
          "modelarmor.googleapis.com/operation_type"
      )
      or meta.get("target")
      or ""
  )
  template_id = str(
      ((entry.get("resource") or {}).get("labels") or {}).get("template_id")
      or meta.get("templateId")
      or ""
  )
  if "RESPONSE" in op.upper() or "response" in template_id.lower():
    target = "Model response"
  else:
    target = "User prompt"

  filter_results = (
      result.get("filterResults") or payload.get("filterResults") or {}
  )
  sdp = (filter_results.get("sdp") or {}).get("sdpFilterResult") or {}
  info_types = (
      (sdp.get("deidentifyResult") or {}).get("infoTypes")
      or (sdp.get("inspectResult") or {}).get("infoTypes")
      or sdp.get("infoTypes")
      or []
  )
  if info_types:
    short = [_SHORT_INFO_TYPES.get(str(t), str(t)) for t in info_types]
    detail = f"SDP ({', '.join(short)})"
  elif blocked:
    reason = str(result.get("sanitizationVerdictReason") or "")
    detail = f"{reason} ({template_id})" if reason and template_id else (
        reason or template_id or "Blocked by filter"
    )
  else:
    detail = f"No match ({template_id})" if template_id else "No match"

  return {
      "timestamp": entry.get("timestamp") or entry.get("receiveTimestamp") or "",
      "decision": decision,
      "target": target,
      "detail": detail,
  }


def _parse_egress_entry(entry: dict) -> dict:
  """Normalizes one IAP GatekeeperAuthorizer.AuthorizeUser log entry."""
  proto = entry.get("protoPayload") or {}
  auth_list = proto.get("authorizationInfo") or []
  auth0 = (
      auth_list[0] if auth_list and isinstance(auth_list[0], dict) else {}
  )
  granted = bool(auth0.get("granted"))
  decision = "Allowed" if granted else "Blocked"

  meta = proto.get("metadata") or {}
  mcp = meta.get("mcp_attributes") or {}
  tool = mcp.get("mcp_tool_name") or meta.get("mcp_tool_name") or ""
  mcp_method = mcp.get("mcp_method") or meta.get("mcp_method") or ""
  if tool and mcp_method:
    target = f"{mcp_method}: {tool}"
  elif tool:
    target = str(tool)
  elif mcp_method:
    target = str(mcp_method)
  else:
    res_name = str(proto.get("resourceName") or auth0.get("resource") or "")
    target = res_name.split("/")[-1] if res_name else "MCP server"

  detail = str(
      auth0.get("permission") or "iap.webServiceVersions.egressViaIAP"
  )
  return {
      "timestamp": entry.get("timestamp") or entry.get("receiveTimestamp") or "",
      "decision": decision,
      "target": target,
      "detail": detail,
  }


@app.get("/demo/gateway-logs")
async def demo_gateway_logs(
    kind: str, http_request: Request, response: Response
):
  if not iap_user_id(http_request):
    response.status_code = 403
    return {"error": "Demo controls work only behind IAP."}
  if kind not in ("ingress", "egress"):
    response.status_code = 400
    return {"error": "kind must be ingress or egress."}
  parts = _demo_provider_parts()
  project_id = (
      parts[0]
      if parts
      else os.environ.get("GOOGLE_CLOUD_PROJECT", default_project or "")
  )
  if not project_id:
    response.status_code = 500
    return {"error": "Set GOOGLE_CLOUD_PROJECT or AUTH_PROVIDER_NAME."}

  if kind == "ingress":
    log_filter = (
        f'logName="projects/{project_id}/logs/'
        'modelarmor.googleapis.com%2Fsanitize_operations"'
    )
    parser = _parse_ingress_entry
  else:
    log_filter = (
        f'logName="projects/{project_id}/logs/'
        'cloudaudit.googleapis.com%2Fdata_access"'
        ' AND protoPayload.serviceName="iap.googleapis.com"'
        ' AND protoPayload.authorizationInfo.permission='
        '"iap.webServiceVersions.egressViaIAP"'
        ' AND labels."iap.googleapis.com/audited_resource_type"='
        '"agentregistry.googleapis.com/McpServer"'
    )
    parser = _parse_egress_entry

  url = f"{LOGGING_API}/entries:list"
  body = {
      "resourceNames": [f"projects/{project_id}"],
      "filter": log_filter,
      "orderBy": "timestamp desc",
      "pageSize": 20,
  }
  status, data = await asyncio.to_thread(_demo_call, "POST", url, body)
  entries = (
      data.get("entries", [])
      if status == 200 and isinstance(data, dict)
      else []
  )
  rows = [parser(e) for e in entries if isinstance(e, dict)]
  return {
      "kind": kind,
      "command": (
          f"gcloud logging read '{log_filter}' --project={project_id}"
          " --limit=20 --format=json"
      ),
      "http": f"POST {url}",
      "status": status,
      "rows": rows,
      "entries": entries,
      "response": data,
  }


# agentic-demos change: options for the Project ID and Location dropdowns.
# PROJECT_OPTIONS and LOCATION_OPTIONS are comma-separated lists. If a list
# is empty, the dropdown has one option: the default value.
def _options(env_name: str, default: str) -> list[str]:
  values = [
      v.strip() for v in os.environ.get(env_name, "").split(",") if v.strip()
  ]
  if default and default not in values:
    values.insert(0, default)
  return values


@app.get("/config")
async def ui_config():
  default_project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
  default_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "")
  return {
      "projects": _options("PROJECT_OPTIONS", default_project),
      "locations": _options("LOCATION_OPTIONS", default_location),
      "default_project": default_project,
      "default_location": default_location,
  }


@app.post("/demo/reset-consent")
async def demo_reset_consent(http_request: Request, response: Response):
  user_id = iap_user_id(http_request)
  if not user_id:
    response.status_code = 403
    return {"error": "Demo controls work only behind IAP."}
  parts = _demo_provider_parts()
  if not parts:
    response.status_code = 500
    return {"error": "Set AUTH_PROVIDER_NAME on the client."}
  _, location, provider = parts
  url = f"{AGENT_IDENTITY_API}/{DEMO_AUTH_PROVIDER_NAME}:revokeAuthorization"
  status, data = await asyncio.to_thread(
      _demo_call, "POST", url, {"userId": user_id}
  )
  return {
      "command": (
          "gcloud alpha agent-identity auth-providers revoke-authorization"
          f" {provider} --location={location} --user-id={user_id}"
      ),
      "http": f"POST {url}",
      "status": status,
      "response": data,
  }


@app.get("/demo/access-summaries")
async def demo_access_summaries(http_request: Request, response: Response):
  if not iap_user_id(http_request):
    response.status_code = 403
    return {"error": "Demo controls work only behind IAP."}
  parts = _demo_provider_parts()
  if not parts:
    response.status_code = 500
    return {"error": "Set AUTH_PROVIDER_NAME on the client."}
  project, location, _ = parts
  url = (
      f"{AGENT_IDENTITY_API}/projects/{project}/locations/{location}"
      "/accessSummaries"
  )
  status, data = await asyncio.to_thread(_demo_call, "GET", url)
  return {
      "command": (
          f"gcloud agent-identity access-summaries list --location={location}"
      ),
      "http": f"GET {url}",
      "status": status,
      "response": data,
  }


class ChatRequest(BaseModel):
  message: str = ""
  agent_type: str = "remote"
  local_agent: str = ""
  project_id: str | None = os.environ.get(
      "GOOGLE_CLOUD_PROJECT", default_project or ""
  )
  location: str | None = os.environ.get("GOOGLE_CLOUD_LOCATION", "")
  agent_id: str | None = os.environ.get("AGENT_ID", "")
  user_id: str = "default_user_id"
  session_id: str | None = None
  is_auth_resume: bool | None = False
  auth_config: dict | None = None
  auth_request_function_call_id: str | None = None


# Endpoint for querying the agent.
@app.post("/chat")
async def chat(request: ChatRequest, response: Response, http_request: Request):
  session_id = request.session_id or str(uuid.uuid4())
  # agentic-demos change: behind IAP, the IAP login is the user ID. The
  # client ignores the user_id value from the form.
  if verified_user_id := iap_user_id(http_request):
    request.user_id = verified_user_id
  # agentic-demos change: the UI sends empty strings when the user does not
  # fill the settings form. Use the server environment values in that case.
  request.project_id = request.project_id or os.environ.get(
      "GOOGLE_CLOUD_PROJECT", default_project or ""
  )
  request.location = request.location or os.environ.get(
      "GOOGLE_CLOUD_LOCATION", ""
  )
  request.agent_id = request.agent_id or os.environ.get("AGENT_ID", "")
  current_agent = None
  client = None
  local_runner = None

  if request.agent_type == "local":
    if not request.local_agent:
      return stream_error("No local agent specified.")

    # Validate that the local agent exists in the project directory
    agent_file = os.path.join(AGENT_PROJECT_DIR, f"{request.local_agent}.py")
    if not os.path.exists(agent_file):
      return stream_error(
          f"Local agent module {request.local_agent} not found in"
          f" {AGENT_PROJECT_DIR}."
      )

    try:
      # Use cached runner if available to persist session history
      if request.local_agent in local_runners:
        local_runner = local_runners[request.local_agent]
      else:
        module = importlib.import_module(request.local_agent)
        app_obj = getattr(module, "app", None)
        if not app_obj:
          return stream_error(
              f"Local agent module {request.local_agent} has no app attribute."
          )
        local_runner = InMemoryRunner(app=app_obj)
        local_runner.auto_create_session = True
        local_runners[request.local_agent] = local_runner
    except Exception as e:
      return stream_error(
          f"Failed to load local agent {request.local_agent}: {e}",
          traceback.format_exc(),
      )
  else:
    client = agentplatform.Client(
        project=request.project_id, location=request.location
    )
    remote_name = (
        f"projects/{request.project_id}/locations/{request.location}"
        f"/reasoningEngines/{request.agent_id}"
    )
    try:
      current_agent = client.runtimes.get(name=remote_name)
    except Exception as e:
      return stream_error(
          f"Failed to load remote agent: {e}", traceback.format_exc()
      )

    if not request.session_id and current_agent:
      try:
        session_obj = (
            await current_agent.async_create_session(user_id=request.user_id)
            if hasattr(current_agent, "async_create_session")
            else current_agent.create_session(user_id=request.user_id)
        )
        session_id = (
            getattr(session_obj, "id", None)
            or (
                session_obj.get("id") if isinstance(session_obj, dict) else None
            )
            or session_id
        )
        client = agentplatform.Client(
            project=request.project_id, location=request.location
        )
        current_agent = client.runtimes.get(name=remote_name)
      except Exception as e:
        return stream_error(
            f"Failed to create session: {e}", traceback.format_exc()
        )

  response.set_cookie(
      key="session_id", value=session_id, httponly=True, samesite="lax"
  )

  def process_agent_event(event):
    if hasattr(event, "model_dump"):
      event_data = (
          event.model_dump(mode="json")
          if "mode" in event.model_dump.__code__.co_varnames
          else event.model_dump()
      )
    elif hasattr(event, "dict"):
      event_data = event.dict()
    elif hasattr(event, "to_dict"):
      event_data = event.to_dict()
    elif isinstance(event, dict):
      event_data = event
    else:
      try:
        event_data = json.loads(json.dumps(event, default=lambda o: o.__dict__))
      except Exception:
        event_data = {"text": str(event)}

    content = event_data.get("content", {})
    parts = content.get("parts", []) if isinstance(content, dict) else []
    long_running = event_data.get("long_running_tool_ids") or event_data.get(
        "longRunningToolIds", []
    )

    for part in parts:
      fc = (
          (part.get("function_call") or part.get("functionCall"))
          if isinstance(part, dict)
          else None
      )
      if fc and fc.get("name") == "adk_request_credential":
        fc_id = fc.get("id")
        if not long_running or fc_id in long_running:
          try:
            args = fc.get("args", {})
            cfg_data = args.get("authConfig") or args.get("auth_config")
            if cfg_data:
              auth_config = (
                  AuthConfig.model_validate(cfg_data)
                  if isinstance(cfg_data, dict)
                  else cfg_data
              )
              auth_uri, consent_nonce = handle_adk_request_credential(
                  auth_config
              )
              if auth_uri:
                event_data.update({
                    "popup_auth_uri": auth_uri,
                    "auth_request_function_call_id": fc_id,
                    "auth_config": (
                        auth_config.model_dump()
                        if hasattr(auth_config, "model_dump")
                        else (
                            auth_config.dict()
                            if hasattr(auth_config, "dict")
                            else auth_config
                        )
                    ),
                    "consent_nonce": consent_nonce,
                })
          except Exception as e:
            print(f"Error processing auth wrapper: {e}")
          break

    return event_data

  async def event_generator():
    _ = client
    yield f"data: {json.dumps({'session_id': session_id})}\n\n"

    if (
        request.is_auth_resume
        and request.auth_request_function_call_id
        and request.auth_config
    ):
      message_to_send = types.Content(
          role="user",
          parts=[
              types.Part(
                  function_response=types.FunctionResponse(
                      id=request.auth_request_function_call_id,
                      name="adk_request_credential",
                      response=request.auth_config,
                  )
              )
          ],
      )
    else:
      message_to_send = types.Content(
          role="user", parts=[types.Part(text=request.message)]
      )

    try:
      if request.agent_type == "local" and local_runner:
        async for event in local_runner.run_async(
            user_id=request.user_id,
            session_id=session_id,
            new_message=message_to_send,
        ):
          yield f"data: {json.dumps(process_agent_event(event))}\n\n"
      elif current_agent:
        dumped_msg = (
            message_to_send.model_dump(exclude_none=True)
            if hasattr(message_to_send, "model_dump")
            else message_to_send.dict(exclude_none=True)
        )
        async for event in current_agent.async_stream_query(
            user_id=request.user_id,
            message=dumped_msg,
            session_id=session_id,
        ):
          yield f"data: {json.dumps(process_agent_event(event))}\n\n"
    except Exception as e:
      yield (
          "data:"
          f" {json.dumps({'error': str(e), 'traceback': traceback.format_exc()})}\n\n"
      )

  return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/validateUserId")
@app.get("/commit")
async def validate_user_id(request: Request):
  # Session data stored in cookies
  # agentic-demos change: behind IAP, the IAP login is the user ID. The
  # client ignores the user ID cookies. The /chat endpoint uses the same IAP
  # login, so the consent request and the finalize call use one user ID.
  user_id = (
      iap_user_id(request)
      or request.cookies.get("consent_user_id")
      or request.cookies.get("user_id")
  )
  consent_nonce = request.cookies.get("consent_nonce")
  session_id = request.cookies.get("session_id")
  # Query params
  user_id_validation_state = request.query_params.get(
      "user_id_validation_state"
  )
  auth_provider_name = request.query_params.get(
      "connector_name"
  ) or request.query_params.get("auth_provider_name")
  if auth_provider_name:
    auth_provider_name = auth_provider_name.replace(
        "/connectors/", "/authProviders/"
    )

  print(
      f"Callback received: user_id_validation_state={user_id_validation_state},"
      f" auth_provider_name={auth_provider_name}, user_id={user_id}"
  )
  # Note: In production, you should probably throw an if the below checks fail.
  # For this example, we'll just return an error message to the user and 200 OK.
  if not user_id:
    return {
        "status": "error",
        "message": (
            "user_id cookie not found. Please ensure cookies are enabled."
        ),
    }
  if not consent_nonce:
    return {
        "status": "error",
        "message": (
            "consent_nonce cookie not found. Please ensure cookies are enabled."
        ),
    }
  if not user_id_validation_state:
    return {
        "status": "error",
        "message": "user_id_validation_state query param not found",
    }
  if not auth_provider_name:
    return {
        "status": "error",
        "message": "connector_name or auth_provider_name query param not found",
    }

  try:
    state_bytes = base64.b64decode(
        user_id_validation_state + "=" * (-len(user_id_validation_state) % 4),
        altchars=b"-_",
        validate=True,
    )

    client_options = None
    if host := os.environ.get("AGENT_IDENTITY_CREDENTIALS_TARGET_HOST"):
      client_options = ClientOptions(api_endpoint=host)

    client = AuthProviderCredentialsServiceClient(
        client_options=client_options, transport="rest"
    )

    finalize_request = FinalizeCredentialsRequest(
        auth_provider=auth_provider_name,
        user_id=user_id,
        user_id_validation_state=state_bytes,
        consent_nonce=consent_nonce,
    )

    print(
        "Calling FinalizeCredentials via AuthProviderCredentialsServiceClient"
        f" for auth_provider: {auth_provider_name}"
    )
    await asyncio.to_thread(client.finalize_credentials, finalize_request)

    # Return a simple HTML page to indicate OAuth success
    # agentic-demos change: the page tells the main page that the consent is
    # complete, then closes itself. The main page then resumes the agent once.
    # It uses three same-origin channels, because GitHub can cut the
    # window.opener link: BroadcastChannel, window.opener.postMessage, and a
    # localStorage "storage" event.
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorization Successful</title>
    </head>
    <body>
        <p>Authorization successful! You can close this window.</p>
        <script>
          const msg = {type: "agent-auth-complete", at: Date.now()};
          try {
            const bc = new BroadcastChannel("agent-auth");
            bc.postMessage(msg);
            bc.close();
          } catch (e) {}
          try {
            if (window.opener) {
              window.opener.postMessage(msg, window.location.origin);
            }
          } catch (e) {}
          try {
            localStorage.setItem("agent-auth-complete", String(msg.at));
          } catch (e) {}
          setTimeout(() => window.close(), 1000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

  except Exception as e:
    print(f"Error finalizing credentials: {e}")
    return {
        "status": "error",
        "message": f"Failed to finalize credentials: {str(e)}",
    }


if __name__ == "__main__":
  # agentic-demos change: read HOST and PORT so that the same file runs on
  # localhost and on Cloud Run.
  uvicorn.run(
      app,
      host=os.environ.get("HOST", "127.0.0.1"),
      port=int(os.environ.get("PORT", "8080")),
  )
