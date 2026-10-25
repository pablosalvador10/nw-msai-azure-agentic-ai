resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${local.name}"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = var.location
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = local.tags
}

locals {
  # Known before the app exists, so the GitHub App's callback URL can be set up first.
  site_url = "https://ca-${local.name}.${azurerm_container_app_environment.this.default_domain}"
}

# Created once an image exists (var.image_tag set). web/publish.py builds a tag and applies it.
resource "azurerm_container_app" "site" {
  count = var.image_tag == "" ? 0 : 1

  name                         = "ca-${local.name}"
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.site.id]
  }

  registry {
    server   = azurerm_container_registry.this.login_server
    identity = azurerm_user_assigned_identity.site.id
  }

  secret {
    name  = "github-client-secret"
    value = var.github_client_secret
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
    # One replica at most: the queue of harness runs lives in that replica's memory.
    min_replicas = var.min_replicas
    max_replicas = 1

    container {
      name   = "site"
      image  = "${azurerm_container_registry.this.login_server}/lectures:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "LECTURES_PUBLIC_URL"
        value = local.site_url
      }
      env {
        name  = "LECTURES_VERSION"
        value = var.image_tag
      }
      env {
        name  = "LECTURES_GITHUB_CLIENT_ID"
        value = var.github_client_id
      }
      env {
        name        = "LECTURES_GITHUB_CLIENT_SECRET"
        secret_name = "github-client-secret"
      }
      env {
        name  = "LECTURES_COURSE_REPO"
        value = var.course_repo
      }
      env {
        name  = "LECTURES_COURSE_REF"
        value = var.course_ref
      }

      liveness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/healthz"
        initial_delay           = 5
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        transport               = "HTTP"
        port                    = 8000
        path                    = "/healthz"
        interval_seconds        = 10
        failure_count_threshold = 3
      }
    }
  }

  lifecycle {
    precondition {
      condition     = var.github_client_id != "" && var.github_client_secret != ""
      error_message = "Set github_client_id and github_client_secret in terraform.tfvars before deploying an image (web/README.md, step 2)."
    }
  }

  depends_on = [azurerm_role_assignment.site_acr_pull]
}
