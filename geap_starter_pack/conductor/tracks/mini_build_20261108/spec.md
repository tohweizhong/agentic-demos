# Specification: Mini build of the GEAP starter pack

## Overview

The mini build is a small version of the starter pack in one sandbox project. It proves that one
reference agent runs on Agent Runtime with identity, catalog, gateway control, and audit on. It
also supports a 10-minute demo for a customer platform team. The source is the "Mini build" section
of [product.md](../../product.md).

## Functional requirements

1. **Layout.** Create the folders from product.md: `terraform/`, `agent-template/`, `pipelines/`,
   `policies/`, `runbooks/`. Add `mcp-server/` for the sample MCP server code, and `scripts/` for
   the Bash helpers. `pipelines/` holds only a note, because component 5 is not in the mini build.
2. **Base setup (Terraform).** Turn on the APIs. Turn on Data Access audit logs for
   `iap.googleapis.com`. Create a regional log bucket and a log sink for the gateway request log and
   the IAP audit log.
3. **Identity baseline (Terraform).** The agent uses Agent Identity. All grants go to the single
   agent principal, not to the project principal set. The agent gets the token creator role on one
   invoker service account only. No grant of `roles/iam.serviceAccountTokenCreator` at the project
   level.
4. **Catalog (Terraform).** Build the sample MCP server image with Cloud Build. Deploy it to Cloud
   Run. Register it in Agent Registry with its tool spec. Register the platform API endpoints that
   the agent needs.
5. **Control (Terraform).** Create the egress Agent Gateway, the IAP authz extension with policy
   version V2, the authz policy, and the IAM access policy with its project binding. The mode starts
   as `DRY_RUN`. Create the Model Armor templates, extension, and policy.
6. **Reference agent (Terraform).** Deploy the ADK agent from `agent-template/` to Agent Runtime
   with Agent Identity, Sessions, and the egress gateway binding.
7. **Sample MCP server.** Two tools: `get_status` (read-only) and `update_status` (write). Data is
   in memory and returns to its start state on each new revision.
8. **Policies.** The IAP access policy and the Model Armor settings are files in `policies/`.
   Terraform reads them. The access policy allows registered destinations in the region and denies
   the `update_status` tool.
9. **Runbooks.** "Add a new agent" and "Reset the demo".
10. **Scripts.** Package the agent source, ask the agent a question, read the audit log, and clean up.

## Non-functional requirements

- The repository is public. No real IDs, customer names, or internal links.
- The build runs from a clean clone, with no code from other folders.
- All text is in Simplified Technical English.

## Acceptance criteria

The offline criteria are for this track before a project is approved. The cloud criteria are the
success criteria in product.md.

| # | Criterion | Kind |
|---|---|---|
| A1 | `terraform fmt -check -recursive` and `terraform validate` pass | Offline |
| A2 | `go test ./...` passes for the MCP server, with more than 60 percent coverage | Offline |
| A3 | `pytest` passes for the agent code, with more than 60 percent coverage | Offline |
| A4 | A Go test checks that `tool_spec.json` matches the tools that the server lists | Offline |
| A5 | `terraform plan` in the approved project has no error | Cloud |
| A6 | The success criteria in product.md pass after `terraform apply` | Cloud |

## Out of scope

- Everything in the "Out of scope" table of product.md.
- Component 5 (agent factory pipeline), VPC-SC, CMEK, and the 3LO auth provider.
- `terraform apply` before the user approves the plan summary.
