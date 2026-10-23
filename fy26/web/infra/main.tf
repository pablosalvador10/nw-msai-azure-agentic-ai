locals {
  # Stable 6-character suffix: same subscription and group, same names, on every apply.
  suffix = substr(sha1("${var.subscription_id}/${var.resource_group_name}"), 0, 6)
  name   = "lectures-${local.suffix}"

  tags = merge(var.tags, {
    course     = "northwestern-msai-fy26"
    component  = "lectures"
    managed-by = "terraform"
  })
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}
