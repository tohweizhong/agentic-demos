#!/usr/bin/env bash
# Step 2. Deploy the agent to Agent Runtime with an Agent Identity.
#
# This script uses "adk deploy agent_engine". Do not use
# "agents-cli deploy --agent-identity" for this demo. That command makes a
# container without classMethods, and the client then fails on create_session.
#
# If AGENT_ID in .env is empty, the script creates a new agent and writes the
# new ID to .env. If AGENT_ID is set, the script updates that agent.
source "$(dirname "$0")/common.sh"
require AGENT_DISPLAY_NAME MODEL_ID MODEL_LOCATION CLIENT_SERVICE

ADK_BIN="${ADK_BIN:-${DEMO_DIR}/.venv/bin/adk}"
if [[ ! -x "${ADK_BIN}" ]]; then
  echo "ERROR: ${ADK_BIN} not found. Create the virtual environment first:" >&2
  echo "  python3 -m venv ${DEMO_DIR}/.venv" >&2
  echo "  ${DEMO_DIR}/.venv/bin/pip install uv" >&2
  echo "  ${DEMO_DIR}/.venv/bin/uv pip install --python ${DEMO_DIR}/.venv/bin/python -r ${AGENT_DIR}/requirements.txt" >&2
  exit 1
fi

# adk deploy sends the values in agent/.env to the agent as environment
# variables. The repository .gitignore excludes this file.
cat > "${AGENT_DIR}/.env" <<EOF
AUTH_PROVIDER_NAME=${AUTH_PROVIDER_NAME}
OAUTH_CONTINUE_URI=${OAUTH_CONTINUE_URI}
MODEL_ID=${MODEL_ID}
MODEL_LOCATION=${MODEL_LOCATION}
EOF
echo "Agent environment: continue URI is ${OAUTH_CONTINUE_URI}"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT
LOG_FILE="${WORK_DIR}/deploy.log"

UPDATE_ARGS=()
if [[ -n "${AGENT_ID:-}" ]]; then
  echo "Updating agent ${AGENT_ID}."
  UPDATE_ARGS=(--agent_engine_id="${AGENT_ID}")
else
  echo "Creating a new agent named ${AGENT_DISPLAY_NAME}."
fi

(
  cd "${DEMO_DIR}"
  "${ADK_BIN}" deploy agent_engine \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --display_name="${AGENT_DISPLAY_NAME}" \
    --description="ADK agent that reads GitHub through Auth Manager 3LO." \
    --temp_folder="${WORK_DIR}/build" \
    "${UPDATE_ARGS[@]}" \
    agent
) 2>&1 | tee "${LOG_FILE}"

NEW_ID="$(grep -oE 'reasoningEngines/[0-9]+' "${LOG_FILE}" | tail -1 | cut -d/ -f2 || true)"
if [[ -z "${NEW_ID}" ]]; then
  echo "ERROR: the deploy output has no reasoningEngines ID. Read the log above." >&2
  exit 1
fi

set_env_value AGENT_ID "${NEW_ID}"
echo
echo "Agent ID: ${NEW_ID} (written to .env)"
echo "Next step: run deploy/03_iam_grants.sh"
