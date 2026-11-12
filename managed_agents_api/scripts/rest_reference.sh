#!/usr/bin/env bash
# REST reference for the Managed Agents API.
#
# The script sends each call with curl, in this order:
#   create -> operation -> get -> list -> update -> interaction -> delete
#
# It uses its own agent, `demo-rest-reference`, so it does not change the agent of the
# Python scripts. It mounts the demo bucket, so run scripts/00b_setup_bucket.py first.
#
# Usage:
#   export PROJECT_ID=your-project-id
#   export BUCKET=your-project-id-managed-agents-demo   # Optional. This is the default.
#   bash scripts/rest_reference.sh            # All steps.
#   bash scripts/rest_reference.sh list       # One step: create, operation, get, list,
#                                             # update, interact, or delete.

set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your Google Cloud project ID.}"
BUCKET="${BUCKET:-${PROJECT_ID}-managed-agents-demo}"
AGENT_ID="demo-rest-reference"
API="https://aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/global"

token() { gcloud auth application-default print-access-token; }

call() {
  # call METHOD URL [JSON_BODY]
  local method="$1" url="$2" body="${3:-}"
  echo "==> ${method} ${url}" >&2
  if [[ -n "${body}" ]]; then
    curl -sS -X "${method}" "${url}" \
      -H "Authorization: Bearer $(token)" \
      -H "X-Goog-User-Project: ${PROJECT_ID}" \
      -H "Content-Type: application/json" \
      -d "${body}"
  else
    curl -sS -X "${method}" "${url}" \
      -H "Authorization: Bearer $(token)" \
      -H "X-Goog-User-Project: ${PROJECT_ID}"
  fi
  echo
}

wait_operation() {
  # wait_operation OPERATION_NAME
  local name="$1" reply
  for _ in $(seq 1 120); do
    reply="$(call GET "https://aiplatform.googleapis.com/v1beta1/${name}" 2>/dev/null)"
    if grep -q '"done": true' <<<"${reply}"; then
      echo "${reply}"
      return 0
    fi
    sleep 5
  done
  echo "The operation is not done after 600 s: ${name}" >&2
  return 1
}

operation_name() { sed -n 's/.*"name": "\([^"]*operations[^"]*\)".*/\1/p' | head -n 1; }

step_create() {
  # The Preview API accepts only `gcs` and `skill_registry` sources. A data source needs
  # the network allowlist, and the only accepted domain is "*". The mount target must
  # be inside /workspace, so the target is ".agent".
  call POST "${API}/agents" '{
    "id": "'"${AGENT_ID}"'",
    "base_agent": "antigravity-preview-05-2026",
    "description": "REST reference agent for the Managed Agents API demo.",
    "system_instruction": "Read /workspace/.agent/AGENTS.md before you start, and follow it.",
    "tools": [{"type": "code_execution"}, {"type": "filesystem"}],
    "base_environment": {
      "type": "remote",
      "sources": [{"type": "gcs", "source": "gs://'"${BUCKET}"'/agent", "target": ".agent"}],
      "network": {"allowlist": [{"domain": "*"}]}
    }
  }' | tee >(cat >&2) | operation_name > "${TMPDIR:-/tmp}/demo-rest-operation"
}

step_operation() {
  local name
  name="$(cat "${TMPDIR:-/tmp}/demo-rest-operation")"
  if [[ -z "${name}" ]]; then
    echo "No operation name. Run the create step first." >&2
    return 1
  fi
  wait_operation "${name}"
}

step_get() { call GET "${API}/agents/${AGENT_ID}"; }

step_list() { call GET "${API}/agents?page_size=50"; }

step_update() {
  # The SDK has no update method. Use PATCH with update_mask. The update is also a
  # long-running operation.
  local name
  name="$(call PATCH "${API}/agents/${AGENT_ID}?update_mask=description" '{
    "name": "'"${AGENT_ID}"'",
    "description": "REST reference agent. Description updated with PATCH."
  }' | tee >(cat >&2) | operation_name)"
  [[ -n "${name}" ]] && wait_operation "${name}" > /dev/null
  step_get
}

step_interact() {
  # The reply is a server-sent event stream. The last event, interaction.completed, has
  # the interaction ID and the environment ID for the next turn.
  echo "==> POST ${API}/interactions" >&2
  curl -sS -N -X POST "${API}/interactions" \
    -H "Authorization: Bearer $(token)" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" \
    -H "Content-Type: application/json" \
    -H "Api-Revision: 2026-05-20" \
    -d '{
      "agent": "'"${AGENT_ID}"'",
      "stream": true,
      "background": true,
      "store": true,
      "input": [{"type": "user_input", "content": [{"type": "text",
        "text": "Count the rows in /workspace/.agent/data/sales.csv. Answer with one number."}]}]
    }' | grep -E '^event: (interaction\.(created|completed)|error)' -A1
}

step_delete() {
  local name
  name="$(call DELETE "${API}/agents/${AGENT_ID}" | tee >(cat >&2) | operation_name)"
  if [[ -n "${name}" ]]; then
    wait_operation "${name}" > /dev/null || true
  fi
  echo "Deleted ${AGENT_ID}."
}

main() {
  case "${1:-all}" in
    create) step_create ;;
    operation) step_operation ;;
    get) step_get ;;
    list) step_list ;;
    update) step_update ;;
    interact) step_interact ;;
    delete) step_delete ;;
    all)
      step_create
      step_operation > /dev/null
      step_get
      step_list
      step_update
      step_interact
      step_delete
      ;;
    *)
      echo "Unknown step: $1" >&2
      exit 2
      ;;
  esac
}

main "$@"
