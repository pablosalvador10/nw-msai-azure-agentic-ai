# Quick Start Guide

Get your local environment ready to run the labs.

## Prerequisites

- [VS Code](https://code.visualstudio.com/) with the [Jupyter extension](https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter)
- [uv](https://docs.astral.sh/uv/) — fast Python package manager
- Python 3.10+ installed

## Step 1: Install uv

### macOS/Linux/WSL

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### macOS (Homebrew alternative)

```bash
brew install uv
```

### Windows (PowerShell)

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Step 2: Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/pablosalvador10/nw-msai-azure-agentic-ai.git
cd nw-msai-azure-agentic-ai/fy25

# Install Python versions (optional - uv will auto-install if needed)
uv python install 3.10 3.11 3.12

# Create a virtual environment (defaults to Python 3.11)
uv venv

# Install all dependencies
uv sync --all-extras --dev

# Install pre-commit hooks (optional but recommended)
uv run pre-commit install
```

### One-Command Setup

If you already have uv installed, you can run the full setup with poe:

```bash
uv sync --all-extras --dev
uv run poe setup
```

## Step 3: Configure Your .env File

Create your `.env` file with your Azure credentials:

```bash
cp .env.example .env
```

**You only need to fill in the variables for the lab you're working on:**

| Lab | Variables Needed |
|-----|------------------|
| Lab 1 | `AZURE_FUNCTION_URL`, `AZURE_FUNCTION_KEY` |
| Lab 2 | `LOGIC_APP_URL` |
| Lab 3-8 | `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `AZURE_OPENAI_ENDPOINT`, `AZURE_AI_API_KEY` |
| Lab 4 | Uses `azd` to manage environment variables automatically |

Open `.env` and fill in what you need:

```bash
# Azure AI Foundry (Lab 3-8)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_AI_API_KEY=your-api-key

# Azure Functions (Lab 1)
# AZURE_FUNCTION_URL=https://your-function-app.azurewebsites.net/api/analyze_data
# AZURE_FUNCTION_KEY=your-function-key-here

# Logic Apps (Lab 2)
# LOGIC_APP_URL=https://prod-xx.eastus.logic.azure.com/workflows/...
```

## Step 4: Open in VS Code

```bash
code .
```

1. Open any notebook in the `notebooks/` folder
2. VS Code will prompt you to select a kernel — choose the `.venv` Python environment
3. You're ready to run cells!

## Available Poe Tasks

We use [poethepoet](https://poethepoet.natn.io/) for task management. Run tasks with `uv run poe <task>`:

### Setup and Installation

| Command | Description |
|---------|-------------|
| `uv run poe setup` | Full setup: venv, install deps, pre-commit hooks |
| `uv run poe venv` | Create virtual environment |
| `uv run poe install` | Install all dependencies |
| `uv run poe pre-commit-install` | Install pre-commit hooks |

### Code Quality

| Command | Description |
|---------|-------------|
| `uv run poe fmt` | Format code with ruff |
| `uv run poe lint` | Run linting and fix issues |
| `uv run poe pyright` | Run Pyright type checking |
| `uv run poe mypy` | Run MyPy type checking |
| `uv run poe check` | Run ALL checks (fmt, lint, pyright, test) |

### Testing

| Command | Description |
|---------|-------------|
| `uv run poe test` | Run all tests with coverage |
| `uv run poe test-unit` | Run only unit tests |
| `uv run poe test-integration` | Run integration tests |

### Cleanup

| Command | Description |
|---------|-------------|
| `uv run poe clean` | Clean cache and build files |

## LLM Setup

Make sure you have an Azure OpenAI service key. The notebooks use `python-dotenv` to load keys from your `.env` file automatically.

When using VSCode with the Python extension, it automatically loads environment variables from `.env`, so you don't need to manually set them.

## Switching Python Versions

To switch to a different Python version:

```bash
# Create venv with specific Python version
uv venv --python 3.12

# Reinstall dependencies
uv sync --all-extras --dev
```

## Next Steps

Each lab will guide you through the Azure services you need:

| Lab | Azure Services Required |
|-----|------------------------|
| [Lab 1: Azure Functions](../notebooks/lab1_azure_functions.ipynb) | Azure Function App |
| [Lab 2: Logic Apps](../notebooks/lab2_logic_apps.ipynb) | Azure Logic App |
| [Lab 3: Single Agent Tool Calling](../notebooks/lab3_single_agent_tool_calling.ipynb) | Azure AI Foundry |
| [Lab 4: MCP Server](../notebooks/lab4_mcp_server_azure_functions.ipynb) | Azure Functions + Azure Developer CLI |
| [Lab 5: Agent + MCP](../notebooks/lab5_single_agent_mcp_integration.ipynb) | Azure AI Foundry + MCP Server from Lab 4 |

Start with the lab that matches your assignment. Each notebook includes setup instructions for the specific Azure resources you'll need.
