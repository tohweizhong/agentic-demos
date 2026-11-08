"""Unit tests for the client backend (client/main.py).

These tests use the FastAPI test client. They do not call Google Cloud.
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
VALIDATE = ("/validateUserId?user_id_validation_state=YWJj"
            "&auth_provider_name=projects/p/locations/l/authProviders/a")


@pytest.fixture
def client():
  return TestClient(main.app)


@pytest.fixture
def finalize_calls(monkeypatch):
  """Replaces the Auth Manager client. Records the finalize requests."""
  calls = []

  class Fake:

    def __init__(self, **unused_kwargs):
      pass

    def finalize_credentials(self, request):
      calls.append(request)

  monkeypatch.setattr(main, "AuthProviderCredentialsServiceClient", Fake)
  return calls


def test_index_page(client):
  assert "Agent Playground" in client.get("/").text


def test_whoami_with_and_without_iap(client):
  assert client.get("/whoami").json() == {"iap": False, "user_id": None}
  assert client.get("/whoami", headers=IAP).json() == {
      "iap": True, "user_id": "user@example.com"}


def test_config_options(client, monkeypatch):
  monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p1")
  monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
  monkeypatch.setenv("PROJECT_OPTIONS", "p2, p3")
  monkeypatch.delenv("LOCATION_OPTIONS", raising=False)
  data = client.get("/config").json()
  assert data["projects"] == ["p1", "p2", "p3"]
  assert data["locations"] == ["us-central1"]
  assert data["default_project"] == "p1"


def test_demo_endpoints_need_iap(client):
  assert client.post("/demo/reset-consent").status_code == 403
  assert client.get("/demo/access-summaries").status_code == 403


def test_demo_endpoints_need_provider(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME", "")
  assert client.post("/demo/reset-consent", headers=IAP).status_code == 500
  assert client.get("/demo/access-summaries",
                    headers=IAP).status_code == 500


def test_demo_reset_uses_iap_user(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME",
                      "projects/p/locations/l/authProviders/a")
  calls = []

  def fake_call(method, url, body=None):
    calls.append((method, url, body))
    return 200, {}

  monkeypatch.setattr(main, "_demo_call", fake_call)
  data = client.post("/demo/reset-consent", headers=IAP).json()
  assert calls == [("POST", main.AGENT_IDENTITY_API +
                    "/projects/p/locations/l/authProviders/a"
                    ":revokeAuthorization", {"userId": "user@example.com"})]
  assert "--user-id=user@example.com" in data["command"]
  data = client.get("/demo/access-summaries", headers=IAP).json()
  assert data["command"].startswith("gcloud agent-identity access-summaries")
  assert calls[-1][0] == "GET"


def test_demo_config(client, monkeypatch):
  monkeypatch.setattr(main, "DEMO_AUTH_PROVIDER_NAME",
                      "projects/p/locations/l/authProviders/a")
  assert client.get("/demo/config").json()["auth_provider"] == "a"


def test_validate_uses_iap_user_not_cookie(client, finalize_calls):
  client.cookies.set("consent_user_id", "form_user")
  client.cookies.set("consent_nonce", "n1")
  resp = client.get(VALIDATE, headers=IAP)
  assert "agent-auth-complete" in resp.text
  assert finalize_calls[-1].user_id == "user@example.com"


def test_validate_without_iap_uses_cookie(client, finalize_calls):
  client.cookies.set("consent_user_id", "form_user")
  client.cookies.set("consent_nonce", "n1")
  client.get(VALIDATE)
  assert finalize_calls[-1].user_id == "form_user"


@pytest.mark.parametrize("cookies,query,message", [
    ({}, VALIDATE, "user_id cookie"),
    ({"consent_user_id": "u"}, VALIDATE, "consent_nonce cookie"),
    ({"consent_user_id": "u", "consent_nonce": "n"}, "/validateUserId",
     "user_id_validation_state"),
    ({"consent_user_id": "u", "consent_nonce": "n"},
     "/validateUserId?user_id_validation_state=YWJj", "connector_name"),
])
def test_validate_errors(client, finalize_calls, cookies, query, message):  # pylint: disable=unused-argument
  for k, v in cookies.items():
    client.cookies.set(k, v)
  assert message in client.get(query).json()["message"]


def test_validate_finalize_error(client, monkeypatch):

  class Failing:

    def __init__(self, **unused_kwargs):
      pass

    def finalize_credentials(self, unused_request):
      raise RuntimeError("boom")

  monkeypatch.setattr(main, "AuthProviderCredentialsServiceClient", Failing)
  client.cookies.set("consent_user_id", "u")
  client.cookies.set("consent_nonce", "n")
  assert "boom" in client.get(VALIDATE).json()["message"]


def test_list_local_agents(client):
  assert "agents" in client.get("/list_local_agents").json()


def test_chat_without_local_agent(client):
  resp = client.post("/chat", json={"agent_type": "local"})
  assert "No local agent specified" in resp.text
