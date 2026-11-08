"""Unit tests for the gateway demo backend endpoints in client/main.py.

These tests use the FastAPI test client and do not call Google Cloud.
"""

import os
import sys

CLIENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, CLIENT_DIR)
os.chdir(CLIENT_DIR)

from fastapi.testclient import TestClient  # pylint: disable=g-import-not-at-top
import pytest

import main  # pylint: disable=g-import-not-at-top

IAP = {"X-Goog-Authenticated-User-Email": "accounts.google.com:user@example.com"}


@pytest.fixture
def client():
  return TestClient(main.app)


def test_demo_config_includes_gateway_agent_ids(client, monkeypatch):
  monkeypatch.setattr(
      main, "DEMO_AUTH_PROVIDER_NAME", "projects/p/locations/l/authProviders/a"
  )
  monkeypatch.setenv("INGRESS_AGENT_ID", "ing-123")
  monkeypatch.setenv("EGRESS_AGENT_ID", "egr-456")
  data = client.get("/demo/config").json()
  assert data["auth_provider"] == "a"
  assert data["ingressAgentId"] == "ing-123"
  assert data["egressAgentId"] == "egr-456"


def test_gateway_logs_requires_iap(client):
  resp = client.get("/demo/gateway-logs?kind=ingress")
  assert resp.status_code == 403


def test_gateway_logs_validates_kind(client):
  resp = client.get("/demo/gateway-logs?kind=unknown", headers=IAP)
  assert resp.status_code == 400


