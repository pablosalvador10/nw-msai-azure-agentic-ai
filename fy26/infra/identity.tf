# One identity for the app: it pulls the image from the registry and calls Foundry.
# No passwords or keys anywhere; Azure issues short-lived tokens to this identity.

resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${local.name}"
  resource_group_name = local.rg_name
  location            = var.location
  tags                = local.tags
}

locals {
  # Built-in role IDs. Microsoft is renaming "Azure AI User" to "Foundry User"; the ID is stable.
  role_foundry_user = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"
  role_acr_pull     = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d"
}

resource "azurerm_role_assignment" "app_acr_pull" {
  scope              = azurerm_container_registry.this.id
  role_definition_id = local.role_acr_pull
  principal_id       = azurerm_user_assigned_identity.app.principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_role_assignment" "app_foundry_user" {
  scope              = azurerm_cognitive_account.foundry.id
  role_definition_id = local.role_foundry_user
  principal_id       = azurerm_user_assigned_identity.app.principal_id
  principal_type     = "ServicePrincipal"
}

# You (whoever runs terraform apply) also get Foundry User, so notebooks can call the models.
resource "azurerm_role_assignment" "me_foundry_user" {
  scope              = azurerm_cognitive_account.foundry.id
  role_definition_id = local.role_foundry_user
  principal_id       = data.azurerm_client_config.current.object_id
}
