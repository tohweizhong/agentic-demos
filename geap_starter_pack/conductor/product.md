# Product Definition: GEAP Starter Pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed.

## Summary

The GEAP starter pack is the governed platform that a customer receives on handover day. Agents
that an agent factory builds run on it with the controls on. A services team builds it once. Each
new agent then uses it. The starter pack is more than Terraform: it is a repository, a working
environment with one reference agent, runbooks, and enablement.

## Problem

An agent factory builds many agents. Each deployed agent gets a new principal. Each principal needs
grants, a catalog entry, and egress rules. Without a shared platform, each team repeats this work,
and grants stay after an agent is removed.

## Users

| User | Need |
|---|---|
| Platform owner (customer) | One governed place where agents run, with controls that they own |
| Security reviewer | Policies kept apart from code, in files that they can review |
| Agent factory team | A reference agent template and a pipeline that deploys their output |
| Operators | Runbooks to add an agent, grant a tool, change a policy, and read a trace |

## Components

The six components come from the source design. No other component is in scope.

| # | Component | Contents | GEAP services | Mini build |
|---|---|---|---|---|
| 1 | Landing zone | Dev, test, and prod projects in the target region. VPC-SC, CMEK, org policies, regional log buckets. Central IT approvals | Agent Runtime, Observability | Partial. One project, APIs, one regional log bucket. No VPC-SC, no CMEK. |
| 2 | Identity baseline | Agent Identity on. IAM role templates for each agent. No project-level `roles/iam.serviceAccountTokenCreator`. One auth provider pattern for 3LO tools | Agent Identity | Partial. Agent Identity on, agent IAM template with no project-level token creator role. The 3LO auth provider pattern is not in the mini build, because the agent_auth folder shows it. |
| 3 | Catalog and control | Customer MCP servers in Agent Registry. Egress Agent Gateway with an IAP V2 policy, first `DRY_RUN`, then enforce. Regional Model Armor template | Agent Registry, Agent Gateway, Model Armor | Yes. One MCP server on Cloud Run, registered. Egress gateway, IAP policy in `DRY_RUN`, then enforce. Model Armor template. Note: the source design names only an egress gateway. The ingress gateway is a backlog addition from 08 Nov 2026. |
| 4 | Reference agent | One ADK agent on Agent Runtime with Sessions. It calls one MCP server through the gateway. The agent factory uses it as the output template | Agent Runtime, Sessions, ADK | Yes. One ADK agent with Agent Identity and Sessions, bound to the egress gateway. |
| 5 | Agent factory pipeline | CI/CD that takes agent factory output, registers it, deploys it, and promotes it through four stages: build, test, production, retire | Agent Registry, Agent Runtime | No |
| 6 | Operations and handover | Dashboards, runbooks, a playbook to add a new agent, two workshops | Observability | Partial. Two runbooks: add a new agent, and reset the demo. |

## Deliverables on handover day

1. A Git repository: Terraform modules, an ADK agent template, CI/CD pipeline files, and policy files.
2. A working environment, deployed from that repository, with one reference agent that runs end to end.
3. Runbooks: add an agent, grant a tool, change a gateway policy, read a trace.
4. Enablement: workshops, and engineers who build the first one or two agents with the customer.

This repository holds item 1 and the runbooks in item 3. Items 2 and 4 are not files.

## Repository layout

```
geap_starter_pack/
├── terraform/        projects, VPC-SC, CMEK, IAM, registry, gateway
├── agent-template/   ADK agent that the agent factory fills in
├── pipelines/        build, test, prod promotion
├── policies/         IAP gateway policy, Model Armor template
└── runbooks/
```

| Folder | Component |
|---|---|
| `terraform/` | 1, 2, 3 |
| `agent-template/` | 4 |
| `pipelines/` | 5 |
| `policies/` | 3 |
| `runbooks/` | 6 |

Nothing in these folders is built yet.

## Regions

| Build | Region | Reason |
|---|---|---|
| Target design | `asia-southeast1` | The customer target region. Agent Runtime, Sessions, Agent Identity, Agent Registry, Agent Gateway, and Observability are GA in this region. |
| Mini build | `us-central1` | The Agent Gateway codelabs use this region. The agent must be in the same region as the gateway. |

