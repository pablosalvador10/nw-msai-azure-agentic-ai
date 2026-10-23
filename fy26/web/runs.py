"""The online harness: score a student's deployed service in the background.

It runs exactly the checks of `python -m harness check --week N --url <url>`. Because the
website calls a URL the student types, every target is validated first: https, a Container
Apps host name, and public IP addresses only. Otherwise the site could be used to reach
addresses inside Azure (server-side request forgery).
"""

import ipaddress
import logging
import re
import socket
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from harness.checks import CORE, WEEKS
from harness.client import Target
from harness.engine import run_week

log = logging.getLogger("lectures.runs")

Progress = Callable[[str], None]
Runner = Callable[[str, int, str | None, Progress], dict[str, Any]]
Resolver = Callable[[str], list[str]]
HOSTNAME = re.compile(r"[a-z0-9]([a-z0-9-]{0,62}\.)+[a-z0-9-]{1,63}")


class TargetError(ValueError):
    """The URL is not one the online harness may call. The message tells the student what to paste."""


class RunRejected(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def resolve_host(host: str) -> list[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)]


def validate_target(
    url: str, suffixes: tuple[str, ...], *, blocked: tuple[str, ...] = (), resolve: Resolver = resolve_host
) -> str:
    """Return the normalized base URL (https://host), or raise TargetError."""
    example = "https://ca-<name>.<environment>.<region>.azurecontainerapps.io"
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError as exc:
        raise TargetError(f"That is not a valid URL. Paste the base URL of your service, like {example}") from exc
    host = (parts.hostname or "").lower()
    if parts.scheme != "https":
        raise TargetError(f"Use the https:// address of your deployed service, like {example}")
    if parts.username or parts.password or port not in (None, 443):
        raise TargetError("Remove the user name, password or port from the URL.")
    if not HOSTNAME.fullmatch(host) or not any(host.endswith(s) and len(host) > len(s) for s in suffixes):
        raise TargetError(f"Paste the URL of your Container App, like {example} (terraform output app_url).")
    if host in blocked:
        raise TargetError("That is the course website, not your service.")
    if parts.path not in ("", "/") or parts.query or parts.fragment:
        raise TargetError("Paste the base URL only, without a path such as /health or /v1/info.")
    try:
        addresses = {ipaddress.ip_address(a.split("%")[0]) for a in resolve(host)}
    except (OSError, UnicodeError, ValueError) as exc:
        raise TargetError(f"{host} does not resolve. Check for typos; copy it from terraform output app_url.") from exc
    if not addresses or not all(a.is_global for a in addresses):
        raise TargetError(f"{host} does not point to a public address, so the online harness cannot call it.")
    return f"https://{host}"


def run_harness(url: str, week: int, api_key: str | None, progress: Progress) -> dict[str, Any]:
    """One harness run against a deployed service; returns the report (the same JSON as the CLI's proof)."""
    target = Target(url, api_key=api_key)
    try:
        return run_week(week, target, progress=progress).to_dict()
    finally:
        target.client.close()


@dataclass
class Run:
    id: str
    owner: str
    week: int
    target: str
    total: int
    created: float = field(default_factory=time.time)
    status: str = "queued"  # queued -> running -> done | failed
    current: str = ""
    completed: int = 0
    report: dict[str, Any] | None = None
    error: str | None = None

    @property
    def active(self) -> bool:
        return self.status in ("queued", "running")


class RunQueue:
    """Runs in memory, a few at a time. The website runs one replica, so this is the only queue."""

    def __init__(self, runner: Runner = run_harness, *, workers: int = 3, per_hour: int = 20, keep_s: int = 7200):
        self._runner = runner
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="harness")
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()
        self.per_hour = per_hour
        self.keep_s = keep_s

    def submit(self, owner: str, url: str, week: int, api_key: str | None) -> Run:
        now = time.time()
        with self._lock:
            self._runs = {k: r for k, r in self._runs.items() if r.active or r.created > now - self.keep_s}
            mine = [r for r in self._runs.values() if r.owner == owner]
            if any(r.active for r in mine):
                raise RunRejected(409, "You already have a run in progress. Wait for it to finish.")
            if sum(r.created > now - 3600 for r in mine) >= self.per_hour:
                raise RunRejected(
                    429,
                    f"You started {self.per_hour} runs in the last hour. Iterate locally in the meantime: "
                    f"uv run python -m harness check --week {week} --in-process",
                )
            run = Run(id=uuid4().hex, owner=owner, week=week, target=url, total=len(CORE) + len(WEEKS[week]))
            self._runs[run.id] = run
        self._pool.submit(self._execute, run, url, api_key)
        return run

    def get(self, owner: str, run_id: str) -> Run | None:
        """A run, only for the student who started it."""
        run = self._runs.get(run_id)
        return run if run and run.owner == owner else None

    def position(self, run: Run) -> int:
        """How many queued runs start before this one."""
        with self._lock:
            return sum(r.status == "queued" and r.created < run.created for r in self._runs.values())

    def _execute(self, run: Run, url: str, api_key: str | None) -> None:
        run.status = "running"
        started = time.perf_counter()

        def progress(check_id: str) -> None:
            run.completed = min(run.completed + (1 if run.current else 0), run.total)
            run.current = check_id

        try:
            run.report = self._runner(url, run.week, api_key, progress)
            run.status, run.completed, run.current = "done", run.total, ""
        except Exception as exc:  # noqa: BLE001 - report any failure to the student instead of hanging
            log.exception("Run %s failed", run.id)
            run.status, run.error = "failed", f"The harness stopped: {type(exc).__name__}. Try again in a minute."
        score = (run.report or {}).get("score")
        log.info(
            "run=%s user=%s week=%s target=%s status=%s score=%s duration_s=%.0f",
            run.id,
            run.owner,
            run.week,
            run.target,
            run.status,
            score,
            time.perf_counter() - started,
        )
