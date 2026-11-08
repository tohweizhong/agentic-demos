#!/usr/bin/env bash
# Shared setup for the deploy scripts. Each script sources this file.
set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${DEMO_DIR}/.env"
AGENT_DIR="${DEMO_DIR}/agent"
CLIENT_DIR="$(cd "${DEMO_DIR}/../client" && pwd)"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: ${ENV_FILE} does not exist. Copy .env.example to .env first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

require() {
  local name
  for name in "$@"; do
    if [[ -z "${!name:-}" || "${!name}" == YOUR_* || "${!name}" == *YOUR_* ]]; then
      echo "ERROR: set ${name} in ${ENV_FILE}." >&2
      exit 1
    fi
  done
}

require PROJECT_ID PROJECT_NUMBER ORG_ID REGION AUTH_PROVIDER_ID

AUTH_PROVIDER_NAME="projects/${PROJECT_ID}/locations/${REGION}/authProviders/${AUTH_PROVIDER_ID}"
CLIENT_SA_EMAIL="${CLIENT_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BUILD_SA_EMAIL="${BUILD_SA_NAME:-}@${PROJECT_ID}.iam.gserviceaccount.com"
# Cloud Run gives each service a deterministic URL in this format.
CLIENT_URL="https://${CLIENT_SERVICE}-${PROJECT_NUMBER}.${REGION}.run.app"
OAUTH_CONTINUE_URI="${CLIENT_URL}/validateUserId"

agent_principal() {
  echo "principal://agents.global.org-${ORG_ID}.system.id.goog/resources/aiplatform/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${AGENT_ID}"
}

# Writes or replaces KEY=VALUE in the .env file.
set_env_value() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}