## Mini build

The mini build proves the pattern in one sandbox project before the full design.

### Goals

1. Prove the controls: the reference agent runs with identity, catalog, gateway control, and audit on.
2. Support a 10-minute demo for a customer platform team. The demo shows identity, catalog,
   gateway control, and audit, in that order.

### Steps

1. Create the repository layout.
2. Terraform: one project, APIs, a regional log bucket, Data Access audit logs for
   `iap.googleapis.com`, an agent IAM template with no project-level token creator role.
3. Terraform: one MCP server on Cloud Run, registered in Agent Registry.
4. Terraform: egress Agent Gateway, IAP policy V2 in `DRY_RUN`, Model Armor template.
5. Deploy the reference ADK agent to Agent Runtime with Agent Identity and Sessions, bound to the
   gateway.
6. Test the call, read the trace and the audit log, change the policy to enforce, and test again.
7. Write two runbooks: add a new agent, and reset the demo.

### IAP policy version

The mini build uses IAP policy V2 (Unified Access Policy).

| Reason | Source |
|---|---|
| The target design uses V2. | Starter pack design |
| Google recommends V2. V1 is the legacy allow policy. | Agent Gateway documentation |
| A move from V1 to V2 is manual. You define the rules again by hand. So a V1 mini build does not carry over to the target design. | Agent Gateway documentation |
| Terraform supports V2 access policies: `google_iam_project_access_policy`, from provider 7.44.0. | Provider changelog |

Risk: the existing egress codelab stack runs V1, and the per-tool denial is proven only on V1. V2 is
not tested in the field yet. If V2 blocks the mini build, fall back to V1 and record the gap.

### Limits

One project, not three. No VPC-SC and no CMEK. Keep the cloud resources for customer demos. A
clean-up script deletes only the mini build resources. Run it after the demos. Keep the repository.

## Related folders (links only)

- Identity baseline: [agent_auth](../../agent_auth/). It shows Agent Identity and the Auth Manager 3LO flow.
- Egress gateway: [curated_codelabs/agent-gateway-governance](../../curated_codelabs/agent-gateway-governance/).

These are links for the reader. The starter pack does not import, copy, or depend on code or
requirements from these folders. It runs from a clean clone with its own files only.

## Out of scope

| Item | Reason |
|---|---|
| GKE as an agent runtime | The starter pack shows the GEAP platform. Agents run on Agent Runtime. |
| Semantic Agent Policy, Agent Anomaly Detection, Evaluation, Managed Agents API | Not available in `asia-southeast1` |
| Memory Bank | Embeddings use `global`. It needs a data residency decision first. |
| Creation of cloud resources during setup | Each deploy needs an approved project first |

## Success criteria for the mini build

- `terraform apply` creates the mini build from a clean clone, with no manual grant.
- The reference agent calls the MCP server through the gateway. The trace shows the call.
- In `DRY_RUN`, a call that the policy does not allow passes. The IAP Data Access audit log
  (`cloudaudit.googleapis.com/data_access`, service `iap.googleapis.com`) records it with
  `request.dryRun=true` and `granted=false`. The gateway request log does not show a denial.
- After the change to enforce, the same call is denied. The agent can show a connection error
  ("MCP session connection lost"), not a clear `403`.
- The IAP Data Access audit log records the denied call.
- The 10-minute demo runs from start to end. The "reset the demo" runbook returns it to its start
  state.
- The clean-up script removes all mini build resources and nothing else.

## Backlog

| Item | Status |
|---|---|
| Ingress gateway (`CLIENT_TO_AGENT`): a second Agent Gateway that controls which clients can call the agent and screens user prompts and agent answers with Model Armor. Bind it with `clientToAgentConfig` on the agent. Reference: the egress codelab is in `curated_codelabs/agent-gateway-governance`. The ingress pattern follows the public Agent Gateway ingress codelab. Do not copy its code | Not built |
| Test option C: replace `iam.allowedPolicyMemberDomains` on the project with `iam.managed.allowedPolicyMembers`, with `allowedMemberSubjects` that names the gateway Service Extensions account. Production pattern for customers | Not tested |
