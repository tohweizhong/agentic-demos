#!/usr/bin/env bash
# Writes terraform/terraform.tfvars from the answers that geap-configure collects.
# The region values (model, model location, malicious URI filter) come from the
# fixed table in this script, not from an agent. Prints a summary at the end.
#
# New file:
#   scripts/configure.sh --project PROJECT_ID --region REGION --prefix PREFIX --tier N \
#     [--allow-google-managed-members true|false] [--mode DRY_RUN|ENFORCE] [--dry-run]
# Move up one tier (keeps every other value):
#   scripts/configure.sh --move-up [--allow-google-managed-members true|false] [--dry-run]
# Show the current values only:
#   scripts/configure.sh --show
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

TFVARS="${TF_DIR}/terraform.tfvars"
MA_YAML="${ROOT}/policies/model_armor.yaml"

# Fixed region table. Only tested regions are listed.
region_model_id()       { case "$1" in us-central1) echo "gemini-3.8-flash";; asia-southeast1) echo "gemini-3.5-flash";; *) echo "";; esac; }
region_model_location() { case "$1" in us-central1) echo "global";; asia-southeast1) echo "asia-southeast1";; *) echo "";; esac; }
region_malicious_uri()  { case "$1" in us-central1) echo "ENABLED";; asia-southeast1) echo "DISABLED";; *) echo "";; esac; }

PROJECT=""; REGION=""; PREFIX=""; TIER=""; GMM=""; MODE=""; MOVE_UP="false"; SHOW="false"; DRY="false"; FORCE="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --tier) TIER="$2"; shift 2 ;;
    --allow-google-managed-members) GMM="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --move-up) MOVE_UP="true"; shift ;;
    --show) SHOW="true"; shift ;;
    --dry-run) DRY="true"; shift ;;
    --force) FORCE="true"; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done

val() { [[ -f "${TFVARS}" ]] || return 0; sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"\{0,1\}\([^\"#]*\)\"\{0,1\}.*/\1/p" "${TFVARS}" | head -1 | sed 's/[[:space:]]*$//' || true; }
current_tier() {
  local r e m i
  r="$(val enable_agent_registry)"; e="$(val enable_egress_gateway)"; m="$(val enable_model_armor)"; i="$(val enable_ingress_gateway)"
  if [[ "$i" == "true" ]]; then echo 5; elif [[ "$m" == "true" ]]; then echo 4; elif [[ "$e" == "true" ]]; then echo 3; elif [[ "$r" == "true" ]]; then echo 2; else echo 1; fi
}

if [[ "${SHOW}" == "true" || "${MOVE_UP}" == "true" ]]; then
  [[ -f "${TFVARS}" ]] || { echo "ERROR: ${TFVARS} does not exist. Run a new configuration first." >&2; exit 1; }
  PROJECT="${PROJECT:-$(val project_id)}"; REGION="${REGION:-$(val region)}"; PREFIX="${PREFIX:-$(val name_prefix)}"
  MODE="${MODE:-$(val iap_enforcement_mode)}"; GMM="${GMM:-$(val allow_google_managed_members)}"
  CUR="$(current_tier)"
  if [[ "${SHOW}" == "true" ]]; then TIER="${CUR}"; else
    [[ "${CUR}" -lt 5 ]] || { echo "Already at Tier 5. Nothing to move up." ; exit 0; }
    TIER=$((CUR + 1))
  fi
fi

[[ -n "${PROJECT}" && -n "${REGION}" && -n "${TIER}" ]] || { echo "ERROR: --project, --region, and --tier are required for a new configuration." >&2; exit 2; }
PREFIX="${PREFIX:-geap}"; MODE="${MODE:-DRY_RUN}"; GMM="${GMM:-false}"
[[ "${PREFIX}" =~ ^[a-z][a-z0-9-]{1,14}$ ]] || { echo "ERROR: prefix must match ^[a-z][a-z0-9-]{1,14}\$" >&2; exit 2; }
[[ "${TIER}" =~ ^[1-5]$ ]] || { echo "ERROR: tier must be 1 to 5" >&2; exit 2; }
[[ "${MODE}" == "DRY_RUN" || "${MODE}" == "ENFORCE" ]] || { echo "ERROR: mode must be DRY_RUN or ENFORCE" >&2; exit 2; }
MODEL_ID="$(region_model_id "${REGION}")"; MODEL_LOC="$(region_model_location "${REGION}")"; MURI="$(region_malicious_uri "${REGION}")"
[[ -n "${MODEL_ID}" ]] || { echo "ERROR: region ${REGION} is not tested. Tested regions: us-central1, asia-southeast1." >&2; exit 2; }

