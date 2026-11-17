#!/usr/bin/env bash
# 10_deploy_mcp_server.sh: deploy the test MCP server to Cloud Run.
# The service is public (no authentication), because connector A uses NO_AUTH.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

gcloud_admin run deploy "${MCP_SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="${LIB_DIR}/mcp_server" \
  --allow-unauthenticated \
  --quiet

url="$(gcloud_admin run services describe "${MCP_SERVICE}" \
  --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
echo
echo "MCP server URL: ${url}/mcp"
echo "Set MCP_URL=${url}/mcp in .env before you run 30_create_mcp_connector.sh."
