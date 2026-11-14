# Component 4 (reference agent): the ADK agent on Agent Runtime with Agent
# Identity, Sessions, and optional egress and ingress gateway bindings. The
# bindings are in Terraform, so that the security owner controls them.

locals {
  agent_archive_path = "${path.module}/${var.agent_source_archive}"
}

# Attaching or changing an Agent Gateway via in-place UpdateReasoningEngine
# fails in the internal Cloud Run revision rollout (Error code 13). Force a
# clean Reasoning Engine replacement when the gateway bindings change.
resource "terraform_data" "agent_gateway_binding" {
  input = {
    egress  = var.enable_egress_gateway
    ingress = var.enable_ingress_gateway
  }
}

resource "google_vertex_ai_reasoning_engine" "agent" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.name_prefix}-reference-agent"
  description  = "Reference agent of the agent governance starter pack mini build."
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

      # Container deploy: Agent Runtime builds ../agent-template/Dockerfile.
      # When an egress gateway is enabled, the Dockerfile installs its root CA.
      image_spec {
        build_args = {
          AGENT_GATEWAY_ROOT_CERTIFICATES = var.enable_egress_gateway ? join("\n", google_network_services_agent_gateway.egress[0].agent_gateway_card[0].root_certificates) : ""
        }
      }
    }

    deployment_spec {
      min_instances = 1
      max_instances = 2

      dynamic "agent_gateway_config" {
        for_each = local.any_gateway_enabled ? [1] : []
        content {
          dynamic "agent_to_anywhere_config" {
            for_each = var.enable_egress_gateway ? [1] : []
            content {
              agent_gateway = google_network_services_agent_gateway.egress[0].id
            }
          }
          dynamic "client_to_agent_config" {
            for_each = var.enable_ingress_gateway ? [1] : []
            content {
              agent_gateway = google_network_services_agent_gateway.ingress[0].id
            }
          }
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
      # Spans go to Cloud Trace through adk api_server --otel_to_cloud (see the
      # Dockerfile). GOOGLE_CLOUD_PROJECT is reserved by Agent Runtime, so it
      # cannot be set here (Error 400 on 14 Nov 2026).
      # Do not put prompt, response, or tool argument text in the spans unless the
      # owner turns it on. ADK records the text by default.
      env {
        name  = "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"
        value = var.trace_message_content ? "true" : "false"
      }
      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = var.trace_message_content ? "SPAN_ONLY" : "NO_CONTENT"
      }
      # The Dockerfile installs the gateway root CA and sets SSL_CERT_FILE,
      # REQUESTS_CA_BUNDLE, and GRPC_DEFAULT_SSL_ROOTS_FILE_PATH.
    }
  }

  lifecycle {
    replace_triggered_by = [terraform_data.agent_gateway_binding]
    precondition {
      condition     = fileexists(local.agent_archive_path)
      error_message = "The agent source archive is missing. Run scripts/package_agent.sh first."
    }
  }

  depends_on = [
    google_project_service.this,
    google_network_security_authz_policy.iap,
    google_network_security_authz_policy.model_armor,
    google_network_security_authz_policy.ingress_model_armor,
    google_project_iam_member.gateway_model_armor,
    # The container needs the base roles when it starts.
    google_project_iam_member.agent_base,
  ]
}
