#!/usr/bin/env bash
# 30_create_mcp_connector.sh: create connector A, a Custom MCP connector that
# points to the test MCP server. The connector uses NO_AUTH.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

if [[ -z "${MCP_URL:-}" ]]; then
  base="$(gcloud_admin run services describe "${MCP_SERVICE}" \
    --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
  MCP_URL="${base}/mcp"
fi
echo "MCP server URL: ${MCP_URL}"

instructions="IAM test connector A. Always call get_marker when the user asks for the connector A marker or the MCP marker."
action_config="$(jq -n --arg uri "${MCP_URL}" --arg ins "${instructions}" '{
  isActionConfigured: true,
  createBapConnection: true,
  actionParams: {auth_type: "NO_AUTH", instance_uri: $uri, mcp_agent_instructions: $ins}
}')"

echo "== 1. setUpDataConnectorV2"
body="$(jq -n --argjson ac "${action_config}" '{
  dataSource: "custom_mcp",
  dataSourceVersion: 1,
  params: {oauth_access_token: "unused"},
  refreshInterval: "86400s",
  entities: [{entityName: "mcp_data"}],
  connectorModes: ["FEDERATED"],
  actionConfig: $ac
}')"
display_name="$(jq -rn --arg s "${MCP_COLLECTION_ID}" '$s|@uri')"
op="$(api POST "${DE_API}/${PARENT}:setUpDataConnectorV2?collectionId=${MCP_COLLECTION_ID}&collectionDisplayName=${display_name}" "${body}")"
op_name="$(jq -r '.name' <<<"${op}")"
if [[ "$(jq -r '.done // false' <<<"${op}")" != "true" ]]; then
  wait_operation "${op_name}"
fi

echo
echo "== 2. Activate the actions (PATCH actionConfig)"
connector="${MCP_COLLECTION_NAME}/dataConnector"
body="$(jq -n --arg name "${connector}" --argjson ac "${action_config}" '{name: $name, actionConfig: $ac}')"
api PATCH "${DE_API}/${connector}?updateMask=actionConfig" "${body}" >/dev/null

echo
echo "== 3. Connector state"
sleep 5
api GET "${DE_API}/${connector}" | jq '{state, actionState, entities}'
echo "Data store of connector A: ${MCP_DATASTORE_ID}"

cat <<EOF

==================================================================
MANUAL STEP (required)
The API does not enable the MCP tools. Without this step, Gemini
Enterprise never calls the MCP server.
  1. Open the Google Cloud console > Gemini Enterprise > Data stores.
  2. Open the data store ${MCP_COLLECTION_ID}.
  3. Open Actions. Click "Reload custom actions".
  4. Enable the action get_marker ("Get Marker").
==================================================================
EOF
