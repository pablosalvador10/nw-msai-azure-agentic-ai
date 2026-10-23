"""Pytest configuration and fixtures."""

import logging
from typing import Any

import pytest

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@pytest.fixture
def sample_function_config() -> dict[str, Any]:
    """Provide sample Azure Function configuration.

    Returns:
        Dictionary with function configuration.
    """
    return {
        "function_url": "https://test.azurewebsites.net/api/testfunction",
        "function_key": "test_key_123",
        "timeout": 30,
    }


@pytest.fixture
def sample_logic_app_config() -> dict[str, Any]:
    """Provide sample Logic App configuration.

    Returns:
        Dictionary with Logic App configuration.
    """
    return {
        "workflow_url": "https://prod-test.eastus.logic.azure.com:443/workflows/test",
        "timeout": 60,
    }


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    """Provide sample request payload.

    Returns:
        Dictionary with sample data.
    """
    return {"data": "test_data", "values": [1, 2, 3, 4, 5], "operation": "process"}


@pytest.fixture
def mock_response_data() -> dict[str, Any]:
    """Provide mock response data.

    Returns:
        Dictionary with mock response.
    """
    return {
        "status": "success",
        "result": "processed",
        "data": {"output": "test_output"},
    }
