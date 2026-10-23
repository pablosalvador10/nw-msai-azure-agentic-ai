"""Tracing and logs to Application Insights (Week 10).

OpenTelemetry records a trace per request: the HTTP call, each agent run, each
model call and each tool call, with timings and token counts. Azure Monitor
stores them; you read them in Application Insights or in the Foundry portal.
"""

import logging
import os

from app.config import Settings

log = logging.getLogger(__name__)


def configure_telemetry(settings: Settings) -> None:
    """Send logs and traces to Application Insights when a connection string is set."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("azure", "httpx", "httpx2", "openai", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if not settings.applicationinsights_connection_string:
        return
    os.environ.setdefault("OTEL_PYTHON_FASTAPI_EXCLUDED_URLS", "health,ready")
    os.environ.setdefault("OTEL_SERVICE_NAME", f"lakeshore-ride-{settings.student_id}")

    from agent_framework.observability import enable_instrumentation
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor(connection_string=settings.applicationinsights_connection_string)
    enable_instrumentation()
    log.info("Telemetry enabled: traces go to Application Insights.")
