variable "project_id" {
  description = "The ID of the sandbox project for the mini build."
  type        = string
}

variable "project_number" {
  description = "The project number of the sandbox project. Get it with: gcloud projects describe PROJECT_ID --format='value(projectNumber)'."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.project_number))
    error_message = "project_number must be the numeric project number."
  }
}

variable "organization_id" {
  description = "The numeric ID of the organization of the project. Agent Identity principals use it in the trust domain."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.organization_id))
    error_message = "organization_id must be the numeric organization ID."
  }
}

variable "region" {
  description = "The region for the mini build. The agent, the gateway, and the registry must be in the same region."
  type        = string
  default     = "us-central1"
}

variable "name_prefix" {
  description = "The prefix for the resource names. Use lowercase letters, numbers, and hyphens."
  type        = string
  default     = "geap"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}$", var.name_prefix))
    error_message = "name_prefix must start with a letter and have 2 to 15 lowercase letters, numbers, or hyphens."
  }
}

variable "enable_agent_registry" {
  description = "Tier 2 (Catalog and Discovery): if true, Terraform registers the sample MCP server and the platform API endpoints in Agent Registry."
  type        = bool
  default     = true
}

variable "enable_egress_gateway" {
  description = "Tier 3 (Outbound Access Control): if true, Terraform deploys the Agent-to-Anywhere (egress) gateway and the IAP V2 policy. Set to false to deploy without an egress gateway."
  type        = bool
  default     = true

  # Terraform 1.9 and later can compare two variables in one validation.
  validation {
    condition     = !var.enable_egress_gateway || var.enable_agent_registry
    error_message = "Tier 3 needs Tier 2. The IAP rules match tools by their Agent Registry name. Set enable_agent_registry = true, or set enable_egress_gateway = false."
  }
}

variable "enable_model_armor" {
  description = "Tier 4 (Content Safety): if true, Terraform deploys the Model Armor templates, the CONTENT_AUTHZ extension, and the three IAM bindings on the gateway Service Extensions service account."
  type        = bool
  default     = true

  validation {
    condition     = !var.enable_model_armor || var.enable_egress_gateway
    error_message = "Tier 4 needs Tier 3. Terraform reads the gateway Service Extensions service account for the three Model Armor roles from the egress gateway. The ingress gateway does not return it. Set enable_egress_gateway = true, or set enable_model_armor = false."
  }
}

variable "enable_ingress_gateway" {
  description = "Tier 5 (Inbound Client Control): if true, Terraform deploys the Client-to-Agent (ingress) gateway and binds it to the agent."
  type        = bool
  default     = false
}

variable "iap_enforcement_mode" {
  description = "The mode of the IAP gateway policy. DRY_RUN logs the decision and does not block. ENFORCE blocks a call that the policy does not allow."
  type        = string
  default     = "DRY_RUN"

  validation {
    condition     = contains(["DRY_RUN", "ENFORCE"], var.iap_enforcement_mode)
    error_message = "iap_enforcement_mode must be DRY_RUN or ENFORCE."
  }
}

variable "authz_fail_open" {
  description = "If true, the gateway lets a call pass when an authz extension does not answer in time. The target design uses false (fail closed)."
  type        = bool
  default     = false
}

variable "authz_timeout" {
  description = "The timeout for each call from the gateway to an authz extension. The value must be from 10ms to 10s."
  type        = string
  default     = "2s"
}

variable "model_id" {
  description = "The Gemini model that the reference agent uses."
  type        = string
  default     = "gemini-3.8-flash"
}

variable "model_location" {
  description = "The location of the Gemini model endpoint."
  type        = string
  default     = "global"
}

variable "log_retention_days" {
  description = "The number of days that the regional log bucket keeps the gateway and IAP logs."
  type        = number
  default     = 30
}

variable "extra_api_hosts" {
  description = "More API hosts that the agent calls through the gateway. The gateway matches each host exactly. The standard Google API hosts for the region are in registry.tf."
  type        = list(string)
  default     = []
}

variable "allow_google_managed_members" {
  description = "If true, Terraform sets a project-level exception to the domain restricted sharing policy. The gateway Model Armor grants need it. In a customer organization, the organization admin must approve this exception."
  type        = bool
  default     = false
}

variable "drs_exception_allowed_values" {
  description = "Values that the project exception adds to iam.allowedPolicyMemberDomains when allow_google_managed_members is true. is:C02h8e9nw is the Google customer ID that owns tenant-project service agents."
  type        = list(string)
  default     = ["is:C02h8e9nw"]
}

variable "existing_mcp_servers" {
  description = "Lateral path, Tier 2: MCP servers that already exist in the project and must be registered in Agent Registry. Key: short name (lowercase letters, numbers, hyphens). url: the MCP endpoint. tool_spec_file: path to a tool spec JSON file, relative to the terraform folder or absolute."
  type = map(object({
    url            = string
    tool_spec_file = string
    display_name   = optional(string)
  }))
  default = {}

  validation {
    condition     = alltrue([for k, v in var.existing_mcp_servers : can(regex("^[a-z][a-z0-9-]{0,20}$", k)) && startswith(v.url, "https://")])
    error_message = "Each key must be lowercase letters, numbers, or hyphens (up to 21 characters), and each url must start with https://."
  }
}

variable "agent_source_archive" {
  description = "The path of the agent source archive, relative to this folder. scripts/package_agent.sh writes it."
  type        = string
  default     = "build/agent_source.tar.gz"
}

variable "build_mcp_image" {
  description = "If true, Terraform builds the MCP server image with Cloud Build when the source changes. The offline tests set it to false."
  type        = bool
  default     = true
}
