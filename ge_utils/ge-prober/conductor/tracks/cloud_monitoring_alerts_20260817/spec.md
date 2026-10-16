# Specification: Implement Cloud Monitoring Alerting & Email Notifications for `ge-prober`

## 1. Overview
Enhance `ge-prober` deployment automation by adding Google Cloud Monitoring notification channels and alert policies. Update the default Cloud Scheduler schedule to run twice daily (09:00 and 17:00 Singapore Time), and parameterize recipient email addresses (`alerts@example.com`) and alert modes (`all` runs vs `failure-only`).

## 2. Functional Requirements
1. **Parameterized Alerting Flags & Environment Variables**:
   - `--alert-email EMAIL` / `-m EMAIL` (default: `alerts@example.com` or `$ALERT_EMAIL`).
   - `--alert-mode MODE` (values: `all` | `failure-only`, default: `all` or `$ALERT_MODE`).
   - `--only-alerting` (creates or updates Notification Channels and Alert Policies without rebuilding container or redeploying Cloud Run Job).
2. **Updated Default Schedule**:
   - Default schedule: `0 9,17 * * *` (09:00 and 17:00 daily).
   - Default time zone: `Asia/Singapore` (SGT, GMT+8).
3. **Automated Alert Policy Provisioning**:
   - Idempotently creates or reuses Email Notification Channel in Cloud Monitoring.
   - For `all` mode: Creates Log-Based Alert policy matching `"PROBER SUMMARY & HEALTH SCORE"` in Cloud Run Job logs.
   - For `failure-only` mode: Creates Metric-Based Alert policy on `completed_execution_count` with `result = "failed"`.
4. **Dry Run Support**:
   - `--dry-run` displays resolved alert email, alert mode, and exact `gcloud monitoring` provisioning commands.
5. **Testing & Documentation**:
   - Extend `test_deploy_job.sh` with test assertions for alerting flags, dry-run output, and invalid modes.
   - Update `README.md` and `PROBER_SPECIFICATION.md`.

## 3. Acceptance Criteria
- [ ] `./deploy_job.sh --help` displays `--alert-email`, `--alert-mode`, and `--only-alerting`.
- [ ] `./deploy_job.sh --dry-run` displays default schedule `0 9,17 * * *`, timezone `Asia/Singapore`, and email `alerts@example.com`.
- [ ] `test_deploy_job.sh` test suite passes all assertions.
- [ ] Documentation reflects alerting options and parameters.
