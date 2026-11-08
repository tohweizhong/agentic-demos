#!/usr/bin/env bash
# Installs the GEAP starter pack CLI skills into the user skills directory
# (~/.gemini/config/skills/) and optionally generates .claude/commands/geap-*.md
# when --claude is passed.
#
# Usage:
#   scripts/install_harness.sh [--dest DIR] [--claude]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

DEST_DIR="${HOME}/.gemini/config/skills"
INSTALL_CLAUDE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)
      DEST_DIR="$2"
      shift 2
      ;;
    --claude)
      INSTALL_CLAUDE="true"
      shift
      ;;
    *)
      echo "Usage: $0 [--dest DIR] [--claude]" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${DEST_DIR}"
for skill_dir in "${ROOT}/.agents/skills"/geap-*; do
  if [[ -d "${skill_dir}" ]]; then
    skill_name="$(basename "${skill_dir}")"
    rm -rf "${DEST_DIR}/${skill_name}"
    cp -r "${skill_dir}" "${DEST_DIR}/${skill_name}"
    echo "Installed ${skill_name} -> ${DEST_DIR}/${skill_name}/SKILL.md"
  fi
done

if [[ "${INSTALL_CLAUDE}" == "true" ]]; then
  CLAUDE_DIR="${ROOT}/.claude/commands"
  mkdir -p "${CLAUDE_DIR}"
  for skill_dir in "${ROOT}/.agents/skills"/geap-*; do
    if [[ -f "${skill_dir}/SKILL.md" ]]; then
      skill_name="$(basename "${skill_dir}")"
      cp "${skill_dir}/SKILL.md" "${CLAUDE_DIR}/${skill_name}.md"
      echo "Generated Claude slash command -> ${CLAUDE_DIR}/${skill_name}.md"
    fi
  done
fi
