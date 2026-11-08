"""Test settings. The package __init__ imports the agent, which reads these."""

import os

os.environ.setdefault("MCP_SERVER_URL", "https://mcp.example.run.app/mcp")
os.environ.setdefault(
    "MCP_INVOKER_SERVICE_ACCOUNT",
    "invoker@example-project.iam.gserviceaccount.com",
)
