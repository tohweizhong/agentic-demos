# Component 3 (catalog): the sample MCP server on Cloud Run, registered in
# Agent Registry, and the platform API endpoints that the agent needs.

locals {
  mcp_source_dir = abspath("${path.module}/../mcp-server")

  # The image tag changes when the MCP server source changes.
  mcp_source_hash = substr(sha1(join("", [
    for f in sort(fileset(local.mcp_source_dir, "{*.go,go.mod,go.sum,Dockerfile,cloudbuild.yaml}")) :
    filesha1("${local.mcp_source_dir}/${f}")
  ])), 0, 12)

  mcp_image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.mcp.repository_id}/work-items:${local.mcp_source_hash}"

  # The gateway matches each host exactly. These are the standard hosts for the
  # region, from the Agent Runtime and Agent Gateway documentation.
  platform_api_hosts = distinct(concat([
    "aiplatform.googleapis.com",
    "aiplatform.mtls.googleapis.com",
    "${var.region}-aiplatform.googleapis.com",
    "${var.region}-aiplatform.mtls.googleapis.com",
    "aiplatform.${var.region}.rep.googleapis.com",
    "agentregistry.googleapis.com",
    "logging.googleapis.com",
    "logging.mtls.googleapis.com",
    "telemetry.googleapis.com",
    "telemetry.mtls.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudtrace.mtls.googleapis.com",
    "monitoring.googleapis.com",
    "monitoring.mtls.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudresourcemanager.mtls.googleapis.com",
    "iamcredentials.googleapis.com",
    "iamcredentials.mtls.googleapis.com",
  ], var.extra_api_hosts))
}

resource "google_artifact_registry_repository" "mcp" {
  project       = var.project_id
  location      = var.region
  repository_id = "${var.name_prefix}-mcp"
  format        = "DOCKER"
  description   = "Images for the sample MCP server of the GEAP starter pack mini build."
  labels        = local.labels

  depends_on = [google_project_service.this]
}

# Cloud Build runs as this service account, not as the default compute account.
resource "google_service_account" "mcp_build" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-mcp-build"
  display_name = "GEAP mini build: MCP image build"
}

resource "google_project_iam_member" "mcp_build" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/storage.objectViewer",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.mcp_build.member
}

resource "google_artifact_registry_repository_iam_member" "mcp_build_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.mcp.repository_id
  role       = "roles/artifactregistry.writer"
  member     = google_service_account.mcp_build.member
}

# Build the image with Cloud Build when the source changes. This needs gcloud on
# the machine that runs Terraform.
resource "terraform_data" "mcp_image" {
  triggers_replace = [local.mcp_image]

  provisioner "local-exec" {
    working_dir = local.mcp_source_dir
    command = var.build_mcp_image ? join(" ", [
      "gcloud builds submit .",
      "--project=${var.project_id}",
      "--region=${var.region}",
      "--config=cloudbuild.yaml",
      "--substitutions=_IMAGE=${local.mcp_image}",
      "--service-account=${google_service_account.mcp_build.id}",
      "--default-buckets-behavior=regional-user-owned-bucket",
      "--quiet",
    ]) : "echo 'build_mcp_image is false: no image build.'"
  }

  depends_on = [
    google_project_iam_member.mcp_build,
    google_artifact_registry_repository_iam_member.mcp_build_writer,
  ]
}

# The MCP server runs as this account. It has no roles.
resource "google_service_account" "mcp_run" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-mcp-run"
  display_name = "GEAP mini build: MCP server runtime"
}

# The agent gets an ID token for this account to call the MCP server. Cloud Run
# checks the token. Only this account has roles/run.invoker on the service.
resource "google_service_account" "mcp_invoker" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-mcp-invoker"
  display_name = "GEAP mini build: MCP invoker"
  description  = "The reference agent gets ID tokens for this account. It can invoke the sample MCP server only."
}

resource "google_cloud_run_v2_service" "mcp" {
  project             = var.project_id
  name                = "${var.name_prefix}-work-items"
  location            = var.region
  description         = "Sample MCP server for the GEAP starter pack mini build. Demo only."
  labels              = local.labels
  deletion_protection = false

  # The gateway uses internet egress in the mini build, so the service accepts
  # traffic from the internet. Cloud Run IAM still checks every call.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.mcp_run.email

    scaling {
      # A cold start takes longer than the MCP timeout of the agent.
      min_instance_count = 1
      max_instance_count = 2
    }

    containers {
      image = local.mcp_image
      ports {
        container_port = 8080
      }
      startup_probe {
        http_get {
          path = "/healthz"
        }
      }
    }
  }

  lifecycle {
    # The "reset the demo" runbook sets this label to start a new revision.
    ignore_changes = [template[0].labels["demo-reset"]]
  }

  depends_on = [terraform_data.mcp_image]
}

resource "google_cloud_run_v2_service_iam_member" "mcp_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.mcp.name
  role     = "roles/run.invoker"
  member   = google_service_account.mcp_invoker.member
}

# Agent Registry: the MCP server and its tools. IAP policy V2 rules can use the
# tool names and the read-only hints from this spec.
resource "google_agent_registry_service" "mcp" {
  project      = var.project_id
  location     = var.region
  service_id   = "${var.name_prefix}-work-items"
  display_name = "Work items (sample)"
  description  = "Sample MCP server with one read-only tool and one write tool."

  interfaces {
    url              = "${google_cloud_run_v2_service.mcp.uri}/mcp"
    protocol_binding = "JSONRPC"
  }

  mcp_server_spec {
    type    = "TOOL_SPEC"
    content = jsonencode(jsondecode(file("${local.mcp_source_dir}/tool_spec.json")))
  }

  depends_on = [google_project_service.this]
}

# Agent Registry: one endpoint with the Google API hosts that the agent calls.
resource "google_agent_registry_service" "google_apis" {
  project      = var.project_id
  location     = var.region
  service_id   = "${var.name_prefix}-google-apis"
  display_name = "Google APIs for Agent Runtime"
  description  = "Platform API hosts for the model, Sessions, tokens, logs, and traces."

  dynamic "interfaces" {
    for_each = local.platform_api_hosts
    content {
      url              = "https://${interfaces.value}"
      protocol_binding = "HTTP_JSON"
    }
  }

  endpoint_spec {
    type = "NO_SPEC"
  }

  depends_on = [google_project_service.this]
}
