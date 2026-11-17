#!/usr/bin/env bash
# 40_create_app.sh: create the test app with connector A and connector B.
# Create the app with all data stores in one call. An app that was created
# with one data store cannot get more data stores later (FAILED_PRECONDITION).
set -euo pipefail
source "$(dirname "$0")/lib.sh"

body="$(jq -n --arg name "${APP_ID}" --arg a "${DOCS_DATASTORE_ID}" --arg b "${MCP_DATASTORE_ID}" '{
  displayName: $name,
  solutionType: "SOLUTION_TYPE_SEARCH",
  industryVertical: "GENERIC",
  appType: "APP_TYPE_INTRANET",
  dataStoreIds: [$a, $b],
  searchEngineConfig: {
    searchTier: "SEARCH_TIER_ENTERPRISE",
    searchAddOns: ["SEARCH_ADD_ON_LLM"]
  },
  commonConfig: {companyName: "IAM Test"}
}')"
op="$(api POST "${DE_API}/${DEFAULT_COLLECTION}/engines?engineId=${APP_ID}" "${body}")"
op_name="$(jq -r '.name' <<<"${op}")"
if [[ "$(jq -r '.done // false' <<<"${op}")" != "true" ]]; then
  wait_operation "${op_name}"
fi

api GET "${DE_API}/${ENGINE_NAME}" | jq '{name, dataStoreIds}'

config_id="$(api GET "${DE_API}/${ENGINE_NAME}/widgetConfigs/default_search_widget_config" | jq -r '.configId // empty')"
if [[ -n "${config_id}" ]]; then
  echo "Web app URL: https://vertexaisearch.cloud.google.com/home/cid/${config_id}"
else
  echo "WARNING: no configId yet. Open the app in the console to get the web app URL."
fi
