# Add an Agent with the Agents CLI

This runbook shows how to deploy a new agent with the `agents-cli` tool and connect it to the starter pack gateways.

## Steps

1.  **Deploy the Agent.**
    Use the `agents-cli deploy` command to create the agent. Pass the egress and ingress gateway endpoints from the Terraform output.

    ```bash
    agents-cli deploy my-agent \
      --agent-identity \
      --agent-gateway-egress "projects/PROJECT_NUMBER/locations/REGION/agentGateways/PREFIX-egress" \
      --agent-gateway-ingress "projects/PROJECT_NUMBER/locations/REGION/agentGateways/PREFIX-ingress"
    ```

2.  **Add the Agent Principal to Terraform.**
    Find the Agent Identity principal of your new agent. Add this principal to the `existing_agent_principals` list in `terraform/terraform.tfvars`.

    ```hcl
    existing_agent_principals = [
      "principal://agents.global.org-ORGANIZATION_ID.system.id.goog/resources/aiplatform/projects/PROJECT_NUMBER/locations/REGION/reasoningEngines/AGENT_ID"
    ]
    ```

3.  **Apply the Terraform Plan.**
    Run Terraform to add the new agent principal to the IAP access policy.

    ```bash
    terraform -chdir=terraform apply
    ```

4.  **Grant the Invoker Role.**
    Grant the `roles/aiplatform.user` role to the users or service accounts that will call the agent.

    ```bash
    gcloud projects add-iam-policy-binding PROJECT_ID \
      --member="user:caller@example.com" \
      --role="roles/aiplatform.user"
    ```

5.  **Call the Agent.**
    Use the Agent Runtime API or the `agents-cli` tool to query the new agent. It now routes traffic through the starter pack gateways.
