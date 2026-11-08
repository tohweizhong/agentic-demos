"""Agent Runtime entry point. Terraform sets entrypoint_object to "app".

AdkApp uses Agent Runtime Sessions when the agent runs on Agent Runtime.
"""

from agentplatform.frameworks import AdkApp

from agent import root_agent

app = AdkApp(agent=root_agent, enable_tracing=True)
