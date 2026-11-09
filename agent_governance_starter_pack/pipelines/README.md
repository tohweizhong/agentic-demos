# Pipelines

Not built. This folder is for component 5, the agent factory pipeline. The mini build does not
cover component 5. See the "Components" table in [product.md](../conductor/product.md).

## Templates

| File | What it does | Status |
|---|---|---|
| [`github-actions-pr-check.yaml`](github-actions-pr-check.yaml) | Runs the offline checks on each pull request: package the agent, `scripts/deploy_checks.sh` (Terraform init, fmt, validate, test with mock providers, tool policy check), Go tests, and Python tests. Copy it to `.github/workflows/` in the customer repository | Template (09 Nov 2026). Not run on GitHub yet |
