"""Week 8: the service as an MCP server.

MCP (Model Context Protocol) is a standard way to offer tools to any AI agent:
GitHub Copilot, Claude, a Foundry agent, or your own. The same functions the
agents use inside this service are published at /mcp for agents outside it.
"""

from collections.abc import Callable
from typing import Any

from mcp.server import MCPServer

from app import domain
from app.state import AppState
from app.tools import handbook_search


def build_mcp(get_state: Callable[[], AppState]) -> MCPServer:
    """The MCP server and its tools. `get_state` returns the running service's state."""
    mcp = MCPServer(
        "lakeshore-ride",
        instructions="Tools for Lakeshore Ride, a bike-share service: handbook search, fares, stations.",
    )

    @mcp.tool()
    async def search_handbook(query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Search the Lakeshore Ride handbook. Returns passages with doc_id, title and text."""
        return await handbook_search(get_state(), query, max(1, min(top_k, 8)))

    @mcp.tool()
    def quote_fare(plan: str, minutes: int, ebike: bool = False) -> dict[str, Any]:
        """Ride fee in US dollars. plan is one of: single, day_pass, member, student."""
        return domain.quote_fare(plan, minutes, ebike)

    @mcp.tool()
    def get_station(station_id: str) -> dict[str, Any]:
        """Live classic bikes, e-bikes and free docks at a station, for example LS-07."""
        return domain.get_station(station_id)

    return mcp
