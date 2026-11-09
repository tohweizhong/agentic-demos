#!/usr/bin/env bash
# Installs or checks the starter pack skills and hooks in .agents/ and .claude/.
#
# Usage:
#   scripts/install_harness.sh [--check]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

CHECK="false"
if [[ "${1:-}" == "--check" ]]; then
  CHECK="true"
fi

if [[ "${CHECK}" == "true" ]]; then
  MISSING=0
  [[ -f "${ROOT}/.agents/hooks.json" ]] || { echo "Missing .agents/hooks.json"; MISSING=1; }
  [[ -f "${ROOT}/.claude/settings.json" ]] || { echo "Missing .claude/settings.json"; MISSING=1; }
  [[ -d "${ROOT}/.agents/skills" ]] || { echo "Missing .agents/skills"; MISSING=1; }
  [[ -L "${ROOT}/.claude/skills" ]] || { echo "Missing .claude/skills symlink"; MISSING=1; }
  if [[ "${MISSING}" -eq 1 ]]; then
    exit 1
  fi
  echo "Harness is fully installed."
  exit 0
fi

mkdir -p "${ROOT}/.agents/skills" "${ROOT}/.claude"
if [[ ! -f "${ROOT}/.agents/hooks.json" ]]; then
  cat << 'JSON' > "${ROOT}/.agents/hooks.json"
{
  "PreToolUse": {
    "command": ["bash", "scripts/agy_guard.sh"]
  }
}
JSON
fi

if [[ ! -f "${ROOT}/.claude/settings.json" ]]; then
  cat << 'JSON' > "${ROOT}/.claude/settings.json"
{}
JSON
fi

if [[ ! -e "${ROOT}/.claude/skills" ]]; then
  ln -s "../.agents/skills" "${ROOT}/.claude/skills"
fi

echo "Installed the harness directories and files."
