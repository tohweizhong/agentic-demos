#!/bin/bash
# Script to list all user licenses and the users assigned to them in a project.
#
# Usage: ./list_user_licenses.sh [target_project_id] [location]
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ ! -f "$DIR/env.sh" ]; then
    echo "Error: env.sh not found." >&2
    echo "Please copy env.sh.template to env.sh and configure your variables." >&2
    exit 1
fi

source "$DIR/env.sh"

PROJECT_ID_VAL="${1:-${TARGET_PROJECT_ID:-}}"
LOCATION_VAL="${2:-${LOCATION:-global}}"

if [ -z "$PROJECT_ID_VAL" ] || [ "$PROJECT_ID_VAL" = "YOUR_TARGET_PROJECT_ID" ]; then
    echo "Error: TARGET_PROJECT_ID is not configured in env.sh or passed as an argument." >&2
    exit 1
fi

ENDPOINT_PREFIX="${ENDPOINT_LOCATION:-global}"

echo "Listing user licenses for project $PROJECT_ID_VAL in location $LOCATION_VAL..."

curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${PROJECT_ID_VAL}" \
  "https://${ENDPOINT_PREFIX}-discoveryengine.googleapis.com/v1/projects/${PROJECT_ID_VAL}/locations/${LOCATION_VAL}/userStores/default_user_store/userLicenses"
