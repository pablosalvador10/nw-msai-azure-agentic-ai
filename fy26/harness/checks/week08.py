"""Week 8: the service as an MCP server, plus one tool you build with a coding agent.

MCP over HTTP is JSON-RPC 2.0: POST {"jsonrpc": "2.0", "id": 1, "method": ..., "params": ...}.
Since revision 2026-07-28 the protocol is stateless: there is no handshake and no session. Every
request carries its protocol version and client identity in params._meta, mirrored in HTTP headers.
"""

import json
from typing import Any

from harness.engine import Check, Context, Outcome
from harness.scoring import arguments_match, mean

MCP_PATH = "/mcp"
PROTOCOL = "2026-07-28"
CLIENT = {"name": "nu-harness", "version": "1"}
REQUIRED_TOOLS = {"search_handbook", "quote_fare", "get_station"}
NEW_TOOL = "nearest_station_with_docks"


class MCPError(Exception):
    pass


def _rpc(ctx: Context, method: str, params: dict[str, Any] | None = None) -> Any:
    params = {
        **(params or {}),
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": PROTOCOL,
            "io.modelcontextprotocol/clientInfo": CLIENT,
            "io.modelcontextprotocol/clientCapabilities": {},
        },
    }
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "MCP-Protocol-Version": PROTOCOL,
        "Mcp-Method": method,
    }
    if "name" in params:
        headers["Mcp-Name"] = params["name"]
    ctx.cache["mcp_id"] = ctx.cache.get("mcp_id", 0) + 1
    ex = ctx.target.post(
        MCP_PATH, {"jsonrpc": "2.0", "id": ctx.cache["mcp_id"], "method": method, "params": params}, headers=headers
    )
    error = ex.response.get("error") if isinstance(ex.response, dict) else None
    if ex.status is None or ex.status >= 400:
        reason = f": {error.get('message')}" if isinstance(error, dict) else ""
        raise MCPError(f"{method} returned {ex.status or ex.error}{reason}")
    message = ex.response if isinstance(ex.response, dict) else _from_sse(str(ex.response))
    if "error" in message:
        raise MCPError(f"{method} error: {message['error']}")
    return message.get("result")


def _from_sse(text: str) -> dict[str, Any]:
    """Servers may answer as a server-sent event stream: take the JSON in the last 'data:' line."""
    data = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
    if not data:
        raise MCPError("Response is neither JSON nor an event stream.")
    return json.loads(data[-1])


def call_tool(ctx: Context, name: str, arguments: dict[str, Any]) -> Any:
    """Call a tool and return its result as Python data."""
    result = _rpc(ctx, "tools/call", {"name": name, "arguments": arguments})
    if result.get("isError"):
        raise MCPError(f"{name} reported an error: {result.get('content')}")
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured["result"] if set(structured) == {"result"} else structured
    text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _tools(ctx: Context) -> dict[str, dict[str, Any]]:
    return ctx.once("mcp_tools", lambda: {t["name"]: t for t in _rpc(ctx, "tools/list").get("tools", [])})


def discover(ctx: Context) -> Outcome:
    result = _rpc(ctx, "server/discover") or {}
    name = result.get("_meta", {}).get("io.modelcontextprotocol/serverInfo", {}).get("name")
    versions = result.get("supportedVersions", [])
    if PROTOCOL not in versions:
        return 0.5, f"server/discover answered, but without protocol {PROTOCOL}: {versions}."
    if not name:
        return 0.5, "server/discover answered without serverInfo.name."
    return 1.0, f"MCP server '{name}', protocol versions {versions}."


def tool_list(ctx: Context) -> Outcome:
    tools = _tools(ctx)
    present = REQUIRED_TOOLS & tools.keys()
    with_schema = {n for n in present if isinstance(tools[n].get("inputSchema"), dict)}
    missing = REQUIRED_TOOLS - present
    return len(with_schema) / len(REQUIRED_TOOLS), f"Tools: {sorted(tools)}." + (
        f" Missing: {sorted(missing)}" if missing else ""
    )


def tool_calls(ctx: Context) -> Outcome:
    outcomes = []
    for row in ctx.dataset("week08"):
        if row["tool"] == NEW_TOOL:
            continue
        try:
            got = call_tool(ctx, row["tool"], row["arguments"])
            outcomes.append((row["id"], _matches(got, row["expect"])))
        except MCPError as exc:
            outcomes.append((row["id"], False))
            ctx.cache.setdefault("mcp_errors", []).append(str(exc))
    wrong = [rid for rid, ok in outcomes if not ok]
    return mean(
        [1.0 if ok else 0.0 for _, ok in outcomes]
    ), f"{len(outcomes) - len(wrong)}/{len(outcomes)} tool calls returned the expected data." + (
        f" Wrong: {', '.join(wrong)}" if wrong else ""
    )


def new_tool(ctx: Context) -> Outcome:
    tools = _tools(ctx)
    if NEW_TOOL not in tools:
        return 0.0, f"'{NEW_TOOL}' is not published yet. Build it with your coding agent (see the Week 8 README)."
    rows = [r for r in ctx.dataset("week08") if r["tool"] == NEW_TOOL]
    outcomes = []
    for row in rows:
        try:
            outcomes.append(_matches(call_tool(ctx, NEW_TOOL, row["arguments"]), row["expect"]))
        except MCPError:
            outcomes.append(False)
    return 0.25 + 0.75 * mean([1.0 if ok else 0.0 for ok in outcomes]), f"{sum(outcomes)}/{len(rows)} answers correct."


def _matches(got: Any, expect: dict[str, Any]) -> bool:
    if "first_doc_id" in expect:
        return (
            isinstance(got, list)
            and bool(got)
            and isinstance(got[0], dict)
            and got[0].get("doc_id") == expect["first_doc_id"]
        )
    return isinstance(got, dict) and arguments_match(got, expect)


CHECKS = [
    Check("w08.mcp.discover", f"MCP server answers discovery (server/discover, {PROTOCOL})", 1.0, discover),
    Check("w08.mcp.tools", "The three course tools are published", 2.0, tool_list),
    Check("w08.mcp.call", "Tool calls return the right data", 3.0, tool_calls),
    Check("w08.mcp.new_tool", f"Your new tool '{NEW_TOOL}' works", 3.0, new_tool),
]
