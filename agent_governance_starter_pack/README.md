# Agent governance starter pack

> [!NOTE]
> Draft. The scope is a proposal. It is not agreed.

The agent governance starter pack is the governed platform on Gemini Enterprise Agent Platform
(GEAP) that a customer receives on handover day. Agents
from an agent factory run on it with the controls on: Agent Identity, Agent Registry, an egress
Agent Gateway, and audit logs.

This folder holds the **mini build**. The mini build proves the pattern in one new or existing
project. The product definition is in [conductor/product.md](conductor/product.md).

## What is in the starter pack

| Part | Contents |
|---|---|
| Terraform (`terraform/`) | Deploys everything. Four boolean variables turn the governance tiers on or off: `enable_agent_registry` (Agent Registry), `enable_egress_gateway` (egress Agent Gateway with IAP policy V2), `enable_model_armor` (Model Armor on the gateways), and `enable_ingress_gateway` (ingress Agent Gateway). `iap_enforcement_mode` sets the IAP policy to `DRY_RUN` or `ENFORCE` |
| 1 reference agent (`agent-template/`) | An ADK agent that runs on Agent Runtime with its own Agent Identity principal. It is deployed as a container so it trusts the egress gateway certificate |
| 1 MCP server (`mcp-server/`) | A sample Go MCP server on Cloud Run with one read-only tool (`get_status`) and one write tool (`update_status`). The IAP policy allows the read tool and denies the write tool |
| Policies (`policies/`) | The IAP access policy (`iap_access_policy.yaml`), multi-agent IAP policy example (`multi_agent_iap_policy.example.yaml`), Model Armor settings (`model_armor.yaml`), Principal Access Boundary example (`principal_access_boundary.example.yaml`), and Cloud Monitoring dashboard (`geap_dashboard.json`) |
| 20 scripts (`scripts/`) | `configure.sh`, `preflight.sh`, `package_agent.sh`, `deploy_checks.sh`, `check_tool_policy.sh`, `check_promotion.sh`, `ask_agent.sh`, `read_audit_log.sh`, `read_session_trace.sh`, `discover.sh`, `adoption_plan.sh`, `bind_existing_agent.sh`, `doctor.sh`, `onboard_agent.sh`, `install_harness.sh`, `teardown_plan.sh`, `cleanup.sh`, `quarantine_agent.sh`, `init_remote_state.sh`, and `agy_guard.sh` |
| 6 runbooks (`runbooks/`) | `add_agent.md`, `add_agents_cli_agent.md`, `switch_policy_mode.md`, `teardown.md`, `handover_checklist.md`, and `principal_access_boundary.md` |
| 2 CI templates (`pipelines/`) | `github-actions-pr-check.yaml` and `cloudbuild-pr-check.yaml` |
| Agent harness (`AGENTS.md`, `.agents/hooks.json`, `.agents/skills/`) | Safety rules, permission gates (`scripts/agy_guard.sh`), and 11 skills (`geap-discover`, `geap-adopt`, `geap-configure`, `geap-preflight`, `geap-deploy`, `geap-verify`, `geap-trace`, `geap-doctor`, `geap-onboard-agent`, `geap-reset`, `geap-teardown`) so a coding agent can run the steps above. A person must approve every `terraform apply` and every clean-up |
| Claude Code harness (`CLAUDE.md`, `.claude/settings.json`, `.claude/skills`) | `CLAUDE.md` imports `AGENTS.md`. `.claude/settings.json` holds the allow, ask, and deny lists. `.claude/skills` is a symlink to `.agents/skills`, so both harnesses use one copy of the 11 skills. See [GUIDE.md](GUIDE.md) Section 1 |
| Day-2 pack (`day2/`) | Built in `scripts/`, `policies/`, `pipelines/`, and `runbooks/`: posture check (`doctor.sh`), promotion readiness (`check_promotion.sh`), agent onboarding (`onboard_agent.sh`), tool policy check (`check_tool_policy.sh`), emergency quarantine (`quarantine_agent.sh`), Principal Access Boundary (`principal_access_boundary.example.yaml`), governance dashboard (`geap_dashboard.json`), CI checks (`pipelines/`), and remote Terraform state (`init_remote_state.sh`). See [day2/README.md](day2/README.md) |

