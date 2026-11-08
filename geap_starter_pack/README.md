# GEAP starter pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed.

The GEAP starter pack is the governed platform that a customer receives on handover day. Agents
from an agent factory run on it with the controls on: Agent Identity, Agent Registry, an egress
Agent Gateway, and audit logs.

This folder holds the **mini build**. The mini build proves the pattern in one sandbox project. The
product definition is in [conductor/product.md](conductor/product.md).

## Layout

| Folder | What it holds | Component |
|---|---|---|
| [`terraform/`](terraform/) | APIs, audit logs, IAM, Cloud Run, Agent Registry, Agent Gateway, Model Armor, the agent | 1, 2, 3, 4 |
| [`agent-template/`](agent-template/) | The ADK reference agent | 4 |
| [`mcp-server/`](mcp-server/) | A sample MCP server in Go, with one read-only tool and one write tool | 3 |
| [`policies/`](policies/) | The IAP access policy and the Model Armor settings | 3 |
| [`pipelines/`](pipelines/) | Not built (component 5) | 5 |
| [`runbooks/`](runbooks/) | Add a new agent. Reset the demo | 6 |
| [`scripts/`](scripts/) | Package the agent, ask the agent, read the audit log, clean up | 6 |

## Related folders

These are links only. The starter pack does not use code from them.

- [`agent_auth`](../agent_auth/): the identity baseline and the 3LO auth provider pattern.
- [`curated_codelabs/agent-gateway-governance`](../curated_codelabs/agent-gateway-governance/): the
  egress gateway codelab with IAP policy V1.
