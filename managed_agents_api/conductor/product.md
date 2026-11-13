# Product Definition: Managed Agents API Demo

## Summary

This demo shows how to build a managed, autonomous agent with the Managed Agents API
on Gemini Enterprise Agent Platform. The demo uses the Agents API (control plane) to
create and manage a data analyst agent. It uses the Interactions API (data plane) to
send tasks to the agent. The agent runs in an isolated sandbox that the Antigravity
harness controls. In the sandbox, the agent reads a CSV file, runs Python, and writes
a chart and a report. The demo is a short, self-contained teaching example. It runs
from a clean clone after the steps in its own README.

Sources:

- Overview: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents
- Create and manage agents: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/create-manage
- Interact with agents: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/interact-with-agents
- Sandbox environment: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents/sandbox-environment

## Launch stage

The Managed Agents API is a Pre-GA (Preview) product. The demo uses only synthetic
data. Do not put proprietary, sensitive, or confidential data in the demo.

## Audience

Developers and customer engineers who build agents. They want to see the API work in
a few minutes.

## Scenario

A data analyst agent. It reads a synthetic sales CSV file. It runs Python in the
sandbox to analyse the data. It writes a chart (PNG) and a Markdown report.

## Features

All five tracks are complete (13 Nov 2026).

1. **Agent lifecycle (Track 1).** Create, get, list, update, and delete an agent. Poll the
   long-running operation. The only supported `base_agent` value is
   `antigravity-preview-05-2026`. The only supported location is `global`.
2. **Interactions (Track 1).** A single-turn interaction, a multi-turn session, and a tool
   override for one interaction (Google Search).
3. **Skills in the bucket (Track 1).** `AGENTS.md` and the `report-writer` skill come from the
   Cloud Storage bucket. The API does not accept inline sources.
4. **Cloud Storage mount (Track 1).** The bucket is mounted at `/workspace/.agent`. The agent
   writes the report and the chart back to it. The Preview API needs the `*` network allowlist
   when a data source is set.
5. **Output download (Track 2).** The report and the chart go to the local `output/` folder.
6. **BigQuery MCP server (Track 2).** One interaction gets the Google-hosted BigQuery MCP server
   with a short-lived token. The token is not stored in the agent.
7. **Skill Registry (Track 3).** A skill published to Skill Registry in `us-central1` and mounted
   in a second agent with a `skill_registry` source.
8. **Evaluation (Track 4).** Task success and safety scores for a recorded interaction and for
   generated scenarios, in a second environment.
9. **Web UI (Track 5).** A Go backend and a TypeScript frontend that stream a task and show the
   output files.

## Format

- Numbered Python scripts, one for each feature. Each script runs alone.
- One step-by-step Jupyter notebook that follows the same order.
- One REST script with `curl` commands for reference.
- One cleanup script for the agents, the bucket, and the registry skill.
- A local web UI in `webui/`.

## Not built

- A bucket in another project. It needs a second project, and the test used one project.
- MCP servers other than BigQuery.
- The `final_response_quality_v1` metric. Its default judge model was not found in the test.
- Cloud Run deployment of the web UI. The `Dockerfile` exists, but it was not deployed.

## Success criteria

- A new user runs the first script within 10 minutes of a clean clone.
- Every script prints what it sends and what it receives.
- The cleanup script leaves no agents in the project.
