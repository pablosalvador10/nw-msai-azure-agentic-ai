variable "subscription_id" {
  description = "Azure subscription for the course website. Find it with: az account show --query id -o tsv"
  type        = string
}

variable "location" {
  description = "Azure region for every resource."
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Resource group for the website. Terraform creates it."
  type        = string
  default     = "lectures"
}

variable "github_client_id" {
  description = "Client ID of the GitHub App students sign in with. Empty until you create the app (see web/README.md)."
  type        = string
  default     = ""
}

variable "github_client_secret" {
  description = "A client secret of that GitHub App. Stored as a Container App secret, never in the image."
  type        = string
  default     = ""
  sensitive   = true
}

variable "course_repo" {
  description = "owner/name of the course repository. Whoever can read it can use the website."
  type        = string
  default     = "pablosalvador10/northwestern-msai-azure-agentic-ai"

  validation {
    condition     = can(regex("^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$", var.course_repo))
    error_message = "course_repo must look like owner/name."
  }
}

variable "course_ref" {
  description = "Branch that links to labs, READMEs and code open on GitHub."
  type        = string
  default     = "main"
}

variable "image_tag" {
  description = "Tag of the website image in the registry. Empty means: platform only, no Container App yet."
  type        = string
  default     = ""

  validation {
    condition     = var.image_tag == "" || can(regex("^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid container image tag."
  }
}

variable "min_replicas" {
  description = "0 scales to zero when idle (first visit waits ~15 s). 1 keeps the site warm during the term."
  type        = number
  default     = 0

  validation {
    condition     = contains([0, 1], var.min_replicas)
    error_message = "min_replicas must be 0 or 1: harness runs live in one replica's memory."
  }
}

variable "tags" {
  description = "Extra tags added to every resource."
  type        = map(string)
  default     = {}
}
