#!/usr/bin/env bash
# 99_cleanup.sh: remove everything that the test created.
# Each step continues if a resource does not exist.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

step() { echo; echo "== $*"; }

step "1. Turn off the toggle"
"${LIB_DIR}/50_toggle.sh" off || echo "WARNING: cannot turn off the toggle."

step "2. Remove the test user from the test resources"
for r in "${ENGINE_NAME}" "${DOCS_DATASTORE_NAME}" "${MCP_COLLECTION_NAME}" "${MCP_DATASTORE_NAME}"; do
  de_remove_member "${r}" "${TEST_MEMBER}" || echo "WARNING: skip ${r}."
done

step "3. Remove the project roles of the test user and the custom role"
for role in "roles/discoveryengine.agentspaceRestrictedUser" "projects/${PROJECT_ID}/roles/${CUSTOM_ROLE_ID}"; do
  if project_roles_of "${TEST_MEMBER}" | grep -qx "${role}"; then
    gcloud_admin projects remove-iam-policy-binding "${PROJECT_ID}" \
      --member="${TEST_MEMBER}" --role="${role}" --condition=None --format=none
    echo "Removed ${role}."
  fi
done
gcloud_admin iam roles delete "${CUSTOM_ROLE_ID}" --project="${PROJECT_ID}" --quiet \
  || echo "WARNING: cannot delete the custom role (it can be deleted already)."

step "4. Delete the app ${APP_ID}"
# Wait for the app delete. A data store that is attached to an app cannot be deleted.
if op="$(api DELETE "${DE_API}/${ENGINE_NAME}")"; then
  op_name="$(jq -r '.name // empty' <<<"${op}")"
  if [[ -n "${op_name}" && "$(jq -r '.done // false' <<<"${op}")" != "true" ]]; then
    wait_operation "${op_name}" || echo "WARNING: the app delete did not finish."
  fi
else
  echo "WARNING: skip the app."
fi

step "5. Delete connector A (collection ${MCP_COLLECTION_ID})"
api DELETE "${DE_API}/${MCP_COLLECTION_NAME}" | jq -r '.name // empty' || echo "WARNING: skip connector A."

step "6. Delete connector B (data store ${DOCS_DATASTORE_ID})"
api DELETE "${DE_API}/${DOCS_DATASTORE_NAME}" | jq -r '.name // empty' || echo "WARNING: skip connector B."

step "7. Delete the bucket gs://${BUCKET}"
gcloud_admin storage rm --recursive "gs://${BUCKET}" --quiet || echo "WARNING: skip the bucket."

step "8. Delete the Cloud Run service ${MCP_SERVICE}"
gcloud_admin run services delete "${MCP_SERVICE}" --project="${PROJECT_ID}" --region="${REGION}" --quiet \
  || echo "WARNING: skip the Cloud Run service."

cat <<EOF

== 9. Organization policy override (not run)
If you made a project-level override of the Custom MCP constraint, delete it with:
  gcloud org-policies delete discoveryengine.managed.disableCustomMcpServerConnector --project=${PROJECT_ID}
Then check the effective policy:
  gcloud org-policies describe discoveryengine.managed.disableCustomMcpServerConnector --effective --project=${PROJECT_ID}
EOF
