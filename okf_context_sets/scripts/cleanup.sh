#!/usr/bin/env bash
# Delete the context set (entries, entry links, entry group) and the BigQuery
# dataset. Asks for confirmation first.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

echo "This script deletes these resources in project ${PROJECT_ID}:"
echo "  - Entry group (context set): ${ENTRY_GROUP_NAME}, with all its entries and entry links"
echo "  - BigQuery dataset: ${PROJECT_ID}:${BQ_DATASET}, with all its tables"
read -r -p "Type the entry group ID (${ENTRY_GROUP}) to confirm: " answer
if [[ "${answer}" != "${ENTRY_GROUP}" ]]; then
  echo "The answer does not match. Nothing is deleted."
  exit 1
fi

API="https://dataplex.googleapis.com/v1"
TOKEN="$(gcloud auth print-access-token)"

if gcloud dataplex entry-groups describe "${ENTRY_GROUP}" \
     --location="${REGION}" --project="${PROJECT_ID}" --format="value(name)" >/dev/null 2>&1; then

  # Entry links. The list method is not public. kcmd records the link IDs in
  # _links.yaml after a pull, so read them from pulled/ or workspace/.
  link_ids="$(cat "${DEMO_DIR}"/pulled/bundle/_links.yaml "${DEMO_DIR}"/workspace/bundle/_links.yaml 2>/dev/null \
    | sed -n 's/^[[:space:]-]*id:[[:space:]]*//p' | tr -d '"'"'" | sort -u || true)"
  for link in ${link_ids}; do
    echo "== Delete entry link ${link}"
    curl -sS -o /dev/null -w "HTTP %{http_code}\n" -X DELETE \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "x-goog-user-project: ${PROJECT_ID}" \
      "${API}/${ENTRY_GROUP_NAME}/entryLinks/${link}"
  done

  echo "== Delete entries"
  entries="$(gcloud dataplex entries list --entry-group="${ENTRY_GROUP}" \
    --location="${REGION}" --project="${PROJECT_ID}" --format="value(name.basename())")"
  for entry in ${entries}; do
    echo "   ${entry}"
    gcloud dataplex entries delete "${entry}" --entry-group="${ENTRY_GROUP}" \
      --location="${REGION}" --project="${PROJECT_ID}" --quiet >/dev/null
  done

  echo "== Delete entry group ${ENTRY_GROUP}"
  gcloud dataplex entry-groups delete "${ENTRY_GROUP}" \
    --location="${REGION}" --project="${PROJECT_ID}" --quiet
else
  echo "== Entry group ${ENTRY_GROUP} does not exist. Skip."
fi

if bq --project_id="${PROJECT_ID}" show --format=none "${PROJECT_ID}:${BQ_DATASET}" >/dev/null 2>&1; then
  echo "== Delete BigQuery dataset ${BQ_DATASET}"
  bq --project_id="${PROJECT_ID}" rm -r -f --dataset "${PROJECT_ID}:${BQ_DATASET}"
else
  echo "== BigQuery dataset ${BQ_DATASET} does not exist. Skip."
fi

echo "== Check"
if gcloud dataplex entry-groups describe "${ENTRY_GROUP}" \
     --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "WARNING: entry group ${ENTRY_GROUP} still exists." >&2
else
  echo "Entry group ${ENTRY_GROUP}: deleted."
fi
if bq --project_id="${PROJECT_ID}" show --format=none "${PROJECT_ID}:${BQ_DATASET}" >/dev/null 2>&1; then
  echo "WARNING: dataset ${BQ_DATASET} still exists." >&2
else
  echo "Dataset ${BQ_DATASET}: deleted."
fi

echo "The local workspace/ and pulled/ folders are not deleted. They now point"
echo "to a deleted context set. Remove them before the next push."
