#!/usr/bin/env bash
# Generates terraform code and IAM grants for onboarding a new agent.
#
# Usage:
#   scripts/onboard_agent.sh --name <agent_key> [--invoker-sa <sa_email>] [--dry-run]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

AGENT_KEY=""
INVOKER_SA=""
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) AGENT_KEY="$2"; shift 2 ;;
    --invoker-sa) INVOKER_SA="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done

[[ -n "${AGENT_KEY}" ]] || { echo "ERROR: --name is required." >&2; exit 2; }

OUT_FILE="${TF_DIR}/agent_${AGENT_KEY}.tf.example"

cat << HCL > "${OUT_FILE}.tmp"
resource "google_vertex_ai_reasoning_engine" "${AGENT_KEY}" {
  project      = var.project_id
  location     = var.region
  display_name = "\${var.name_prefix}-${AGENT_KEY}"

  spec {
    package_spec {
      env {
        name  = "MODEL_ID"
        value = var.model_id
      }
      env {
        name  = "MODEL_LOCATION"
        value = var.model_location
      }
      # The source archive must exist before Terraform applies.
      # You can build it using scripts/package_agent.sh.
      inline_source {
        source_archive = fileexists(local.agent_archive_path) ? filebase64(local.agent_archive_path) : null
      }
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
    }
  }
}

# The single-principal IAM grant for the agent's identity.
resource "google_project_iam_member" "${AGENT_KEY}_agent_identity" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "principal://agents.global.org-\${var.organization_id}.system.id.goog/resources/aiplatform/projects/\${var.project_number}/locations/\${var.region}/reasoningEngines/\${google_vertex_ai_reasoning_engine.${AGENT_KEY}.name}"
}
HCL

if [[ -n "${INVOKER_SA}" ]]; then
  cat << HCL >> "${OUT_FILE}.tmp"

# The invoker SA binding for this specific agent.
resource "google_project_iam_member" "${AGENT_KEY}_invoker" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${INVOKER_SA}"
  condition {
    title       = "Reasoning Engine ${AGENT_KEY} Only"
    description = "Limit access to the specific Reasoning Engine"
    expression  = "resource.name == 'projects/\${var.project_number}/locations/\${var.region}/reasoningEngines/\${google_vertex_ai_reasoning_engine.${AGENT_KEY}.name}'"
  }
}
HCL
fi

cat << HCL >> "${OUT_FILE}.tmp"

# To add to policies/iap_access_policy.yaml:
# - principals:
#   - principal://agents.global.org-ORG_ID.system.id.goog/resources/aiplatform/projects/NUMBER/locations/REGION/reasoningEngines/ID
HCL

if [[ "${DRY_RUN}" == "true" ]]; then
  cat "${OUT_FILE}.tmp"
  rm -f "${OUT_FILE}.tmp"
  exit 0
fi

mv "${OUT_FILE}.tmp" "${OUT_FILE}"
echo "Wrote ${OUT_FILE} with the new agent configuration."