The skill names (`geap-*`) and the default resource prefix (`name_prefix = "geap"`) keep the short
platform name, so existing deployments keep their resource names.

**Start here:** [GUIDE.md](GUIDE.md) is the step-by-step guide from a new or existing project to a
working mini build, with the known problems and their fixes.

## How it works

Terraform creates every resource in the diagram. The agent calls tools and Google APIs only through
the egress Agent Gateway. The gateway asks IAP and Model Armor for a decision on each call.

```mermaid
flowchart LR
    tf["Terraform"] -. "creates all resources" .-> project

    subgraph project["Sandbox project"]
        user["User or scripts/ask_agent.sh"] --> agent

        subgraph runtime["Agent Runtime"]
            agent["Reference ADK agent (container)"]
            ident["Agent Identity principal"]
            agent --- ident
        end

        subgraph iam["IAM"]
            base["Project agent principal set: aiplatform.agentDefaultAccess"]
            single["Single agent principal: aiplatform.user, token creator on the invoker account"]
            uap["IAM access policy (IAP policy V2): allow registered, deny update_status"]
        end
        ident -.- base
        ident -.- single
        ident -.- uap

        agent --> gw

        subgraph gwbox["Egress Agent Gateway"]
            gw["Gateway (AGENT_TO_ANYWHERE)"]
            iapx["IAP authz extension (REQUEST_AUTHZ)"]
            max["Model Armor authz extension (CONTENT_AUTHZ), runs as the tenant service account"]
            gw --> iapx
            gw --> max
        end
        iapx -.- uap

        reg["Agent Registry: MCP server with tool spec, Google API endpoint"]
        gw -. "governs destinations in" .-> reg

        gw --> mcp["Cloud Run MCP server: get_status (read-only), update_status (write)"]
        gw --> apis["Google APIs: model, Sessions, tokens, logs, traces"]

        subgraph logs["Logs"]
            gwlog["Gateway request log"]
            iaplog["IAP Data Access audit log"]
            cl["Cloud Logging: agent stdout and stderr"]
        end
        gw -.-> gwlog
        iapx -.-> iaplog
        agent -.-> cl

        ingress["Ingress Agent Gateway (CLIENT_TO_AGENT)"] --> agent
        user --> ingress
    end

    pipeline["Agent factory CI/CD pipeline, component 5: not built"] -.-> agent
    envs["Dev, test, and prod projects with VPC-SC and CMEK, component 1: not built"] -.- project
    dash["Dashboards, component 6: not built"] -.- logs

    classDef notbuilt stroke-dasharray: 5 5,fill:#f4f4f4,color:#555
    class pipeline,envs,dash notbuilt
```

Legend: solid border = built in the mini build. Dashed border = not built.

## Governance tiers

