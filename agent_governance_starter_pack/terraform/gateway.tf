# Component 3 (control): the egress and ingress Agent Gateways, the IAP policy
# (version V2), and Model Armor. The policy files are in ../policies so that a
# security reviewer can read them without the Terraform.

locals {
  gateway_name         = "${var.name_prefix}-egress"
  ingress_gateway_name = "${var.name_prefix}-ingress"
  any_gateway_enabled  = var.enable_egress_gateway || var.enable_ingress_gateway
  model_armor_enabled  = var.enable_model_armor && local.any_gateway_enabled

  # Scope of egress Model Armor (backlog item 37). auto: at Tier 5 the ingress
  # gateway screens user prompts and agent replies, so egress screens only the
  # MCP servers. At Tier 4 nothing else screens prompts, so egress screens all
  # egress traffic, including model calls.
  model_armor_egress_scope = var.model_armor_egress_scope != "auto" ? var.model_armor_egress_scope : (
    var.enable_ingress_gateway ? "mcp_servers" : "all_egress"
  )
  mcp_server_hosts = distinct(concat(
    [for u in concat([google_cloud_run_v2_service.mcp.uri], coalesce(google_cloud_run_v2_service.mcp.urls, [])) : trimprefix(u, "https://")],
    [for k, v in var.existing_mcp_servers : regex("^https://([^/:]+)", v.url)[0]],
  ))

  iap_policy = yamldecode(templatefile("${path.module}/../policies/iap_access_policy.yaml", {
    region      = var.region
    name_prefix = var.name_prefix
  }))

  model_armor = yamldecode(file(var.model_armor_policy_file != "" ? var.model_armor_policy_file : "${path.module}/../policies/model_armor.yaml"))
  # Optional request: and response: sections override the shared settings for one
  # template (backlog item 38). A missing section uses the shared settings.
  # malicious_uri is shared only, because the region decides if it is supported.
  model_armor_shared = { for k, v in local.model_armor : k => v if !contains(["request", "response"], k) }
  model_armor_side = {
    request  = merge(local.model_armor_shared, try(local.model_armor.request, {}))
    response = merge(local.model_armor_shared, try(local.model_armor.response, {}))
  }

  # IAP enforces when iamEnforcementMode is not set. Only DRY_RUN changes it.
  iap_extension_metadata = merge(
    { iapPolicyVersion = "V2" },
    var.iap_enforcement_mode == "DRY_RUN" ? { iamEnforcementMode = "DRY_RUN" } : {},
  )
}

resource "google_network_services_agent_gateway" "egress" {
  count = var.enable_egress_gateway ? 1 : 0

  project     = var.project_id
  name        = local.gateway_name
  location    = var.region
  description = "Egress gateway for the agent governance starter pack mini build."
  labels      = local.labels

  google_managed {
    governed_access_path = "AGENT_TO_ANYWHERE"
  }

  # The gateway governs the destinations in this registry.
  registries = ["//agentregistry.googleapis.com/projects/${var.project_id}/locations/${var.region}"]

  depends_on = [google_project_service.this]
}

moved {
  from = google_network_services_agent_gateway.egress
  to   = google_network_services_agent_gateway.egress[0]
}

# The gateway control plane needs a short time before policies can attach.
resource "time_sleep" "gateway_ready" {
  count = var.enable_egress_gateway ? 1 : 0

  create_duration = "30s"
  depends_on      = [google_network_services_agent_gateway.egress]
}

moved {
  from = time_sleep.gateway_ready
  to   = time_sleep.gateway_ready[0]
}

# IAP REQUEST_AUTHZ extension. The gateway asks IAP for a decision on each call.
resource "google_network_services_authz_extension" "iap" {
  count = var.enable_egress_gateway ? 1 : 0

  project     = var.project_id
  name        = "${local.gateway_name}-iap-authz"
  location    = var.region
  description = "IAP authorization (policy version V2) for agent egress."
  labels      = local.labels
  service     = "iap.googleapis.com"
  timeout     = var.authz_timeout
  fail_open   = var.authz_fail_open
  metadata    = local.iap_extension_metadata

  depends_on = [google_project_service.this]
}

