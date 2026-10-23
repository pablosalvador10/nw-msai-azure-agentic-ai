# infra · Terraform for your resource group

Terraform reads the `.tf` files in this folder, compares them with what exists in Azure, and makes Azure match. You describe the end state; Terraform works out the steps.

## Files

| File | What it declares |
|---|---|
| `providers.tf` | Terraform and provider versions; which Azure subscription; which resource providers to register |
| `variables.tf` | Inputs: your `student_id`, region, model choices, image tag. Each has a description and, where useful, validation |
| `main.tf` | Naming rules, tags, and the resource group |
| `foundry.tf` | Microsoft Foundry: the AI Services account, your project, the chat and embedding deployments |
| `registry.tf` | Azure Container Registry for your images |
| `identity.tf` | The app's managed identity and its role assignments (pull images, call models), plus your own model access |
| `containerapp.tf` | Container Apps environment and the app itself (ingress, scale, probes, environment variables) |
| `monitoring.tf` | Log Analytics workspace and Application Insights |
| `outputs.tf` | Values the rest of the course reads: endpoints, names, the app URL |

Your inputs live in `terraform.tfvars` (written by the setup notebook) and `image.auto.tfvars` (written by `course.deploy()`). Both are gitignored, as is the state file `terraform.tfstate`, which records what Terraform created.

## Commands (run from `fy26/`)

```bash
terraform -chdir=infra init        # download the azurerm provider
terraform -chdir=infra plan        # show what would change
terraform -chdir=infra apply       # make the changes (asks for confirmation)
terraform -chdir=infra output      # print the outputs
terraform -chdir=infra destroy     # delete everything (end of course)
```

## Design choices worth noticing

- **No keys anywhere.** `local_auth_enabled = false` turns off API keys on Foundry. The app authenticates with a managed identity; you authenticate with `az login`. Access is granted by role assignments in `identity.tf`.
- **Infrastructure and releases are separate.** The Container App exists only once `image_tag` is set. A release is: build a new image tag, then `terraform apply` with that tag. Terraform stays the single source of truth for what runs.
- **Stable names.** A six-character suffix derived from your subscription, resource group and `student_id` makes names globally unique and identical on every apply.
- **Scale to zero.** `min_replicas = 0` means you pay nothing while nobody calls the service. The price is a slow first request after idle time.
- **Health probes.** Liveness hits `/health` (is the process alive?), readiness hits `/ready` (can it serve?). Without them, Container Apps only checks that the port is open.

## Learn more

- [Terraform on Azure documentation](https://learn.microsoft.com/en-us/azure/developer/terraform/)
- [azurerm provider documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Role-based access control for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry)
- [Image pull from Azure Container Registry with managed identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull)
- [Health probes in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/health-probes)
