output "agent_resource_name" {
  description = "The full resource name of the reference agent on Agent Runtime."
  value       = "projects/${local.project_number}/locations/${var.region}/reasoningEngines/${google_vertex_ai_reasoning_engine.agent.name}"
}

output "agent_principal" {
  description = "The Agent Identity principal of the reference agent."
  value       = local.agent_principal
}

output "gateway_id" {
  description = "The resource name of the egress Agent Gateway."
  value       = google_network_services_agent_gateway.egress.id
}

output "iap_enforcement_mode" {
  description = "The current mode of the IAP gateway policy."
  value       = var.iap_enforcement_mode
}

output "mcp_server_url" {
  description = "The MCP endpoint of the sample MCP server on Cloud Run."
  value       = "${google_cloud_run_v2_service.mcp.uri}/mcp"
}

output "log_bucket" {
  description = "The regional log bucket for the gateway request log and the IAP audit log."
  value       = google_logging_project_bucket_config.audit.id
}

output "region" {
  description = "The region of the mini build."
  value       = var.region
}

output "project_id" {
  description = "The project of the mini build."
  value       = var.project_id
}
