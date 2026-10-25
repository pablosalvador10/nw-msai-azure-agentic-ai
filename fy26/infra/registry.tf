resource "azurerm_container_registry" "this" {
  name                = "acr${replace(local.name, "-", "")}"
  resource_group_name = local.rg_name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}
