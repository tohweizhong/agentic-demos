#!/bin/bash
# Step 1: List the workforce pools in an organization.
#
# Workforce pools are organization resources. If you do not give ORG_ID, the script
# lists the organizations that you can see. If there is only one, the script uses it.
#
# Required role: roles/iam.workforcePoolViewer (or higher) on the organization.
#
# Usage: ./1_list_pools.sh [ORG_ID] [LOCATION]
#   LOCATION  Optional. Default: global.
set -uo pipefail

ORG_ID="${1:-}"
LOCATION="${2:-global}"

if ! command -v gcloud >/dev/null 2>&1; then
    echo "Error: gcloud is not installed." >&2
    exit 1
fi

echo "Signed in as: $(gcloud config get-value account 2>/dev/null)"
echo

if [ -z "$ORG_ID" ]; then
    echo "=== Organizations you can see ==="
    ORGS="$(gcloud organizations list --format="value(name.basename())")" || exit 1
    gcloud organizations list --format="table(name.basename():label=ORG_ID,displayName)"
    echo
    COUNT="$(echo "$ORGS" | grep -c .)"
    if [ "$COUNT" -eq 0 ]; then
        echo "Error: you cannot see any organization. Sign in with an organization account." >&2
        exit 1
    elif [ "$COUNT" -gt 1 ]; then
        echo "More than one organization. Run again with an ORG_ID: $0 ORG_ID" >&2
        exit 1
    fi
    ORG_ID="$ORGS"
fi

echo "=== Workforce pools in organization $ORG_ID ($LOCATION) ==="
OUT="$(gcloud iam workforce-pools list --organization="$ORG_ID" --location="$LOCATION" \
    --format="table(name.basename():label=POOL_ID,displayName,state,sessionDuration)" 2>&1)"
STATUS=$?
echo "$OUT"
if [ "$STATUS" -ne 0 ]; then
    echo >&2
    echo "Error: cannot list workforce pools. You need roles/iam.workforcePoolViewer" >&2
    echo "(or higher) on organization $ORG_ID." >&2
    exit 1
fi
if [ -z "$OUT" ] || [[ "$OUT" == *"Listed 0 items"* ]]; then
    echo "The organization has no workforce pools in $LOCATION."
    exit 0
fi
echo
echo "Next step: ./2_list_providers.sh POOL_ID"