moved {
  from = google_network_services_authz_extension.iap
  to   = google_network_services_authz_extension.iap[0]
}

resource "google_network_security_authz_policy" "iap" {
  count = var.enable_egress_gateway ? 1 : 0

  project        = var.project_id
  name           = "${local.gateway_name}-iap-policy"
  location       = var.region
  description    = "Sends each agent egress call to the IAP authz extension."
  labels         = local.labels
  policy_profile = "REQUEST_AUTHZ"
  action         = "CUSTOM"

  target {
    resources = [google_network_services_agent_gateway.egress[0].id]
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.iap[0].id]
    }
  }

  depends_on = [time_sleep.gateway_ready]
}

moved {
  from = google_network_security_authz_policy.iap
  to   = google_network_security_authz_policy.iap[0]
}

# IAM access policy (Unified Access Policy, IAP policy V2). The rules come from
# ../policies/iap_access_policy.yaml. The principal is the reference agent only.
resource "google_iam_project_access_policy" "agent_egress" {
  count = var.enable_egress_gateway ? 1 : 0

  project          = var.project_id
  location         = "global"
  access_policy_id = local.iap_policy.access_policy_id
  display_name     = local.iap_policy.display_name

  details {
    dynamic "rules" {
      for_each = local.iap_policy.rules
      content {
        description = rules.value.description
        effect      = rules.value.effect
        principals  = concat([local.agent_principal], var.existing_agent_principals)

        operation {
          permissions = ["iap.googleapis.com/resources.egressViaIAP"]
        }

        conditions {
          service    = "iap.googleapis.com"
          expression = rules.value.expression
        }
      }
    }
  }

  depends_on = [google_project_service.this]
}

moved {
  from = google_iam_project_access_policy.agent_egress
  to   = google_iam_project_access_policy.agent_egress[0]
}

resource "google_iam_projects_policy_binding" "agent_egress" {
  count = var.enable_egress_gateway ? 1 : 0

  project           = var.project_id
  location          = "global"
  policy_binding_id = "${var.name_prefix}-agent-egress"
  display_name      = "GEAP mini build agent egress"
  policy_kind       = "ACCESS"
  policy            = "projects/${var.project_id}/locations/global/accessPolicies/${google_iam_project_access_policy.agent_egress[0].access_policy_id}"

  target {
    resource = "//cloudresourcemanager.googleapis.com/projects/${var.project_id}"
  }
}

moved {
  from = google_iam_projects_policy_binding.agent_egress
  to   = google_iam_projects_policy_binding.agent_egress[0]
}

# Model Armor templates in the regional endpoint. The settings come from
# ../policies/model_armor.yaml.
resource "google_model_armor_template" "this" {
  for_each = local.model_armor_enabled ? toset(["request", "response"]) : toset([])

  project     = var.project_id
  location    = var.region
  template_id = "${var.name_prefix}-agw-${each.key}"
  labels      = local.labels

  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = local.model_armor_side[each.key].prompt_injection_and_jailbreak.enforcement
      confidence_level   = local.model_armor_side[each.key].prompt_injection_and_jailbreak.confidence_level
    }

    # Some regions (for example asia-southeast1) reject this field, also with
    # DISABLED (Error 400 CAPABILITY_NOT_SUPPORTED). Send it only when enabled.
    dynamic "malicious_uri_filter_settings" {
      for_each = try(local.model_armor.malicious_uri.enforcement, "DISABLED") == "ENABLED" ? [1] : []
      content {
        filter_enforcement = "ENABLED"
      }
    }

    sdp_settings {
      basic_config {
        filter_enforcement = local.model_armor_side[each.key].sensitive_data_protection_basic.enforcement
      }
    }

    rai_settings {
      dynamic "rai_filters" {
        for_each = local.model_armor_side[each.key].responsible_ai
        content {
          filter_type      = rai_filters.value.filter_type
          confidence_level = rai_filters.value.confidence_level
        }
      }
    }
  }

  template_metadata {
    enforcement_type = local.model_armor_side[each.key].enforcement_type
  }

  depends_on = [google_project_service.this]
}

