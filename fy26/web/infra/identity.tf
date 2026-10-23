# The website's identity: it pulls the image from the registry. It needs nothing else in Azure.

resource "azurerm_user_assigned_identity" "site" {
  name                = "id-${local.name}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "site_acr_pull" {
  scope = azurerm_container_registry.this.id
  # AcrPull (built-in role)
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/7f951dda-4ed3-4680-a7ca-43fe172d538d"
  principal_id       = azurerm_user_assigned_identity.site.principal_id
  principal_type     = "ServicePrincipal"
}
