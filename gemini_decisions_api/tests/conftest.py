"""Shared pytest settings."""

import os

# Do not build the real agent from .env when tests import decisions_agent.agent.
os.environ.setdefault("DECISIONS_AGENT_SKIP_BUILD", "1")
# The ADK Gemini model needs a key value at creation time. Tests replace the client.
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-used")
