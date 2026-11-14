# Offline tests. They use mock providers, so they create no cloud resources and
# need no credentials. Run: terraform test

mock_provider "google" {
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
        root_certificates                  = ["-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----"]
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
  project_number  = "123456789012"
  organization_id = "111111111111"
  # Any file that exists. The plan only checks that the archive is there.
  agent_source_archive = "adk_class_methods.json"
  # Never call Cloud Build from a test.
  build_mcp_image = false
  # Set every value that a local terraform.tfvars can change. terraform test
  # also reads terraform.tfvars.
  region                       = "us-central1"
  enable_agent_registry        = true
  enable_egress_gateway        = true
  enable_model_armor           = true
  enable_ingress_gateway       = false
  iap_enforcement_mode         = "DRY_RUN"
  allow_google_managed_members = false
  authz_fail_open              = false
}

run "dry_run_mode_sets_the_dry_run_field" {
  command = apply

  assert {
    condition     = google_network_services_authz_extension.iap[0].metadata["iamEnforcementMode"] == "DRY_RUN"
    error_message = "The IAP extension must start in DRY_RUN."
  }

  assert {
    condition     = google_network_services_authz_extension.iap[0].metadata["iapPolicyVersion"] == "V2"
    error_message = "The IAP extension must use policy version V2."
  }

  assert {
    condition     = google_network_services_authz_extension.iap[0].fail_open == false
    error_message = "The authz extensions must fail closed by default."
  }
}

run "enforce_removes_the_dry_run_field" {
  command = apply

  variables {
    iap_enforcement_mode = "ENFORCE"
  }

  assert {
    condition     = !contains(keys(google_network_services_authz_extension.iap[0].metadata), "iamEnforcementMode")
    error_message = "In ENFORCE mode, the IAP extension must not set iamEnforcementMode."
  }
}

run "access_policy_comes_from_the_policy_file" {
  command = apply

  assert {
    condition     = google_iam_project_access_policy.agent_egress[0].access_policy_id == "${var.name_prefix}-agent-egress"
    error_message = "The access policy ID must use the name prefix, so that two copies can run in one project."
  }

  assert {
    condition     = length(google_iam_project_access_policy.agent_egress[0].details[0].rules) == 2
    error_message = "The access policy must have the two rules from policies/iap_access_policy.yaml."
  }

  assert {
    condition = alltrue([
      for r in google_iam_project_access_policy.agent_egress[0].details[0].rules :
      r.principals == tolist(["principal://agents.global.org-111111111111.system.id.goog/resources/aiplatform/projects/123456789012/locations/us-central1/reasoningEngines/1111111111111111111"])
    ])
    error_message = "Each rule must apply to the single reference agent principal."
  }

  assert {
    condition = anytrue([
      for r in google_iam_project_access_policy.agent_egress[0].details[0].rules :
      r.effect == "DENY" && strcontains(one(r.conditions).expression, "update_status")
    ])
    error_message = "The access policy must deny the update_status tool."
  }

  assert {
    condition = anytrue([
      for r in google_iam_project_access_policy.agent_egress[0].details[0].rules :
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
    condition     = !contains(local.agent_base_roles, "roles/iam.serviceAccountTokenCreator")
    error_message = "The agent principal set must not get roles/iam.serviceAccountTokenCreator."
  }

  assert {
    condition     = google_service_account_iam_member.agent_token_creator.member == local.agent_principal
    error_message = "The token creator grant must go to the single agent principal."
  }

  assert {
    condition     = google_service_account_iam_member.agent_token_creator.role == "roles/iam.serviceAccountTokenCreator"
    error_message = "The agent must get the token creator role on the invoker service account."
  }
}

run "base_roles_go_to_the_principal_set" {
  command = apply

  assert {
    condition     = google_project_iam_member.agent_base["roles/aiplatform.agentDefaultAccess"].member == "principalSet://agents.global.org-111111111111.system.id.goog/attribute.platformContainer/aiplatform/projects/123456789012"
    error_message = "The base roles must go to the agent principal set of the project."
  }
}

run "agent_uses_identity_and_gateways" {
  command = apply

  variables {
    enable_egress_gateway  = true
    enable_ingress_gateway = true
  }

  assert {
    condition     = google_vertex_ai_reasoning_engine.agent.spec[0].identity_type == "AGENT_IDENTITY"
    error_message = "The agent must use Agent Identity."
  }

  assert {
    condition     = google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].agent_gateway_config[0].agent_to_anywhere_config[0].agent_gateway == google_network_services_agent_gateway.egress[0].id
    error_message = "The agent must be bound to the egress gateway."
  }

  assert {
    condition     = google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].agent_gateway_config[0].client_to_agent_config[0].agent_gateway == google_network_services_agent_gateway.ingress[0].id
    error_message = "The agent must be bound to the ingress gateway."
  }

  assert {
    condition     = google_network_services_agent_gateway.ingress[0].google_managed[0].governed_access_path == "CLIENT_TO_AGENT"
    error_message = "The ingress gateway must use the CLIENT_TO_AGENT governed access path."
  }
}

