#!/usr/bin/env bash
# Shared settings for the scripts. The values come from the Terraform outputs.
set -euo pipefail

export TZ="${TZ:-Asia/Singapore}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/terraform"

now_sgt() {
  TZ="Asia/Singapore" date +"%Y-%m-%d %H:%M:%S SGT"
}

tf_output() {
  terraform -chdir="${TF_DIR}" output -raw "$1"
}

need() {
  for cmd in "$@"; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
      echo "ERROR: ${cmd} is not installed." >&2
      exit 1
    fi
  done
}
