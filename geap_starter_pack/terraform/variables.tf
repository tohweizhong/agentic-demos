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
