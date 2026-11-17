#!/usr/bin/env bash
# 70_round2_grants.sh: round 2 roles.
#   1. Create the custom role customRestrictedEndUser with two permissions.
#   2. Replace the project role of the test user with the custom role.
#   3. Give agentspaceUser on connector B (docs data store) only.
# All IAM changes read the policy and keep the existing bindings.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

echo "== 1. Custom role ${CUSTOM_ROLE_ID}"
if gcloud_admin iam roles describe "${CUSTOM_ROLE_ID}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "The role exists. Skip."
else
  gcloud_admin iam roles create "${CUSTOM_ROLE_ID}" \
    --project="${PROJECT_ID}" \
    --title="Custom Restricted End User" \
    --description="Gemini Enterprise end user without project-wide data store access." \
    --permissions="discoveryengine.devToolsConfigs.get,discoveryengine.locations.buildAuthorizationUrl" \
    --stage=GA --format=none
fi

echo "== 2. Replace the project role of ${TEST_MEMBER}"
gcloud_admin projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${TEST_MEMBER}" \
  --role="projects/${PROJECT_ID}/roles/${CUSTOM_ROLE_ID}" \
  --condition=None --format=none
if project_roles_of "${TEST_MEMBER}" | grep -qx "roles/discoveryengine.agentspaceRestrictedUser"; then
  gcloud_admin projects remove-iam-policy-binding "${PROJECT_ID}" \
    --member="${TEST_MEMBER}" \
    --role="roles/discoveryengine.agentspaceRestrictedUser" \
    --condition=None --format=none
fi

echo "== 3. agentspaceUser on connector B (${DOCS_DATASTORE_ID}) only"
de_add_binding "${DOCS_DATASTORE_NAME}" "roles/discoveryengine.agentspaceUser" "${TEST_MEMBER}"

echo
echo "Project roles of ${TEST_MEMBER}:"
project_roles_of "${TEST_MEMBER}"
echo "Round 2 started at $(date -u '+%Y-%m-%d %H:%M:%S UTC'). Check after about 5 minutes."
