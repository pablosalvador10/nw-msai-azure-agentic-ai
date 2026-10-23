resource "azurerm_container_registry" "this" {
  name                = "acr${replace(local.name, "-", "")}"
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}
