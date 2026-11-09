# Principal Access Boundary (PAB) for Agents

This runbook shows how an organization administrator can restrict the cloud resources that the agents in a project can reach. It uses a Principal Access Boundary (PAB) policy.

## Steps

1.  **Create the PAB Policy.**
    Review the example in `policies/principal_access_boundary.example.yaml`. Run this command to create the policy in your organization:

    ```bash
    gcloud iam principal-access-boundary-policies create agent-pab \
      --organization="ORGANIZATION_ID" \
      --location="global" \
      --policy-file="policies/principal_access_boundary.example.yaml"
    ```

2.  **Bind the Policy to the Agent Principal Set.**
    Bind the policy to all agents in the project using their principal set. Replace `PROJECT_NUMBER` and `ORGANIZATION_ID` with your values.

    ```bash
    gcloud iam principal-access-boundary-policy-bindings create agent-pab-binding \
      --organization="ORGANIZATION_ID" \
      --location="global" \
      --principal="principalSet://agents.global.org-ORGANIZATION_ID.system.id.goog/attribute.platformContainer/aiplatform/projects/PROJECT_NUMBER" \
      --policy="organizations/ORGANIZATION_ID/locations/global/principalAccessBoundaryPolicies/agent-pab"
    ```
