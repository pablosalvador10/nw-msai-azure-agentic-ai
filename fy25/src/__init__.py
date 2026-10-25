"""
Azure AI Foundry Agent Extension.

This package provides abstractions and integrations for Azure AI Foundry agents,
including Azure Functions and Logic Apps integrations.
"""

__version__ = "0.1.0"
__author__ = "Northwestern MSAI"

# Tracing utilities
from src.tracing import (
    GenAIAttributes,
    add_span_attribute,
    get_tracer,
    record_exception,
    setup_aitk_tracing,
    setup_tracing,
    traced,
)

__all__ = [
    # Tracing
    "setup_tracing",
    "setup_aitk_tracing",
    "get_tracer",
    "traced",
    "add_span_attribute",
    "record_exception",
    "GenAIAttributes",
]