run "agent_trace_export_without_message_text" {
  command = plan

  assert {
    condition     = contains([for e in google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].env : e.value if e.name == "GOOGLE_CLOUD_PROJECT"], "example-project")
    error_message = "The agent must set GOOGLE_CLOUD_PROJECT so that the Cloud Trace export has a valid project."
  }

  assert {
    condition     = alltrue([for e in google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].env : e.value == "false" if contains(["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"], e.name)])
    error_message = "By default the spans must not record message text."
  }
}

run "tier_1_without_gateways" {
  command = apply

  variables {
    enable_agent_registry  = false
    enable_egress_gateway  = false
    enable_model_armor     = false
    enable_ingress_gateway = false
  }

  assert {
    condition     = length(google_agent_registry_service.mcp) == 0 && length(google_agent_registry_service.google_apis) == 0
    error_message = "Tier 1 mode must not create Agent Registry entries when enable_agent_registry is false."
  }

  assert {
    condition     = length(google_network_services_agent_gateway.egress) == 0 && length(google_network_services_agent_gateway.ingress) == 0
    error_message = "Tier 1 mode must not create any Agent Gateway."
  }

  assert {
    condition     = length(google_project_iam_member.gateway_model_armor) == 0
    error_message = "Tier 1 mode must not create any gcp-sa-dep Model Armor bindings."
  }

  assert {
    condition     = length(google_vertex_ai_reasoning_engine.agent.spec[0].deployment_spec[0].agent_gateway_config) == 0
    error_message = "Tier 1 mode must not set agent_gateway_config on the agent."
  }
}

run "tier_3_egress_gateway_without_model_armor" {
  command = apply

  variables {
    enable_agent_registry  = true
    enable_egress_gateway  = true
    enable_model_armor     = false
    enable_ingress_gateway = false
  }

  assert {
    condition     = length(google_network_services_agent_gateway.egress) == 1 && length(google_network_security_authz_policy.iap) == 1
    error_message = "Tier 3 mode must create the egress gateway and IAP policy."
  }

  assert {
    condition     = length(google_model_armor_template.this) == 0 && length(google_project_iam_member.gateway_model_armor) == 0
    error_message = "Tier 3 without Model Armor must not create Model Armor templates or gcp-sa-dep bindings."
  }
}

run "tier_3_without_tier_2_is_rejected" {
  command = plan

  variables {
    enable_agent_registry  = false
    enable_egress_gateway  = true
    enable_model_armor     = false
    enable_ingress_gateway = false
  }

  expect_failures = [var.enable_egress_gateway]
}

run "tier_4_without_tier_3_is_rejected" {
  command = plan

  variables {
    enable_agent_registry  = true
    enable_egress_gateway  = false
    enable_model_armor     = true
    enable_ingress_gateway = true
  }

  expect_failures = [var.enable_model_armor]
}

run "agent_image_trusts_the_gateway_ca" {
  command = apply

  assert {
    condition     = strcontains(google_vertex_ai_reasoning_engine.agent.spec[0].source_code_spec[0].image_spec[0].build_args["AGENT_GATEWAY_ROOT_CERTIFICATES"], "BEGIN CERTIFICATE")
    error_message = "The agent image build must get the gateway root CA."
  }
}

run "registry_has_the_tool_spec" {
  command = apply

  assert {
    condition     = length(jsondecode(google_agent_registry_service.mcp[0].mcp_server_spec[0].content).tools) == 2
    error_message = "The registered MCP server must have the two tools from tool_spec.json."
  }
}

run "drs_exception_allow_all_by_default" {
  command = apply

  variables {
    allow_google_managed_members = true
  }

  assert {
    condition     = google_org_policy_policy.allow_google_managed_members[0].spec[0].rules[0].allow_all == "TRUE"
    error_message = "The default project exception must be allow_all (the tested mode)."
  }
}

