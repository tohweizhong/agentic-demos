#!/usr/bin/env bash
# 20_create_docs_datastore.sh: create connector B, a Cloud Storage data store
# with two text files that hold the marker DOC-MARKER-B.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

echo "== 1. Create the data store ${DOCS_DATASTORE_ID}"
body="$(jq -n --arg name "${DOCS_DATASTORE_ID}" '{
  displayName: $name,
  industryVertical: "GENERIC",
  solutionTypes: ["SOLUTION_TYPE_SEARCH"],
  contentConfig: "CONTENT_REQUIRED"
}')"
op="$(api POST "${DE_API}/${DEFAULT_COLLECTION}/dataStores?dataStoreId=${DOCS_DATASTORE_ID}" "${body}")"
wait_operation "$(jq -r '.name' <<<"${op}")"

echo
echo "== 2. Create the bucket gs://${BUCKET} and upload two files"
if ! gcloud_admin storage buckets describe "gs://${BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud_admin storage buckets create "gs://${BUCKET}" \
    --project="${PROJECT_ID}" --location="${REGION}" --uniform-bucket-level-access
fi
tmp="$(mktemp -d)"
trap 'rm -rf "${tmp}"' EXIT
cat >"${tmp}/iamtest_doc1.txt" <<'EOF'
IAM test document one for connector B.
The connector B marker is DOC-MARKER-B.
This document exists only for the connector IAM test.
EOF
cat >"${tmp}/iamtest_doc2.txt" <<'EOF'
IAM test document two for connector B.
If you can read this, you have access to connector B. The marker is DOC-MARKER-B.
EOF
gcloud_admin storage cp "${tmp}/iamtest_doc1.txt" "${tmp}/iamtest_doc2.txt" "gs://${BUCKET}/"

echo
echo "== 3. Import the files"
body="$(jq -n --arg uri "gs://${BUCKET}/*.txt" '{
  gcsSource: {inputUris: [$uri], dataSchema: "content"},
  reconciliationMode: "INCREMENTAL"
}')"
op="$(api POST "${DE_API}/${DOCS_DATASTORE_NAME}/branches/default_branch/documents:import" "${body}")"
wait_operation "$(jq -r '.name' <<<"${op}")"
echo "Connector B is ready: ${DOCS_DATASTORE_NAME}"
