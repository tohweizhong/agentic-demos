# agentic-demos

Self-contained demos, starter packs, utilities, and codelabs for Gemini Enterprise Agent Platform (GEAP), Agent Development Kit (ADK), Agent-to-Agent (A2A), and Model Context Protocol (MCP).

## Gemini Enterprise Agent Platform (GEAP)

* [agent_governance_starter_pack](./agent_governance_starter_pack/): Governed agent platform on GEAP with Terraform tiers for Agent Identity, Agent Registry, egress and ingress Agent Gateways (IAP policy V2 and Model Armor), audit logs, Day-2 operations scripts, and an ADK reference agent on Agent Runtime.
* [agent_services_starter_pack](./agent_services_starter_pack/): ADK sample code for Sessions, Memory Bank, and OpenTelemetry observability on Agent Runtime in `asia-southeast1`. Complements [agent_governance_starter_pack](./agent_governance_starter_pack/).
* [agent_auth](./agent_auth/): Agent Identity and Auth Manager demos (three-legged OAuth GitHub consent flow with a Cloud Run client behind Identity-Aware Proxy).
* [managed_agents_api](./managed_agents_api/): Managed Agents API demo on GEAP: agent lifecycle, a data analyst agent in a managed sandbox with a Cloud Storage mount, sessions, tool overrides, the BigQuery MCP server, a Skill Registry skill, evaluation, and a Go and TypeScript web UI.
* [gemini_decisions_api](./gemini_decisions_api/): Gemini Decisions API demo: typed yes/no, choice, and score decisions in Python, an evaluation command, and an ADK router agent.
* [okf_context_sets](./okf_context_sets/): Push an Open Knowledge Format (OKF) bundle into a Knowledge Catalog context set with `kcmd`, pull it back, load a matching BigQuery table, and test it in a Gemini Enterprise app.
* [agents_cli](./agents_cli/): Agents generated and managed with `agents-cli` (for example `hr-onboarding-agent`).

## ADK and Agent-to-Agent (A2A)

* [adk2_examples](./adk2_examples/): Three ADK 2.0 workflow examples: conditional graph routing, human-in-the-loop pause and resume, and iterative code-and-fix loops.
* [adk_multiagent](./adk_multiagent/): Multi-agent ADK example (Campaign Orchestrator, Creative Director, and Financial Analyst).
* [adk_mcp_explainer](./adk_mcp_explainer/): Secure FastMCP server and ADK client agent playground on Cloud Run.
* [a2a_adk_sample](./a2a_adk_sample/): Deploying an A2A-enabled ADK agent to Cloud Run and registering it with Gemini Enterprise.
* [a2a_from_scratch](./a2a_from_scratch/): A2A protocol demo with a purchasing concierge agent and remote seller agents.

## Gemini Enterprise Utilities

* [ge_utils](./ge_utils/): Auxiliary scripts and tools for Gemini Enterprise:
  * [ae_ge_publish](./ge_utils/ae_ge_publish/): ADK to Agent Engine to Gemini Enterprise registration.
  * [agentspace_stream_assist](./ge_utils/agentspace_stream_assist/): Invoking Gemini Enterprise agents with the `streamAssist` API.
  * [ge-prober](./ge_utils/ge-prober/): Go synthetic monitoring tool and smoke prober for Gemini Enterprise.
  * [ge_license_distribute](./ge_utils/ge_license_distribute/): Gemini Enterprise license distribution scripts.
  * [ge_list_agents](./ge_utils/ge_list_agents/): Gemini Enterprise agent lister and identity resolver.
  * [sdp_content_policy](./ge_utils/sdp_content_policy/): Scripts for managing Sensitive Data Protection content policies on data stores.
  * [ge_wif_scim_check](./ge_utils/ge_wif_scim_check/): Script to check a Workforce Identity Federation pool for SCIM tenants and provider attribute mappings.

## Codelabs

* [codelabs](./codelabs/): Authored codelabs for Antigravity, ADK, and MCP:
  * [adk-im8-compliance-agent](./codelabs/adk-im8-compliance-agent/): IM8 compliance agent built with Agents CLI and ADK, deployed to Agent Runtime and Gemini Enterprise.
  * [adk-im8-compliance-agent-mcp](./codelabs/adk-im8-compliance-agent-mcp/): Autonomous IM8 compliance checking and remediation agent built with Antigravity and FastMCP.
  * [build-nus-transit-hub-antigravity](./codelabs/build-nus-transit-hub-antigravity/): NUS Campus Transit Hub and Telegram Bot built with Next.js 16 and grammY.
  * [build-parallel-multi-agent-chemistry-assistant](./codelabs/build-parallel-multi-agent-chemistry-assistant/): Organic Chemistry parallel multi-agent research and lab inventory companion.
* [curated_codelabs](./curated_codelabs/): Public codelabs by other authors, with run notes, fixes, and demo talking points:
  * [agent-gateway-governance](./curated_codelabs/agent-gateway-governance/): Agent Gateway with IAP per-tool egress policy and Model Armor, for an ADK agent on Agent Runtime and Gemini Enterprise.

## Earlier Samples and Notebooks

* [adk_101](./adk_101/): ADK 101 training notebook for Vertex AI Workbench.
* [adk_cloud_run](./adk_cloud_run/): Quickstart notes for deploying an ADK agent to Google Cloud Run.
* [deep_research](./deep_research/): Prototyping the Gemini Deep Research and Interactions API.
* [doc_ai](./doc_ai/): Sample notebook and test PDFs for Vertex AI Document AI.
* [gemini_supervised_fine_tuning](./gemini_supervised_fine_tuning/): Jupyter Notebook for Gemini Supervised Fine-Tuning (SFT).
* [gemini_transcription](./gemini_transcription/): Real-time audio transcription and streaming with the Gemini Multimodal Live API.
* [vertex_ai_custom_ml_models](./vertex_ai_custom_ml_models/): Training and deploying custom machine learning models on Vertex AI.
