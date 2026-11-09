# Runbook: add a new agent

## Purpose

Add a second agent from the agent factory to the starter pack. The new agent gets its own Agent
Identity, its own grants, and the same egress gateway controls as the reference agent.

## Before you start

- The mini build is deployed. `terraform output` shows `agent_resource_name`.
- You have the agent source in the same form as [`agent-template/`](../agent-template/): a
  `Dockerfile`, a `requirements.txt`, and an ADK agent package with `__init__.py` and `agent.py`.

> [!IMPORTANT]
> With an egress gateway, use the container deploy path (`image_spec` with the Dockerfile). The
> Dockerfile must install the gateway root CA and set `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and
> `GRPC_DEFAULT_SSL_ROOTS_FILE_PATH`. A source deploy with `python_spec` failed in the mini build:
> the Agent Runtime start-up gRPC call did not trust the gateway root CA.
- You know which registered destinations the new agent must call.
- The domain restricted sharing prerequisite in the [README](../README.md) is solved. If not, the
  gateway Model Armor grants fail, and Model Armor does not scan the traffic of the new agent.

## Steps

1. Copy `agent-template/` to a new folder, for example `agent-orders/`. Rename the package folder
   and change the `COPY` line and the `CMD` line in the Dockerfile to match.
2. Make a source archive for the new agent. Use the same `tar` command as
   [`scripts/package_agent.sh`](../scripts/package_agent.sh), with the new folder and a new output
   file, for example `terraform/build/agent_orders.tar.gz`.
3. In `terraform/`, copy `agent.tf` to `agent_orders.tf`. Change the resource name, the
   `display_name`, and the archive path. Keep `identity_type = "AGENT_IDENTITY"`, the `image_spec`
   block with the gateway root CA, and the `agent_gateway_config` block. Without the gateway block, the gateway does not control the agent.
4. Copy `iam_agent.tf` to `iam_agent_orders.tf`. Change the resource names and the principal, so
   that the grants go to the new agent only. Give the new agent only the roles that it needs.
5. Add the new agent principal to the access policy. In `gateway.tf`, the rules use
   `principals = [local.agent_principal]`. Add the new principal to this list, or add rules for the
   new agent in [`policies/iap_access_policy.yaml`](../policies/iap_access_policy.yaml).
6. If the new agent calls a new MCP server or API, register it in Agent Registry first (see
   `registry.tf`). The gateway blocks a destination that is not registered.
7. Run the checks and the plan:

   ```bash
   scripts/deploy_checks.sh                       # init, fmt, validate, test
   terraform -chdir=terraform plan -out=tfplan
   ```

   Expected: the plan adds one agent and its grants, and changes the access policy. It does not
   destroy the reference agent.

8. Apply the plan with `terraform apply tfplan`. The agent deployment takes about 10 to 15 minutes.

## Check the result

1. Wait 2 to 3 minutes after `terraform apply` so the egress gateway loads the updated IAP access policy for the new agent principal.
2. Run `terraform output` and find the new agent resource name.
3. Ask the new agent a question with the `-a` flag on [`scripts/ask_agent.sh`](../scripts/ask_agent.sh):
   ```bash
   scripts/ask_agent.sh -a "projects/PROJECT_NUMBER/locations/REGION/reasoningEngines/NEW_AGENT_ID" "What is the status of ITEM-001?"
   ```
4. Run [`scripts/read_audit_log.sh`](../scripts/read_audit_log.sh). The IAP Data Access audit log
   shows the decisions for the new agent principal.

## Restore

Remove the files that you added in steps 3 and 4, and the principal from step 5. Run
`terraform apply`. Terraform deletes the new agent and its grants.
