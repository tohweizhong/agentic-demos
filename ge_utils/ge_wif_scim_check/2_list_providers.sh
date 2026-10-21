#!/bin/bash
# Step 2: List the providers in a workforce pool.
#
# A SCIM tenant and the attribute mapping belong to a provider, not to the pool.
# Use this list to find the PROVIDER_ID for step 3.
#
# Required role: roles/iam.workforcePoolViewer (or higher) on the organization.
#
# Usage: ./2_list_providers.sh POOL_ID [LOCATION]
#   LOCATION  Optional. Default: global.
set -uo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 POOL_ID [LOCATION]" >&2
    echo "Run ./1_list_pools.sh to find the POOL_ID." >&2
    exit 1
fi
POOL="$1"
LOCATION="${2:-global}"

if ! command -v gcloud >/dev/null 2>&1; then
    echo "Error: gcloud is not installed." >&2
    exit 1
fi

echo "=== Providers in workforce pool $POOL ($LOCATION) ==="
OUT="$(gcloud iam workforce-pools providers list --workforce-pool="$POOL" --location="$LOCATION" \
    --format="table(name.basename():label=PROVIDER_ID,displayName,state,disabled,oidc.issuerUri:label=OIDC_ISSUER,saml.yesno(yes=SAML,no=-):label=SAML)" 2>&1)"
STATUS=$?
echo "$OUT"
if [ "$STATUS" -ne 0 ]; then
    echo >&2
    if [[ "$OUT" == *NOT_FOUND* ]]; then
        echo "Error: workforce pool '$POOL' does not exist in $LOCATION." >&2
        echo "Run ./1_list_pools.sh to find the correct POOL_ID." >&2
    else
        echo "Error: cannot list providers. You need roles/iam.workforcePoolViewer" >&2
        echo "(or higher) on the organization." >&2
    fi
    exit 1
fi
if [ -z "$OUT" ] || [[ "$OUT" == *"Listed 0 items"* ]]; then
    echo "The pool has no providers."
    exit 0
fi
echo
echo "Next step: ./3_check_wif_scim.sh $POOL [PROVIDER_ID]"
