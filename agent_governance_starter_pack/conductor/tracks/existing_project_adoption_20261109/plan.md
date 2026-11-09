# Plan: lateral paths for existing projects

Status: in progress. Phase 1 built on 09 Nov 2026.

## Phase 1: Discovery

- [x] Task: `scripts/discover.sh` (read-only). Built and tested on 09 Nov 2026 against two projects (4 agents, 2 gateways, 64 registry entries; and the rehearsal project). Lists the resources in the specification, with the
      identity type and gateway bindings of each agent and the registry state of each MCP server.
      Stops with `status: ERROR` when it cannot read the project.
- [x] Task: JSON and Markdown report (`--markdown`). Starter pack resources are marked and left out of the lateral steps. One table for each tier: what exists, what is governed, what is not.
- [x] Task: skill `geap-discover`. Not tested in `agy` yet.

## Phase 2: Adoption plan

- [ ] Task: `scripts/adoption_plan.sh --tier N` reads the discovery JSON and prints the lateral steps
      for tier N, with risk and order. No change to the project.
- [ ] Task: `geap-configure` asks "new project or existing project" first, and runs `geap-discover`
      for an existing project.

## Phase 3: Lateral tools

- [ ] Task: register an existing MCP server (Terraform `google_agent_registry_service`, tool spec from
      the server or from a file).
- [ ] Task: move an agent to `AGENT_IDENTITY` (deploy again or update in place), and grant its roles to
      the new principal. Record the old principal for clean-up.
- [ ] Task: bind an agent to the egress or ingress gateway (`agentGatewayConfig` in Terraform).
- [ ] Task: add IAP access policy rules for an agent principal and its tools, in `DRY_RUN`.
- [ ] Task: skill `geap-adopt` with an approval gate before each change.

## Phase 4: Rehearsal

- [ ] Task: test project with two agents and two MCP servers that the starter pack did not create.
- [ ] Task: lateral path to Tier 3 in `DRY_RUN`, read the decisions, then `ENFORCE`.
- [ ] Task: record the results in this track and in GUIDE.md.