def test_gateway_logs_needs_project(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME", "")
  monkeypatch.setattr(main, "default_project", "")
  monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
  resp = client.get("/demo/gateway-logs?kind=ingress", headers=IAP)
  assert resp.status_code == 500


def test_gateway_logs_ingress_parses_model_armor_entries(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME", "")
  monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
  calls = []

  sample_entries = [
      {
          "timestamp": "2026-11-08T08:38:46.162528237Z",
          "resource": {"labels": {"template_id": "agw-response-template"}},
          "jsonPayload": {
              "operationType": "SANITIZE_MODEL_RESPONSE",
              "sanitizationResult": {
                  "filterMatchState": "MATCH_FOUND",
                  "sanitizationVerdict": (
                      "MODEL_ARMOR_SANITIZATION_VERDICT_BLOCK"
                  ),
                  "filterResults": {
                      "sdp": {
                          "sdpFilterResult": {
                              "deidentifyResult": {
                                  "matchState": "MATCH_FOUND",
                                  "infoTypes": ["US_SOCIAL_SECURITY_NUMBER"],
                              }
                          }
                      }
                  },
              },
          },
      },
      {
          "timestamp": "2026-11-08T08:38:46.028620653Z",
          "resource": {"labels": {"template_id": "agw-request-template"}},
          "jsonPayload": {
              "operationType": "SANITIZE_USER_PROMPT",
              "sanitizationResult": {
                  "filterMatchState": "NO_MATCH_FOUND",
                  "sanitizationVerdict": (
                      "MODEL_ARMOR_SANITIZATION_VERDICT_ALLOW"
                  ),
              },
          },
      },
  ]

  def fake_call(method, url, body=None):
    calls.append((method, url, body))
    return 200, {"entries": sample_entries}

  monkeypatch.setattr(main, "_demo_call", fake_call)
  resp = client.get("/demo/gateway-logs?kind=ingress", headers=IAP)
  assert resp.status_code == 200
  data = resp.json()
  assert len(calls) == 1
  method, url, body = calls[0]
  assert method == "POST"
  assert url == "https://logging.googleapis.com/v2/entries:list"
  assert body["resourceNames"] == ["projects/demo-proj"]
  assert body["orderBy"] == "timestamp desc"
  assert body["pageSize"] == 20
  assert "modelarmor.googleapis.com%2Fsanitize_operations" in body["filter"]
  assert "gcloud logging read" in data["command"]
  assert len(data["rows"]) == 2
  assert data["rows"][0] == {
      "timestamp": "2026-11-08T08:38:46.162528237Z",
      "decision": "Blocked",
      "target": "Model response",
      "detail": "SDP (SSN)",
  }
  assert data["rows"][1] == {
      "timestamp": "2026-11-08T08:38:46.028620653Z",
      "decision": "Allowed",
      "target": "User prompt",
      "detail": "No match (agw-request-template)",
  }


def test_gateway_logs_egress_parses_iap_entries(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME", "")
  monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-proj")
  calls = []

  sample_entries = [
      {
          "timestamp": "2026-11-08T08:38:58.217554736Z",
          "protoPayload": {
              "serviceName": "iap.googleapis.com",
              "methodName": "GatekeeperAuthorizer.AuthorizeUser",
              "resourceName": "projects/1/locations/us-central1/iap_web/mcp-1",
              "authorizationInfo": [
                  {
                      "granted": False,
                      "permission": "iap.webServiceVersions.egressViaIAP",
                  }
              ],
              "metadata": {
                  "mcp_attributes": {
                      "mcp_method": "tools/call",
                      "mcp_tool_name": "send_email",
                  }
              },
          },
      },
      {
          "timestamp": "2026-11-08T08:39:05.028326031Z",
          "protoPayload": {
              "serviceName": "iap.googleapis.com",
              "methodName": "GatekeeperAuthorizer.AuthorizeUser",
              "resourceName": "projects/1/locations/us-central1/iap_web/mcp-1",
              "authorizationInfo": [
                  {
                      "granted": True,
                      "permission": "iap.webServiceVersions.egressViaIAP",
                  }
              ],
              "metadata": {
                  "mcp_attributes": {
                      "mcp_method": "tools/call",
                      "mcp_tool_name": "read_email",
                  }
              },
          },
      },
  ]

  def fake_call(method, url, body=None):
    calls.append((method, url, body))
    return 200, {"entries": sample_entries}

  monkeypatch.setattr(main, "_demo_call", fake_call)
  resp = client.get("/demo/gateway-logs?kind=egress", headers=IAP)
  assert resp.status_code == 200
  data = resp.json()
  assert len(calls) == 1
  method, url, body = calls[0]
  assert method == "POST"
  assert url == "https://logging.googleapis.com/v2/entries:list"
  assert "cloudaudit.googleapis.com%2Fdata_access" in body["filter"]
  assert "iap.webServiceVersions.egressViaIAP" in body["filter"]
  assert "agentregistry.googleapis.com/McpServer" in body["filter"]
  assert "gcloud logging read" in data["command"]
  assert len(data["rows"]) == 2
  assert data["rows"][0] == {
      "timestamp": "2026-11-08T08:38:58.217554736Z",
      "decision": "Blocked",
      "target": "tools/call: send_email",
      "detail": "iap.webServiceVersions.egressViaIAP",
  }
  assert data["rows"][1] == {
      "timestamp": "2026-11-08T08:39:05.028326031Z",
      "decision": "Allowed",
      "target": "tools/call: read_email",
      "detail": "iap.webServiceVersions.egressViaIAP",
  }


def test_parsers_fallback_branches():
  ing = main._parse_ingress_entry({
      "receiveTimestamp": "2026-11-08T09:00:00Z",
      "jsonPayload": {
          "sanitizationResult": {
              "sanitizationVerdict": "MODEL_ARMOR_SANITIZATION_VERDICT_BLOCK",
              "sanitizationVerdictReason": "Prompt injection",
          }
      },
  })
  assert ing["decision"] == "Blocked"
  assert ing["detail"] == "Prompt injection"

  egr_tool = main._parse_egress_entry({
      "timestamp": "2026-11-08T09:00:00Z",
      "protoPayload": {
          "authorizationInfo": [{"granted": True}],
          "metadata": {"mcp_attributes": {"mcp_tool_name": "get_doc"}},
      },
  })
  assert egr_tool["target"] == "get_doc"

  egr_method = main._parse_egress_entry({
      "timestamp": "2026-11-08T09:00:00Z",
      "protoPayload": {
          "authorizationInfo": [{"granted": True}],
          "metadata": {"mcp_attributes": {"mcp_method": "tools/list"}},
      },
  })
  assert egr_method["target"] == "tools/list"

  egr_res = main._parse_egress_entry({
      "timestamp": "2026-11-08T09:00:00Z",
      "protoPayload": {
          "resourceName": "projects/1/locations/l/mcpServers/srv-1",
          "authorizationInfo": [{"granted": False}],
      },
  })
  assert egr_res["target"] == "srv-1"
  assert egr_res["decision"] == "Blocked"


def test_chat_remote_and_local_branches(client, monkeypatch):
  # Non-existent local agent.
  r1 = client.post(
      "/chat",
      json={"agent_type": "local", "local_agent": "no_such_agent_xyz"},
      headers=IAP,
  )
  assert "not found" in r1.text

  # Fake remote agent streaming and auth resume.
  class FakeRuntime:

    async def async_create_session(self, user_id):
      _ = user_id
      return {"id": "sess-99"}

    async def async_stream_query(self, user_id, message, session_id):
      _ = (user_id, message, session_id)
      yield {
          "content": {
              "parts": [
                  {
                      "function_call": {
                          "id": "fc-1",
                          "name": "adk_request_credential",
                          "args": {},
                      }
                  },
                  {"text": "Hello from remote agent"},
              ]
          }
      }

  class FakeRuntimes:

    def get(self, name):
      _ = name
      return FakeRuntime()

    def list(self):
      class Item:
        api_resource = type(
            "R",
            (),
            {"name": "projects/p/locations/l/reasoningEngines/1", "display_name": "A1"},
        )()

      return [Item()]

  class FakeClient:

    def __init__(self, **unused_kwargs):
      self.runtimes = FakeRuntimes()

  monkeypatch.setattr(main.agentplatform, "Client", FakeClient)
  assert "A1" in client.get("/list_agents?project_id=p&location=l").text

  r2 = client.post(
      "/chat",
      json={"message": "hi", "project_id": "p", "location": "l", "agent_id": "1"},
      headers=IAP,
  )
  assert "Hello from remote agent" in r2.text

  r3 = client.post(
      "/chat",
      json={
          "message": "",
          "project_id": "p",
          "location": "l",
          "agent_id": "1",
          "session_id": "sess-99",
          "is_auth_resume": True,
          "auth_request_function_call_id": "fc-1",
          "auth_config": {"exchanged_auth_credential": {}},
      },
      headers=IAP,
  )
  assert "Hello from remote agent" in r3.text

