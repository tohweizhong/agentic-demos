#!/usr/bin/env bash
# Step 3. Grant the IAM roles.
#
# - The agent identity gets roles/agentidentity.user on the auth provider.
#   The agent uses this role to get the user token from the Auth Manager vault.
# - The client service account gets roles/aiplatform.user on the project, to
#   call the agent, and roles/agentidentity.user on the auth provider only, to
#   call credentials:finalize after the user gives consent.
source "$(dirname "$0")/common.sh"
require AGENT_ID CLIENT_SA_NAME

echo "Granting roles/agentidentity.user on the provider to the agent identity."
gcloud agent-identity auth-providers add-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --role="roles/agentidentity.user" \
  --member="$(agent_principal)" >/dev/null

if ! gcloud iam service-accounts describe "${CLIENT_SA_EMAIL}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating service account ${CLIENT_SA_EMAIL}."
  gcloud iam service-accounts create "${CLIENT_SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="Agent auth demo client"
  # A new service account can take some seconds to become visible to IAM.
  sleep 15
fi

echo "Granting roles/aiplatform.user on the project to the client."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" \
  --role="roles/aiplatform.user" \
  --condition=None >/dev/null

echo "Granting roles/agentidentity.user on the provider to the client."
gcloud agent-identity auth-providers add-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --role="roles/agentidentity.user" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" >/dev/null

# Demo controls (DEMO ONLY). Two custom roles, each with one permission.
# No predefined role is small enough: revokeAuthorizations is only in the
# editor and admin roles.
# - agentAuthDemoRevoke on the auth provider: reset consent for a user.
# - agentAuthDemoSummaries on the project: list access summaries.
ensure_custom_role() {
  local role_id="$1" title="$2" permission="$3"
  if ! gcloud iam roles describe "${role_id}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Creating custom role ${role_id}."
    gcloud iam roles create "${role_id}" --project="${PROJECT_ID}" \
      --title="${title}" --permissions="${permission}" --stage=GA >/dev/null
  fi
}
ensure_custom_role agentAuthDemoRevoke "Agent auth demo: revoke consent" \
  agentidentity.authProviders.revokeAuthorizations
ensure_custom_role agentAuthDemoSummaries "Agent auth demo: list access summaries" \
  agentidentity.accessSummaries.list

echo "Granting the demo controls roles to the client."
gcloud agent-identity auth-providers add-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --role="projects/${PROJECT_ID}/roles/agentAuthDemoRevoke" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" \
  --role="projects/${PROJECT_ID}/roles/agentAuthDemoSummaries" \
  --condition=None >/dev/null

echo
echo "Auth provider IAM policy:"
gcloud agent-identity auth-providers get-iam-policy "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="${REGION}"
echo "Next step: run deploy/04_deploy_client.sh"
