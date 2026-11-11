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
{
  "permissions": {
    "allow": [
      "command(scripts/preflight.sh)", "command(scripts/preflight.sh *)",
      "command(scripts/deploy_checks.sh)", "command(scripts/deploy_checks.sh *)",
      "command(scripts/discover.sh)", "command(scripts/discover.sh *)",
      "command(scripts/doctor.sh)", "command(scripts/doctor.sh *)",
      "command(scripts/adoption_plan.sh)", "command(scripts/adoption_plan.sh *)",
      "command(scripts/bind_existing_agent.sh)", "command(scripts/bind_existing_agent.sh *)",
      "command(scripts/teardown_plan.sh)", "command(scripts/teardown_plan.sh *)",
      "command(scripts/package_agent.sh)", "command(scripts/package_agent.sh *)",
      "command(scripts/ask_agent.sh)", "command(scripts/ask_agent.sh *)",
      "command(scripts/read_audit_log.sh)", "command(scripts/read_audit_log.sh *)",
      "command(scripts/read_session_trace.sh)", "command(scripts/read_session_trace.sh *)",
      "command(scripts/check_promotion.sh)", "command(scripts/check_promotion.sh *)",
      "command(scripts/check_tool_policy.sh)", "command(scripts/check_tool_policy.sh *)",
      "command(scripts/configure.sh)", "command(scripts/configure.sh *)",
      "command(scripts/onboard_agent.sh)", "command(scripts/onboard_agent.sh *)",
      "command(terraform plan)", "command(terraform plan *)",
      "command(terraform output)", "command(terraform output *)",
      "command(gcloud)", "command(gcloud *)",
      "command(git status)", "command(git status *)",
      "command(git diff)", "command(git diff *)",
      "command(cat)", "command(cat *)",
      "command(grep)", "command(grep *)",
      "command(ls)", "command(ls *)",
      "command(jq)", "command(jq *)"
    ],
    "deny": [
      "command(terraform destroy)", "command(terraform destroy *)"
    ],
    "ask": [
      "command(terraform apply)", "command(terraform apply *)",
      "command(scripts/cleanup.sh)", "command(scripts/cleanup.sh *)"
    ]
  }
}
JSON
fi

AGY_SETTINGS="${HOME}/.gemini/antigravity-cli/settings.json"
if [[ -d "$(dirname "${AGY_SETTINGS}")" ]]; then
  if [[ -f "${AGY_SETTINGS}" ]]; then
    # Merge permissions into existing settings.json
    jq -s '.[0] * .[1]' "${AGY_SETTINGS}" "${ROOT}/.claude/settings.json" > "${AGY_SETTINGS}.tmp"
    mv "${AGY_SETTINGS}.tmp" "${AGY_SETTINGS}"
  else
    # Create new settings.json with toolPermission mode
    jq '. + {"toolPermission": "request-review", "allowNonWorkspaceAccess": false}' "${ROOT}/.claude/settings.json" > "${AGY_SETTINGS}"
  fi
fi


if [[ ! -e "${ROOT}/.claude/skills" ]]; then
  ln -s "../.agents/skills" "${ROOT}/.claude/skills"
fi

echo "Installed the harness directories and files."
