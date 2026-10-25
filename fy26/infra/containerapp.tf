resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.name}"
  resource_group_name        = local.rg_name
  location                   = var.location
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = local.tags

  # Azure adds a "Consumption" workload profile by itself. Ignoring it keeps every plan clean.
  lifecycle {
    ignore_changes = [workload_profile]
  }
}

# The app is created only once an image exists (var.image_tag set).
# Every deployment = build a new image tag, then terraform apply with that tag.
resource "azurerm_container_app" "this" {
  count = var.image_tag == "" ? 0 : 1

  name                         = "ca-${local.name}"
  resource_group_name          = local.rg_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = local.tags

  lifecycle {
    ignore_changes = [workload_profile_name]
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  dynamic "secret" {
    for_each = var.service_api_key == "" ? [] : [1]
    content {
      name  = "service-api-key"
      value = var.service_api_key
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 2

    http_scale_rule {
      name                = "http"
      concurrent_requests = "20"
    }

    container {
      name   = "app"
      image  = "${azurerm_container_registry.this.login_server}/app:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
      env {
        name  = "FOUNDRY_PROJECT_ENDPOINT"
        value = local.foundry_project_endpoint
      }
      env {
        name  = "FOUNDRY_OPENAI_ENDPOINT"
        value = local.foundry_openai_endpoint
      }
      env {
        name  = "FOUNDRY_MODEL"
        value = azurerm_cognitive_deployment.chat.name
      }
      env {
        name  = "FOUNDRY_EMBEDDING_MODEL"
        value = azurerm_cognitive_deployment.embedding.name
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.this.connection_string
      }
      env {
        name  = "STUDENT_ID"
        value = var.student_id
      }
      env {
        name  = "APP_VERSION"
        value = var.image_tag
      }
      env {
        name  = "PUBLIC_HOSTNAME"
        value = "ca-${local.name}.${azurerm_container_app_environment.this.default_domain}"
      }
      dynamic "env" {
        for_each = var.service_api_key == "" ? [] : [1]
        content {
          name        = "SERVICE_API_KEY"
          secret_name = "service-api-key"
        }
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/health"
        initial_delay           = 5
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/ready"
        interval_seconds        = 10
        failure_count_threshold = 3
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.app_acr_pull,
    azurerm_role_assignment.app_foundry_user,
  ]
}
