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

from app.config import Settings

log = logging.getLogger(__name__)

OPEN_PATHS = {"/health", "/ready", "/v1/info", "/docs", "/openapi.json"}


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
            if not secrets.compare_digest(given, expected):
                return JSONResponse({"detail": "Missing or invalid X-API-Key."}, status_code=401)
        return await call_next(request)

    @app.middleware("http")
    async def body_limit(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_body_bytes:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
        return await call_next(request)

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
