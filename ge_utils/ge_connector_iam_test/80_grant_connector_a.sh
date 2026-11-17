#!/usr/bin/env bash
# 80_grant_connector_a.sh: give the test user agentspaceUser on connector A.
# A connector has two resources: the collection and its data store. Grant both.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

echo "== 1. Collection ${MCP_COLLECTION_ID}"
de_add_binding "${MCP_COLLECTION_NAME}" "roles/discoveryengine.agentspaceUser" "${TEST_MEMBER}"

echo "== 2. Data store ${MCP_DATASTORE_ID}"
de_add_binding "${MCP_DATASTORE_NAME}" "roles/discoveryengine.agentspaceUser" "${TEST_MEMBER}"

echo "Grant done at $(date -u '+%Y-%m-%d %H:%M:%S UTC'). Check after about 1 minute."
