"""Tests for the MCP toolset and the ID token source."""

import pytest

import tools


class FakeIdTokenCredentials:
  """Acts like google.auth IDTokenCredentials. Counts the refresh calls."""

  def __init__(self):
    self.valid = False
    self.token = None
    self.refresh_count = 0

  def refresh(self, request):
    del request
    self.refresh_count += 1
    self.token = f"id-token-{self.refresh_count}"
    self.valid = True


def make_source(fake):
  return tools.InvokerTokenSource(
      audience="https://mcp.example.run.app",
      invoker_email="invoker@example-project.iam.gserviceaccount.com",
      credentials_factory=lambda audience, email: fake,
      request_factory=lambda: object(),
  )


def test_audience_is_the_service_url_without_the_path():
  assert (
      tools.audience_for("https://mcp.example.run.app/mcp")
      == "https://mcp.example.run.app"
  )


def test_audience_rejects_a_url_without_https():
  with pytest.raises(ValueError):
    tools.audience_for("http://mcp.example.run.app/mcp")


def test_token_refreshes_once_and_then_uses_the_cache():
  fake = FakeIdTokenCredentials()
  source = make_source(fake)
  assert source.token() == "id-token-1"
  assert source.token() == "id-token-1"
  assert fake.refresh_count == 1


def test_token_refreshes_again_when_it_is_no_longer_valid():
  fake = FakeIdTokenCredentials()
  source = make_source(fake)
  source.token()
  fake.valid = False
  assert source.token() == "id-token-2"


def test_headers_have_a_bearer_token():
  source = make_source(FakeIdTokenCredentials())
  assert source.headers(None) == {"Authorization": "Bearer id-token-1"}


def test_credentials_factory_receives_audience_and_email():
  seen = {}

  def factory(audience, email):
    seen["audience"] = audience
    seen["email"] = email
    return FakeIdTokenCredentials()

  source = tools.InvokerTokenSource(
      audience="https://mcp.example.run.app",
      invoker_email="invoker@example-project.iam.gserviceaccount.com",
      credentials_factory=factory,
      request_factory=lambda: object(),
  )
  source.token()
  assert seen == {
      "audience": "https://mcp.example.run.app",
      "email": "invoker@example-project.iam.gserviceaccount.com",
  }


def test_toolset_needs_the_mcp_settings():
  with pytest.raises(RuntimeError, match="MCP_SERVER_URL"):
    tools.work_items_toolset(env={})


def test_toolset_uses_the_url_and_the_header_provider():
  env = {
      "MCP_SERVER_URL": "https://mcp.example.run.app/mcp",
      "MCP_INVOKER_SERVICE_ACCOUNT": (
          "invoker@example-project.iam.gserviceaccount.com"
      ),
  }
  toolset = tools.work_items_toolset(env=env)
  assert toolset._connection_params.url == env["MCP_SERVER_URL"]
  assert toolset._header_provider is not None


def test_default_factory_impersonates_the_invoker_account(monkeypatch):
  source = object()
  monkeypatch.setattr(
      tools.google.auth, "default", lambda scopes: (source, "example-project")
  )
  made = {}

  def fake_credentials(**kwargs):
    made["target"] = kwargs
    return "target-credentials"

  def fake_id_token_credentials(**kwargs):
    made["id_token"] = kwargs
    return "id-token-credentials"

  monkeypatch.setattr(
      tools.impersonated_credentials, "Credentials", fake_credentials
  )
  monkeypatch.setattr(
      tools.impersonated_credentials,
      "IDTokenCredentials",
      fake_id_token_credentials,
  )
  result = tools._impersonated_id_token_credentials(
      "https://mcp.example.run.app", "invoker@example.iam.gserviceaccount.com"
  )
  assert result == "id-token-credentials"
  assert made["target"]["source_credentials"] is source
  assert (
      made["target"]["target_principal"]
      == "invoker@example.iam.gserviceaccount.com"
  )
  assert made["id_token"]["target_credentials"] == "target-credentials"
  assert made["id_token"]["target_audience"] == "https://mcp.example.run.app"
