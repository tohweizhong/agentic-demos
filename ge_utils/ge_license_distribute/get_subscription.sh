#!/bin/bash
# Script to get subscription details including license configurations and distribution status.
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ ! -f "$DIR/env.sh" ]; then
    echo "Error: env.sh not found." >&2
    echo "Please copy env.sh.template to env.sh and configure your variables." >&2
    exit 1
fi

source "$DIR/env.sh"

# Validate required variables
if [ -z "${BILLING_ACCOUNT_ID:-}" ] || [ "$BILLING_ACCOUNT_ID" = "YOUR_BILLING_ACCOUNT_ID" ]; then
    echo "Error: BILLING_ACCOUNT_ID is not configured in env.sh" >&2
    exit 1
fi

if [ -z "${USER_PROJECT_NUMBER:-}" ] || [ "$USER_PROJECT_NUMBER" = "YOUR_USER_PROJECT_NUMBER" ]; then
    echo "Error: USER_PROJECT_NUMBER is not configured in env.sh" >&2
    exit 1
fi

echo "Retrieving subscription details for Billing Account: $BILLING_ACCOUNT_ID..."

curl -X GET \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $USER_PROJECT_NUMBER" \
  "https://discoveryengine.googleapis.com/v1alpha/billingAccounts/${BILLING_ACCOUNT_ID}/billingAccountLicenseConfigs"
