# Spec: Track 3 — Skill Registry skill

Decision: the user delegated all choices on 13 Nov 2026 11:20 SGT ("see to it that this managed api demo is fully built out"). The user was away, so the agent approved the spec and the plan.

## Overview

Publish one skill to Skill Registry and attach it to a second agent with a `skill_registry`
source. Show that the agent follows the skill.

## Functional requirements

### FR1. Publish the skill (`scripts/07_skill_registry.py`)
- Zip `assets/registry-skills/sales-chart-style/` and create the skill `sales-chart-style` in
  `us-central1` (Skill Registry is regional). Wait for the long-running operation.
- If the skill exists, update it with the current files.
- Note in the README: a skill ID stays reserved after a delete.

### FR2. Agent with the registry skill
- Create `demo-skill-analyst` with two sources: the demo bucket (`gcs`) and the registry skill
  (`skill_registry`), mounted under `.agent/skills`.
- Send one task that asks for a revenue chart by region.
- Check the result: the chart file name follows the skill rule
  (`chart_<metric>_by_<category>.png`) and is in the bucket.

### FR3. Cleanup
- `scripts/99_cleanup.py --skills` deletes the registry skill after a confirmation.

### FR4. Documents
- README, notebook, and `scripts/rest_reference.sh` (a `skill` step).

## Acceptance criteria
1. The skill is `ACTIVE` in Skill Registry.
2. The agent writes a chart whose file name follows the skill.
3. Unit tests pass. `ruff check` is clean.

## Out of scope
- Skill versions other than the default. Built-in `gcp-` skills.
