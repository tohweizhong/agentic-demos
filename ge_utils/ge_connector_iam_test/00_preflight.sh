#!/usr/bin/env bash
# 00_preflight.sh: read-only checks before the test. This script changes nothing.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

echo "== 1. Project settings (experienceState and toggle)"
project="$(api GET "${DE_API}/projects/${PROJECT_NUMBER}")"
state="$(jq -r '.experienceState // "UNSET"' <<<"${project}")"
toggle="$(jq -r '.customerProvidedConfig.resourceAccessControlConfig.dataStoreAccessControlEnabled // false' <<<"${project}")"
echo "experienceState: ${state}"
echo "dataStoreAccessControlEnabled: ${toggle}"
if [[ "${state}" != "LEGACY_ONLY" ]]; then
  echo "WARNING: experienceState is not LEGACY_ONLY. This test covers classic Gemini Enterprise only."
fi
if [[ "${toggle}" == "true" ]]; then
  echo "WARNING: the toggle is already on. It applies to all apps and data stores in this location."
fi

echo
echo "== 2. Effective organization policies"
# If the Organization Policy API is off in this project, add
# --billing-project=<a project where the API is on> to these commands.
for c in disableCustomMcpServerConnector allowedDataSources allowedEgressFqdns; do
  echo "-- discoveryengine.managed.${c}"
  gcloud_admin org-policies describe "discoveryengine.managed.${c}" \
    --effective --project="${PROJECT_ID}" --format=yaml \
    || echo "WARNING: cannot read this policy. If the Organization Policy API is off, use --billing-project."
done
echo "NOTE: if disableCustomMcpServerConnector shows 'enforce: true', you cannot create a Custom MCP connector."
echo "NOTE: allowedDataSources and allowedEgressFqdns block provisioning only in VPC-SC projects or listed projects."

echo
echo "== 3. Project-level roles of ${TEST_MEMBER}"
roles="$(project_roles_of "${TEST_MEMBER}")"
if [[ -z "${roles}" ]]; then
  echo "(no direct project-level roles)"
else
  echo "${roles}"
fi
if grep -Eq '^roles/(owner|editor|discoveryengine\.)' <<<"${roles}"; then
  echo "WARNING: the test user holds a predefined Discovery Engine role, Owner, or Editor at project level."
  echo "WARNING: these roles cancel the resource-level control. The connector stays visible."
fi
echo "NOTE: this check shows direct bindings only. Also check the groups of the test user."
