---
name: geap-doctor
description: Inspect the live Google Cloud project for governance tier posture, IAP mode drift, and ungoverned (rogue) agents.
---

# Skill: geap-doctor

Run `scripts/doctor.sh` to verify the live governance posture of the target project and detect any ungoverned Reasoning Engines.

## Steps

1. Run `scripts/doctor.sh` from `geap_starter_pack/`.
2. Inspect the JSON output:
   - `tiers`: confirm that each of the 5 Governance Tiers reports `PASS` (or `OFF` when disabled in `terraform/terraform.tfvars`).
   - `iap_enforcement_mode`: confirm that `live_on_extension` matches `configured_in_tfvars` (`DRY_RUN` or `ENFORCE`).
   - `model_armor_gcp_sa_dep_roles`: confirm that `count` is `3` when Tier 4 (Model Armor) is enabled.
   - `agents.rogue_agents`: confirm that `rogue_count` is `0`. If any Reasoning Engine appears in `rogue_agents`, report its resource name and `missing_controls` (`AGENT_IDENTITY`, `agentToAnywhereConfig`, or `clientToAgentConfig`).
