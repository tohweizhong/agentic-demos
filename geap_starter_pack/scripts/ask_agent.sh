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
USER_ID="demo-user"
SESSION_ID=""
while getopts "a:u:s:" opt; do
  case "${opt}" in
    a) AGENT="${OPTARG}" ;;
    u) USER_ID="${OPTARG}" ;;
    s) SESSION_ID="${OPTARG}" ;;
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
  SESSION_ID="$(call "${API}:query" "${body}" | jq -r '.output.id')"
  echo "New session: ${SESSION_ID}"
fi
echo "User: ${USER_ID}  Session: ${SESSION_ID}"
echo

body="$(jq -n --arg u "${USER_ID}" --arg s "${SESSION_ID}" --arg m "${MESSAGE}" \
  '{class_method: "async_stream_query", input: {user_id: $u, session_id: $s, message: $m}}')"

# Each line of the stream is one ADK event in JSON. Print the tool calls, the
# tool results, and the text.
call "${API}:streamQuery?alt=sse" "${body}" | while IFS= read -r line; do
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
done
