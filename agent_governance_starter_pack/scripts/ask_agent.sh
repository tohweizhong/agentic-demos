#!/usr/bin/env bash
# Sends one message to the reference agent on Agent Runtime and prints the reply.
#
# Usage: scripts/ask_agent.sh [-a AGENT_RESOURCE_NAME] [-u USER_ID] [-s SESSION_ID] "MESSAGE"
#
# Without -s, the script creates a new session and prints its ID. Use the same
# -u and -s again to continue the conversation in that session.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform gcloud curl jq

AGENT=""
USER_ID="operator"
SESSION_ID=""
PASSED_SESSION_ID=""
while getopts "a:u:s:" opt; do
  case "${opt}" in
    a) AGENT="${OPTARG}" ;;
    u) USER_ID="${OPTARG}" ;;
    s) SESSION_ID="${OPTARG}"; PASSED_SESSION_ID="${OPTARG}" ;;
    *) echo "Usage: $0 [-a AGENT_RESOURCE_NAME] [-u USER_ID] [-s SESSION_ID] \"MESSAGE\"" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
MESSAGE="${1:?Give the message as the last argument.}"

if [[ -z "${AGENT}" ]]; then
  AGENT="$(tf_output agent_resource_name)"
fi
REGION="$(tf_output region)"
PROJECT="$(tf_output project_id)"
API="https://${REGION}-aiplatform.googleapis.com/v1/${AGENT}"
TOKEN="$(gcloud auth print-access-token)"

call() {
  curl -sS --fail-with-body -X POST "$1" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "x-goog-user-project: ${PROJECT}" \
    -H "Content-Type: application/json" \
    -d "$2"
}

if [[ -z "${SESSION_ID}" ]]; then
  body="$(jq -n --arg u "${USER_ID}" '{class_method: "async_create_session", input: {user_id: $u}}')"
  for _try in 1 2 3; do
    SESSION_ID="$(call "${API}:query" "${body}" 2>/dev/null | jq -r '.output.id // empty' || true)"
    [[ -n "${SESSION_ID}" ]] && break
    if [[ "${_try}" -lt 3 ]]; then
      echo "[retry] Waiting 10s for endpoint/IAM readiness..." >&2
      sleep 10
      TOKEN="$(gcloud auth print-access-token)"
    fi
  done
  [[ -n "${SESSION_ID}" ]] || { echo "ERROR: async_create_session failed after 3 attempts on ${AGENT}" >&2; exit 1; }
  echo "New session: ${SESSION_ID}"
fi
echo "User: ${USER_ID}  Session: ${SESSION_ID}"
echo

body="$(jq -n --arg u "${USER_ID}" --arg s "${SESSION_ID}" --arg m "${MESSAGE}" \
  '{class_method: "async_stream_query", input: {user_id: $u, session_id: $s, message: $m}}')"

# Each line of the stream is one ADK event in JSON. Print the tool calls, the
# tool results, and the text.
ATTEMPTS=0
MAX_ATTEMPTS=3
while [[ "${ATTEMPTS}" -lt "${MAX_ATTEMPTS}" ]]; do
  ATTEMPTS=$((ATTEMPTS + 1))
  
  # Stream output into a temporary file
  TMP_OUT="$(mktemp)"
  if ! call "${API}:streamQuery?alt=sse" "${body}" 2> "${TMP_OUT}.err" | while IFS= read -r line; do
    line="${line#data: }"
    [[ -z "${line}" ]] && continue
    echo "${line}" | jq -r '
      ((.content.parts // [])[] |
        if .function_call then "[tool call] \(.function_call.name) \(.function_call.args | tostring)"
        elif .function_response then "[tool result] \(.function_response.name): \(.function_response.response | tostring | .[0:300])"
        elif .text then "[agent] \(.text)"
        else empty end),
      (if .error_code then "[error] \(.error_code): \(.error_message)"
       elif .error then "[error] \(.error | tostring)"
       else empty end)' 2>/dev/null || echo "${line}"
  done > "${TMP_OUT}"; then
    cat "${TMP_OUT}.err" >> "${TMP_OUT}"
  fi
  rm -f "${TMP_OUT}.err"
  
  if ! grep -q -E "Model Armor:|Denied by IAP" "${TMP_OUT}" && \
     grep -q -E "\[error\] MALFORMED_FUNCTION_CALL|RefreshError|401|403|The caller does not have permission" "${TMP_OUT}"; then
    if [[ "${ATTEMPTS}" -lt "${MAX_ATTEMPTS}" ]]; then
      echo "[retry] Waiting 10s for IAM propagation..." >&2
      sleep 10
      TOKEN="$(gcloud auth print-access-token)"

      if [[ -z "${PASSED_SESSION_ID}" ]]; then
        body_session="$(jq -n --arg u "${USER_ID}" '{class_method: "async_create_session", input: {user_id: $u}}')"
        SESSION_ID="$(call "${API}:query" "${body_session}" | jq -r '.output.id')"
        body="$(jq -n --arg u "${USER_ID}" --arg s "${SESSION_ID}" --arg m "${MESSAGE}"           '{class_method: "async_stream_query", input: {user_id: $u, session_id: $s, message: $m}}')"
      fi
      rm -f "${TMP_OUT}"
      continue
    fi
  fi
  
  cat "${TMP_OUT}"
  rm -f "${TMP_OUT}"
  break
done
