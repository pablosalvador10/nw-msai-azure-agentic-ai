# Microsoft Foundry = an AI Services account (the resource) + a project (your workspace)
# + model deployments (the models your code calls by name).

resource "azurerm_cognitive_account" "foundry" {
  name                       = "aif-${local.name}"
  resource_group_name        = local.rg_name
  location                   = var.location
  kind                       = "AIServices"
  sku_name                   = "S0"
  custom_subdomain_name      = "aif-${local.name}"
  project_management_enabled = true
  local_auth_enabled         = false # Entra ID only: no API keys to leak.
  tags                       = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_account_project" "this" {
  name                 = "proj-${var.student_id}"
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = var.location
  display_name         = "Northwestern FY26 (${var.student_id})"
  description          = "Course project: agentic AI on Microsoft Foundry."
  tags                 = local.tags

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_cognitive_deployment" "chat" {
  name                 = var.chat_model.name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.chat_model.name
    version = var.chat_model.version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.chat_model.capacity
  }
}

resource "azurerm_cognitive_deployment" "embedding" {
  name                 = var.embedding_model.name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.embedding_model.name
    version = var.embedding_model.version
  }

  sku {
    name     = "GlobalStandard"
    capacity = var.embedding_model.capacity
  }

  # An account accepts one deployment change at a time.
  depends_on = [azurerm_cognitive_deployment.chat]
}

locals {
  foundry_host             = "aif-${local.name}"
  foundry_project_endpoint = "https://${local.foundry_host}.services.ai.azure.com/api/projects/${azurerm_cognitive_account_project.this.name}"
  foundry_openai_endpoint  = "https://${local.foundry_host}.openai.azure.com/openai/v1/"
}
