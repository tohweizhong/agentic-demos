# Pipelines

This folder holds CI pull-request check templates for the starter pack. The full agent factory deployment pipeline is not built yet.

## Templates

| File | What it does | Status |
|---|---|---|
| [`github-actions-pr-check.yaml`](github-actions-pr-check.yaml) | Runs the offline checks on each pull request: package the agent, `scripts/deploy_checks.sh` (Terraform init, fmt, validate, test with mock providers, tool policy check), Go tests, and Python tests. Copy it to `.github/workflows/` in the customer repository | Template (09 Nov 2026). Not run on GitHub yet |
