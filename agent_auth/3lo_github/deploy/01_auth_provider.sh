#!/usr/bin/env bash
# Step 1. Enable the APIs and make sure that the GitHub auth provider exists.
#
# If the provider does not exist, this script creates it. Then you must
# register a GitHub OAuth app with the provider redirect URL as the callback,
# put the client ID and secret in .env, and run this script again.
source "$(dirname "$0")/common.sh"

gcloud services enable \
  agentidentity.googleapis.com \
  agentregistry.googleapis.com \
  aiplatform.googleapis.com \
  apphub.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iap.googleapis.com \
  --project="${PROJECT_ID}"

if gcloud agent-identity auth-providers describe "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  echo "Auth provider ${AUTH_PROVIDER_ID} exists. The script uses it."
else
  echo "Creating auth provider ${AUTH_PROVIDER_ID}."
  gcloud agent-identity auth-providers create "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --three-legged-oauth-authorization-url="https://github.com/login/oauth/authorize" \
    --three-legged-oauth-token-url="https://github.com/login/oauth/access_token"
  set_env_value AUTH_PROVIDER_OWNED_BY_DEMO true
fi

if [[ -n "${GITHUB_CLIENT_ID:-}" && -n "${GITHUB_CLIENT_SECRET:-}" ]]; then
  echo "Setting the GitHub client ID and secret on the provider."
  gcloud agent-identity auth-providers update "${AUTH_PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --three-legged-oauth-client-id="${GITHUB_CLIENT_ID}" \
    --three-legged-oauth-client-secret="${GITHUB_CLIENT_SECRET}" >/dev/null
fi

REDIRECT_URL="$(gcloud agent-identity auth-providers describe "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="${REGION}" \
  --format="value(authProviderTypeParams.threeLeggedOauth.redirectUrl)")"
CLIENT_ID_SET="$(gcloud agent-identity auth-providers describe "${AUTH_PROVIDER_ID}" \
  --project="${PROJECT_ID}" --location="${REGION}" \
  --format="value(authProviderTypeParams.threeLeggedOauth.clientId)")"

echo
echo "Provider redirect URL (use it as the GitHub OAuth app callback URL):"
echo "  ${REDIRECT_URL}"
if [[ -z "${CLIENT_ID_SET}" ]]; then
  echo "WARNING: the provider has no GitHub client ID. Set GITHUB_CLIENT_ID and"
  echo "GITHUB_CLIENT_SECRET in .env, then run this script again."
else
  echo "The provider has a GitHub client ID. Step 1 is complete."
fi
