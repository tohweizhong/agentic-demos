# Shared functions for the connector-level IAM test scripts.
#
# Each script sources this file. The file reads .env, sets the default values,
# and gives helpers for the access token, the REST calls, and IAM bindings.
# Requirements: bash, curl, jq, gcloud.

set -euo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "${LIB_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${LIB_DIR}/.env"
  set +a
else
  echo "ERROR: ${LIB_DIR}/.env not found. Copy .env.example to .env and set the values." >&2
  exit 1
fi

for tool in curl jq gcloud; do
  command -v "${tool}" >/dev/null 2>&1 || { echo "ERROR: ${tool} is not installed." >&2; exit 1; }
done

: "${PROJECT_ID:?Set PROJECT_ID in .env}"
: "${PROJECT_NUMBER:?Set PROJECT_NUMBER in .env}"
: "${TEST_USER:?Set TEST_USER in .env}"
LOCATION="${LOCATION:-global}"
REGION="${REGION:-us-central1}"
APP_ID="${APP_ID:-iamtest-app}"
MCP_COLLECTION_ID="${MCP_COLLECTION_ID:-iamtest-mcp-a}"
DOCS_DATASTORE_ID="${DOCS_DATASTORE_ID:-iamtest-docs-b}"
BUCKET="${BUCKET:-${PROJECT_ID}-iamtest-docs-b}"
MCP_SERVICE="${MCP_SERVICE:-iamtest-mcp-a}"
ADMIN_ACCOUNT="${ADMIN_ACCOUNT:-}"

# The Custom MCP connector creates one data store with this ID.
MCP_DATASTORE_ID="${MCP_COLLECTION_ID}_mcp_data"
CUSTOM_ROLE_ID="customRestrictedEndUser"
TEST_MEMBER="user:${TEST_USER}"

# The global location uses the global endpoint. The multi-regions (us, eu) use
# a regional endpoint.
if [[ "${LOCATION}" == "global" ]]; then
  DE_HOST="https://discoveryengine.googleapis.com"
else
  DE_HOST="https://${LOCATION}-discoveryengine.googleapis.com"
fi
DE_API="${DE_HOST}/v1alpha"
PARENT="projects/${PROJECT_NUMBER}/locations/${LOCATION}"
DEFAULT_COLLECTION="${PARENT}/collections/default_collection"
ENGINE_NAME="${DEFAULT_COLLECTION}/engines/${APP_ID}"
DOCS_DATASTORE_NAME="${DEFAULT_COLLECTION}/dataStores/${DOCS_DATASTORE_ID}"
MCP_COLLECTION_NAME="${PARENT}/collections/${MCP_COLLECTION_ID}"
MCP_DATASTORE_NAME="${DEFAULT_COLLECTION}/dataStores/${MCP_DATASTORE_ID}"

# gcloud_admin runs gcloud as the admin account, if ADMIN_ACCOUNT is set.
gcloud_admin() {
  if [[ -n "${ADMIN_ACCOUNT}" ]]; then
    gcloud --account="${ADMIN_ACCOUNT}" "$@"
  else
    gcloud "$@"
  fi
}

# token prints an access token for the admin account.
token() {
  gcloud_admin auth print-access-token
}

# api METHOD URL [BODY] sends one REST call and prints the response body.
# The function stops the script if the HTTP status is not 2xx.
api() {
  local method="$1" url="$2" body="${3:-}"
  local out status
  out="$(mktemp)"
  local args=(-sS -o "${out}" -w '%{http_code}' -X "${method}"
    -H "Authorization: Bearer $(token)"
    -H "Content-Type: application/json"
    -H "X-Goog-User-Project: ${PROJECT_ID}")
  if [[ -n "${body}" ]]; then
    args+=(--data "${body}")
  fi
  status="$(curl "${args[@]}" "${url}")"
  if [[ "${status}" != 2* ]]; then
    echo "ERROR: ${method} ${url} returned HTTP ${status}" >&2
    cat "${out}" >&2
    rm -f "${out}"
    return 1
  fi
  cat "${out}"
  rm -f "${out}"
}

# api_status METHOD URL prints only the HTTP status. Use it to check if a
# resource exists. It does not stop the script.
api_status() {
  local method="$1" url="$2"
  curl -sS -o /dev/null -w '%{http_code}' -X "${method}" \
    -H "Authorization: Bearer $(token)" \
    -H "X-Goog-User-Project: ${PROJECT_ID}" "${url}"
}

# wait_operation OPERATION_NAME polls a long-running operation until it is done.
wait_operation() {
  local op="$1" resp
  for _ in $(seq 1 120); do
    resp="$(api GET "${DE_API}/${op}")"
    if [[ "$(jq -r '.done // false' <<<"${resp}")" == "true" ]]; then
      if jq -e '.error' <<<"${resp}" >/dev/null; then
        echo "ERROR: operation ${op} failed:" >&2
        jq '.error' <<<"${resp}" >&2
        return 1
      fi
      echo "Operation done: ${op}"
      return 0
    fi
    echo "Waiting for operation ${op} ..."
    sleep 10
  done
  echo "ERROR: operation ${op} is not done after 20 minutes." >&2
  return 1
}

# de_add_binding RESOURCE ROLE MEMBER adds one member to one role on a
# Discovery Engine resource (engine, collection, or data store).
# The function reads the policy, adds the member, and writes the policy back
# with the same etag. It keeps all other bindings.
de_add_binding() {
  local resource="$1" role="$2" member="$3" policy new
  policy="$(api GET "${DE_API}/${resource}:getIamPolicy")"
  new="$(jq --arg role "${role}" --arg member "${member}" '
    .bindings = (.bindings // [])
    | if any(.bindings[]; .role == $role) then
        .bindings |= map(if .role == $role then .members = ((.members // []) + [$member] | unique) else . end)
      else
        .bindings += [{role: $role, members: [$member]}]
      end' <<<"${policy}")"
  api POST "${DE_API}/${resource}:setIamPolicy" "$(jq -n --argjson p "${new}" '{policy: $p}')" \
    | jq -c '{etag, bindings}'
}

# de_remove_member RESOURCE MEMBER removes one member from every role on a
# Discovery Engine resource. The function keeps all other members.
de_remove_member() {
  local resource="$1" member="$2" policy new
  policy="$(api GET "${DE_API}/${resource}:getIamPolicy")"
  new="$(jq --arg member "${member}" '
    .bindings = ((.bindings // [])
      | map(.members = ((.members // []) - [$member]))
      | map(select((.members | length) > 0)))' <<<"${policy}")"
  api POST "${DE_API}/${resource}:setIamPolicy" "$(jq -n --argjson p "${new}" '{policy: $p}')" \
    | jq -c '{etag, bindings}'
}

# project_roles_of MEMBER prints the project-level roles of one member.
project_roles_of() {
  gcloud_admin projects get-iam-policy "${PROJECT_ID}" \
    --flatten="bindings[].members" \
    --filter="bindings.members=\"$1\"" \
    --format="value(bindings.role)"
}
