"""HTTP access to the service under test. Every call is recorded as evidence."""

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import httpx2

RETRY_STATUSES = {429, 502, 503, 504}
MAX_BODY_CHARS = 2000


@dataclass
class Exchange:
    method: str
    path: str
    status: int | None
    latency_ms: float
    request: Any = None
    response: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is not None and 200 <= self.status < 300

    def json(self) -> Any:
        return self.response if isinstance(self.response, (dict, list)) else None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("request", "response"):
            text = json.dumps(data[key], ensure_ascii=False) if not isinstance(data[key], str) else data[key]
            if text and len(text) > MAX_BODY_CHARS:
                data[key] = text[:MAX_BODY_CHARS] + f"... [{len(text)} chars]"
        return data


class Target:
    """The endpoint being tested: a URL, or an in-process app via FastAPI's TestClient."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        client: httpx2.Client | None = None,
        api_key: str | None = None,
        timeout: float = 90.0,
        retries: int = 3,
    ) -> None:
        if client is None and not base_url:
            raise ValueError("Give a base_url or a client.")
        self.client = client or httpx2.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        self.label = base_url or str(self.client.base_url)
        self.api_key = api_key
        self.retries = retries
        self._log: list[Exchange] = []

    def begin(self) -> None:
        self._log = []

    def end(self) -> list[Exchange]:
        log, self._log = self._log, []
        return log

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
        authenticate: bool = True,
    ) -> Exchange:
        sent_headers = {"Accept": "application/json"}
        if authenticate and self.api_key:
            sent_headers["X-API-Key"] = self.api_key
        sent_headers.update(headers or {})

        attempt = 0
        while True:
            start = time.perf_counter()
            try:
                response = self.client.request(method, path, json=json_body, content=content, headers=sent_headers)
                exchange = Exchange(
                    method=method,
                    path=path,
                    status=response.status_code,
                    latency_ms=round((time.perf_counter() - start) * 1000, 1),
                    request=json_body if json_body is not None else _preview(content),
                    response=_body(response),
                    headers={
                        k.lower(): v
                        for k, v in response.headers.items()
                        if k.lower().startswith(("x-", "mcp-", "content-type", "retry-after"))
                    },
                )
            except httpx2.HTTPError as exc:
                exchange = Exchange(
                    method=method,
                    path=path,
                    status=None,
                    latency_ms=round((time.perf_counter() - start) * 1000, 1),
                    request=json_body,
                    error=f"{type(exc).__name__}: {exc}",
                )
            retryable = exchange.status in RETRY_STATUSES or (
                exchange.status is None and "Timeout" not in (exchange.error or "")
            )
            if retryable and attempt < self.retries:
                attempt += 1
                time.sleep(_retry_after(exchange, attempt))
                continue
            self._log.append(exchange)
            return exchange

    def get(self, path: str, **kwargs: Any) -> Exchange:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, body: Any = None, **kwargs: Any) -> Exchange:
        return self.request("POST", path, json_body=body, **kwargs)


def _body(response: httpx2.Response) -> Any:
    if "json" in response.headers.get("content-type", ""):
        try:
            return response.json()
        except ValueError:
            pass
    return response.text[:MAX_BODY_CHARS]


def _preview(content: bytes | str | None) -> str | None:
    if content is None:
        return None
    text = content.decode("utf-8", "replace") if isinstance(content, bytes) else content
    return text if len(text) <= 200 else f"{text[:200]}... [{len(text)} chars]"


def _retry_after(exchange: Exchange, attempt: int) -> float:
    """Honor Retry-After (capped), else exponential backoff: 2, 4, 8 seconds."""
    header = exchange.headers.get("retry-after", "")
    if header.isdigit():
        return min(float(header), 15.0)
    return min(2.0**attempt, 15.0)
