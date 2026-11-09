import sys

with open('scripts/agy_guard.sh', 'r') as f:
    content = f.read()

old_regex = """SAFE='^(scripts/(preflight|deploy_checks|teardown_plan|package_agent|ask_agent|read_audit_log|discover|check_tool_policy|check_promotion|doctor|adoption_plan)\\.sh([[:space:]].*)?|scripts/(quarantine_agent|init_remote_state)\\.sh([[:space:]].*)?|scripts/(onboard_agent|bind_existing_agent)\\.sh[[:space:]].*--dry-run.*|scripts/configure\\.sh[[:space:]].*(--dry-run|--show).*|terraform(-chdir=[^[:space:]]+)?([[:space:]]+-chdir=[^[:space:]]+)?[[:space:]]+(plan|output|validate|fmt|test|state[[:space:]]+list|show)([[:space:]].*)?|gcloud[[:space:]].*[[:space:]](describe|list|get-iam-policy|get-ancestors|get-value)([[:space:]].*)?|git[[:space:]]+(status|log|diff|pull)([[:space:]].*)?|cat[[:space:]].*|grep[[:space:]].*|ls([[:space:]].*)?)$'"""

new_regex = """SAFE='^(cd([[:space:]].*)?|scripts/(preflight|deploy_checks|teardown_plan|package_agent|ask_agent|read_audit_log|discover|check_tool_policy|check_promotion|doctor|adoption_plan)\\.sh([[:space:]].*)?|scripts/(quarantine_agent|init_remote_state)\\.sh([[:space:]].*)?|scripts/(onboard_agent|bind_existing_agent)\\.sh[[:space:]].*--dry-run.*|scripts/configure\\.sh[[:space:]].*(--dry-run|--show).*|terraform(-chdir=[^[:space:]]+)?([[:space:]]+-chdir=[^[:space:]]+)?[[:space:]]+(plan|output|validate|fmt|test|state[[:space:]]+list|show)([[:space:]].*)?|gcloud[[:space:]].*[[:space:]](describe|list|get-iam-policy|get-ancestors|get-value)([[:space:]].*)?|git[[:space:]]+(status|log|diff|pull)([[:space:]].*)?|cat[[:space:]].*|grep[[:space:]].*|ls([[:space:]].*)?)$'"""

if old_regex in content:
    content = content.replace(old_regex, new_regex)
else:
    print("Failed to replace regex in agy_guard.sh")
    sys.exit(1)

with open('scripts/agy_guard.sh', 'w') as f:
    f.write(content)
