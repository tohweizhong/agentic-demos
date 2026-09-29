# Multi-Agent ADK Example

Distributed multi-agent system built with the Google Agent Development Kit (ADK), MCP Toolbox, and Cloud Run.

## Components

- [campaign_orchestrator/](campaign_orchestrator/): Root orchestrator agent deployed to Vertex AI Agent Engine (`deploy_agent_engine.py`).
- [creative_director/](creative_director/): Creative director agent with `data_analyst` (and `mcp-toolbox`) and `market_researcher` sub-agents.
- [financial_analyst/](financial_analyst/): Financial analyst agent service packaged for Cloud Run.