run "drs_exception_google_customer_id" {
  command = apply

  variables {
    allow_google_managed_members = true
    drs_exception_mode           = "google_customer_id"
  }

  assert {
    condition     = google_org_policy_policy.allow_google_managed_members[0].spec[0].inherit_from_parent == true
    error_message = "The google_customer_id mode must keep the parent allow list (inherit_from_parent)."
  }

  assert {
    condition     = google_org_policy_policy.allow_google_managed_members[0].spec[0].rules[0].values[0].allowed_values == tolist(["is:C02h8e9nw"])
    error_message = "The google_customer_id mode must add only the Google customer ID."
  }
}

run "existing_mcp_servers_are_registered" {
  command = apply

  variables {
    existing_mcp_servers = {
      crm = {
        url            = "https://crm-mcp.example.com/mcp"
        tool_spec_file = "../mcp-server/tool_spec.json"
      }
    }
  }

  assert {
    condition     = google_agent_registry_service.existing_mcp["crm"].service_id == "${var.name_prefix}-ext-crm"
    error_message = "An existing MCP server must be registered with the ext- name."
  }

  assert {
    condition     = google_agent_registry_service.existing_mcp["crm"].interfaces[0].url == "https://crm-mcp.example.com/mcp"
    error_message = "The registry entry must use the URL of the existing server."
  }
}

run "existing_agents_share_the_access_policy" {
  command = apply

  variables {
    existing_agent_principals = [
      "principal://agents.global.org-111111111111.system.id.goog/resources/aiplatform/projects/123456789012/locations/us-central1/reasoningEngines/2222222222222222222"
    ]
  }

  assert {
    condition = alltrue([
      for r in google_iam_project_access_policy.agent_egress[0].details[0].rules :
      length(r.principals) == 2 && contains(r.principals, "principal://agents.global.org-111111111111.system.id.goog/resources/aiplatform/projects/123456789012/locations/us-central1/reasoningEngines/2222222222222222222")
    ])
    error_message = "Each access policy rule must apply to the reference agent and to each existing agent principal."
  }
}

run "model_armor_template_loads_yaml" {
  command = apply

  assert {
    condition     = google_model_armor_template.this["request"].filter_config[0].pi_and_jailbreak_filter_settings[0].filter_enforcement == "ENABLED"
    error_message = "The template must load the pi_and_jailbreak enforcement from the YAML."
  }

  assert {
    condition     = google_model_armor_template.this["request"].filter_config[0].sdp_settings[0].basic_config[0].filter_enforcement == "ENABLED"
    error_message = "The template must load the sdp enforcement from the YAML."
  }

  assert {
    condition     = length(google_model_armor_template.this["request"].filter_config[0].rai_settings[0].rai_filters) > 0
    error_message = "The template must load the rai_filters from the YAML."
  }
}

run "egress_scope_auto_at_tier_4_screens_all_egress" {
  command = plan

  variables {
    enable_ingress_gateway = false
  }

  assert {
    condition     = output.model_armor_egress_scope == "all_egress"
    error_message = "At Tier 4, auto must resolve to all_egress."
  }

  assert {
    condition     = length(google_network_security_authz_policy.model_armor[0].http_rules) == 0
    error_message = "all_egress must have no host rule, so all egress traffic goes to Model Armor."
  }
}

run "egress_scope_auto_at_tier_5_screens_mcp_servers" {
  command = apply

  variables {
    enable_ingress_gateway = true
  }

  assert {
    condition     = output.model_armor_egress_scope == "mcp_servers"
    error_message = "At Tier 5, auto must resolve to mcp_servers."
  }

  assert {
    condition     = contains(google_network_security_authz_policy.model_armor[0].http_rules[0].to[0].operations[0].hosts[*].exact, "geap-work-items-example.a.run.app")
    error_message = "mcp_servers must list the starter pack MCP server host."
  }
}

run "egress_scope_all_egress_at_tier_5" {
  command = plan

  variables {
    enable_ingress_gateway   = true
    model_armor_egress_scope = "all_egress"
  }

  assert {
    condition     = length(google_network_security_authz_policy.model_armor[0].http_rules) == 0
    error_message = "An explicit all_egress must have no host rule."
  }
}

run "egress_scope_rejects_unknown_value" {
  command = plan

  variables {
    model_armor_egress_scope = "everything"
  }

  expect_failures = [var.model_armor_egress_scope]
}
