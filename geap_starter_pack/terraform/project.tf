# Component 1 (partial) and the audit part of the mini build:
# APIs, Data Access audit logs for IAP, a regional log bucket, and a log sink.

locals {
  services = [
    "aiplatform.googleapis.com",
    "agentregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "iap.googleapis.com",
    "logging.googleapis.com",
    "modelarmor.googleapis.com",
    "monitoring.googleapis.com",
    "networksecurity.googleapis.com",
    "networkservices.googleapis.com",
    "orgpolicy.googleapis.com",
    "run.googleapis.com",
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "telemetry.googleapis.com",
  ]
}

resource "google_project_service" "this" {
  for_each = toset(local.services)

  project = var.project_id
  service = each.value

  # Keep the APIs on after destroy. Other work in the project can need them.
  disable_on_destroy = false
}

# IAP writes the gateway allow and deny decisions, and the dry-run results, to
# the Data Access audit log. These logs are off by default.
resource "google_project_iam_audit_config" "iap" {
  project = var.project_id
  service = "iap.googleapis.com"

  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }

  depends_on = [google_project_service.this]
}

# A regional log bucket keeps the gateway and IAP logs in the region.
resource "google_logging_project_bucket_config" "audit" {
  project        = var.project_id
  location       = var.region
  bucket_id      = "${var.name_prefix}-agent-audit"
  retention_days = var.log_retention_days
  description    = "Gateway request log and IAP audit log for the GEAP starter pack mini build."

  depends_on = [google_project_service.this]
}

resource "google_logging_project_sink" "audit" {
  project     = var.project_id
  name        = "${var.name_prefix}-agent-audit"
  description = "Copies the gateway request log and the IAP audit log to the regional bucket."
  destination = "logging.googleapis.com/${google_logging_project_bucket_config.audit.id}"

  filter = join(" OR ", [
    "logName=\"projects/${var.project_id}/logs/networkservices.googleapis.com%2Fgateway_requests\"",
    "(logName=\"projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Fdata_access\" AND protoPayload.serviceName=\"iap.googleapis.com\")",
  ])

  # A sink to a log bucket in the same project does not need a separate writer identity.
  unique_writer_identity = false
}

# Optional: a project-level exception to domain restricted sharing. The gateway
# Model Armor grants go to a Google-managed service account. Off by default.
resource "google_org_policy_policy" "allow_google_managed_members" {
  count = var.allow_google_managed_members ? 1 : 0

  name   = "projects/${var.project_id}/policies/iam.allowedPolicyMemberDomains"
  parent = "projects/${var.project_id}"

  spec {
    rules {
      allow_all = "TRUE"
    }
  }

  depends_on = [google_project_service.this]
}
