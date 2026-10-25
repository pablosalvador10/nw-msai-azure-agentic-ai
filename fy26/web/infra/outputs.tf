output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "container_app_name" {
  value = "ca-${local.name}"
}

output "site_url" {
  description = "The course website. Share this link with students."
  value       = local.site_url
}

output "github_callback_url" {
  description = "Paste into the GitHub App: Callback URL."
  value       = "${local.site_url}/auth/callback"
}
