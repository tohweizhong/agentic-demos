---
name: geap-preflight
description: Run the read-only preflight scan on the target project before any agent governance starter pack deployment.
---

# Skill: geap-preflight

Run the read-only preflight scan and check that the target project is ready.

## Steps

1. Run the preflight script from `agent_governance_starter_pack/`:
   ```bash
   scripts/preflight.sh
   ```
2. Parse the JSON output and report:
   - `status` (`GO` or `NO_GO`)
   - `blockers` (if any)
   - `warnings` (if any)
   - `existing_resources` summary
3. If `status` is `NO_GO`, stop and list each blocker from the JSON output. Do not run `terraform apply`.
