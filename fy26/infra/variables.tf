variable "subscription_id" {
  description = "Azure subscription to deploy into. Find it with: az account show --query id -o tsv"
  type        = string
}

variable "student_id" {
  description = "Your NetID (or any short id). Used in resource names and returned by /v1/info."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.student_id))
    error_message = "student_id must be 3-12 lowercase letters or digits, starting with a letter."
  }
}

variable "location" {
  description = "Azure region for every resource. The model deployments below must be available there."
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Resource group to deploy into. Leave empty to use rg-nu-<student_id>."
  type        = string
  default     = ""
}

variable "create_resource_group" {
  description = "Create the resource group (true) or use one that already exists (false)."
  type        = bool
  default     = true
}

variable "chat_model" {
  description = "Chat model deployment. capacity is in thousands of tokens per minute."
  type = object({
    name     = string
    version  = string
    capacity = number
  })
  default = {
    name     = "gpt-5.4-mini"
    version  = "2026-03-17"
    capacity = 100
  }
}

variable "embedding_model" {
  description = "Embedding model deployment used for retrieval (Week 6 onward)."
  type = object({
    name     = string
    version  = string
    capacity = number
  })
  default = {
    name     = "text-embedding-3-small"
    version  = "1"
    capacity = 100
  }
}

variable "image_tag" {
  description = "Tag of the app image in your registry. Empty means: create the platform only, no Container App yet."
  type        = string
  default     = ""

  validation {
    condition     = var.image_tag == "" || can(regex("^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid container image tag."
  }
}

variable "service_api_key" {
  description = "Optional API key the service requires on /v1 routes (Week 10). Empty disables the check."
  type        = string
  default     = ""
  sensitive   = true
}

variable "tags" {
  description = "Extra tags added to every resource."
  type        = map(string)
  default     = {}
}
