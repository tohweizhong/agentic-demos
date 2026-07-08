#!/bin/bash
# Script to remove licenses from individual users (unassign them).
#
# Usage: ./remove_user_license.sh <user_email_1> [user_email_2] ...
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ ! -f "$DIR/env.sh" ]; then
    echo "Error: env.sh not found." >&2
    echo "Please copy env.sh.template to env.sh and configure your variables." >&2
    exit 1
fi

source "$DIR/env.sh"

USERS=("$@")
if [ ${#USERS[@]} -eq 0 ]; then
    echo "Error: No user emails specified." >&2
    echo "Usage: $0 <user_email_1> [user_email_2] ..." >&2
    exit 1
fi

# Validation of required variables
if [ -z "${TARGET_PROJECT_ID:-}" ] || [ "$TARGET_PROJECT_ID" = "YOUR_TARGET_PROJECT_ID" ]; then
    echo "Error: TARGET_PROJECT_ID is not configured in env.sh." >&2
    exit 1
fi

LOCATION_VAL="${LOCATION:-global}"
ENDPOINT_PREFIX="${ENDPOINT_LOCATION:-global}"

echo "Removing licenses from ${#USERS[@]} user(s) in project $TARGET_PROJECT_ID..."

# Build JSON array manually to avoid external dependencies
USER_LICENSES_JSON=""
for user in "${USERS[@]}"; do
    if [ -n "$USER_LICENSES_JSON" ]; then
        USER_LICENSES_JSON="${USER_LICENSES_JSON},"
    fi
    USER_LICENSES_JSON="${USER_LICENSES_JSON}{\"userPrincipal\":\"${user}\"}"
done

PAYLOAD="{\"inlineSource\":{\"userLicenses\":[${USER_LICENSES_JSON}],\"updateMask\":{\"paths\":[\"userPrincipal\",\"licenseConfig\"]}},\"deleteUnassignedUserLicenses\":true}"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: ${TARGET_PROJECT_ID}" \
  -d "$PAYLOAD" \
  "https://${ENDPOINT_PREFIX}-discoveryengine.googleapis.com/v1/projects/${TARGET_PROJECT_ID}/locations/${LOCATION_VAL}/userStores/default_user_store:batchUpdateUserLicenses"
