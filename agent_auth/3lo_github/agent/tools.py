"""GitHub MCP toolset that uses Auth Manager for 3-legged OAuth (3LO).

The agent never holds a GitHub secret. When the agent calls a GitHub tool,
ADK asks Auth Manager for the token of the current user. If no token exists,
ADK sends a consent request to the client, and the user signs in to GitHub.
"""

from __future__ import annotations

import os

from google.adk.auth.credential_manager import CredentialManager
from google.adk.integrations.agent_identity import GcpAuthProvider
from google.adk.integrations.agent_identity import GcpAuthProviderScheme
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

# Register the Google Cloud auth provider in the global credential manager.
CredentialManager.register_auth_provider(GcpAuthProvider())

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"

# Full resource name of the Auth Manager auth provider. The deploy script
# sets this value from the .env file.
AUTH_PROVIDER_NAME = os.environ.get(
    "AUTH_PROVIDER_NAME",
    "projects/YOUR_PROJECT_ID/locations/us-central1/authProviders/YOUR_AUTH_PROVIDER_ID",
)

# The client URL that receives the browser after the user gives consent.
# The client finalizes the credential at this URL.
OAUTH_CONTINUE_URI = os.environ.get(
    "OAUTH_CONTINUE_URI", "http://localhost:8080/validateUserId"
)


def github_toolset() -> McpToolset:
  """Returns the GitHub MCP toolset with 3LO credentials from Auth Manager."""
  auth_scheme = GcpAuthProviderScheme(
      name=AUTH_PROVIDER_NAME,
      # The "repo" scope is necessary to read private repositories.
      scopes=["repo"],
      continue_uri=OAUTH_CONTINUE_URI,
  )
  return McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url=GITHUB_MCP_URL,
          headers={
              "X-MCP-Toolsets": "all",
              "X-MCP-Readonly": "true",
          },
      ),
      auth_scheme=auth_scheme,
  )
