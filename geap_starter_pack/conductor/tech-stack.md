# Technology Stack: GEAP Starter Pack

| Layer | Technology |
|---|---|
| Infrastructure as code | Terraform 1.9 or later. Provider `hashicorp/google` `~> 8.10` (8.10.0 checked). Providers `hashicorp/archive` and `hashicorp/time` for the agent source archive and for waits |
| Terraform state | Local state for the mini build. A Cloud Storage backend is a later step for the target design |
| Agent language | Python 3.12 or later. Agent Runtime builds the agent with Python 3.13 |
| Agent framework | Google ADK, `google-adk[agent-identity,gcp,mcp]`, version 2.5 or later and below 3.0 |
| Agent hosting | Agent Runtime, `google_vertex_ai_reasoning_engine` with `source_code_spec` (inline source archive) |
| Agent identity | `identity_type = "AGENT_IDENTITY"` on the agent. No service account on the agent |
| Sessions | Agent Runtime Sessions, used by the ADK app when it runs on Agent Runtime |
| Model | Gemini, called in the `global` location |
| MCP server | Go, standard library and the official MCP Go SDK (`github.com/modelcontextprotocol/go-sdk`), streamable HTTP transport |
| MCP hosting | Cloud Run (`google_cloud_run_v2_service`). Image in Artifact Registry, built with Cloud Build. Base image `gcr.io/distroless/static` |
| Catalog | Agent Registry (`google_agent_registry_service`): one MCP server with a tool spec, and the platform API endpoints |
| Egress control | Agent Gateway (`google_network_services_agent_gateway`), Google-managed, `AGENT_TO_ANYWHERE`, internet egress |
| Gateway policy | IAP authz extension with `iapPolicyVersion = "V2"`, an authz policy (`REQUEST_AUTHZ`), and an IAM access policy (`google_iam_project_access_policy`) bound to the project (`google_iam_projects_policy_binding`) |
| Content control | Model Armor templates in the regional endpoint, and a `CONTENT_AUTHZ` authz extension and policy on the gateway |
| Audit | Data Access audit logs for `iap.googleapis.com`. A regional log bucket and a log sink for the gateway request log and the IAP audit log |
| Scripts | Bash with `gcloud` and `curl`. Settings in the gitignored `terraform.tfvars` |
| Tests | `terraform fmt -check`, `terraform validate`, `terraform plan`. `go test` for the MCP server. `pytest` for the agent code |

## Labels and clean-up

`terraform destroy` from the Terraform state is the main clean-up method. Labels are extra.

Label support in provider 8.10.0 (checked with `terraform providers schema`):

| Resource | Labels |
|---|---|
| `google_network_services_agent_gateway` | Yes |
| `google_network_services_authz_extension` | Yes |
| `google_network_security_authz_policy` | Yes |
| `google_model_armor_template` | Yes |
| `google_vertex_ai_reasoning_engine` | Yes |
| `google_cloud_run_v2_service`, `google_artifact_registry_repository` | Yes |
| `google_agent_registry_service` | No |
| `google_iam_project_access_policy`, `google_iam_projects_policy_binding` | No |

## Decisions

- The agent is deployed by Terraform, not by a deploy command. The source design recommends that the
  gateway binding stays in Terraform, so that the security owner controls it.
- The mini build uses internet egress. A VPC egress path (network attachment) is for the target
  design, because VPC-SC needs it.
- The agent calls the MCP server with an ID token for a dedicated invoker service account. The
  agent gets the token creator role on that one service account only, not on the project.
- Grants to agents have two levels. Base roles go to the principal set of all agents in the project,
  before Terraform creates an agent: `roles/aiplatform.agentDefaultAccess` (logs, metrics, traces,
  telemetry, quota, model predict). The container needs them when it starts, and a single agent
  principal exists only after the agent exists. Tool access and Sessions go to the single agent
  principal: the token creator role on the invoker account, `roles/aiplatform.user`, and the IAP
  egress policy. `roles/aiplatform.agentDefaultAccess` has the stage ALPHA.
- There is no Terraform or HCL style guide in the Conductor library. `terraform fmt` is the style
  check for Terraform.

## Exceptions

- None. The MCP server is in Go and the agent is in Python, as the repository rules ask.
