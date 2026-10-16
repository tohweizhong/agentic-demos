#!/bin/bash
# Script to distribute Gemini Enterprise licenses to a specific project.
#
# Usage: ./distribute_license.sh <license_count> [target_project_number] [location] [license_config_id]
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ ! -f "$DIR/env.sh" ]; then
    echo "Error: env.sh not found." >&2
    echo "Please copy env.sh.template to env.sh and configure your variables." >&2
    exit 1
fi

source "$DIR/env.sh"

# Read inputs, with fallbacks from env.sh
LICENSE_COUNT="${1:-}"
TARGET_PROJECT_NUMBER="${2:-${TARGET_PROJECT_NUMBER:-}}"
LOCATION_VAL="${3:-${LOCATION:-}}"
LICENSE_CONFIG_ID="${4:-}"

if [ -z "$LICENSE_COUNT" ]; then
    echo "Usage: $0 <license_count> [target_project_number] [location] [license_config_id]" >&2
    echo "Example: $0 5" >&2
    exit 1
fi

# Validation of required variables
if [ -z "$TARGET_PROJECT_NUMBER" ] || [ "$TARGET_PROJECT_NUMBER" = "YOUR_TARGET_PROJECT_NUMBER" ]; then
    echo "Error: Target project number is not configured in env.sh or passed as an argument." >&2
    exit 1
fi

if [ -z "$LOCATION_VAL" ] || [ "$LOCATION_VAL" = "YOUR_LOCATION" ]; then
    echo "Error: Location is not configured in env.sh or passed as an argument." >&2
    exit 1
fi

if [ -z "${BILLING_ACCOUNT_ID:-}" ] || [ "$BILLING_ACCOUNT_ID" = "YOUR_BILLING_ACCOUNT_ID" ]; then
    echo "Error: BILLING_ACCOUNT_ID is not configured in env.sh" >&2
    exit 1
fi

if [ -z "${BILLING_ACCOUNT_LICENSE_CONFIG_ID:-}" ] || [ "$BILLING_ACCOUNT_LICENSE_CONFIG_ID" = "YOUR_BILLING_ACCOUNT_LICENSE_CONFIG_ID" ]; then
    echo "Error: BILLING_ACCOUNT_LICENSE_CONFIG_ID is not configured in env.sh" >&2
    exit 1
fi

if [ -z "${USER_PROJECT_NUMBER:-}" ] || [ "$USER_PROJECT_NUMBER" = "YOUR_USER_PROJECT_NUMBER" ]; then
    echo "Error: USER_PROJECT_NUMBER is not configured in env.sh" >&2
    exit 1
fi

# Endpoint prefix mapping
ENDPOINT_PREFIX="${ENDPOINT_LOCATION:-global}"

echo "Distributing $LICENSE_COUNT licenses to project $TARGET_PROJECT_NUMBER in location $LOCATION_VAL..."

# Construct request payload
PAYLOAD=$(cat <<EOF
{
  "projectNumber": "$TARGET_PROJECT_NUMBER",
  "location": "$LOCATION_VAL",
  "licenseCount": $LICENSE_COUNT
EOF
)

if [ -n "$LICENSE_CONFIG_ID" ]; then
    PAYLOAD="$PAYLOAD, \"licenseConfigId\": \"$LICENSE_CONFIG_ID\""
fi

PAYLOAD="$PAYLOAD }"

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $USER_PROJECT_NUMBER" \
  -d "$PAYLOAD" \
  "https://${ENDPOINT_PREFIX}-discoveryengine.googleapis.com/v1alpha/billingAccounts/${BILLING_ACCOUNT_ID}/billingAccountLicenseConfigs/${BILLING_ACCOUNT_LICENSE_CONFIG_ID}:distributeLicenseConfig"
