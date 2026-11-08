# Offline tests. They use mock providers, so they create no cloud resources and
# need no credentials. Run: terraform test

mock_provider "google" {
  mock_data "google_project" {
    defaults = {
      number = "123456789012"
    }
  }

  mock_resource "google_vertex_ai_reasoning_engine" {
    defaults = {
      name = "1111111111111111111"
    }
  }

  mock_resource "google_network_services_agent_gateway" {
    defaults = {
      id = "projects/example-project/locations/us-central1/agentGateways/geap-egress"
      agent_gateway_card = [{
        service_extensions_service_account = "service-123456789012@gcp-sa-example.iam.gserviceaccount.com"
        root_certificates                  = []
        mtls_endpoint                      = ""
      }]
    }
  }

  mock_resource "google_service_account" {
    defaults = {
      email  = "example@example-project.iam.gserviceaccount.com"
      member = "serviceAccount:example@example-project.iam.gserviceaccount.com"
      name   = "projects/example-project/serviceAccounts/example@example-project.iam.gserviceaccount.com"
      id     = "projects/example-project/serviceAccounts/example@example-project.iam.gserviceaccount.com"
    }
  }

  mock_resource "google_cloud_run_v2_service" {
    defaults = {
      uri = "https://geap-work-items-example.a.run.app"
    }
  }
}

mock_provider "time" {}

variables {
  project_id      = "example-project"
  organization_id = "111111111111"
  # Any file that exists. The plan only checks that the archive is there.
  agent_source_archive = "adk_class_methods.json"
  # Never call Cloud Build from a test.
  build_mcp_image = false
}

run "dry_run_is_the_default" {
  command = apply

  assert {
    condition     = google_network_services_authz_extension.iap.metadata["iamEnforcementMode"] == "DRY_RUN"
    error_message = "The IAP extension must start in DRY_RUN."
  }

  assert {
    condition     = google_network_services_authz_extension.iap.metadata["iapPolicyVersion"] == "V2"
    error_message = "The IAP extension must use policy version V2."
  }

  assert {
    condition     = google_network_services_authz_extension.iap.fail_open == false
    error_message = "The authz extensions must fail closed by default."
  }
}

run "enforce_removes_the_dry_run_field" {
  command = apply

  variables {
    iap_enforcement_mode = "ENFORCE"
  }

  assert {
    condition     = !contains(keys(google_network_services_authz_extension.iap.metadata), "iamEnforcementMode")
    error_message = "In ENFORCE mode, the IAP extension must not set iamEnforcementMode."
  }
}

run "access_policy_comes_from_the_policy_file" {
  command = apply

  assert {
    condition     = length(google_iam_project_access_policy.agent_egress.details[0].rules) == 2
    error_message = "The access policy must have the two rules from policies/iap_access_policy.yaml."
  }

  assert {
    condition = alltrue([
      for r in google_iam_project_access_policy.agent_egress.details[0].rules :
      r.principals == tolist(["principal://agents.global.org-111111111111.system.id.goog/resources/aiplatform/projects/123456789012/locations/us-central1/reasoningEngines/1111111111111111111"])
    ])
    error_message = "Each rule must apply to the single reference agent principal."
  }

  assert {
    condition = anytrue([
      for r in google_iam_project_access_policy.agent_egress.details[0].rules :
      r.effect == "DENY" && strcontains(one(r.conditions).expression, "update_status")
    ])
    error_message = "The access policy must deny the update_status tool."
  }

  assert {
    condition = anytrue([
      for r in google_iam_project_access_policy.agent_egress.details[0].rules :
      r.effect == "ALLOW" && strcontains(one(r.conditions).expression, "'us-central1'")
    ])
    error_message = "The allow rule must name the region of the mini build."
  }
}

run "no_project_level_token_creator" {
  command = apply

  assert {
    condition     = !contains(local.agent_project_roles, "roles/iam.serviceAccountTokenCreator")
    error_message = "The agent must not get roles/iam.serviceAccountTokenCreator at the project level."
  }

  assert {
    condition     = google_service_account_iam_member.agent_token_creator.role == "roles/iam.serviceAccountTokenCreator"
    error_message = "The agent must get the token creator role on the invoker service account."
  }
}

run "agent_uses_identity_and_gateway" {
  command = apply

  assert {
    condition     = google_vertex_ai_reasoning_engine.agent.spec[0].identity_type == "AGENT_IDENTITY"
    error_message = "The agent must use Agent Identity."
  }

  assert {
    condition     = google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].agent_gateway_config[0].agent_to_anywhere_config[0].agent_gateway == google_network_services_agent_gateway.egress.id
    error_message = "The agent must be bound to the egress gateway."
  }
}

run "registry_has_the_tool_spec" {
  command = apply

  assert {
    condition     = length(jsondecode(google_agent_registry_service.mcp.mcp_server_spec[0].content).tools) == 2
    error_message = "The registered MCP server must have the two tools from tool_spec.json."
  }
}