You can turn each governance layer on or off with a boolean variable in `terraform/terraform.tfvars`.
Each tier adds one control on top of the tiers below it. [GUIDE.md](GUIDE.md#choose-your-tier) shows the
variable values for each tier.

![Agent governance starter pack tiers](images/governance_tiers.svg)

The pyramid shows two paths. The vertical path adds one control for each tier. The lateral path (left, built with `geap-discover`, `geap-adopt`, `existing_mcp_servers`, `existing_agent_principals`, and `scripts/bind_existing_agent.sh`) brings the agents, MCP servers, and clients that already exist in the project under the same control. See the [lateral paths track](conductor/tracks/existing_project_adoption_20261109/index.md).


| Tier | Name | GEAP Services | Terraform Variable | Key Behavior |
|---|---|---|---|---|
| **Tier 1** | **Identity and Runtime Baseline** | Agent Runtime (`AGENT_IDENTITY` and Sessions), Cloud Run MCP server, regional Cloud Logging bucket | *(Always on)* | Every agent gets a unique SPIFFE identity and calls the MCP server with Cloud Run IAM (`roles/run.invoker`). Needs no organization policy changes |
| **Tier 2** | **Catalog and Discovery** | Agent Registry (`mcpServers` and `endpoints`) | `enable_agent_registry` (default `true`) | Registers the MCP server tool specification and the platform API endpoints in Agent Registry |
| **Tier 3** | **Outbound Access Control (Egress IAP)** | Egress Agent Gateway (`AGENT_TO_ANYWHERE`) and IAP Policy V2 (`REQUEST_AUTHZ` in `DRY_RUN` or `ENFORCE`) | `enable_egress_gateway` (default `true`) | Enforces per-tool CEL rules (`destination.agent_registry.mcp_server.tool.name`) on outbound agent traffic. Needs no domain restriction exception when `enable_model_armor = false` |
| **Tier 4** | **Content Safety (Model Armor)** | Model Armor templates, `CONTENT_AUTHZ` extension, and 3 `gcp-sa-dep` IAM grants | `enable_model_armor` (default `true`) | Screens prompts and tool outputs for prompt injection, jailbreaks, and sensitive data on active gateways. **Only Tier 4 can need the domain restriction setup, when the organization enforces it** |
| **Tier 5** | **Inbound Client Control (Ingress Gateway)** | Ingress Agent Gateway (`CLIENT_TO_AGENT`) and `clientToAgentConfig` (attaches Model Armor when `enable_model_armor = true`) | `enable_ingress_gateway` (default `false`) | Controls inbound client traffic to the agent |

### Egress Model Armor scope

The variable `model_armor_egress_scope` decides which egress traffic goes to Model Armor:

| Value | Egress Model Armor screens | Use |
|---|---|---|
| `auto` (default) | `mcp_servers` when `enable_ingress_gateway = true`, else `all_egress` | At Tier 5, the ingress gateway screens user prompts and agent replies, so egress screens only tool traffic. At Tier 4, egress screens everything |
| `mcp_servers` | Only the MCP server hosts: the starter pack MCP server and `existing_mcp_servers` | Tool calls and tool results only. The agent's model calls are not screened on egress |
| `all_egress` | All egress traffic, including each model call with its full context | The most coverage. Each model call adds a Model Armor check, and a false positive stops the reply |

`terraform output model_armor_egress_scope` shows the value after `auto` is resolved. The sample
MCP server has a test item, `ITEM-099`, whose title is a prompt injection. `geap-verify` uses it to
check that Model Armor screens tool results.

The request flow below is in `ENFORCE` mode. The denied call never gets to Cloud Run.

```mermaid
sequenceDiagram
    actor U as User
    participant A as Agent on Agent Runtime
    participant G as Egress Agent Gateway
    participant I as IAP policy V2
    participant M as Model Armor
    participant R as Cloud Run MCP server

    U->>A: "What is the status of ITEM-001?"
    A->>G: Model call with the prompt
    G->>M: Check prompt
    M-->>G: Allowed
    A->>G: tools/call get_status
    G->>I: egressViaIAP for the agent principal
    I-->>G: Allowed by the allow rule
    G->>R: get_status
    R-->>A: ITEM-001 is open

    U->>A: "Set ITEM-001 to in_progress."
    A->>G: tools/call update_status
    G->>I: egressViaIAP for the agent principal
    I-->>G: Denied by the deny rule on update_status
    G-->>A: Error. The request is not sent to Cloud Run
    A-->>U: The call to update_status failed

    U->>A: Prompt injection text
    A->>G: Model call with the prompt
    G->>M: Check prompt
    M-->>G: Blocked
    G-->>A: 403 Security Policy Violation
```

## Layout

| Folder | What it holds | Component |
|---|---|---|
| [`terraform/`](terraform/) | APIs, audit logs, IAM, Cloud Run, Agent Registry, Agent Gateway, Model Armor, the agent | 1, 2, 3, 4 |
| [`agent-template/`](agent-template/) | The ADK reference agent | 4 |
| [`mcp-server/`](mcp-server/) | A sample MCP server in Go, with one read-only tool and one write tool | 3 |
| [`policies/`](policies/) | IAP access policies, Model Armor settings, Principal Access Boundary example, and Cloud Monitoring dashboard | 3, 6 |
| [`pipelines/`](pipelines/) | GitHub Actions and Cloud Build pull request check templates | 5 |
| [`runbooks/`](runbooks/) | Add a new ADK or `agents-cli` agent. Switch policy mode and reset state. Tear down the starter pack. Handover checklist. Principal Access Boundary | 6 |
| [`scripts/`](scripts/) | 20 scripts: preflight, configure, offline deploy checks, tool policy check, promotion check, discovery, lateral adoption plan, bind existing agent, doctor, onboard agent, install harness, quarantine agent, init remote state, package agent, ask agent, read audit log, read session trace, teardown plan, cleanup, and `agy` guard hook | 6 |
| [`.agents/skills/`](.agents/skills/) | 11 CLI skills (`geap-discover`, `geap-adopt`, `geap-configure`, `geap-preflight`, `geap-deploy`, `geap-verify`, `geap-trace`, `geap-doctor`, `geap-onboard-agent`, `geap-reset`, `geap-teardown`), [`AGENTS.md`](AGENTS.md), and [`.agents/hooks.json`](.agents/hooks.json) with `scripts/agy_guard.sh` | 6 |
| [`day2/`](day2/) | Day-2 operational tool index and design rules | 6 |

## Related folders

These are links only. The starter pack does not use code from them.

- [`agent_auth`](../agent_auth/): the identity baseline and the 3LO auth provider pattern.
- [`curated_codelabs/agent-gateway-governance`](../curated_codelabs/agent-gateway-governance/): the
  egress gateway codelab with IAP policy V1.

## agents-cli and the starter pack

The starter pack does not use agents-cli. Terraform deploys the reference agent with
`google_vertex_ai_reasoning_engine`: a source archive from `scripts/package_agent.sh`, a
container built from `agent-template/Dockerfile` (`adk api_server`), `AGENT_IDENTITY`, and the
class methods in `terraform/adk_class_methods.json`.

| Job | Tool | Reason |
|---|---|---|
| Gateways, IAP access policy, Model Armor, Agent Registry, IAM | Terraform | agents-cli cannot create or manage gateways. The security owner owns these resources |
| Bind an agent to a gateway | Terraform | The security owner controls which gateway each agent uses |
| Deploy the reference agent | Terraform | `agents-cli deploy` builds a container with no class methods, so `:query` and `:streamQuery` do not work |
| Agent developer work: scaffold, local run, evaluation | agents-cli is an option | This is agent code, not platform. It belongs to component 5 (pipeline), which is not built |

An agent that agents-cli deploys can use the starter pack gateways with
`--agent-gateway-egress` or `--agent-gateway-ingress`. Follow
[`runbooks/add_agents_cli_agent.md`](runbooks/add_agents_cli_agent.md).

## Deploy the mini build

Prerequisites: a new or existing Google Cloud project with billing, `gcloud`, Terraform 1.9 or
later, and the Owner role on the project. All resources use `var.name_prefix` (default `geap`),
all APIs set `disable_on_destroy = false`, and `scripts/cleanup.sh` removes only `<name_prefix>-*`
resources by default ([runbooks/teardown.md](runbooks/teardown.md)). The mini build uses `us-central1`.

```bash
cd agent_governance_starter_pack
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform/terraform.tfvars: project_id, project_number, and organization_id.

gcloud auth application-default login
# Cloud Shell only: Terraform does not read $CLOUDSDK_CONFIG.
# Run this in the same tab where you run terraform or agy. Run it again after a Cloud Shell restart.
export GOOGLE_APPLICATION_CREDENTIALS="$CLOUDSDK_CONFIG/application_default_credentials.json"
scripts/package_agent.sh

cd terraform
terraform init
terraform fmt -check -recursive && terraform validate && terraform test
terraform plan -out=tfplan
terraform apply tfplan
```

### Known prerequisite: domain restricted sharing

The gateway calls Model Armor as a Google-managed service agent,
`service-TENANT_PROJECT_NUMBER@gcp-sa-dep.iam.gserviceaccount.com`. The number is the number of the
gateway tenant project, not of your project. Terraform grants this service agent 3 roles on your
project: `roles/modelarmor.calloutUser`, `roles/modelarmor.user`, and
`roles/serviceusage.serviceUsageConsumer`. Without them, Model Armor does not scan the gateway
traffic.

If the organization enforces `iam.allowedPolicyMemberDomains`, IAM refuses the 3 grants with
`User service-...@gcp-sa-dep.iam.gserviceaccount.com is not in permitted organization`. This
constraint has no exception for one principal
([Domain-restricted sharing](https://docs.cloud.google.com/organization-policy/domain-restricted-sharing)).
A project-level `iam.allowedPolicyMemberDomains` exception is necessary while the organization uses
this constraint. The exception can add only the Google customer ID `is:C02h8e9nw`, which owns the
tenant service agents. It does not need `allowAll`. A project-level
`iam.managed.allowedPolicyMembers` policy does not help while the organization uses the legacy
constraint, because IAM checks both constraints.

The organization admin chooses one approach before the apply. The numbers match
[GUIDE.md](GUIDE.md) Section 3:

| Approach | How it works | Use |
|---|---|---|
| Approach 1: managed constraint | The organization replaces `iam.allowedPolicyMemberDomains` with `iam.managed.allowedPolicyMembers`, and the project names the service agent in `allowedMemberSubjects` | Production |
| Approach 2: short-lived project exception | Set `allow_google_managed_members = true` and apply. Terraform creates a project-level exception (by default it keeps the parent allow list and adds `is:C02h8e9nw`), waits, and grants the 3 roles. Then run `scripts/configure.sh --allow-google-managed-members false --dry-run`, the same command without `--dry-run`, and plan and apply again. The tier and the policy mode stay. The grants stay | Sandbox projects |
| Approach 3: keep the exception | Keep `allow_google_managed_members = true` | Disposable sandbox projects only |

With Approach 2, note two points:

- IAM uses a new exception about 80 seconds after Terraform creates it. The effective policy shows
  the exception after a few seconds, so Terraform waits `org_policy_wait_seconds` (default 120)
  more before the grants. If the grants still fail with `not in permitted organization`, wait 2
  minutes, then plan and apply again.
- `drs_exception_mode = "allow_all"` is the alternative. It allows all members on the project for the
  time of the grant.
- Each gateway has its own tenant service agent. Keep the exception until each gateway with Model
  Armor has its grants.

If you want to deploy without the `gcp-sa-dep` Model Armor grants, set `enable_model_armor = false` (Tiers 1 to 3) or set `enable_egress_gateway = false` and `enable_ingress_gateway = false` (Tiers 1 and 2) in `terraform/terraform.tfvars`.

## Check the controls after deployment

Start with `iap_enforcement_mode = "DRY_RUN"`. [switch_policy_mode.md](runbooks/switch_policy_mode.md)
moves the policy between `DRY_RUN` and `ENFORCE`.

| Control | What to check | Command or page |
|---|---|---|
| **Identity** | The agent has its own Agent Identity principal. Tool access, Sessions, and the IAP policy apply to this single principal. Start-up base roles go to the project agent principal set. There is no project-level token creator role | `terraform output agent_principal`. IAM page of the project |
| **Catalog** | The MCP server and the Google API endpoints are in Agent Registry. The tool spec marks `get_status` as read-only | Agent Registry page. [`tool_spec.json`](mcp-server/tool_spec.json) |
| **Gateway control** | In `DRY_RUN`, the request "Set ITEM-003 to closed" passes. After the change to `ENFORCE` and a 3-minute wait, the same request is denied. The agent does not get a clear `403`. It reports one of two ADK errors: "MCP session connection lost" or "MCP tool execution failed: Server returned an error response" | `scripts/ask_agent.sh "Set ITEM-003 to closed"`. [`policies/iap_access_policy.yaml`](policies/iap_access_policy.yaml) |
| **Audit** | Use the evidence that exists: the agent error for `update_status`, and no matching request in the Cloud Run request log | Agent reply. `gcloud logging read` on `run.googleapis.com/requests`. `scripts/read_audit_log.sh 15m` for the logs that do appear. `scripts/read_session_trace.sh SESSION_ID` marks the denied call as `NO_DOWNSTREAM`: the tool span has an error and no gateway or MCP span below it |

The change to `ENFORCE` takes about 2 minutes to apply, and the gateway uses it 1 to 3 minutes
later.

> [!WARNING]
> Known gap (08 Nov 2026 test, IAP policy V2): the IAP Data Access audit log had entries only for
> MCP base methods (`initialize`, `notifications/initialized`). It had no entry for the `tools/call`
> decisions, including the enforced denial. The gateway request log also had no entry for the
> denied call. Until this gap is solved, use the agent reply as the evidence of a denial.

## Clean up

To remove all starter pack resources from the project, run:

```bash
scripts/cleanup.sh
```

The script runs `terraform destroy`, then removes the `<name_prefix>-*` resources that are not in the
Terraform state. Three project-wide steps run only with `--include-project-wide`. The APIs stay on.
[runbooks/teardown.md](runbooks/teardown.md) lists what the script deletes and what it keeps.
