import sys

with open('GUIDE.md', 'r') as f:
    content = f.read()

# Replace skill table
old_table = """| `geap-discover` | `.agents/skills/geap-discover/SKILL.md` | Read-only scan of an existing project: agents, MCP servers, gateways, access policies, and the lateral steps for each tier |
| `geap-configure` | `.agents/skills/geap-configure/SKILL.md` | Asks for the project, region, name prefix, governance tier, domain restricted sharing approach, and IAP mode, then writes `terraform/terraform.tfvars` |
| `geap-preflight` | `.agents/skills/geap-preflight/SKILL.md` | Runs `scripts/preflight.sh` and checks the JSON readiness report (`GO` or `NO_GO`) |
| `geap-deploy` | `.agents/skills/geap-deploy/SKILL.md` | Packages the agent source, runs offline unit tests, runs `terraform plan`, and pauses for human approval before `terraform apply` |
| `geap-verify` | `.agents/skills/geap-verify/SKILL.md` | Verifies the deployed agent, Model Armor content screening, IAP tool authorization, and Cloud Logging entries |
| `geap-reset` | `.agents/skills/geap-reset/SKILL.md` | Returns `iap_enforcement_mode` to `DRY_RUN` and resets the sample MCP server state |
| `geap-teardown` | `.agents/skills/geap-teardown/SKILL.md` | Destroys all Terraform resources and sweeps any out-of-state GEAP resources in the project (requires human confirmation) |"""

new_table = """| `geap-discover` | `.agents/skills/geap-discover/SKILL.md` | Read-only scan of an existing project: agents, MCP servers, gateways, access policies, and the lateral steps for each tier |
| `geap-adopt` | `.agents/skills/geap-adopt/SKILL.md` | Interactive lateral adoption of an existing project |
| `geap-configure` | `.agents/skills/geap-configure/SKILL.md` | Asks for the project, region, name prefix, governance tier, domain restricted sharing approach, and IAP mode, then writes `terraform/terraform.tfvars` |
| `geap-preflight` | `.agents/skills/geap-preflight/SKILL.md` | Runs `scripts/preflight.sh` and checks the JSON readiness report (`GO` or `NO_GO`) |
| `geap-deploy` | `.agents/skills/geap-deploy/SKILL.md` | Packages the agent source, runs offline unit tests, runs `terraform plan`, and pauses for human approval before `terraform apply` |
| `geap-verify` | `.agents/skills/geap-verify/SKILL.md` | Verifies the deployed agent, Model Armor content screening, IAP tool authorization, and Cloud Logging entries |
| `geap-doctor` | `.agents/skills/geap-doctor/SKILL.md` | Runs the posture check to find stale IAM grants and missing gateway bindings |
| `geap-onboard-agent` | `.agents/skills/geap-onboard-agent/SKILL.md` | Generates terraform code and IAM grants for onboarding a new agent |
| `geap-reset` | `.agents/skills/geap-reset/SKILL.md` | Returns `iap_enforcement_mode` to `DRY_RUN` and resets the sample MCP server state |
| `geap-teardown` | `.agents/skills/geap-teardown/SKILL.md` | Destroys all Terraform resources and sweeps any out-of-state GEAP resources in the project (requires human confirmation) |"""

if old_table in content:
    content = content.replace(old_table, new_table)

# Replace "the five" with "the ten"
content = content.replace("the five skills", "the ten skills")
content = content.replace("the five `geap-*` skills", "the ten `geap-*` skills")

# Replace settings.json allow list
old_allow = '"allow": ["command(scripts/preflight.sh)", "command(scripts/deploy_checks.sh)"]'
new_allow = '"allow": ["command(scripts/preflight.sh)", "command(scripts/deploy_checks.sh)", "command(scripts/discover.sh)", "command(scripts/doctor.sh)", "command(scripts/adoption_plan.sh)", "command(scripts/bind_existing_agent.sh)", "command(scripts/teardown_plan.sh)", "command(scripts/package_agent.sh)", "command(scripts/ask_agent.sh)", "command(scripts/read_audit_log.sh)", "command(scripts/check_promotion.sh)", "command(scripts/check_tool_policy.sh)"]'
content = content.replace(old_allow, new_allow)

with open('GUIDE.md', 'w') as f:
    f.write(content)
