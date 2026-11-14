#!/usr/bin/env bash
# Pull the context set back into pulled/bundle/ with kcmd.
# The first read after a new push can fail with status 403 for about one
# minute, while IAM permissions propagate. Both `kcmd init` and `kcmd pull`
# read the context set, so this script tries both again.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
require_kcmd

OUT="${DEMO_DIR}/pulled"
mkdir -p "${OUT}"
cd "${OUT}"

attempts=6
for (( i = 1; i <= attempts; i++ )); do
  echo "== Attempt ${i} of ${attempts}"
  if [[ -f catalog.yaml ]] || kcmd init --entry-group "${ENTRY_GROUP_ID}" --format okf; then
    if kcmd pull; then
      echo "Pull is complete. Files:"
      ls -1 bundle/
      echo "Compare with the source: diff -ru bundle pulled/bundle"
      exit 0
    fi
  fi
  if (( i < attempts )); then
    echo "Read failed. Wait 20 seconds for IAM propagation, then try again."
    sleep 20
  fi
done

echo "ERROR: kcmd pull failed ${attempts} times." >&2
exit 1
