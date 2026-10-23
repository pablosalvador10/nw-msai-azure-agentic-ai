"""
Azure AI Foundry Agent core implementation using Microsoft Agent Framework.

This module provides integration between Microsoft Agent Framework and Azure services
(Functions and Logic Apps) as agent tools.
"""

import logging
from collections.abc import Callable
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field

from src.abstractions.azure_functions import AzureFunctionsClient, FunctionConfig
from src.abstractions.logic_apps import LogicAppConfig, LogicAppsClient

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel):
    """Configuration for the AI Foundry agent using Microsoft Agent Framework.

    Attributes:
        project_endpoint: Azure AI Foundry project endpoint URL.
        use_managed_identity: Whether to use Azure Managed Identity for authentication.
        model_name: Name of the model deployment to use (e.g., "gpt-4", "gpt-35-turbo").
        instructions: System instructions for the agent.
    """

    project_endpoint: str = Field(..., description="Azure AI Foundry project endpoint URL")
    use_managed_identity: bool = Field(
        True, description="Use Azure Managed Identity for authentication"
    )
    model_name: str = Field("gpt-4", description="Model deployment name to use")
    instructions: str = Field(
        "You are a helpful AI assistant with access to Azure tools.",
        description="System instructions for the agent",
    )


class FoundryAgent:
    """Azure AI Foundry Agent using Microsoft Agent Framework.

    This agent uses the official Microsoft Agent Framework SDK to create agents
    that can use Azure Functions and Logic Apps as tools.

    Example:
        >>> from azure.identity import DefaultAzureCredential
        >>> config = AgentConfig(
        ...     project_endpoint="https://my-project.api.azureml.ms",
        ...     model_name="gpt-4"
        ... )
        >>> agent = FoundryAgent(config)
        >>>
        >>> # Register Azure Function as tool
        >>> function_config = FunctionConfig(
        ...     function_url="https://myapp.azurewebsites.net/api/process",
        ...     function_key="key123"
        ... )
        >>> agent.register_azure_function_tool("process_data", function_config)
        >>>
        >>> # Create and run agent
        >>> agent_id = agent.create_agent()
        >>> response = agent.run_agent(agent_id, "Process this data: [1, 2, 3]")
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the Foundry Agent with Microsoft Agent Framework.

        :param config: Configuration for the agent containing endpoint and model details.
        :raises ValueError: If configuration is invalid or credentials cannot be obtained.
        """
        self.config = config
        self._tools: dict[str, Callable] = {}
        self._function_tools: list[FunctionTool] = []

        try:
            credential = DefaultAzureCredential()
            self._client = AIProjectClient(
                endpoint=self.config.project_endpoint, credential=credential
            )
            logger.info(f"Initialized Foundry Agent with project: {self.config.project_endpoint}")
        except Exception as e:
            logger.error(f"Failed to initialize Foundry Agent: {str(e)}")
            raise ValueError(f"Agent initialization failed: {str(e)}") from e

    def register_azure_function_tool(
        self, name: str, config: FunctionConfig, description: str | None = None
    ) -> None:
        """Register an Azure Function as an agent tool.

        :param name: Unique identifier for the tool.
        :param config: Configuration object containing Azure Function endpoint and authentication details.
        :param description: Optional description of the function's purpose and capabilities.
        :raises ValueError: If tool registration fails or configuration is invalid.
        """
        try:
            client = AzureFunctionsClient(config)

            def tool_function(**kwargs: Any) -> dict[str, Any]:
                """Wrapper function for Azure Function invocation."""
                logger.info(f"Invoking Azure Function tool: {name}")
                try:
                    result = client.invoke_function(kwargs)
                    logger.info(f"Azure Function tool '{name}' executed successfully")
                    return result
                except Exception as e:
                    logger.error(f"Azure Function tool '{name}' failed: {str(e)}")
                    return {"error": str(e), "status": "failed"}

            tool_function.__name__ = name
            self._tools[name] = tool_function

            function_tool = FunctionTool(
                name=name,
                description=description
                or f"Azure Function tool: {name} - Invokes Azure Function at {config.function_url}",
                parameters={
                    "type": "object",
                    "properties": {
                        "payload": {
                            "type": "object",
                            "description": "JSON payload to send to the Azure Function",
                        }
                    },
                    "required": ["payload"],
                },
            )
            self._function_tools.append(function_tool)
            logger.info(f"Registered Azure Function tool: {name}")
        except Exception as e:
            logger.error(f"Failed to register Azure Function tool '{name}': {str(e)}")
            raise ValueError(
                f"Azure Function tool registration failed for '{name}': {str(e)}"
            ) from e

    def register_logic_app_tool(
        self, name: str, config: LogicAppConfig, description: str | None = None
    ) -> None:
        """Register a Logic App workflow as an agent tool.

        :param name: Unique identifier for the tool.
        :param config: Configuration object containing Logic App workflow endpoint details.
        :param description: Optional description of the workflow's purpose and capabilities.
        :raises ValueError: If tool registration fails or configuration is invalid.
        """
        try:
            client = LogicAppsClient(config)

            def tool_function(**kwargs: Any) -> dict[str, Any]:
                """Wrapper function for Logic App workflow invocation."""
                logger.info(f"Invoking Logic App tool: {name}")
                try:
                    result = client.trigger_workflow(kwargs)
                    logger.info(f"Logic App tool '{name}' executed successfully")
                    return result
                except Exception as e:
                    logger.error(f"Logic App tool '{name}' failed: {str(e)}")
                    return {"error": str(e), "status": "failed"}

            tool_function.__name__ = name
            self._tools[name] = tool_function

            function_tool = FunctionTool(
                name=name,
                description=description
                or f"Logic App workflow tool: {name} - Triggers workflow at {config.workflow_url}",
                parameters={
                    "type": "object",
                    "properties": {
                        "payload": {
                            "type": "object",
                            "description": "JSON payload to send to the Logic App workflow",
                        }
                    },
                    "required": ["payload"],
                },
            )
            self._function_tools.append(function_tool)
            logger.info(f"Registered Logic App tool: {name}")
        except Exception as e:
            logger.error(f"Failed to register Logic App tool '{name}': {str(e)}")
            raise ValueError(f"Logic App tool registration failed for '{name}': {str(e)}") from e

    def register_custom_tool(
        self,
        name: str,
        function: Callable,
        description: str,
        parameters: dict[str, Any],
    ) -> None:
        """Register a custom Python function as a tool.

        :param name: Unique identifier for the tool.
        :param function: Callable Python function that implements the tool logic.
        :param description: Description of the tool's purpose and capabilities.
        :param parameters: JSON schema defining the function parameters.
        :raises ValueError: If tool registration fails.
        """
        try:
            self._tools[name] = function
            function_tool = FunctionTool(name=name, description=description, parameters=parameters)
            self._function_tools.append(function_tool)
            logger.info(f"Registered custom tool: {name}")
        except Exception as e:
            logger.error(f"Failed to register custom tool '{name}': {str(e)}")
            raise ValueError(f"Custom tool registration failed for '{name}': {str(e)}") from e

    def create_agent(self, name: str | None = None) -> str:
        """Create an agent with registered tools using Microsoft Agent Framework.

        :param name: Optional custom name for the agent. Defaults to "Azure Tools Agent".
        :return: The unique identifier of the created agent.
        :raises RuntimeError: If agent creation fails due to API errors or invalid configuration.
        """
        agent_name = name or "Azure Tools Agent"
        logger.info(f"Creating agent: {agent_name}")

        try:
            agent = self._client.agents.create_agent(
                model=self.config.model_name,
                name=agent_name,
                instructions=self.config.instructions,
                tools=self._function_tools,
                tool_resources={},
            )
            logger.info(f"Agent created with ID: {agent.id}")
            return agent.id
        except Exception as e:
            logger.error(f"Failed to create agent '{agent_name}': {str(e)}")
            raise RuntimeError(f"Agent creation failed: {str(e)}") from e

    def run_agent(self, agent_id: str, user_message: str, thread_id: str | None = None) -> str:
        """Run the agent with a user message.

        :param agent_id: The unique identifier of the agent to execute.
        :param user_message: The user's input message or query.
        :param thread_id: Optional thread ID for maintaining conversation context across multiple turns.
        :return: The agent's response text.
        :raises RuntimeError: If agent execution fails or encounters API errors.
        """
        logger.info(f"Running agent {agent_id} with message: {user_message[:50]}...")

        try:
            if not thread_id:
                thread = self._client.agents.create_thread()
                thread_id = thread.id
                logger.info(f"Created new thread: {thread_id}")

            self._client.agents.create_message(
                thread_id=thread_id, role="user", content=user_message
            )

            run = self._client.agents.create_and_process_run(thread_id=thread_id, agent_id=agent_id)

            logger.info(f"Agent run completed with status: {run.status}")

            messages = self._client.agents.list_messages(thread_id=thread_id)

            for message in messages:
                if message.role == "assistant":
                    content = message.content[0]
                    if hasattr(content, "text"):
                        return content.text.value

            logger.warning("No assistant response found in messages")
            return "No response generated"
        except Exception as e:
            logger.error(f"Failed to run agent {agent_id}: {str(e)}")
            raise RuntimeError(f"Agent execution failed: {str(e)}") from e

    def list_tools(self) -> list[str]:
        """Get a list of all registered tools.

        :return: List of tool names currently registered with the agent.
        """
        return list(self._tools.keys())

    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent.

        :param agent_id: The unique identifier of the agent to delete.
        :raises RuntimeError: If agent deletion fails.
        """
        try:
            self._client.agents.delete_agent(agent_id)
            logger.info(f"Deleted agent: {agent_id}")
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
            raise RuntimeError(f"Agent deletion failed: {str(e)}") from e
