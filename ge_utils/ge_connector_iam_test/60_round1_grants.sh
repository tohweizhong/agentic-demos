#!/usr/bin/env bash
# 60_round1_grants.sh: round 1 roles. The test user gets the predefined
# restricted role at project level and agentspaceUser on the app.
# This is a common setup for end users of classic Gemini Enterprise.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

echo "== 1. Project role: roles/discoveryengine.agentspaceRestrictedUser"
gcloud_admin projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="${TEST_MEMBER}" \
  --role="roles/discoveryengine.agentspaceRestrictedUser" \
  --condition=None --format=none

echo "== 2. App role: roles/discoveryengine.agentspaceUser on ${APP_ID}"
de_add_binding "${ENGINE_NAME}" "roles/discoveryengine.agentspaceUser" "${TEST_MEMBER}"

echo
echo "Project roles of ${TEST_MEMBER}:"
project_roles_of "${TEST_MEMBER}"
