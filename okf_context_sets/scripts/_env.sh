# Shared settings for the scripts in this folder. Source it. Do not run it.
# It reads .env, exports the gcloud settings that kcmd needs, and puts the
# local kcmd install on PATH.

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export DEMO_DIR

if [[ ! -f "${DEMO_DIR}/.env" ]]; then
  echo "ERROR: ${DEMO_DIR}/.env does not exist. Run: cp .env.example .env, then edit it." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "${DEMO_DIR}/.env"
set +a

: "${PROJECT_ID:?Set PROJECT_ID in .env}"
: "${REGION:?Set REGION in .env}"
: "${ENTRY_GROUP:?Set ENTRY_GROUP in .env}"
: "${BQ_DATASET:=okf_demo}"
: "${BQ_LOCATION:=US}"
: "${KCMD_VERSION:=0.2.5}"

if [[ "${PROJECT_ID}" == "your-project-id" ]]; then
  echo "ERROR: Replace the PROJECT_ID placeholder in .env." >&2
  exit 1
fi

# kcmd reads the project and the region from the gcloud configuration.
# If compute/region is not set, kcmd fails with
# "Unable to retrieve project, location, or token". These variables fix it
# without a change to your gcloud configuration.
export CLOUDSDK_CORE_PROJECT="${PROJECT_ID}"
export CLOUDSDK_COMPUTE_REGION="${REGION}"

# Load nvm if Node is installed with nvm and node or npm is not on PATH.
if { ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; } && [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]]; then
  # shellcheck disable=SC1091
  source "${NVM_DIR:-$HOME/.nvm}/nvm.sh" >/dev/null
fi

export PATH="${DEMO_DIR}/.tools/node_modules/.bin:${PATH}"

ENTRY_GROUP_ID="${PROJECT_ID}.${REGION}.${ENTRY_GROUP}"
ENTRY_GROUP_NAME="projects/${PROJECT_ID}/locations/${REGION}/entryGroups/${ENTRY_GROUP}"
export ENTRY_GROUP_ID ENTRY_GROUP_NAME

require_kcmd() {
  if ! command -v kcmd >/dev/null 2>&1; then
    echo "ERROR: kcmd is not installed. Run scripts/setup.sh first." >&2
    exit 1
  fi
}
