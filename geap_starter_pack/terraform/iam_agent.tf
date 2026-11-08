# Component 2 (identity baseline): grants for the reference agent.
# - Every grant goes to the single agent principal, not to the principal set of
#   all agents in the project.
# - The agent gets the token creator role on one service account only. There is
#   no project-level roles/iam.serviceAccountTokenCreator.

locals {
  # The Agent Identity principal of the reference agent. The trust domain uses
  # the organization ID.
  agent_principal = join("", [
    "principal://agents.global.org-${var.organization_id}.system.id.goog",
    "/resources/aiplatform/projects/${local.project_number}",
    "/locations/${var.region}/reasoningEngines/${google_vertex_ai_reasoning_engine.agent.name}",
  ])

  # The project roles that the agent needs to run: the model and Sessions,
  # quota, logs, metrics, and traces.
  agent_project_roles = [
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/serviceusage.serviceUsageConsumer",
    "roles/telemetry.writer",
  ]
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
