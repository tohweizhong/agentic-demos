# Component 2 (identity baseline): grants for the agents.
#
# - Base roles go to the principal set of all agents in the project, before
#   Terraform creates an agent. The agent needs them when its container starts
#   (logs, metrics, traces, quota). A single agent principal exists only after
#   the agent exists, so it cannot hold the start-up roles.
# - Tool access and Sessions go to the single agent principal: the token creator
#   role on one invoker service account, roles/aiplatform.user, and the IAP
#   egress policy in gateway.tf.
# - There is no project-level roles/iam.serviceAccountTokenCreator.

locals {
  # All Agent Runtime agents in this project.
  agent_principal_set = join("", [
    "principalSet://agents.global.org-${var.organization_id}.system.id.goog",
    "/attribute.platformContainer/aiplatform/projects/${local.project_number}",
  ])

  # The Agent Identity principal of the reference agent. The trust domain uses
  # the organization ID.
  agent_principal = join("", [
    "principal://agents.global.org-${var.organization_id}.system.id.goog",
    "/resources/aiplatform/projects/${local.project_number}",
    "/locations/${var.region}/reasoningEngines/${google_vertex_ai_reasoning_engine.agent.name}",
  ])

  # roles/aiplatform.agentDefaultAccess has the start-up permissions: log
  # entries, metrics, traces, telemetry, service usage, project get, and model
  # predict. Its stage is ALPHA (checked with gcloud iam roles describe).
  agent_base_roles = [
    "roles/aiplatform.agentDefaultAccess",
  ]

  # Roles for the reference agent only. roles/aiplatform.user covers Sessions.
  agent_project_roles = [
    "roles/aiplatform.user",
  ]
}

resource "google_project_iam_member" "agent_base" {
  for_each = toset(local.agent_base_roles)

  project = var.project_id
  role    = each.value
  member  = local.agent_principal_set
}

resource "google_project_iam_member" "agent" {
  for_each = toset(local.agent_project_roles)

  project = var.project_id
  role    = each.value
  member  = local.agent_principal
}

# The agent can get tokens for the MCP invoker account only.
resource "google_service_account_iam_member" "agent_token_creator" {
  service_account_id = google_service_account.mcp_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.agent_principal
}
