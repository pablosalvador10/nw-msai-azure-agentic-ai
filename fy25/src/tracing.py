"""
Tracing and Observability utilities for AI agents.

This module provides a centralized tracing configuration for the project,
supporting both Azure Monitor Application Insights and AI Toolkit local tracing.

Usage:
    from src.tracing import setup_tracing, setup_aitk_tracing, get_tracer, traced

    # Option 1: Setup tracing with Azure AI Foundry project (production)
    setup_tracing(project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"])

    # Option 2: Setup tracing with AI Toolkit local collector (development)
    setup_aitk_tracing()

    # Option 3: Setup tracing with explicit connection string
    setup_tracing(connection_string="InstrumentationKey=...")

    # Get a tracer for custom spans
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my-operation"):
        # Your code here
        pass

    # Or use the decorator
    @traced("my-function")
    def my_function():
        pass
"""

import functools
import logging
import os
from typing import Any, Callable, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Tracer

logger = logging.getLogger(__name__)

# Type variable for generic function decoration
F = TypeVar("F", bound=Callable[..., Any])

# Global state for tracing configuration
_tracing_configured = False
_tracer_provider = None


def setup_tracing(
    *,
    project_endpoint: Optional[str] = None,
    connection_string: Optional[str] = None,
    service_name: str = "northwestern-agentic-ai",
    enable_content_capture: bool = False,
    instrument_openai: bool = True,
    instrument_agents: bool = True,
) -> bool:
    """
    Configure tracing with Azure Monitor Application Insights.

    This function sets up OpenTelemetry tracing and automatically instruments
    the OpenAI SDK and Azure AI Agents SDK for automatic trace capture.

    Args:
        project_endpoint: Azure AI Foundry project endpoint. If provided, the
            Application Insights connection string will be retrieved automatically.
        connection_string: Explicit Application Insights connection string.
            Use this if you want to specify the connection string directly.
        service_name: Name to identify this service in traces (default: "northwestern-agentic-ai").
        enable_content_capture: Whether to capture message content (prompts/responses).
            ⚠️ Only enable in development - may expose PII in production.
        instrument_openai: Whether to instrument the OpenAI SDK (default: True).
        instrument_agents: Whether to instrument the Azure AI Agents SDK (default: True).

    Returns:
        True if tracing was configured successfully, False otherwise.

    Raises:
        ValueError: If neither project_endpoint nor connection_string is provided.

    Example:
        >>> # Setup with Foundry project (recommended)
        >>> setup_tracing(project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"])

        >>> # Setup with explicit connection string
        >>> setup_tracing(connection_string="InstrumentationKey=...")

        >>> # Enable content capture for debugging
        >>> setup_tracing(
        ...     project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        ...     enable_content_capture=True
        ... )
    """
    global _tracing_configured, _tracer_provider

    if _tracing_configured:
        logger.warning("Tracing already configured, skipping re-initialization")
        return True

    if not project_endpoint and not connection_string:
        raise ValueError("Either project_endpoint or connection_string must be provided")

    # Set environment variables for content capture
    if enable_content_capture:
        os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
        logger.info("Content capture enabled - message content will be traced")

    # Set service name
    os.environ["OTEL_SERVICE_NAME"] = service_name

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        # Get connection string from project if not provided
        if not connection_string and project_endpoint:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential

            project_client = AIProjectClient(
                endpoint=project_endpoint,
                credential=DefaultAzureCredential(),
            )
            connection_string = project_client.telemetry.get_application_insights_connection_string()
            logger.info("Retrieved Application Insights connection string from project")

        # Configure Azure Monitor
        configure_azure_monitor(connection_string=connection_string)
        logger.info(f"Azure Monitor configured for service: {service_name}")

        # Instrument OpenAI SDK
        if instrument_openai:
            try:
                from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

                OpenAIInstrumentor().instrument()
                logger.info("OpenAI SDK instrumented - all API calls will be traced")
            except ImportError:
                logger.warning(
                    "opentelemetry-instrumentation-openai-v2 not installed, "
                    "OpenAI calls will not be auto-traced"
                )

        # Instrument Azure AI Agents SDK
        if instrument_agents:
            try:
                from azure.ai.agents.telemetry import AIAgentsInstrumentor

                AIAgentsInstrumentor().instrument()
                logger.info("Azure AI Agents SDK instrumented")
            except ImportError:
                logger.debug("Azure AI Agents telemetry not available (optional)")

        _tracing_configured = True
        return True

    except ImportError as e:
        logger.error(
            f"Missing tracing packages: {e}\n"
            "Install with: uv pip install azure-monitor-opentelemetry "
            "opentelemetry-instrumentation-openai-v2"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to configure tracing: {e}")
        return False


def setup_aitk_tracing(
    *,
    endpoint: str = "http://localhost:4318",
    service_name: str = "northwestern-agentic-ai",
    enable_content_capture: bool = True,
    instrument_openai: bool = True,
    instrument_agents: bool = True,
) -> bool:
    """
    Configure tracing with AI Toolkit local OTLP collector.

    This function sets up OpenTelemetry tracing to send traces to the AI Toolkit
    local collector in VS Code. This is ideal for local development and debugging.

    Prerequisites:
        1. Install AI Toolkit extension in VS Code
        2. Open Tracing view in AI Toolkit
        3. Click "Start Collector" to start the local OTLP server

    Args:
        endpoint: OTLP HTTP endpoint (default: "http://localhost:4318").
        service_name: Name to identify this service in traces.
        enable_content_capture: Whether to capture message content (default: True for dev).
        instrument_openai: Whether to instrument the OpenAI SDK (default: True).
        instrument_agents: Whether to instrument the Azure AI Agents SDK (default: True).

    Returns:
        True if tracing was configured successfully, False otherwise.

    Example:
        >>> # Basic setup - traces go to AI Toolkit in VS Code
        >>> setup_aitk_tracing()

        >>> # Custom service name
        >>> setup_aitk_tracing(service_name="my-agent-app")
    """
    global _tracing_configured, _tracer_provider

    if _tracing_configured:
        logger.warning("Tracing already configured, skipping re-initialization")
        return True

    # Set environment variables for content capture (enabled by default for local dev)
    if enable_content_capture:
        os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
        logger.info("Content capture enabled for AI Toolkit tracing")

    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create resource with service name
        resource = Resource.create({"service.name": service_name})

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)

        # Configure OTLP exporter to AI Toolkit local collector
        otlp_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")

        # Add span processor
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set as global tracer provider
        otel_trace.set_tracer_provider(tracer_provider)
        _tracer_provider = tracer_provider

        logger.info(f"AI Toolkit tracing configured: {endpoint}")
        logger.info(f"Service name: {service_name}")

        # Instrument OpenAI SDK
        if instrument_openai:
            try:
                from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

                OpenAIInstrumentor().instrument()
                logger.info("OpenAI SDK instrumented for AI Toolkit tracing")
            except ImportError:
                logger.warning(
                    "opentelemetry-instrumentation-openai-v2 not installed, "
                    "OpenAI calls will not be auto-traced"
                )

        # Instrument Azure AI Agents SDK
        if instrument_agents:
            try:
                from azure.ai.agents.telemetry import AIAgentsInstrumentor

                AIAgentsInstrumentor().instrument()
                logger.info("Azure AI Agents SDK instrumented")
            except ImportError:
                logger.debug("Azure AI Agents telemetry not available (optional)")

        _tracing_configured = True
        print("✅ AI Toolkit tracing configured!")
        print(f"   Endpoint: {endpoint}")
        print(f"   Service: {service_name}")
        print("\n📋 Next steps:")
        print("   1. Open AI Toolkit in VS Code sidebar")
        print("   2. Click 'Tracing' in the tree view")
        print("   3. Click 'Start Collector' if not already running")
        print("   4. Run your AI code - traces will appear automatically!")
        return True

    except ImportError as e:
        logger.error(
            f"Missing tracing packages: {e}\n"
            "Install with: uv pip install opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-http "
            "opentelemetry-instrumentation-openai-v2"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to configure AI Toolkit tracing: {e}")
        return False


def get_tracer(name: str = __name__) -> Tracer:
    """
    Get an OpenTelemetry tracer instance for creating custom spans.

    Args:
        name: Name for the tracer, typically __name__ of the calling module.

    Returns:
        OpenTelemetry Tracer instance.

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("process-data") as span:
        ...     span.set_attribute("data.size", len(data))
        ...     result = process(data)
        ...     span.set_attribute("result.status", "success")
    """
    return trace.get_tracer(name)


def traced(
    span_name: Optional[str] = None,
    *,
    attributes: Optional[dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Decorator to automatically create a span for a function.

    Args:
        span_name: Name for the span. Defaults to the function name.
        attributes: Optional dictionary of attributes to add to the span.

    Returns:
        Decorated function with automatic tracing.

    Example:
        >>> @traced("process-claims")
        ... def process_claims(claims: list[str]) -> list[str]:
        ...     return [assess(c) for c in claims]

        >>> @traced(attributes={"operation.type": "assessment"})
        ... def assess_claim(claim: str) -> str:
        ...     return "True" if valid else "False"
    """

    def decorator(func: F) -> F:
        tracer = get_tracer(func.__module__)
        name = span_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(name) as span:
                # Add custom attributes if provided
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function arguments as attributes (safely)
                try:
                    if args:
                        span.set_attribute("function.args_count", len(args))
                    if kwargs:
                        span.set_attribute("function.kwargs_keys", str(list(kwargs.keys())))
                except Exception:
                    pass  # Don't fail tracing if attribute setting fails

                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def add_span_attribute(key: str, value: Any) -> None:
    """
    Add an attribute to the current active span.

    This is useful for adding context to spans from within nested function calls.

    Args:
        key: Attribute key (use semantic conventions where applicable).
        value: Attribute value (must be string, int, float, bool, or list of these).

    Example:
        >>> def process_request(request_id: str):
        ...     add_span_attribute("request.id", request_id)
        ...     add_span_attribute("request.processed", True)
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(key, value)


def record_exception(exception: Exception, *, escaped: bool = True) -> None:
    """
    Record an exception on the current active span.

    Args:
        exception: The exception to record.
        escaped: Whether the exception escaped the span (default: True).

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     record_exception(e)
        ...     raise
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.record_exception(exception, escaped=escaped)


# Semantic conventions for GenAI operations
class GenAIAttributes:
    """OpenTelemetry Semantic Conventions for Generative AI operations.

    Use these attribute names for consistent, interoperable traces.
    See: https://opentelemetry.io/docs/specs/semconv/gen-ai/
    """

    # Request attributes
    SYSTEM = "gen_ai.system"  # e.g., "openai", "azure_openai"
    REQUEST_MODEL = "gen_ai.request.model"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_TOP_P = "gen_ai.request.top_p"

    # Response attributes
    RESPONSE_ID = "gen_ai.response.id"
    RESPONSE_MODEL = "gen_ai.response.model"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"

    # Token usage
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

    # Tool calling
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call_id"


__all__ = [
    "setup_tracing",
    "setup_aitk_tracing",
    "get_tracer",
    "traced",
    "add_span_attribute",
    "record_exception",
    "GenAIAttributes",
]
