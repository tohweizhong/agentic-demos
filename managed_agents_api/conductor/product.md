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

Track 1 (complete) has features 1 to 4. Feature 5 moved to a later track.

1. **Agent lifecycle.** Create, get, list, update, and delete an agent. Poll the
   long-running operation that `CreateAgent` returns. The only supported
   `base_agent` value is `antigravity-preview-05-2026`. The only supported location
   is `global`.
2. **Interactions.** Send a single-turn interaction. Continue a multi-turn session.
   Override the agent tools for one interaction (the demo adds Google Search).
3. **Skills.** Put an `AGENTS.md` file and a `SKILL.md` file into the sandbox. The skill
   tells the agent how to write the report. The API does not accept inline sources, so
   these files come from the Cloud Storage bucket.
4. **Cloud Storage mount.** Mount a Cloud Storage bucket at `/workspace/.agent`. The agent
   reads the input CSV file from the bucket and writes the report and the chart back to it.
   The Preview API needs the `*` network allowlist when a data source is set.
5. **MCP server tools (later track).** Connect the Google-hosted BigQuery MCP server. This
   requires the `roles/mcp.toolUser` IAM role.

## Format

- Numbered Python scripts, one for each feature. Each script runs alone.
- One step-by-step Jupyter notebook that follows the same order.
- One REST script with `curl` commands for reference.
- One cleanup script that deletes every agent that the demo created, and the bucket.

## Later tracks (not in the first version)

- MCP server tools, for example the BigQuery MCP server.
- Skills from the Skill Registry.
- Download of the output files, and a bucket in another project.
- A web UI: a TypeScript frontend and a Go backend. The repository rules select
  these languages.
- URL context tool, and Google Search in the stored agent configuration.
- Evaluation with the GenAI Evaluation Service.

## Success criteria

- A new user runs the first script within 10 minutes of a clean clone.
- Every script prints what it sends and what it receives.
- The cleanup script leaves no agents in the project.
