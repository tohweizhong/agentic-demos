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

## Deploy the mini build

Prerequisites: a sandbox project with billing, `gcloud`, Terraform 1.9 or later, and the Owner role
on the project. Use a dedicated project. The mini build uses `us-central1`.

```bash
cd geap_starter_pack
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform/terraform.tfvars: project_id and organization_id.

gcloud auth application-default login
scripts/package_agent.sh

cd terraform
terraform init
terraform fmt -check -recursive && terraform validate && terraform test
terraform plan -out=tfplan
terraform apply tfplan
```

If the organization uses domain restricted sharing, the Model Armor grants to the gateway fail.
Then set `allow_google_managed_members = true`, after the organization admin approves it.

## Demo: identity, catalog, gateway control, audit (10 minutes)

Run [reset the demo](runbooks/reset_demo.md) before you start.

| Minute | Show | Command or page |
|---|---|---|
| 0 to 2 | **Identity.** The agent has its own Agent Identity principal. All grants go to it, and there is no project-level token creator role | `terraform output agent_principal`. IAM page of the project |
| 2 to 4 | **Catalog.** The MCP server and the Google API endpoints are in Agent Registry. The tool spec marks `get_status` as read-only | Agent Registry page. [`tool_spec.json`](mcp-server/tool_spec.json) |
| 4 to 7 | **Gateway control.** In `DRY_RUN`, ask "Set ITEM-003 to closed". The call passes. Change to `ENFORCE` and ask again. The call is denied. The agent can show "MCP session connection lost", not a clear `403` | `scripts/ask_agent.sh "Set ITEM-003 to closed"`. [`policies/iap_access_policy.yaml`](policies/iap_access_policy.yaml) |
| 7 to 10 | **Audit.** The IAP Data Access audit log shows the dry-run entry (`DRY_RUN` true, `GRANTED` false) and the enforced denial | `scripts/read_audit_log.sh 15m` |

The change to `ENFORCE` takes some minutes. For a 10-minute demo, prepare a second terminal, or
show the enforced result from an earlier run.

## Clean up

Keep the resources for customer demos. After the demos, run:

```bash
scripts/cleanup.sh
```

The script runs `terraform destroy` and deletes the Cloud Build source bucket. It deletes only the
mini build resources.
