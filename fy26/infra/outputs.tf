output "resource_group_name" {
  value = local.rg_name
}

output "foundry_account_name" {
  value = azurerm_cognitive_account.foundry.name
}

output "foundry_project_endpoint" {
  value = local.foundry_project_endpoint
}

output "foundry_openai_endpoint" {
  value = local.foundry_openai_endpoint
}

output "chat_deployment" {
  value = azurerm_cognitive_deployment.chat.name
}

output "embedding_deployment" {
  value = azurerm_cognitive_deployment.embedding.name
}

output "acr_name" {
  value = azurerm_container_registry.this.name
}

output "acr_login_server" {
  value = azurerm_container_registry.this.login_server
}

output "container_app_name" {
  value = "ca-${local.name}"
}

output "app_url" {
  value = var.image_tag == "" ? "" : "https://${azurerm_container_app.this[0].ingress[0].fqdn}"
}

output "student_id" {
  value = var.student_id
}

output "log_analytics_workspace_id" {
  description = "Workspace GUID for: az monitor log-analytics query -w <id> --analytics-query '<KQL>'"
  value       = azurerm_log_analytics_workspace.this.workspace_id
}

output "applicationinsights_connection_string" {
  value     = azurerm_application_insights.this.connection_string
  sensitive = true
}
