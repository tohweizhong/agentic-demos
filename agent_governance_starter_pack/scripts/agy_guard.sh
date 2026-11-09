#!/usr/bin/env bash
# PreToolUse hook for the Antigravity CLI (agy). agy runs it before each
# run_command call, sends the tool call as JSON on stdin, and reads one JSON
# decision from stdout: {"decision":"deny|ask|allow|force_ask","reason":"..."}.
#
# Why a hook: agy reads permission rules only from user-level files
# (~/.gemini/antigravity-cli/settings.json and ~/.gemini/config/). A workspace
# cannot ship permission rules, but it can ship .agents/hooks.json. Source:
# third_party/jetski/cortex/customization/hooks/jsonhook/SPEC.md (checked 09 Nov 2026).
#
# The hook checks the full command line, so it also catches commands behind
# "cd ... &&", pipes, "bash -c", "eval", and "sudo".
set -uo pipefail

INPUT="$(cat)"
CMD="$(printf '%s' "${INPUT}" | jq -r '.toolCall.args.CommandLine // .toolCall.args.command // empty' 2>/dev/null)"

out() { jq -cn --arg d "$1" --arg r "$2" '{decision: $d, reason: $r}'; exit 0; }

[[ -z "${CMD}" ]] && out "ask" "agent governance starter pack guard: no command line found"

# 1. Never allowed.
if grep -Eq '\|[[:space:]]*([^|]*/)?cleanup\.sh' <<<"${CMD}"; then
  out "deny" "Do not pipe input into cleanup.sh. Run it with --confirm PROJECT_ID after the user approves (AGENTS.md)."
fi
if grep -Eq '(^|[;&|[:space:]])yes[[:space:]]*\|' <<<"${CMD}"; then
  out "deny" "Do not answer a prompt with 'yes |' (AGENTS.md)."
fi
if grep -Eq 'gcloud[[:space:]]+(organizations|org-policies[[:space:]]+(set-policy|delete|reset))' <<<"${CMD}"; then
  out "deny" "Organization and org policy changes are not allowed from the agent (AGENTS.md)."
fi
if grep -Eq '(bash|sh)[[:space:]]+-c|(^|[;&|[:space:]])eval[[:space:]]' <<<"${CMD}" && grep -Eq 'terraform|cleanup\.sh|gcloud' <<<"${CMD}"; then
  out "deny" "Do not wrap terraform, gcloud, or cleanup.sh in bash -c or eval. Run the command directly."
fi

# 2. Always ask a person, even if a CLI rule would allow it.
if grep -Eq 'terraform([[:space:]]+-chdir=[^[:space:]]+)?[[:space:]]+(apply|destroy|import|state[[:space:]]+(rm|mv|push))' <<<"${CMD}"; then
  out "force_ask" "Terraform changes cloud resources or state. A person must approve this command."
fi
if grep -Eq '(^|[/[:space:]])cleanup\.sh' <<<"${CMD}"; then
  out "force_ask" "cleanup.sh deletes resources. A person must approve this command."
fi
if grep -Eq 'gcloud[[:space:]].*[[:space:]](delete|remove-iam-policy-binding|add-iam-policy-binding|set-iam-policy|undelete)([[:space:]]|$)' <<<"${CMD}"; then
  out "force_ask" "This gcloud command changes resources or IAM. A person must approve it."
fi
if grep -Eq 'scripts/configure\.sh' <<<"${CMD}" && ! grep -Eq -- '--dry-run|--show' <<<"${CMD}"; then
  out "ask" "configure.sh writes terraform.tfvars. Approve after you check the CONFIGURE line from the --dry-run run."
fi

# 3. Read-only commands of the starter pack. A compound command is allowed only
#    if every part is on this list.
SAFE='^(scripts/(preflight|deploy_checks|teardown_plan|package_agent|ask_agent|read_audit_log|discover|check_tool_policy)\.sh([[:space:]].*)?|scripts/configure\.sh[[:space:]].*(--dry-run|--show).*|terraform(-chdir=[^[:space:]]+)?([[:space:]]+-chdir=[^[:space:]]+)?[[:space:]]+(plan|output|validate|fmt|test|state[[:space:]]+list|show)([[:space:]].*)?|gcloud[[:space:]].*[[:space:]](describe|list|get-iam-policy|get-ancestors|get-value)([[:space:]].*)?|git[[:space:]]+(status|log|diff|pull)([[:space:]].*)?|cat[[:space:]].*|grep[[:space:]].*|ls([[:space:]].*)?)$'
ALL_SAFE="true"
while IFS= read -r part; do
  part="$(sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s#^\./##' <<<"${part}")"
  [[ -z "${part}" ]] && continue
  grep -Eq "${SAFE}" <<<"${part}" || { ALL_SAFE="false"; break; }
done < <(sed -E 's/(&&|\|\||;|\|)/\n/g' <<<"${CMD}")
[[ "${ALL_SAFE}" == "true" ]] && out "allow" "Read-only command of the agent governance starter pack."

out "ask" "Not on the starter pack read-only list. A person must approve it."
