# Product Definition: Agent Governance Starter Pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed.

## Summary

The agent governance starter pack is the governed platform that a customer receives on handover day. Agents
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
| 6 | Operations and handover | Dashboards, runbooks, a playbook to add a new agent, two workshops | Observability | Partial. Two runbooks: add a new agent (`add_agent.md`), and switch policy mode (`switch_policy_mode.md`). |

## Deliverables on handover day

1. A Git repository: Terraform modules, an ADK agent template, CI/CD pipeline files, and policy files.
2. A working environment, deployed from that repository, with one reference agent that runs end to end.
3. Runbooks: add an agent, grant a tool, change a gateway policy, read a trace.
4. Enablement: workshops, and engineers who build the first one or two agents with the customer.

This repository holds item 1 and the runbooks in item 3. Items 2 and 4 are not files.

## Repository layout

```
agent_governance_starter_pack/
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
2. Give a customer platform team a repeatable check of identity, catalog, gateway control, and
   audit, in that order.

### Steps

1. Create the repository layout.
2. Terraform: one project, APIs, a regional log bucket, Data Access audit logs for
   `iap.googleapis.com`, an agent IAM template with no project-level token creator role.
3. Terraform: one MCP server on Cloud Run, registered in Agent Registry.
4. Terraform: egress Agent Gateway, IAP policy V2 in `DRY_RUN`, Model Armor template.
5. Deploy the reference ADK agent to Agent Runtime with Agent Identity and Sessions, bound to the
   gateway.
6. Test the call, read the trace and the audit log, change the policy to enforce, and test again.
7. Write two runbooks: add a new agent, and switch the policy mode.

### Governance tiers

The mini build splits the controls into five progressive tiers so a customer can start with Tier 1 and turn on higher tiers as approvals arrive:

| Tier | Name | GEAP Services | Terraform Variable | Key Behavior |
|---|---|---|---|---|
| **Tier 1** | **Identity and Runtime Baseline** | Agent Runtime (`AGENT_IDENTITY` and Sessions), Cloud Run MCP server, regional Cloud Logging bucket | *(Always on)* | Every agent gets a unique SPIFFE identity and calls the MCP server with Cloud Run IAM (`roles/run.invoker`). Needs no organization policy changes |
| **Tier 2** | **Catalog and Discovery** | Agent Registry (`mcpServers` and `endpoints`) | `enable_agent_registry` (default `true`) | Registers the MCP server and API endpoints in Agent Registry |
| **Tier 3** | **Outbound Access Control (Egress IAP)** | Egress Agent Gateway (`AGENT_TO_ANYWHERE`) and IAP Policy V2 (`REQUEST_AUTHZ` in `DRY_RUN` or `ENFORCE`) | `enable_egress_gateway` (default `true`) | Enforces per-tool CEL rules on outbound agent traffic. Needs no domain restriction exception when `enable_model_armor = false` |
| **Tier 4** | **Content Safety (Model Armor)** | Model Armor templates, `CONTENT_AUTHZ` extension, and 3 `gcp-sa-dep` IAM grants | `enable_model_armor` (default `true`) | Screens prompts and tool outputs for prompt injection, jailbreaks, and sensitive data on active gateways. **Only Tier 4 needs the domain restriction setup** |
| **Tier 5** | **Inbound Client Control (Ingress Gateway)** | Ingress Agent Gateway (`CLIENT_TO_AGENT`) and `clientToAgentConfig` (attaches Model Armor when `enable_model_armor = true`) | `enable_ingress_gateway` (default `false`) | Controls inbound client traffic to the agent |

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

One project, not three. No VPC-SC and no CMEK. A clean-up script deletes only the mini build
resources. Keep the repository.

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
- The checks run from start to end. The "switch policy mode" runbook returns the environment to its
  start state.
- The clean-up script removes all mini build resources and nothing else.

## Backlog

This table is the single list of open starter pack work. [tracks.md](tracks.md) links to it.

### Test status

An agent tested the starter pack live on 08 Nov 2026 in 4 stages: a harness check, a full project reset, the five tiers from zero, and the onboarding of a second agent. An agent also tested all five tiers in `asia-southeast1` on 09 Nov 2026 ([region test track](tracks/region_test_20261109/plan.md)). The repository owner did not do a manual test yet. The steps are in the [manual test track](tracks/manual_test_20261109/plan.md).

| # | Item | Status |
|---|---|---|
| 1 | Ingress gateway (`CLIENT_TO_AGENT`): a second Agent Gateway that controls which clients can call the agent and screens user prompts and agent answers with Model Armor. Bind it with `clientToAgentConfig` on the agent. Reference: the egress codelab is in `curated_codelabs/agent-gateway-governance`. The ingress pattern follows the public Agent Gateway ingress codelab. Do not copy its code | Done (08 Nov 2026). Added `google_network_services_agent_gateway.ingress` (`CLIENT_TO_AGENT`), `ingress_model_armor` policy, `client_to_agent_config` binding, and the 5-tier Governance Tiers model (`enable_agent_registry`, `enable_egress_gateway`, `enable_model_armor`, `enable_ingress_gateway`) |
| 2 | Test option C: replace `iam.allowedPolicyMemberDomains` on the project with `iam.managed.allowedPolicyMembers`, with `allowedMemberSubjects` that names the gateway Service Extensions account. Production pattern for customers | Done (08 Nov 2026). Tested on the sandbox project. `iam.managed.allowedPolicyMembers` allows the `gcp-sa-dep` service agent, but `iam.allowedPolicyMemberDomains` and `iam.managed.allowedPolicyMembers` are evaluated separately. `iam.allowedPolicyMemberDomains` must also be relaxed on the project or migrated at the organization level |
| 3 | IAP audit log gap: the IAP Data Access audit log has no entry for `tools/call` decisions, with policy V1 or V2 | Filed (08 Nov 2026). Tracked in issue tracker |
| 4 | V1 comparison | Done (08 Nov 2026). V1 and V2 both deny `update_status`. The IAP audit log records only MCP base methods with both versions. The gateway request log recorded the V1 denial (`403`, `DENIED`), but not the V2 denial |
| 5 | Bug draft for the `python_spec` start failure behind an egress gateway | Filed (08 Nov 2026). Tracked in issue tracker along with the IAP V2 log gap and the domain restricted sharing documentation gap |
| 6 | Return the environment to its start state. `terraform.tfvars` is at `ENFORCE` | Done (08 Nov 2026). Reset `iap_enforcement_mode` to `DRY_RUN` |
| 7 | Keep [GUIDE.md](../GUIDE.md) current after each step | Ongoing |
| 8 | Preflight scan: a read-only script (`scripts/preflight.sh`) that checks the target project before any change and writes a JSON go or no-go report. It checks org policies that affect the build (domain restricted sharing and others), enabled APIs, caller roles, billing, existing gateways, agents, Agent Registry entries, and Cloud Run services with the same names, and an existing Terraform state | Done (08 Nov 2026). `scripts/preflight.sh` tested on the sandbox project (`status: GO`) |
| 9 | Antigravity CLI harness: skills `geap-preflight`, `geap-deploy`, `geap-verify`, `geap-reset`, `geap-teardown` that call the scripts. An `AGENTS.md` with the safety rules (one project, no org-level change, stop on error). A `settings.json` permission list that allows read-only `gcloud` and `terraform plan`, and needs a person to approve `terraform apply`. Headless runs only for preflight and plan (`agy -p ... --output-format json`). The `agy` flags come from Duckie and are not checked in public docs: Not verified | Done (08 Nov 2026). Added `.agents/skills/geap-*`, `AGENTS.md`, and `settings.json` |
| 10 | The repository `.gitignore` excludes `.agents/`. Options: an exception rule for `agent_governance_starter_pack/.agents/`, or another folder for the skills | Done (08 Nov 2026): added `!agent_governance_starter_pack/.agents/` to the repository `.gitignore` |
| 11 | Claude Code harness: `CLAUDE.md` (imports `AGENTS.md`), `.claude/settings.json` (the same allow, ask, and deny lists as `settings.json`), and `.claude/skills` (a symlink to `.agents/skills`, so the five `geap-*` skills have one copy). The original plan used `.claude/commands/` slash commands. Skills replace them | Draft built (09 Nov 2026). Tested by an agent on a Cloud Workstation with Claude Code 2.1.319 on Vertex AI: the skills load through the symlink, `CLAUDE.md` imports `AGENTS.md`, headless `geap-preflight` runs, the permission rules block `terraform apply` (`ask`) and `gcloud org-policies set-policy` (`deny`), and `terraform plan` runs from the `allow` list. Not tested: `terraform apply` through the harness, and `managed-settings.json`. Not manually tested by the repository owner |
| 12 | Live Posture and Rogue Agent Doctor (`scripts/doctor.sh` and `geap-doctor` skill): scan live `reasoningEngines`, gateways, IAM bindings, and `AuthzPolicy` resources to flag any agent missing gateway bindings. Also find stale grants of deleted agents (`principal://.../reasoningEngines/<ID>` members whose agent no longer exists) in the project policy, the service account policies, and the gateway access policy Planned in `day2/`. | Not built |
| 13 | Policy Promotion Readiness Report (`scripts/check_promotion.sh` and `geap-promote` skill): query Cloud Logging over a lookback window to list which agent principals and tools will be blocked before switching `iap_enforcement_mode` from `DRY_RUN` to `ENFORCE`. Planned in `day2/`. | Not built |
| 14 | Automated Agent Onboarding (`scripts/onboard_agent.sh` and `geap-onboard-agent` skill): scaffold the Terraform resource block, single-principal IAM grants, and `DRY_RUN` IAP rule for a new agent. Planned in `day2/`. | Not built |
| 15 | MCP Tool Spec Policy Linter (`scripts/check_tool_policy.sh` and `geap-audit-tools` skill): compare `mcp-server/tool_spec.json` against `policies/iap_access_policy.yaml` and fail if any non-read-only tool lacks an explicit IAP rule. Planned in `day2/`. | Not built |
| 16 | Emergency Agent Quarantine (`scripts/quarantine_agent.sh` and `geap-quarantine` skill): revoke one `AGENT_ID` principal from `roles/iam.serviceAccountTokenCreator` and the IAP access policy without disrupting shared gateways. Planned in `day2/`. | Not built |
| 17 | Multi-Harness Skill Installer (`scripts/install_harness.sh`): install the starter pack rules and skills into `.agents/skills/`, `~/.gemini/config/skills/`, or `CLAUDE.md` and `.claude/commands/` | Not built |
| 18 | Policy-as-Code Model Armor Config: read `policies/model_armor_config.yaml` with `yamldecode()` in `terraform/gateway.tf` so security teams can tune filter thresholds in YAML (`policies/model_armor.yaml` is currently loaded with `yamldecode()` in `terraform/gateway.tf`) | Not built |
| 19 | Drop-In CI Validation Pipeline (`pipelines/cloudbuild-pr-check.yaml` and `pipelines/github-actions-pr-check.yaml`): run `terraform fmt -check`, `terraform validate`, `terraform test`, tool policy linting, `go test`, and `pytest` on pull requests. Planned in `day2/`. | Not built |
| 20 | Remote Terraform State Bootstrap (`scripts/init_remote_state.sh`): create a versioned GCS bucket (`gs://PROJECT_ID-tfstate`), write `terraform/backend.tf`, and migrate local state. Planned in `day2/`. | Not built |
| 21 | Cloud Monitoring Governance Dashboard (`policies/geap_dashboard.json`): define panels for Model Armor blocks, gateway status codes, and Cloud Run MCP latency. Planned in `day2/`. | Not built |
| 22 | Multi-Agent Least-Privilege Example: show a `reader` agent principal denied `update_status` alongside an `approver` agent principal allowed `update_status` in `policies/iap_access_policy.yaml` | Not built |
| 23 | Day-1 Handover Sign-Off Checklist (`runbooks/handover_checklist.md`): provide a verification checklist for GCS state migration, org policy setup, quota checks, tier selection, and emergency contacts | Not built |
| 24 | Principal access boundary for agents: bind a principal access boundary policy at the project to the agent identities principal set `//agents.global.org-ORGANIZATION_ID.system.id.goog/attribute.container/projects/PROJECT_NUMBER`, so the agents of one project can get access only to the resources in the boundary. An organization administrator must create the policy. Not tested. Planned in `day2/`. | Not built |
| 25 | agents-cli agent behind the starter pack gateways: deploy a second agent with `agents-cli deploy --agent-identity --agent-gateway-egress <egress gateway> --agent-gateway-ingress <ingress gateway>`, add its principal to the IAP access policy and the IAM grants in Terraform, and check that the egress deny, Model Armor, and the ingress screen work for it. Also check how a client calls it, because `agents-cli deploy` builds a container with no class methods | Not built |
| 26 | Prefix the IAP access policy ID: `policies/iap_access_policy.yaml` sets `access_policy_id: geap-agent-egress`, which does not use `name_prefix`. Two copies in one project collide on this policy. Build the ID from `name_prefix` in `terraform/gateway.tf` (for example `${var.name_prefix}-agent-egress`), keep a `moved` or import note for existing deployments, and add a `terraform test` case | Not built |
| 27 | Interactive configuration skill `geap-configure`: asks for project, region, name prefix, governance tier, domain restricted sharing approach, and IAP mode, then writes `terraform/terraform.tfvars`. `geap-deploy` runs it when the file is missing or has placeholders, and otherwise asks the user to confirm the tier and region | Draft built (09 Nov 2026). Not tested |
| 28 | `agy` harness safety (found in the manual rehearsal on 09 Nov 2026): `agy` ignored the Claude Code format `settings.json`, ran `echo PROJECT_ID \| scripts/cleanup.sh` with no permission prompt, and loaded a user-level skill from outside the folder that changed `gcloud` commands | Draft fix (09 Nov 2026): `.agents/settings.json` in `agy` format with `allowNonWorkspaceAccess: false` and regex `ask` and `deny` rules; `scripts/cleanup.sh` refuses piped input and takes `--confirm PROJECT_ID`; AGENTS.md rules against outside skills and piped answers; root `settings.json` removed. The `agy` format is from an internal assistant: Not verified. Test in the rehearsal |
| 29 | Teardown sweep and preflight defects (found in the manual rehearsal on 09 Nov 2026): the out-of-state sweep used old IAM v2 endpoints and the prefixed ID for the access policy, used `gcloud` for Model Armor templates, and treated failed checks as "already deleted". `preflight.sh` reported failed `gcloud` calls as project facts | Fixed (09 Nov 2026): IAM v3 endpoints, access policy ID from `policies/iap_access_policy.yaml` (deleted only when no binding uses it), Model Armor REST, failed checks count as failures, `gcloud` account check; `preflight.sh` returns `status: ERROR` when it cannot read the project. Tested: syntax, piped input refusal, preflight error path. Not tested: a live sweep |
| 30 | Lateral paths for existing projects: discovery, adoption plan per tier, lateral tools (register an MCP server, move an agent to `AGENT_IDENTITY`, bind an agent to a gateway, add IAP rules for its principal), skills `geap-discover` and `geap-adopt`, and a rehearsal in a project with existing resources. See [the track](tracks/existing_project_adoption_20261109/index.md) | Planned (09 Nov 2026). Not built |
| 31 | Deploy step fixes from the manual rehearsal (problems 13, 14, 15, 17): no `terraform init` in `geap-deploy`, `cd terraform &&` commands that make CLI permission rules match `cd`, and the agent skipped the test result | Done (09 Nov 2026): `scripts/deploy_checks.sh` (init, fmt, validate, test, one `DEPLOY_CHECKS:` line), `terraform -chdir=terraform` in skills, runbooks, and GUIDE, AGENTS.md rule. Tested: `DEPLOY_CHECKS: PASS (... test 12 passed, 0 failed)` |
| 32 | Cloud Shell credentials for Terraform (rehearsal problem 16): `terraform apply` used the broken metadata server because the ADC file was only in `$CLOUDSDK_CONFIG` | Done (09 Nov 2026): `scripts/preflight.sh` reports `terraform_credentials.source` and a blocker with the `export GOOGLE_APPLICATION_CREDENTIALS=...` fix; two GUIDE troubleshooting rows |
