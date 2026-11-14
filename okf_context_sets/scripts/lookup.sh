#!/usr/bin/env bash
# Show what an agent receives from the context set.
# Usage: scripts/lookup.sh [entry-id] [search-query]
# Defaults: entry project-borealis, query "Borealis".
set -euo pipefail
source "$(dirname "$0")/_env.sh"

ENTRY="${1:-project-borealis}"
QUERY="${2:-Borealis}"

echo "== Context lookup: ${ENTRY}"
gcloud alpha dataplex context lookup \
  --resources="${ENTRY_GROUP_NAME}/entries/${ENTRY}" \
  --location="${REGION}" \
  --project="${PROJECT_ID}"

echo
echo "== Entry search: \"${QUERY}\""
echo "(A new entry can take some minutes to appear in search results.)"
gcloud dataplex entries search "${QUERY}" \
  --project="${PROJECT_ID}" \
  --scope="projects/${PROJECT_ID}" \
  --limit=10 \
  --format="table(name.segment(5):label=ENTRY_GROUP, name.basename():label=ENTRY, entrySource.displayName:label=TITLE)"
