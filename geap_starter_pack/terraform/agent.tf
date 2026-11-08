# Component 4 (reference agent): the ADK agent on Agent Runtime with Agent
# Identity, Sessions, and the egress gateway binding. The binding is in
# Terraform, so that the security owner controls it.

locals {
  agent_archive_path = "${path.module}/${var.agent_source_archive}"
}

resource "google_vertex_ai_reasoning_engine" "agent" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.name_prefix}-reference-agent"
  description  = "Reference agent of the GEAP starter pack mini build."
  labels       = local.labels

  # Delete the agent together with its sessions.
  deletion_policy = "FORCE"

  spec {
    agent_framework = "google-adk"
    identity_type   = "AGENT_IDENTITY"
    class_methods   = jsonencode(jsondecode(file("${path.module}/adk_class_methods.json")))

    source_code_spec {
      inline_source {
        source_archive = fileexists(local.agent_archive_path) ? filebase64(local.agent_archive_path) : null
      }

      python_spec {
        version           = "3.13"
        entrypoint_module = "agent_engine_app"
        entrypoint_object = "app"
        requirements_file = "requirements.txt"
      }
    }

    deployment_spec {
      min_instances = 1
      max_instances = 2

      agent_gateway_config {
        agent_to_anywhere_config {
          agent_gateway = google_network_services_agent_gateway.egress.id
        }
      }

      env {
        name  = "MCP_SERVER_URL"
        value = "${google_cloud_run_v2_service.mcp.uri}/mcp"
      }
      env {
        name  = "MCP_INVOKER_SERVICE_ACCOUNT"
        value = google_service_account.mcp_invoker.email
      }
      env {
        name  = "MODEL_ID"
        value = var.model_id
      }
      env {
        name  = "MODEL_LOCATION"
        value = var.model_location
      }
      env {
        name  = "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY"
        value = "true"
      }
      # The gateway inspects TLS with its own CA. Agent Runtime adds the CA to the
      # system store. These settings make httpx, requests, and gRPC use that store.
      env {
        name  = "SSL_CERT_FILE"
        value = "/etc/ssl/certs/ca-certificates.crt"
      }
      env {
        name  = "REQUESTS_CA_BUNDLE"
        value = "/etc/ssl/certs/ca-certificates.crt"
      }
      env {
        name  = "GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"
        value = "/etc/ssl/certs/ca-certificates.crt"
      }
    }
  }

  lifecycle {
    precondition {
      condition     = fileexists(local.agent_archive_path)
      error_message = "The agent source archive is missing. Run scripts/package_agent.sh first."
    }
  }

  depends_on = [
    google_project_service.this,
    google_network_security_authz_policy.iap,
    # The container needs the base roles when it starts.
    google_project_iam_member.agent_base,
  ]
}
