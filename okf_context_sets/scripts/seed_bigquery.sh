#!/usr/bin/env bash
# Create the BigQuery dataset and load seed/projects.csv into the projects table.
# A Gemini Enterprise app needs a BigQuery data store in federated query mode
# to use Knowledge Catalog. This table gives that data store data to query.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

TABLE="${PROJECT_ID}:${BQ_DATASET}.projects"

if bq --project_id="${PROJECT_ID}" show --format=none "${PROJECT_ID}:${BQ_DATASET}" >/dev/null 2>&1; then
  echo "== Dataset ${BQ_DATASET} exists"
else
  echo "== Create dataset ${BQ_DATASET} in ${BQ_LOCATION}"
  bq --project_id="${PROJECT_ID}" mk --dataset \
    --location="${BQ_LOCATION}" \
    --description="Fictional project catalog for the OKF context set demo." \
    "${PROJECT_ID}:${BQ_DATASET}"
fi

echo "== Load seed/projects.csv into ${TABLE}"
bq --project_id="${PROJECT_ID}" load --replace \
  --source_format=CSV --skip_leading_rows=1 \
  "${TABLE}" "${DEMO_DIR}/seed/projects.csv" "${DEMO_DIR}/seed/schema.json"
bq --project_id="${PROJECT_ID}" update \
  --description="Fictional projects. One row for each entry in the OKF context set." \
  "${TABLE}"

echo "== Check the table"
bq --project_id="${PROJECT_ID}" query --use_legacy_sql=false --format=pretty \
  "SELECT project_id, title, status, owner_email FROM \`${PROJECT_ID}.${BQ_DATASET}.projects\` ORDER BY project_id"
