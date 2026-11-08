# Runbook: add a new agent

## Purpose

Add a second agent from the agent factory to the starter pack. The new agent gets its own Agent
Identity, its own grants, and the same egress gateway controls as the reference agent.

## Before you start

- The mini build is deployed. `terraform output` shows `agent_resource_name`.
- You have the agent source in a folder with `agent.py`, `agent_engine_app.py`, `tools.py`, and
  `requirements.txt`, in the same form as [`agent-template/`](../agent-template/).
- You know which registered destinations the new agent must call.

## Steps

1. Copy the agent source to a new folder next to `agent-template/`, for example `agent-orders/`.
2. Make a source archive for the new agent. Use the same `tar` command as
   [`scripts/package_agent.sh`](../scripts/package_agent.sh), with the new folder and a new output
   file, for example `terraform/build/agent_orders.tar.gz`.
3. In `terraform/`, copy `agent.tf` to `agent_orders.tf`. Change the resource name, the
   `display_name`, and the archive path. Keep `identity_type = "AGENT_IDENTITY"` and the
   `agent_gateway_config` block. Without the gateway block, the gateway does not control the agent.
4. Copy `iam_agent.tf` to `iam_agent_orders.tf`. Change the resource names and the principal, so
   that the grants go to the new agent only. Give the new agent only the roles that it needs.
5. Add the new agent principal to the access policy. In `gateway.tf`, the rules use
   `principals = [local.agent_principal]`. Add the new principal to this list, or add rules for the
   new agent in [`policies/iap_access_policy.yaml`](../policies/iap_access_policy.yaml).
6. If the new agent calls a new MCP server or API, register it in Agent Registry first (see
   `registry.tf`). The gateway blocks a destination that is not registered.
7. Run the checks and the plan:

   ```bash
   cd terraform
   terraform fmt -check -recursive
   terraform validate
   terraform test
   terraform plan -out=tfplan
   ```

   Expected: the plan adds one agent and its grants, and changes the access policy. It does not
   destroy the reference agent.

8. Apply the plan with `terraform apply tfplan`. The agent deployment takes about 10 to 15 minutes.

## Check the result

1. Run `terraform output` and find the new agent resource name.
2. Ask the new agent a question. Use [`scripts/ask_agent.sh`](../scripts/ask_agent.sh) with the
   new resource name.
3. Run [`scripts/read_audit_log.sh`](../scripts/read_audit_log.sh). The IAP Data Access audit log
   shows the decisions for the new agent principal.

## Restore

Remove the files that you added in steps 3 and 4, and the principal from step 5. Run
`terraform apply`. Terraform deletes the new agent and its grants.
