# Component 1 (partial) and the audit part of the mini build:
# APIs, Data Access audit logs for IAP, a regional log bucket, and a log sink.

locals {
  # Terraform needs these two APIs to read and turn on the other APIs. In a new
  # project they can be off, so Terraform turns them on first.
  bootstrap_services = [
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
  ]

  services = [
    "aiplatform.googleapis.com",
    "agentregistry.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
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
    "storage.googleapis.com",
    "telemetry.googleapis.com",
  ]
}

resource "google_project_service" "bootstrap" {
  for_each = toset(local.bootstrap_services)

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# A new API can take some time before other calls can use it.
resource "time_sleep" "bootstrap_services" {
  create_duration = "60s"
  depends_on      = [google_project_service.bootstrap]
}

resource "google_project_service" "this" {
  for_each = toset(local.services)

  project = var.project_id
  service = each.value

  # Keep the APIs on after destroy. Other work in the project can need them.
  disable_on_destroy = false

  depends_on = [time_sleep.bootstrap_services]
}

moved {
  from = google_project_service.this["cloudresourcemanager.googleapis.com"]
  to   = google_project_service.bootstrap["cloudresourcemanager.googleapis.com"]
}

moved {
  from = google_project_service.this["serviceusage.googleapis.com"]
  to   = google_project_service.bootstrap["serviceusage.googleapis.com"]
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
  description    = "Gateway request log and IAP audit log for the agent governance starter pack mini build."

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

  # The API always sets a unique writer identity. A sink to a log bucket in the
  # same project needs no extra grant for it.
  unique_writer_identity = true
}

# Optional: a project-level exception to domain restricted sharing. The gateway
# Model Armor grants go to a Google-managed service account. Off by default.
resource "google_org_policy_policy" "allow_google_managed_members" {
  count = var.allow_google_managed_members ? 1 : 0

  name   = "projects/${var.project_id}/policies/iam.allowedPolicyMemberDomains"
  parent = "projects/${var.project_id}"

  # Two modes (see GUIDE Section 3):
  # - allow_all (default): tested live on 08 and 09 Nov 2026. Allow all members on
  #   the project for the time of the grant.
  # - google_customer_id: keep the parent allow list and add is:C02h8e9nw, the
  #   Google customer ID that owns tenant-project service agents. This is the
  #   go/argolis-tips guidance, but a live test on 08 Nov 2026 failed with
  #   FAILED_PRECONDITION (possibly a propagation delay; not verified).
  # Set allow_google_managed_members back to false and apply again after the three
  # Model Armor roles exist.
  spec {
    inherit_from_parent = var.drs_exception_mode == "google_customer_id" ? true : null
    rules {
      allow_all = var.drs_exception_mode == "allow_all" ? "TRUE" : null
      dynamic "values" {
        for_each = var.drs_exception_mode == "google_customer_id" ? [1] : []
        content {
          allowed_values = var.drs_exception_allowed_values
        }
      }
    }
  }

  depends_on = [google_project_service.this]
}
