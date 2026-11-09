# Runbook: Tear Down the Starter Pack

Use this runbook to remove the agent governance starter pack from a project. The script is
[`scripts/cleanup.sh`](../scripts/cleanup.sh). The Antigravity and Claude Code skill is
`geap-teardown`.

## Before you start

- Run the script from the clone that deployed the project. That clone has the Terraform state.
- Run `gcloud auth application-default login`. The sweep uses the Application Default Credentials
  token.
- Choose the log bucket mode and the project-wide mode from the tables below.
- The script asks you to type the project ID. Nothing is deleted before you type it.

## Command

```bash
scripts/cleanup.sh [--keep-log-bucket | --purge-all] [--include-project-wide]
```

| Flag | Use it when |
|---|---|
| `--keep-log-bucket` (default) | You plan to deploy again into the same project from the same clone. The audit log bucket stays, and the script imports it into the Terraform state again |
| `--purge-all` | You do not plan to deploy again soon. The audit log bucket is deleted and stays soft-deleted for 7 days. During those 7 days, a deploy with the same `name_prefix` fails |
| `--include-project-wide` | The project holds the starter pack and nothing else. Without this flag, the project-wide steps only report what they find |

## What the script deletes and what it keeps

"Name-scoped" means that the step acts only on resources named `<name_prefix>-*`.
"Project-wide" means that the step can also act on resources that other teams created.

| Resource | Deleted by | Scope | After clean-up |
|---|---|---|---|
| Reference agent (Reasoning Engine) | `terraform destroy`, or the sweep (display name `<name_prefix>-reference-agent`) | Name-scoped | Deleted |
| Authz policies (`<name_prefix>-egress-iap-policy`, `<name_prefix>-egress-ma-policy`, `<name_prefix>-ingress-ma-policy`) | `terraform destroy`, or the sweep | Name-scoped | Deleted. The sweep deletes the policies first and waits for each delete to finish |
| Agent Gateways (`<name_prefix>-egress`, `<name_prefix>-ingress`) | `terraform destroy`, or the sweep | Name-scoped | Deleted. A gateway takes 4 to 5 minutes to delete |
| Authz extensions (`<name_prefix>-egress-iap-authz`, `<name_prefix>-egress-ma-authz`) | `terraform destroy`, or the sweep | Name-scoped | Deleted, after the policies |
| Model Armor templates | `terraform destroy`, or the sweep | Name-scoped | Deleted |
| IAP access policy and its policy binding | `terraform destroy`, or the sweep | Name-scoped | Deleted |
| Agent Registry entries (MCP server, Google APIs endpoint) | `terraform destroy`, or the sweep | Name-scoped | Deleted |
| Cloud Run MCP server, Artifact Registry repository, and the three service accounts | `terraform destroy`, or the sweep | Name-scoped | Deleted |
| Project IAM bindings that Terraform created (agent base role, build roles, the three `gcp-sa-dep` Model Armor roles) | `terraform destroy` | Name-scoped (Terraform state) | Deleted |
| IAP Data Access audit config and the log sink | `terraform destroy`, or the sweep | Name-scoped | Deleted |
| Audit log bucket `<name_prefix>-agent-audit` | The log bucket step | Name-scoped | Kept with `--keep-log-bucket`. Soft-deleted for 7 days with `--purge-all` |
| Cloud Build source bucket `gs://<PROJECT_ID>_<REGION>_cloudbuild` | Project-wide step | **Project-wide**: every Cloud Build job in the project uses it | Deleted only with `--include-project-wide` |
| The three Model Armor roles on **every** `@gcp-sa-dep` member | Project-wide step | **Project-wide**: another team's gateway can use these grants | Removed only with `--include-project-wide` |
| Project-level overrides of `iam.allowedPolicyMemberDomains` and `iam.managed.allowedPolicyMembers` | Project-wide step | **Project-wide**: another team can depend on them | Deleted only with `--include-project-wide` |
| APIs (Vertex AI, Network Services, Model Armor, Agent Registry, and others) | Not deleted | Project-wide | Kept on. All `google_project_service` resources set `disable_on_destroy = false` |
| Google-managed service agents and their roles, and the default compute service account | Not deleted | Project-wide | Kept. Google creates these, not the starter pack |
| Local files `terraform/build/agent_source.tar.gz` and `terraform/tfplan` | The script | Local | Deleted |

## Check the result

1. The script ends with `Clean-up done.` and exit code 0. If a step fails, it prints
   `Clean-up NOT complete` and exits with code 1. Read the errors and run the script again.
2. Run `scripts/preflight.sh`. It must show no gateways, agents, or Cloud Run services with the
   prefix.

## Known problems

| Symptom | Cause | Fix |
|---|---|---|
| `terraform destroy` fails on `<name_prefix>-egress-ma-policy` with `Error code 13, message: an internal error has occurred` | Seen twice on 09 Nov 2026. A direct REST `DELETE` on the same policy succeeded at once. The cause is not clear | Run the script again. The sweep deletes the policy through the REST API and waits for the operation. Then run the script one more time so `terraform destroy` finishes |
| The sweep reports an HTTP error such as `401` or `403` | The token is not valid for the REST endpoint. The gcloud CLI token can be bound to Certificate Based Access | Run `gcloud auth application-default login` and run the script again |
| A deploy fails with `409 ALREADY_EXISTS` on the log bucket | The bucket is soft-deleted (`--purge-all`), or it is in the state of another clone | Wait 7 days, use another `name_prefix`, or run the script with `--keep-log-bucket` from the clone that deployed |

## Test record

The full reset was tested live on 08 Nov 2026 (55 resources destroyed, then a fresh deploy).
A second run on 09 Nov 2026 hit the code 13 problem above. After a direct REST delete of the
policy, `terraform destroy` finished and the Terraform state was empty. That run found the
defects that this version of the script fixes: the delete order, the token, the false
`Clean-up done` message, and the project-wide steps.
