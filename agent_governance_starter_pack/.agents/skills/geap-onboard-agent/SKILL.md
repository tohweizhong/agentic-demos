---
name: geap-onboard-agent
description: Generates terraform code and IAM grants for onboarding a new agent.
---
# GEAP Onboard Agent

This skill runs `scripts/onboard_agent.sh`.

## Steps
1. Run `scripts/onboard_agent.sh --name <agent_key> [--invoker-sa <sa_email>] --dry-run` to preview the configuration.
2. After approval, run without `--dry-run` to write the example `.tf` file.
