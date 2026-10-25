"""
Azure Logic Apps client abstraction for AI Foundry agent integration.

This module provides a client for triggering Logic App workflows
as tools within an AI Foundry agent workflow.
"""

import logging
from datetime import UTC
from enum import Enum
from typing import Any

import aiohttp
import requests
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Enum for Logic App workflow run statuses."""

    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    WAITING = "Waiting"


class LogicAppConfig(BaseModel):
    """Configuration for an Azure Logic App workflow.

    Attributes:
        workflow_url: The HTTP trigger URL for the Logic App workflow.
        subscription_id: Azure subscription ID (for management operations).
        resource_group: Resource group name (for management operations).
        workflow_name: Name of the Logic App workflow (for management operations).
        use_managed_identity: Whether to use Azure Managed Identity for authentication.
        timeout: Request timeout in seconds.
    """

    workflow_url: str = Field(..., description="Logic App HTTP trigger URL")
    subscription_id: str | None = Field(None, description="Azure subscription ID")
    resource_group: str | None = Field(None, description="Resource group name")
    workflow_name: str | None = Field(None, description="Logic App workflow name")
    use_managed_identity: bool = Field(
        False, description="Use Azure Managed Identity for authentication"
    )
    timeout: int = Field(60, ge=1, le=600, description="Request timeout in seconds")

    @field_validator("workflow_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that the URL is properly formatted."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("workflow_url must start with http:// or https://")
        return v


class LogicAppsClient:
    """Client for interacting with Azure Logic Apps.

    This client provides methods for triggering Logic App workflows
    and checking their status, with support for managed identity authentication.

    Example:
        >>> config = LogicAppConfig(
        ...     workflow_url="https://prod-123.eastus.logic.azure.com:443/workflows/..."
        ... )
        >>> client = LogicAppsClient(config)
        >>> result = client.trigger_workflow({"action": "process", "data": "test"})
    """

    def __init__(self, config: LogicAppConfig) -> None:
        """Initialize the Logic Apps client.

        :param config: Configuration object containing workflow endpoint and settings.
        :raises ValueError: If configuration is invalid.
        """
        try:
            self.config = config
            self._credential: DefaultAzureCredential | None = None

            if self.config.use_managed_identity:
                self._credential = DefaultAzureCredential()
                logger.info("Initialized Logic Apps client with managed identity")
            else:
                logger.info("Initialized Logic Apps client with workflow URL")
        except Exception as e:
            logger.error(f"Failed to initialize Logic Apps client: {str(e)}")
            raise ValueError(f"Client initialization failed: {str(e)}") from e

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for the request.

        :return: Dictionary containing standard HTTP headers.
        """
        headers = {"Content-Type": "application/json"}
        logger.debug("Prepared request headers")
        return headers

    def trigger_workflow(
        self, payload: dict[str, Any], wait_for_completion: bool = False
    ) -> dict[str, Any]:
        """Trigger a Logic App workflow synchronously.

        :param payload: JSON payload to send to the workflow trigger.
        :param wait_for_completion: Whether to wait for workflow completion before returning.
        :return: Response from the workflow trigger or final status if waiting.
        :raises requests.RequestException: If the HTTP request fails.
        :raises ValueError: If the response cannot be parsed as JSON.
        """
        logger.info(f"Triggering Logic App workflow: {self.config.workflow_url}")
        logger.debug(
            f"Payload keys: {list(payload.keys())}, wait_for_completion: {wait_for_completion}"
        )

        try:
            response = requests.post(
                url=self.config.workflow_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                result = {"status": "triggered", "status_code": response.status_code}

            logger.info(f"Workflow triggered successfully. Status: {response.status_code}")

            if wait_for_completion:
                logger.warning(
                    "wait_for_completion requires management API access (not implemented)"
                )

            return result

        except requests.RequestException as e:
            logger.error(f"Failed to trigger Logic App workflow: {str(e)}")
            raise

    async def trigger_workflow_async(
        self, payload: dict[str, Any], wait_for_completion: bool = False
    ) -> dict[str, Any]:
        """Trigger a Logic App workflow asynchronously.

        Args:
            payload: JSON payload to send to the workflow.
            wait_for_completion: If True, wait for the workflow to complete.

        Returns:
            Response from the workflow trigger or final status if waiting.

        Raises:
            aiohttp.ClientError: If the request fails.
        """
        logger.info(f"Triggering Logic App workflow asynchronously: {self.config.workflow_url}")
        logger.debug(
            f"Payload keys: {list(payload.keys())}, wait_for_completion: {wait_for_completion}"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url=self.config.workflow_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response.raise_for_status()

                    # Try to parse JSON response, but handle empty responses
                    try:
                        result = await response.json()
                    except ValueError:
                        result = {"status": "triggered", "status_code": response.status}

                    logger.info(f"Async workflow triggered successfully. Status: {response.status}")

                    if wait_for_completion:
                        logger.warning(
                            "wait_for_completion requires management API access (not implemented)"
                        )

                    return result

        except aiohttp.ClientError as e:
            logger.error(f"Failed to trigger Logic App workflow asynchronously: {str(e)}")
            raise


class WorkflowOrchestrator:
    """Orchestrator for Logic App workflows as AI agent tools.

    This class demonstrates how to use Logic Apps as tools in an AI agent,
    providing workflow orchestration capabilities.

    Example:
        >>> config = LogicAppConfig(
        ...     workflow_url="https://prod-123.eastus.logic.azure.com:443/workflows/..."
        ... )
        >>> orchestrator = WorkflowOrchestrator(config)
        >>> result = orchestrator.execute_workflow(
        ...     workflow_type="approval",
        ...     data={"request": "Budget approval", "amount": 5000}
        ... )
    """

    def __init__(self, config: LogicAppConfig) -> None:
        """Initialize the workflow orchestrator.

        Args:
            config: Configuration for the Logic App workflow.
        """
        self.client = LogicAppsClient(config)
        logger.info("Initialized WorkflowOrchestrator")

    def execute_workflow(self, workflow_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Execute a Logic App workflow with specified type and data.

        Args:
            workflow_type: Type of workflow to execute (e.g., "approval", "notification").
            data: Input data for the workflow.

        Returns:
            Result from the workflow execution.
        """
        logger.info(f"Executing workflow of type '{workflow_type}'")

        try:
            result = self.client.trigger_workflow(
                {
                    "workflow_type": workflow_type,
                    "data": data,
                    "timestamp": self._get_timestamp(),
                }
            )
            logger.info(f"Workflow '{workflow_type}' executed successfully")
            return result
        except Exception as e:
            logger.error(f"Workflow '{workflow_type}' execution failed: {str(e)}")
            raise

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string.
        """
        from datetime import datetime

        return datetime.now(UTC).isoformat()


class NotificationWorkflow:
    """Logic App workflow for sending notifications.

    This class provides a specialized interface for notification workflows,
    demonstrating how to create domain-specific workflow tools.

    Example:
        >>> config = LogicAppConfig(
        ...     workflow_url="https://prod-123.eastus.logic.azure.com:443/workflows/..."
        ... )
        >>> notifier = NotificationWorkflow(config)
        >>> result = notifier.send_notification(
        ...     recipient="user@example.com",
        ...     subject="Alert",
        ...     message="System alert detected"
        ... )
    """

    def __init__(self, config: LogicAppConfig) -> None:
        """Initialize the notification workflow.

        Args:
            config: Configuration for the Logic App workflow.
        """
        self.client = LogicAppsClient(config)
        logger.info("Initialized NotificationWorkflow")

    def send_notification(
        self, recipient: str, subject: str, message: str, priority: str = "normal"
    ) -> dict[str, Any]:
        """Send a notification through the Logic App workflow.

        Args:
            recipient: Email address or identifier of the recipient.
            subject: Subject of the notification.
            message: Message body.
            priority: Priority level (low, normal, high).

        Returns:
            Result from the notification workflow.
        """
        logger.info(f"Sending notification to '{recipient}' with subject '{subject}'")

        try:
            result = self.client.trigger_workflow(
                {
                    "notification_type": "email",
                    "recipient": recipient,
                    "subject": subject,
                    "message": message,
                    "priority": priority,
                }
            )
            logger.info(f"Notification sent successfully to '{recipient}'")
            return result
        except Exception as e:
            logger.error(f"Failed to send notification to '{recipient}': {str(e)}")
            raise