PROJECT_NUMBER="$(val project_number)"; ORG_ID="$(val organization_id)"
if [[ -z "${PROJECT_NUMBER}" || "${PROJECT_NUMBER}" == "PROJECT_NUMBER" || "$(val project_id)" != "${PROJECT}" ]]; then
  PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)' 2>/dev/null || true)"
fi
if [[ -z "${ORG_ID}" || "${ORG_ID}" == "ORG_ID" || "$(val project_id)" != "${PROJECT}" ]]; then
  ORG_ID="$(gcloud projects get-ancestors "${PROJECT}" --format='value(id,type)' 2>/dev/null | awk '$2=="organization"{print $1}')"
fi
[[ -n "${PROJECT_NUMBER}" && -n "${ORG_ID}" ]] || { echo "ERROR: cannot read the project number or the organization ID of ${PROJECT}. Check gcloud auth." >&2; exit 1; }

b() { [[ "$1" -ge "$2" ]] && echo true || echo false; }
REG="$(b "${TIER}" 2)"; EGR="$(b "${TIER}" 3)"; MAR="$(b "${TIER}" 4)"; ING="$(b "${TIER}" 5)"

CONTENT="# Written by scripts/configure.sh. terraform.tfvars is gitignored. Never commit real IDs.

project_id      = \"${PROJECT}\"
project_number  = \"${PROJECT_NUMBER}\"
organization_id = \"${ORG_ID}\"
region          = \"${REGION}\"
name_prefix     = \"${PREFIX}\"

# Governance tier ${TIER} (Tier 1 is always on). README: Governance tiers.
enable_agent_registry  = ${REG}
enable_egress_gateway  = ${EGR}
enable_model_armor     = ${MAR}
enable_ingress_gateway = ${ING}

# Start in DRY_RUN. Change to ENFORCE after the checks in DRY_RUN pass.
iap_enforcement_mode = \"${MODE}\"

# Approach 2 for domain restricted sharing (Tier 4 and Tier 5). See GUIDE Section 3.
allow_google_managed_members = ${GMM}

# Fixed values for ${REGION} (from the region table in scripts/configure.sh).
model_id       = \"${MODEL_ID}\"
model_location = \"${MODEL_LOC}\"
"

COMPUTED_CONFIG="CONFIGURE: project=${PROJECT} number=${PROJECT_NUMBER} org=${ORG_ID} region=${REGION} prefix=${PREFIX} tier=${TIER} registry=${REG} egress=${EGR} model_armor=${MAR} ingress=${ING} mode=${MODE} allow_google_managed_members=${GMM} model_id=${MODEL_ID} model_location=${MODEL_LOC} malicious_uri=${MURI}"
echo "${COMPUTED_CONFIG}"
if [[ "${SHOW}" == "true" ]]; then exit 0; fi

DRY_RUN_FILE="${TF_DIR}/.configure_dry_run"
if [[ "${DRY}" == "true" ]]; then
  echo "${COMPUTED_CONFIG}" > "${DRY_RUN_FILE}"
  echo "Dry run: no file written."
  printf '%s' "${CONTENT}"
  exit 0
fi

if [[ "${FORCE}" != "true" ]]; then
  if [[ ! -f "${DRY_RUN_FILE}" ]]; then
    echo "ERROR: Run scripts/configure.sh ... --dry-run first." >&2
    exit 2
  fi
  if [[ "$(cat "${DRY_RUN_FILE}")" != "${COMPUTED_CONFIG}" ]]; then
    echo "ERROR: The parameters changed since the last --dry-run. Run scripts/configure.sh ... --dry-run first." >&2
    exit 2
  fi
fi

if [[ ! -f "${TF_DIR}/build/agent_source.tar.gz" ]]; then
  "${ROOT}/scripts/package_agent.sh" >/dev/null
fi

printf '%s' "${CONTENT}" > "${TFVARS}"
sed -i "/^malicious_uri:/,/enforcement:/ s/enforcement: .*/enforcement: ${MURI}/" "${MA_YAML}"
echo "Wrote ${TFVARS} and set malicious_uri.enforcement: ${MURI} in policies/model_armor.yaml."
[[ "${MURI}" == "DISABLED" ]] && echo "Do not commit policies/model_armor.yaml with DISABLED." || true
