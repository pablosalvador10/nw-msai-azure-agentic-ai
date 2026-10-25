"""MCP Server Azure Functions - Lab 4

This module defines MCP tools that can be consumed by AI agents like GitHub Copilot.
We're exposing the data analysis functionality from Lab 1 as MCP tools.
"""

import json
import logging
from typing import Any

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# ============================================================================
# MCP Tool Properties Definitions
# ============================================================================


class ToolProperty:
    """Defines a property for an MCP tool."""

    def __init__(self, name: str, property_type: str, description: str):
        self.name = name
        self.property_type = property_type
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        return {"propertyName": self.name, "propertyType": self.property_type, "description": self.description}


# Tool properties for analyze_data
tool_properties_analyze_data = [
    ToolProperty("values", "string", "A JSON array of numbers to analyze, e.g., [1, 2, 3, 4, 5]")
]
tool_properties_analyze_data_json = json.dumps([p.to_dict() for p in tool_properties_analyze_data])

# Tool properties for save_snippet
tool_properties_save_snippet = [
    ToolProperty("snippet_name", "string", "The name to save the snippet under"),
    ToolProperty("snippet_content", "string", "The code snippet content to save"),
]
tool_properties_save_snippet_json = json.dumps([p.to_dict() for p in tool_properties_save_snippet])

# Tool properties for get_snippet
tool_properties_get_snippet = [ToolProperty("snippet_name", "string", "The name of the snippet to retrieve")]
tool_properties_get_snippet_json = json.dumps([p.to_dict() for p in tool_properties_get_snippet])


# ============================================================================
# MCP Tool: hello_mcp
# ============================================================================


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="hello_mcp",
    description="A simple hello world tool to verify MCP server connectivity.",
    toolProperties="[]",
)
def hello_mcp(context) -> str:
    """
    A simple hello world MCP tool.
    Returns a greeting message to verify the MCP server is working.
    """
    logging.info("hello_mcp tool invoked")
    return json.dumps(
        {"message": "Hello from MCP Server! 👋", "status": "success", "lab": "Lab 4 - MCP Server with Azure Functions"}
    )


# ============================================================================
# MCP Tool: analyze_data (from Lab 1)
# ============================================================================


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="analyze_data",
    description="Analyze a list of numbers and return statistics including count, sum, mean, min, and max.",
    toolProperties=tool_properties_analyze_data_json,
)
def analyze_data(context) -> str:
    """
    Analyze numerical data - the same functionality from Lab 1!

    This tool receives a list of numbers and returns statistical analysis.
    """
    logging.info("analyze_data MCP tool invoked")

    try:
        content = json.loads(context)
        values_str = content["arguments"].get("values", "[]")

        # Parse the values (they come as a JSON string)
        values = json.loads(values_str) if isinstance(values_str, str) else values_str

        if not values:
            return json.dumps({"error": "No values provided"})

        # Perform the analysis (same as Lab 1)
        result = {
            "count": len(values),
            "sum": sum(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "values": values,
        }

        logging.info(f"Analysis complete: {result}")
        return json.dumps(result)

    except Exception as e:
        logging.error(f"Error in analyze_data: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# MCP Tool: save_snippet
# ============================================================================

# In-memory storage for snippets (in production, use Azure Blob Storage)
_snippets_storage: dict[str, str] = {}


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="save_snippet",
    description="Save a code snippet with a given name for later retrieval.",
    toolProperties=tool_properties_save_snippet_json,
)
def save_snippet(context) -> str:
    """
    Save a code snippet to storage.
    """
    logging.info("save_snippet MCP tool invoked")

    try:
        content = json.loads(context)
        snippet_name = content["arguments"].get("snippet_name", "")
        snippet_content = content["arguments"].get("snippet_content", "")

        if not snippet_name:
            return json.dumps({"error": "No snippet name provided"})

        if not snippet_content:
            return json.dumps({"error": "No snippet content provided"})

        # Save the snippet
        _snippets_storage[snippet_name] = snippet_content

        logging.info(f"Saved snippet: {snippet_name}")
        return json.dumps(
            {
                "message": f"Snippet '{snippet_name}' saved successfully",
                "snippet_name": snippet_name,
                "status": "success",
            }
        )

    except Exception as e:
        logging.error(f"Error in save_snippet: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# MCP Tool: get_snippet
# ============================================================================


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="get_snippet",
    description="Retrieve a previously saved code snippet by name.",
    toolProperties=tool_properties_get_snippet_json,
)
def get_snippet(context) -> str:
    """
    Retrieve a code snippet from storage.
    """
    logging.info("get_snippet MCP tool invoked")

    try:
        content = json.loads(context)
        snippet_name = content["arguments"].get("snippet_name", "")

        if not snippet_name:
            return json.dumps({"error": "No snippet name provided"})

        if snippet_name not in _snippets_storage:
            return json.dumps(
                {"error": f"Snippet '{snippet_name}' not found", "available_snippets": list(_snippets_storage.keys())}
            )

        snippet_content = _snippets_storage[snippet_name]

        logging.info(f"Retrieved snippet: {snippet_name}")
        return json.dumps({"snippet_name": snippet_name, "content": snippet_content, "status": "success"})

    except Exception as e:
        logging.error(f"Error in get_snippet: {str(e)}")
        return json.dumps({"error": str(e)})


# ============================================================================
# MCP Tool: list_snippets
# ============================================================================


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="list_snippets",
    description="List all saved code snippets.",
    toolProperties="[]",
)
def list_snippets(context) -> str:
    """
    List all saved snippets.
    """
    logging.info("list_snippets MCP tool invoked")

    return json.dumps(
        {"snippets": list(_snippets_storage.keys()), "count": len(_snippets_storage), "status": "success"}
    )
