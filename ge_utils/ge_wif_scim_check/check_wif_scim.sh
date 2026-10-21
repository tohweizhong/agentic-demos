#!/bin/bash
# Checks a Workforce Identity Federation (WIF) pool for two facts:
#   1. Does each provider in the pool have a SCIM tenant?
#   2. What is the attribute mapping of each provider, and does google.subject keep
#      the case from the identity provider?
#
# SCIM tenants are child resources of a provider, not of a pool. There is no
# "gcloud iam workforce-pools tenants" command. The correct command is
# "gcloud iam workforce-pools providers scim-tenants list".
#
# Required role: a role on the ORGANIZATION that can read workforce pool providers and
# list their SCIM tenants, for example roles/iam.workforcePoolAdmin.
#
# Usage: ./check_wif_scim.sh <WORKFORCE_POOL_ID> [PROVIDER_ID] [LOCATION]
#   PROVIDER_ID  Optional. If you do not set it, the script checks every provider in the pool.
#   LOCATION     Optional. Default: global.
set -uo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <WORKFORCE_POOL_ID> [PROVIDER_ID] [LOCATION]" >&2
    exit 1
fi
POOL="$1"
PROVIDER_ARG="${2:-}"
LOCATION="${3:-global}"

if ! command -v gcloud >/dev/null 2>&1; then
    echo "Error: gcloud is not installed." >&2
    exit 1
fi

# Stop with a clear message when a gcloud command fails.
fail() {
    echo >&2
    echo "Error: $1" >&2
    echo "Check that you are signed in with 'gcloud auth login' as a user with" >&2
    echo "roles/iam.workforcePoolAdmin (or equivalent) on the organization." >&2
    exit 1
}

echo "=== Workforce pool ==="
gcloud iam workforce-pools describe "$POOL" --location="$LOCATION" \
    --format="yaml(name,parent,state)" || fail "cannot read workforce pool '$POOL'."
echo

if [ -n "$PROVIDER_ARG" ]; then
    PROVIDERS="$PROVIDER_ARG"
else
    PROVIDERS="$(gcloud iam workforce-pools providers list \
        --workforce-pool="$POOL" --location="$LOCATION" \
        --format="value(name.basename())")" || fail "cannot list providers in pool '$POOL'."
    if [ -z "$PROVIDERS" ]; then
        echo "The pool has no providers."
        exit 0
    fi
fi

for PROVIDER in $PROVIDERS; do
    echo "=== Provider: $PROVIDER ==="
    PROVIDER_YAML="$(gcloud iam workforce-pools providers describe "$PROVIDER" \
        --workforce-pool="$POOL" --location="$LOCATION" \
        --format="yaml(name,state,attributeMapping,scimUsage)")" \
        || fail "cannot read provider '$PROVIDER'."
    echo "$PROVIDER_YAML"
    echo

    echo "--- SCIM tenants of $PROVIDER (deleted tenants included) ---"
    TENANTS_YAML="$(gcloud iam workforce-pools providers scim-tenants list \
        --provider="$PROVIDER" --workforce-pool="$POOL" --location="$LOCATION" \
        --show-deleted --format="yaml(name,state,claimMapping)")" \
        || fail "cannot list SCIM tenants of provider '$PROVIDER'."
    if [ -z "$TENANTS_YAML" ]; then
        echo "(none)"
    else
        echo "$TENANTS_YAML"
    fi
    echo

    # Summary for this provider.
    SUBJECT_MAP="$(echo "$PROVIDER_YAML" | grep -E '^\s+google\.subject:' | sed 's/^[^:]*: *//')"
    ACTIVE_TENANTS="$(echo "$TENANTS_YAML" | grep -c -E '^state: ACTIVE')"
    TENANT_SUBJECT_MAP="$(echo "$TENANTS_YAML" | grep -E '^\s+google\.subject:' | head -1 | sed 's/^[^:]*: *//')"

    echo "--- Summary for $PROVIDER ---"
    if [ "$ACTIVE_TENANTS" -gt 0 ]; then
        echo "SCIM tenant:            YES ($ACTIVE_TENANTS active)"
    else
        echo "SCIM tenant:            NO"
    fi
    echo "Provider google.subject: ${SUBJECT_MAP:-(not set)}"
    if [[ "$SUBJECT_MAP" == *lowerAscii* ]]; then
        echo "Subject case:           lowercase (lowerAscii is used)"
    else
        echo "Subject case:           kept from the identity provider (case-sensitive)"
    fi
    if [ "$ACTIVE_TENANTS" -gt 0 ]; then
        echo "SCIM google.subject:    ${TENANT_SUBJECT_MAP:-(not set)}"
        P_LOWER=no; T_LOWER=no
        [[ "$SUBJECT_MAP" == *lowerAscii* ]] && P_LOWER=yes
        [[ "$TENANT_SUBJECT_MAP" == *lowerAscii* ]] && T_LOWER=yes
        if [ "$P_LOWER" != "$T_LOWER" ]; then
            echo "WARNING: only one of the two google.subject mappings uses lowerAscii()."
            echo "         The SCIM subject and the sign-in subject can then differ in case."
        fi
    fi
    echo
done
