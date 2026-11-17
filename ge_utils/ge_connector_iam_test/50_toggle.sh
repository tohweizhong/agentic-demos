#!/usr/bin/env bash
# 50_toggle.sh on|off: turn the resource access control toggle on or off.
# The toggle applies to all apps and data stores in this location of the project.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

case "${1:-}" in
  on) value=true ;;
  off) value=false ;;
  *) echo "Usage: $0 on|off" >&2; exit 2 ;;
esac

mask="customer_provided_config.resource_access_control_config.data_store_access_control_enabled"
body="$(jq -n --argjson v "${value}" '{customerProvidedConfig: {resourceAccessControlConfig: {dataStoreAccessControlEnabled: $v}}}')"
api PATCH "${DE_API}/projects/${PROJECT_NUMBER}?updateMask=${mask}" "${body}" >/dev/null

echo "Toggle set to ${1} at $(date -u '+%Y-%m-%d %H:%M:%S UTC')."
api GET "${DE_API}/projects/${PROJECT_NUMBER}" | jq '{experienceState, customerProvidedConfig}'
