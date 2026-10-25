"""HTTP middleware: request ids, API key, body size limit, rate limit (Week 10).

Middleware wraps every request. The last one added runs first.
"""

import logging
import secrets
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings

log = logging.getLogger(__name__)

OPEN_PATHS = {"/health", "/ready", "/v1/info", "/docs", "/openapi.json"}
TOO_LARGE = "Request body too large."


def is_model_rate_limited(exc: BaseException) -> bool:
    """True when the error chain contains a 429 from the model: the deployment's tokens or requests per minute are used up."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = f"{type(current).__name__} {current}".lower()
        if "ratelimiterror" in text or "rate_limit_exceeded" in text or "error code: 429" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


class BodyLimit:
    """Answer 413 when a request body is larger than `max_bytes`.

    Content-Length is checked before anything is read. A body sent without it (a chunked upload)
    is read here, chunk by chunk, and refused as soon as it passes the limit; a body within the
    limit is then handed to the app unchanged. The service never buffers more than the limit.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        length = Headers(scope=scope).get("content-length", "")
        if length.isdigit() and int(length) > self.max_bytes:
            await JSONResponse({"detail": TOO_LARGE}, status_code=413)(scope, receive, send)
            return

        chunks: list[bytes] = []
        size, more = 0, True
        while more:
            message = await receive()
            if message["type"] != "http.request":  # the client went away
                await self.app(scope, _replay([message], receive), send)
                return
            chunks.append(message.get("body", b""))
            size += len(chunks[-1])
            if size > self.max_bytes:
                await JSONResponse({"detail": TOO_LARGE}, status_code=413)(scope, receive, send)
                return
            more = message.get("more_body", False)

        body = {"type": "http.request", "body": b"".join(chunks), "more_body": False}
        await self.app(scope, _replay([body], receive), send)


def _replay(messages: list[Message], receive: Receive) -> Receive:
    """A receive channel that returns `messages` first, then whatever the client sends next."""
    pending = list(messages)

    async def replayed() -> Message:
        return pending.pop(0) if pending else await receive()

    return replayed


def install(app: FastAPI, settings: Settings) -> None:
    """Add request ids, body limit, API key and rate limit to every request."""
    hits: dict[str, deque[float]] = defaultdict(deque)

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if request.url.path in OPEN_PATHS:
            return await call_next(request)
        # The Container Apps ingress appends the caller's address last; earlier entries are client-supplied.
        client = request.headers.get("x-forwarded-for", request.client.host if request.client else "?")
        key, now = client.split(",")[-1].strip(), time.monotonic()
        if len(hits) > 10_000:  # forget callers idle for a minute, so memory stays bounded
            for idle in [k for k, w in hits.items() if not w or now - w[-1] > 60]:
                del hits[idle]
        window = hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Too many requests."}, status_code=429, headers={"Retry-After": "10"})
        window.append(now)
        return await call_next(request)

    @app.middleware("http")
    async def api_key(request: Request, call_next):
        expected = settings.service_api_key.get_secret_value() if settings.service_api_key else ""
        if expected and request.url.path not in OPEN_PATHS:
            given = request.headers.get("x-api-key", "")
            # Compare bytes: compare_digest rejects str with non-ASCII characters, which would be a 500.
            if not secrets.compare_digest(given.encode(), expected.encode()):
                return JSONResponse({"detail": "Missing or invalid X-API-Key."}, status_code=401)
        return await call_next(request)

    app.add_middleware(BodyLimit, max_bytes=settings.max_body_bytes)

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            if is_model_rate_limited(exc):
                log.warning("Model rate limit reached request_id=%s path=%s", rid, request.url.path)
                response = JSONResponse(
                    {"detail": "The model is at capacity. Retry shortly.", "request_id": rid},
                    status_code=503,
                    headers={"Retry-After": "10"},
                )
            else:
                log.exception("Unhandled error request_id=%s path=%s", rid, request.url.path)
                response = JSONResponse({"detail": "Internal error.", "request_id": rid}, status_code=500)
        response.headers["X-Request-ID"] = rid
        elapsed_ms = (time.perf_counter() - start) * 1000
        log.info(
            "%s %s -> %s in %.0f ms request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            rid,
        )
        return response
