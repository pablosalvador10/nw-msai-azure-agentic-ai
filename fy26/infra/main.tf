data "azurerm_client_config" "current" {}

locals {
  resource_group_name = var.resource_group_name != "" ? var.resource_group_name : "rg-nu-${var.student_id}"

  # Stable 6-character suffix: same inputs, same names, on every apply.
  suffix = substr(sha1("${var.subscription_id}/${local.resource_group_name}/${var.student_id}"), 0, 6)
  name   = "${var.student_id}-${local.suffix}"

  tags = merge(var.tags, {
    course     = "northwestern-msai-fy26"
    student    = var.student_id
    managed-by = "terraform"
  })
}

resource "azurerm_resource_group" "this" {
  count    = var.create_resource_group ? 1 : 0
  name     = local.resource_group_name
  location = var.location
  tags     = local.tags
}

data "azurerm_resource_group" "existing" {
  count = var.create_resource_group ? 0 : 1
  name  = local.resource_group_name
}

locals {
  rg_name = var.create_resource_group ? azurerm_resource_group.this[0].name : data.azurerm_resource_group.existing[0].name
}
