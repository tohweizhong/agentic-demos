"""MCP toolset for the sample MCP server.

The agent calls the MCP server through the egress Agent Gateway. Cloud Run
checks an ID token. The agent gets that token for one invoker service account.
The agent has the token creator role on that account only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import os
import threading
from typing import Any
from urllib import parse

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport import requests as google_auth_requests
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
_MCP_TIMEOUT_SECONDS = 30.0


def audience_for(url: str) -> str:
  """Returns the Cloud Run audience for an MCP URL: the URL without the path."""
  parts = parse.urlsplit(url)
  if parts.scheme != "https" or not parts.netloc:
    raise ValueError(f"The MCP server URL must use https: {url!r}")
  return f"{parts.scheme}://{parts.netloc}"


def _impersonated_id_token_credentials(audience: str, invoker_email: str) -> Any:
  """Makes ID token credentials for the invoker account from the agent identity."""
  source, _ = google.auth.default(scopes=[_CLOUD_PLATFORM_SCOPE])
  target = impersonated_credentials.Credentials(
      source_credentials=source,
      target_principal=invoker_email,
      target_scopes=[_CLOUD_PLATFORM_SCOPE],
      lifetime=3600,
  )
  return impersonated_credentials.IDTokenCredentials(
      target_credentials=target,
      target_audience=audience,
      include_email=True,
  )


class InvokerTokenSource:
  """Gives an ID token for the invoker account, and keeps it until it expires."""

  def __init__(
      self,
      audience: str,
      invoker_email: str,
      credentials_factory: Callable[[str, str], Any] = _impersonated_id_token_credentials,
      request_factory: Callable[[], Any] = google_auth_requests.Request,
  ):
    self._audience = audience
    self._invoker_email = invoker_email
    self._credentials_factory = credentials_factory
    self._request_factory = request_factory
    self._credentials = None
    self._lock = threading.Lock()

  def token(self) -> str:
    """Returns a valid ID token. Gets a new token when the old one is not valid."""
    with self._lock:
      if self._credentials is None:
        self._credentials = self._credentials_factory(
            self._audience, self._invoker_email
        )
      if not self._credentials.valid:
        self._credentials.refresh(self._request_factory())
      return self._credentials.token

  def headers(self, readonly_context: Any = None) -> dict[str, str]:
    """ADK header provider: adds the ID token to each MCP request."""
    del readonly_context
    return {"Authorization": f"Bearer {self.token()}"}


def work_items_toolset(env: Mapping[str, str] = os.environ) -> McpToolset:
  """Returns the MCP toolset for the sample work items MCP server."""
  url = env.get("MCP_SERVER_URL")
  invoker = env.get("MCP_INVOKER_SERVICE_ACCOUNT")
  if not url or not invoker:
    raise RuntimeError(
        "Set MCP_SERVER_URL and MCP_INVOKER_SERVICE_ACCOUNT. Terraform sets"
        " them on the agent."
    )
  token_source = InvokerTokenSource(audience_for(url), invoker)
  return McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url=url, timeout=_MCP_TIMEOUT_SECONDS
      ),
      header_provider=token_source.headers,
  )