# Model Armor CONTENT_AUTHZ extension. The gateway sends prompts and tool
# responses to Model Armor.
resource "google_network_services_authz_extension" "model_armor" {
  count = local.model_armor_enabled ? 1 : 0

  project     = var.project_id
  name        = "${local.gateway_name}-ma-authz"
  location    = var.region
  description = "Model Armor content checks for agent egress."
  labels      = local.labels
  service     = "modelarmor.${var.region}.rep.googleapis.com"
  timeout     = var.authz_timeout
  fail_open   = var.authz_fail_open

  metadata = {
    model_armor_settings = jsonencode([{
      request_template_id  = google_model_armor_template.this["request"].id
      response_template_id = google_model_armor_template.this["response"].id
    }])
  }
}

moved {
  from = google_network_services_authz_extension.model_armor
  to   = google_network_services_authz_extension.model_armor[0]
}

resource "google_network_security_authz_policy" "model_armor" {
  count = var.enable_egress_gateway && var.enable_model_armor ? 1 : 0

  project        = var.project_id
  name           = "${local.gateway_name}-ma-policy"
  location       = var.region
  description    = "Sends agent egress content to the Model Armor extension."
  labels         = local.labels
  policy_profile = "CONTENT_AUTHZ"
  action         = "CUSTOM"

  target {
    resources = [google_network_services_agent_gateway.egress[0].id]
  }

  # mcp_servers scope: only traffic to the MCP server hosts goes to Model Armor.
  # all_egress scope: no rule, so all egress traffic goes to Model Armor.
  dynamic "http_rules" {
    for_each = local.model_armor_egress_scope == "mcp_servers" ? [1] : []
    content {
      to {
        operations {
          dynamic "hosts" {
            for_each = local.mcp_server_hosts
            content {
              exact = hosts.value
            }
          }
        }
      }
    }
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.model_armor[0].id]
    }
  }

  # Create the policies one at a time. The gateway accepts one change at a time.
  depends_on = [google_network_security_authz_policy.iap]
}

moved {
  from = google_network_security_authz_policy.model_armor
  to   = google_network_security_authz_policy.model_armor[0]
}

# The gateway calls Model Armor as its Service Extensions service account. That
# account is in a Google-managed project.
resource "google_project_iam_member" "gateway_model_armor" {
  for_each = var.enable_egress_gateway && var.enable_model_armor ? toset([
    "roles/modelarmor.calloutUser",
    "roles/modelarmor.user",
    "roles/serviceusage.serviceUsageConsumer",
  ]) : toset([])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_network_services_agent_gateway.egress[0].agent_gateway_card[0].service_extensions_service_account}"

  depends_on = [
    google_org_policy_policy.allow_google_managed_members,
    time_sleep.org_policy_ready,
  ]
}

# Client-to-Agent (ingress) gateway. It screens incoming prompts and outgoing
# agent answers with Model Armor.
resource "google_network_services_agent_gateway" "ingress" {
  count = var.enable_ingress_gateway ? 1 : 0

  project     = var.project_id
  name        = local.ingress_gateway_name
  location    = var.region
  description = "Ingress gateway for the agent governance starter pack mini build."
  labels      = local.labels

  google_managed {
    governed_access_path = "CLIENT_TO_AGENT"
  }

  depends_on = [google_project_service.this]
}

resource "time_sleep" "ingress_gateway_ready" {
  count = var.enable_ingress_gateway ? 1 : 0

  create_duration = "30s"
  depends_on      = [google_network_services_agent_gateway.ingress]
}

resource "google_network_security_authz_policy" "ingress_model_armor" {
  count = var.enable_ingress_gateway && var.enable_model_armor ? 1 : 0

  project        = var.project_id
  name           = "${local.ingress_gateway_name}-ma-policy"
  location       = var.region
  description    = "Sends client-to-agent content to the Model Armor extension."
  labels         = local.labels
  policy_profile = "CONTENT_AUTHZ"
  action         = "CUSTOM"

  target {
    resources = [google_network_services_agent_gateway.ingress[0].id]
  }

  custom_provider {
    authz_extension {
      resources = [google_network_services_authz_extension.model_armor[0].id]
    }
  }

  depends_on = [time_sleep.ingress_gateway_ready]
}

