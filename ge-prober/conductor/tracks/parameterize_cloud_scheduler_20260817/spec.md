# Specification: Parameterize Cloud Scheduler and Deployment for `ge-prober`

## 1. Overview
Enhance `ge-prober` deployment automation by parameterizing Google Cloud Scheduler and Google Cloud Run Job creation. Provide a flexible, idempotent bash workflow that supports CLI flags, environment variable overrides, dedicated Service Account configuration, custom cron schedules, time zones, pre-flight parameter validation, IAM diagnostics, and dry-run mode.

## 2. Functional Requirements
1. **CLI Flag & Environment Variable Support**:
   - `deploy_job.sh` supports standard flags: `--project`, `--region`, `--engine-id`, `--location`, `--job-name`, `--scheduler-name`, `--schedule`, `--time-zone`, `--service-account`, `--dry-run`, `--skip-build`, `--only-scheduler`, `--help`.
   - Precedence: CLI Flags > Environment Variables > Defaults.
2. **Configurable Cloud Scheduler**:
   - Customizable cron expression (`SCHEDULE_CRON`, default `0 1 * * *`).
   - Customizable time zone (`TIME_ZONE`, default `Asia/Singapore`).
   - Customizable trigger target (Cloud Run Job execution endpoint).
   - Dedicated OIDC / OAuth Service Account (`SCHEDULER_SA_EMAIL`), falling back gracefully to the current active gcloud identity.
3. **Pre-flight Validation & IAM Diagnostics**:
   - Validates existence of `gcloud` CLI and active authenticated configuration.
   - Validates cron expression format and timezone string.
   - Verifies / reminds required IAM permissions (`roles/run.invoker` for Scheduler SA, `roles/run.admin` for deployer).
4. **Execution Modes**:
   - Full deployment: Build container $\rightarrow$ Deploy Cloud Run Job $\rightarrow$ Configure Cloud Scheduler.
   - Standalone scheduler mode (`--only-scheduler`): Update or create Scheduler trigger without rebuilding container.
   - Dry-run mode (`--dry-run`): Print resolved configuration and exact `gcloud` commands without executing them.
5. **Documentation**:
   - Update `README.md` and `PROBER_SPECIFICATION.md` with full usage examples, table of environment variables, and CLI flag references.

## 3. Acceptance Criteria
- [ ] `./deploy_job.sh --help` displays all flags, environment variables, and defaults.
- [ ] `./deploy_job.sh --dry-run` performs parameter resolution and outputs planned `gcloud` execution steps.
- [ ] `./deploy_job.sh --only-scheduler --schedule="0 2 * * *" --time-zone="UTC"` correctly configures the scheduler without executing container builds.
- [ ] Automated/mock validation tests verify CLI flag parsing, help text, and dry-run behavior.
