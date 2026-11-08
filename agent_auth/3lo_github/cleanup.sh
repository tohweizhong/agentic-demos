#!/usr/bin/env bash
# Deletes only the resources that .env names for this demo.
#
# - The Cloud Run service CLIENT_SERVICE.
# - The agent AGENT_ID.
# - The client service account CLIENT_SA_NAME and its project role.
# - The build service account BUILD_SA_NAME and its project role.
# - The IAM bindings that this demo added on the auth provider.
# - The auth provider, only if AUTH_PROVIDER_OWNED_BY_DEMO=true.
#
# The script asks for confirmation before it deletes anything.
source "$(dirname "$0")/deploy/common.sh"

echo "This script deletes these resources in project ${PROJECT_ID}:"
echo "  Cloud Run service: ${CLIENT_SERVICE:-<none>}"
echo "  Agent: ${AGENT_ID:+projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${AGENT_ID}}"
echo "  Service account: ${CLIENT_SA_EMAIL}"
[[ -n "${BUILD_SA_NAME:-}" ]] && echo "  Build service account: ${BUILD_SA_EMAIL}"
echo "  Auth provider bindings for the agent and the client service account"
if [[ "${AUTH_PROVIDER_OWNED_BY_DEMO:-false}" == "true" ]]; then
  echo "  Auth provider: ${AUTH_PROVIDER_NAME}"
fi
read -r -p "Type yes to continue: " ANSWER
[[ "${ANSWER}" == "yes" ]] || { echo "Stopped."; exit 0; }

set +e

if [[ -n "${CLIENT_SERVICE:-}" ]]; then
  gcloud run services delete "${CLIENT_SERVICE}" \
    --project="${PROJECT_ID}" --region="${REGION}" --quiet
fi

if [[ -n "${AGENT_ID:-}" ]]; then
  gcloud agent-identity auth-providers remove-iam-policy-binding "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" --location="${REGION}" \
    --role="roles/agentidentity.user" --member="$(agent_principal)" >/dev/null
  # "force=true" also deletes the sessions of the agent.
  curl -sS -X DELETE \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines/${AGENT_ID}?force=true"
  echo
fi

gcloud agent-identity auth-providers remove-iam-policy-binding "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="${REGION}" \
  --role="roles/agentidentity.user" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" >/dev/null
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CLIENT_SA_EMAIL}" \
  --role="roles/aiplatform.user" --condition=None >/dev/null
gcloud iam service-accounts delete "${CLIENT_SA_EMAIL}" \
  --project="${PROJECT_ID}" --quiet

if [[ -n "${BUILD_SA_NAME:-}" ]]; then
  gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${BUILD_SA_EMAIL}" \
    --role="roles/cloudbuild.builds.builder" --condition=None >/dev/null
  gcloud iam service-accounts delete "${BUILD_SA_EMAIL}" \
    --project="${PROJECT_ID}" --quiet
fi

if [[ "${AUTH_PROVIDER_OWNED_BY_DEMO:-false}" == "true" ]]; then
  gcloud agent-identity auth-providers delete "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" --location="${REGION}" --quiet
fi

echo "Cleanup is complete. Remove AGENT_ID from .env if you deploy again."
