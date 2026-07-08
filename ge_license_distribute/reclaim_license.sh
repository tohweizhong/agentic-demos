#!/bin/bash
# Script to reclaim/retract licenses from a project back to the billing account pool.
# Note: You can only perform this action once per day.
#
# Usage: ./reclaim_license.sh <license_count> <license_config_id> [target_project_number] [location]
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ ! -f "$DIR/env.sh" ]; then
    echo "Error: env.sh not found." >&2
    echo "Please copy env.sh.template to env.sh and configure your variables." >&2
    exit 1
fi

source "$DIR/env.sh"

# Read inputs
LICENSE_COUNT="${1:-}"
LICENSE_CONFIG_ID="${2:-}"
TARGET_PROJECT_NUMBER="${3:-${TARGET_PROJECT_NUMBER:-}}"
LOCATION_VAL="${4:-${LOCATION:-}}"

if [ -z "$LICENSE_COUNT" ] || [ -z "$LICENSE_CONFIG_ID" ]; then
    echo "Usage: $0 <license_count> <license_config_id> [target_project_number] [location]" >&2
    echo "Example: $0 2 license-config-uuid" >&2
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

ENDPOINT_PREFIX="${ENDPOINT_LOCATION:-global}"
LICENSE_CONFIG_PATH="projects/${TARGET_PROJECT_NUMBER}/locations/${LOCATION_VAL}/licenseConfigs/${LICENSE_CONFIG_ID}"

echo "Reclaiming $LICENSE_COUNT licenses from $LICENSE_CONFIG_PATH..."

curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $USER_PROJECT_NUMBER" \
  -d '{
    "licenseConfig": "'"$LICENSE_CONFIG_PATH"'",
    "licenseCount": '"$LICENSE_COUNT"'
  }' \
  "https://${ENDPOINT_PREFIX}-discoveryengine.googleapis.com/v1alpha/billingAccounts/${BILLING_ACCOUNT_ID}/billingAccountLicenseConfigs/${BILLING_ACCOUNT_LICENSE_CONFIG_ID}:retractLicenseConfig"
