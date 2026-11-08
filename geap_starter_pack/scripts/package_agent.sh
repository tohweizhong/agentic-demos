#!/usr/bin/env bash
# Packages the reference agent source for Agent Runtime.
# Terraform reads the archive from terraform/build/agent_source.tar.gz.
# The archive is the same for the same source, so Terraform sees a change only
# when the source changes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${ROOT}/agent-template"
OUT_DIR="${ROOT}/terraform/build"
OUT="${OUT_DIR}/agent_source.tar.gz"

FILES=(Dockerfile requirements.txt work_items/__init__.py work_items/agent.py work_items/tools.py)

for f in "${FILES[@]}"; do
  if [[ ! -f "${SRC}/${f}" ]]; then
    echo "ERROR: ${SRC}/${f} is missing." >&2
    exit 1
  fi
done

mkdir -p "${OUT_DIR}"
tar --sort=name --mtime='2020-01-01 00:00:00 UTC' --owner=0 --group=0 --numeric-owner \
  -C "${SRC}" -cf - "${FILES[@]}" | gzip -n -9 > "${OUT}"

echo "Wrote ${OUT}"
tar -tzf "${OUT}"
