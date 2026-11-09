# Specification: lateral paths for existing projects

## Problem

The starter pack has one "vertical" path. It starts from a clean project, builds its own reference
agent and MCP server, and moves up from Tier 1 to Tier 5. A customer project usually already has
agents, MCP servers, and sometimes gateways that the starter pack did not create. Today the starter
pack governs only its own resources, and it does not tell the operator what happens to the others.

A "lateral" path brings existing resources to the same tier as the starter pack. Each tier needs a
vertical step (add the control) and a lateral step (put the existing resources under the control).

```
              vertical: add the control
Tier 5  ingress gateway        <-- lateral: bind existing agents, move their clients to the gateway
Tier 4  Model Armor on egress  <-- lateral: no change per agent, every bound agent is screened
Tier 3  egress gateway + IAP   <-- lateral: bind existing agents, add IAP rules for each principal
Tier 2  Agent Registry         <-- lateral: register existing MCP servers and endpoints
Tier 1  Agent Identity         <-- lateral: move existing agents to AGENT_IDENTITY, grant roles
```

## What each tier does to existing resources today

| Tier | Effect on existing resources | Lateral step that is missing |
|---|---|---|
| 1 | None, except that the project-wide grant of `roles/aiplatform.agentDefaultAccess` to the agent principal set also applies to existing Agent Identity agents | Find agents without `AGENT_IDENTITY`. Deploy them again with it (new principal). Grant their roles to the new principal |
| 2 | Only the starter pack MCP server and Google APIs endpoint are registered. Agent Runtime agents can register by themselves (internal assistant, not verified) | Register each existing MCP server and endpoint (tool spec, URL) |
| 3 | An existing agent does not use the gateway until it has `agentGatewayConfig`. After that, it can reach only registered destinations. The IAP access policy names only the starter pack agent | Bind each agent. Add IAP rules for its principal and its tools. Start in `DRY_RUN` and read the decisions before `ENFORCE` |
| 4 | Model Armor screens every agent that is bound to the egress gateway | Domain restricted sharing step for the gateway service agent (once per project) |
| 5 | Every agent that is bound to the ingress gateway is screened | Bind each agent. Change each client to call through the gateway |

## Risks in a project that is in use

- Name collisions with existing gateways, registry entries, Model Armor templates, or log buckets.
- The fixed IAP access policy ID (backlog item 26).
- Project-wide resources: the IAP Data Access audit config and the agent principal set grant.
- A deploy again for `AGENT_IDENTITY` gives a new principal. Old grants stay as inactive grants.
- Binding an agent to the egress gateway in `ENFORCE` can break its calls to unregistered hosts.

## Scope

1. **Discovery (read-only):** list agents (with identity type and gateway bindings), Cloud Run and
   other MCP servers (registered or not), gateways, authz extensions and policies, IAP access policies
   and bindings, Model Armor templates, and project-wide grants. Write a JSON and a Markdown report.
2. **Adoption plan:** for a chosen tier, list each existing resource, the change it needs, the risk,
   and the order. Nothing changes in the project.
3. **Lateral tools:** register an MCP server, move an agent to `AGENT_IDENTITY`, bind an agent to a
   gateway, add IAP rules for an agent principal. Each tool shows a plan and needs approval. Changes
   go through Terraform where the starter pack manages the resource.
4. **Skills:** `geap-discover` and `geap-adopt` for the agent harness, with the same approval gates as
   `geap-deploy`. `geap-configure` asks "new project or existing project" first.
5. **Rehearsal:** a test project with agents and MCP servers that the starter pack did not create,
   taken laterally to Tier 3 in `DRY_RUN`, then `ENFORCE`.

## Out of scope

- Changes to agents on GKE (the starter pack covers Agent Runtime).
- Cross-project registries and gateways (one project only, as now).

## Acceptance criteria

- Discovery finds every agent and MCP server in the test project, with no false facts when a call fails
  (the preflight lesson from 09 Nov 2026).
- The adoption plan for each tier names every change before any change happens.
- In the rehearsal, each existing agent reaches the chosen tier, and its tool calls still work in
  `DRY_RUN`. The IAP decisions for each agent are visible before `ENFORCE`.

## Related backlog items

12 (posture check), 13 (promotion readiness), 14 (onboard an agent), 26 (access policy ID),
28 and 29 (harness and teardown fixes), and the new item 30 for this track.
