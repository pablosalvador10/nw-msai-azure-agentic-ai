"""Lakeshore Ride support API.

Run locally from the fy26/ folder:

    uv run uvicorn app.main:app --reload

Then open http://localhost:8000/docs.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.transport_security import TransportSecuritySettings

from app import middleware
from app.config import Settings, get_settings
from app.contract import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    ClassifyRequest,
    ClassifyResponse,
    InfoResponse,
    ResolveRequest,
    ResolveResponse,
)
from app.mcp_server import build_mcp
from app.services import ask, chat, classify, resolve
from app.state import AppState
from app.telemetry import configure_telemetry

# What this service can do. Add to it when you add a capability.
CAPABILITIES = ["chat", "classify", "ask", "resolve", "mcp", "guardrails"]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the service: routes, middleware, the MCP endpoint and shared state."""
    settings = settings or get_settings()
    configure_telemetry(settings)

    holder: dict[str, AppState] = {}
    mcp = build_mcp(lambda: holder["state"])
    # Answer MCP requests only when they are addressed to this service. A web page cannot then use
    # DNS rebinding to reach a server on your laptop through your browser.
    hosts = ["127.0.0.1", "127.0.0.1:*", "localhost", "localhost:*", "testserver", settings.public_hostname]
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,  # every request stands alone: scales out, no sticky sessions
        json_response=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[h for h in hosts if h],
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*"],
        ),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        state = AppState(settings)
        holder["state"] = app.state.services = state
        if not settings.missing():
            await state.warm_up()
        async with mcp.session_manager.run():
            yield
        await state.aclose()

    app = FastAPI(
        title="Lakeshore Ride Support API",
        version=settings.app_version,
        description="Northwestern MS AI, FY26. The service you build, deploy and get graded on.",
        lifespan=lifespan,
    )
    middleware.install(app, settings)

    def state_of(request: Request) -> AppState:
        return request.app.state.services

    @app.get("/health", tags=["platform"])
    async def health() -> dict[str, str]:
        """Liveness: the process is up. Never calls a model."""
        return {"status": "ok"}

    @app.get("/ready", tags=["platform"])
    async def ready(request: Request) -> JSONResponse:
        """Readiness: configuration is complete, so the service can take traffic."""
        missing = settings.missing()
        if missing:
            return JSONResponse({"status": "not_ready", "missing": missing}, status_code=503)
        index = "built" if state_of(request).index_ready else "pending"
        return JSONResponse({"status": "ready", "index": index})

    @app.get("/v1/info", tags=["platform"])
    async def info(request: Request) -> InfoResponse:
        return InfoResponse(
            student_id=settings.student_id,
            version=settings.app_version,
            model=state_of(request).models.name,
            capabilities=CAPABILITIES,
        )

    @app.post("/v1/chat", tags=["week 5"])
    async def chat_route(body: ChatRequest, request: Request) -> ChatResponse:
        return await chat.chat(state_of(request), body)

    @app.post("/v1/classify", tags=["week 5"])
    async def classify_route(body: ClassifyRequest, request: Request) -> ClassifyResponse:
        return await classify.classify(state_of(request), body)

    @app.post("/v1/ask", tags=["week 6"])
    async def ask_route(body: AskRequest, request: Request) -> AskResponse:
        return await ask.ask(state_of(request), body)

    @app.post("/v1/resolve", tags=["week 7"])
    async def resolve_route(body: ResolveRequest, request: Request) -> ResolveResponse:
        return await resolve.resolve(state_of(request), body)

    # Week 8: MCP endpoint at /mcp. Mounted last so the routes above take precedence.
    app.mount("/", mcp_app)
    return app


app = create_app()
