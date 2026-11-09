---
name: geap-discover
description: Read-only scan of an existing project. Lists all agents, MCP servers, gateways, registry entries, and access policies, shows which tier controls cover each one, and lists the lateral steps to bring existing resources to each tier. Use before geap-configure in a project that already has agents.
---

# Skill: geap-discover

Run the read-only discovery for the lateral path (resources that the starter pack did not create).

## Steps

1. Read `project_id`, `region`, and `name_prefix` from `terraform/terraform.tfvars`. If the file does
   not exist, ask the user for the project ID and the region.
2. Run the scan and show the Markdown report to the user:
   ```bash
   scripts/discover.sh --project PROJECT_ID --region REGION --prefix PREFIX --markdown
   ```
3. If the status is `ERROR`, stop and show the error. If it is `PARTIAL`, list the failed calls and say
   that those resources are not in the report. Never present a failed call as "none found".
4. Explain the lateral steps for the tier that the user wants. The tools for the lateral steps are
   planned, not built (backlog item 30). Do not change any resource from this skill.
