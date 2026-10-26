"""The course website: lectures and slides behind GitHub sign-in, and the online harness.

Run it locally (from fy26/, with a GitHub App whose callback is http://localhost:8000/auth/callback):

    LECTURES_GITHUB_CLIENT_ID=... LECTURES_GITHUB_CLIENT_SECRET=... LECTURES_COURSE_REPO=owner/repo \
    uv run uvicorn --factory web.main:create_app --reload

Every path except /healthz and /auth/* needs a session. See web/README.md for the design.
"""

import hmac
import html
import logging
import secrets
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlencode, urlsplit

import httpx2
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from web.auth import GitHub, GitHubError, Signer, User, pkce_challenge
from web.catalog import Catalog
from web.config import Settings
from web.hints import WEEK_TITLES, advice, week_links
from web.render import MERMAID
from web.runs import Resolver, Run, RunQueue, RunRejected, TargetError, resolve_host, validate_target
from web.shell import Page, Shell
from web.site import Site

log = logging.getLogger("lectures")

STATIC = Path(__file__).parent / "static"
# Shared website assets at /_site/. The Mermaid bundle is downloaded at image build (see web/Dockerfile).
SITE_FILES = {name: STATIC / name for name in ("site.js", "site.css", "score.js", "lecture-addon.js", "favicon.svg")}
VENDOR_FILES = {"mermaid-12.2.0.min.js": STATIC / "vendor" / "mermaid-12.2.0.min.js"}
SESSION_COOKIE = "lectures_session"
STATE_COOKIE = "lectures_oauth"
STATE_TTL_S = 600

PAGE_CSS = (
    "body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;box-sizing:border-box;"
    "font:16px/1.6 'Segoe UI Variable Text','Segoe UI',-apple-system,system-ui,sans-serif;color:#11142b;"
    "background:#f6f7fb}main{width:min(520px,100%);padding:36px 40px;border:1px solid #e3e6ee;border-radius:16px;"
    "background:#fff;box-shadow:0 1px 2px rgba(16,20,48,.04),0 18px 48px rgba(16,20,48,.07)}"
    ".brand{display:flex;align-items:center;gap:10px;margin:0 0 22px;font-weight:650;font-size:.92rem}"
    ".brand i{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#3341b8,#4b5bdb 48%,#0078d4)}"
    "h1{margin:0 0 10px;font-size:1.45rem;letter-spacing:-.015em}.body{color:#454b60}a{color:#252f8c}"
    "button{margin-top:18px;padding:9px 16px;border:0;border-radius:10px;background:#3341b8;color:#fff;"
    "font:inherit;font-weight:600;cursor:pointer}button:hover{background:#252f8c}"
)


class RunRequest(BaseModel):
    url: str = Field(min_length=8, max_length=300)
    week: Literal[5, 6, 7, 8, 10]
    api_key: str | None = Field(default=None, max_length=256)


def page(status: int, title: str, body_html: str) -> HTMLResponse:
    """A small standalone page (sign-in errors, sign-out). body_html must already be escaped."""
    return HTMLResponse(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)} · Agentic AI on Microsoft Foundry</title><style>{PAGE_CSS}</style></head>"
        f'<body><main><p class="brand"><i></i>Agentic AI on Microsoft Foundry</p><h1>{html.escape(title)}</h1>'
        f'<div class="body">{body_html}</div></main></body></html>',
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


def safe_next(path: str) -> str:
    """Only same-site paths after sign-in, never another host (open redirect) or the auth routes (loop)."""
    if not path.startswith("/") or path.startswith(("//", "/\\", "/auth/")) or any(c in path for c in "\r\n\\"):
        return "/"
    return path


def create_app(
    settings: Settings | None = None,
    *,
    github: GitHub | None = None,
    runs: RunQueue | None = None,
    resolve: Resolver = resolve_host,
) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = FastAPI(title="Course website", docs_url=None, redoc_url=None, openapi_url=None)

    missing = settings.missing()
    secret = settings.github_client_secret.get_secret_value().encode() or secrets.token_bytes(32)
    sessions, states = Signer(secret, "session"), Signer(secret, "oauth-state")
    github = github or GitHub(settings.github_client_id, settings.github_client_secret.get_secret_value())
    runs = runs or RunQueue(workers=settings.max_parallel_runs, per_hour=settings.runs_per_hour)
    site = Site(settings.site_dir, settings.course_repo, settings.course_ref, settings.course_dir)
    shell = Shell(Catalog.load(settings.site_dir), MERMAID)

    public = urlsplit(settings.public_url)
    public_origin = f"{public.scheme}://{public.netloc}"
    callback_url = f"{settings.public_url.rstrip('/')}/auth/callback"
    session_ttl = settings.session_hours * 3600
    cookie = {"httponly": True, "secure": settings.secure_cookies, "samesite": "lax"}

    @app.middleware("http")
    async def gate(request: Request, call_next: Any) -> Response:
        """Every request needs a valid session, except health probes and the sign-in routes themselves."""
        path = request.url.path
        if path != "/healthz":
            if missing:
                return page(503, "Not configured yet", "Set " + html.escape(", ".join(missing)) + ".")
            if not path.startswith("/auth/") and path != "/favicon.ico":
                data = sessions.loads(request.cookies.get(SESSION_COOKIE))
                if data is None:
                    if path.startswith("/api/"):
                        return JSONResponse({"detail": "Sign in first."}, status_code=401)
                    target = path + (f"?{request.url.query}" if request.url.query else "")
                    return RedirectResponse(f"/auth/login?{urlencode({'next': target})}", status_code=303)
                request.state.user = User(login=data["login"], id=data["id"])
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "private, no-cache")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_body(request: Request, exc: RequestValidationError) -> JSONResponse:
        # The default handler echoes the request body, which can contain the student's API key.
        fields = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
        return JSONResponse({"detail": f"Check these fields: {', '.join(fields) or 'body'}."}, status_code=422)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": settings.version}

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/auth/login")
    def login(next_path: str = Query("/", alias="next")) -> Response:
        state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
        response = RedirectResponse(github.authorize_url(callback_url, state, pkce_challenge(verifier)), 302)
        value = states.dumps({"state": state, "verifier": verifier, "next": safe_next(next_path)}, STATE_TTL_S)
        response.set_cookie(STATE_COOKIE, value, max_age=STATE_TTL_S, path="/auth", **cookie)
        return response

    @app.get("/auth/callback")
    def callback(request: Request, code: str = "", state: str = "", error: str = "") -> Response:
        again = '<a href="/auth/login">Sign in with GitHub</a>'
        if error:
            return page(403, "Sign-in cancelled", f"GitHub did not sign you in. {again} to try again.")
        data = states.loads(request.cookies.get(STATE_COOKIE))
        if not data or not code or not hmac.compare_digest(state.encode(), str(data.get("state", "")).encode()):
            return page(400, "Sign-in expired", f"That sign-in link is no longer valid. {again}.")
        try:
            token = github.exchange(code, callback_url, data["verifier"])
            user = github.user(token)
            allowed = github.can_read(token, settings.course_repo)
        except (GitHubError, httpx2.HTTPError) as exc:
            log.warning("Sign-in failed: %s", exc)
            return page(502, "GitHub did not answer", f"Try again in a minute. {again}.")
        if not allowed:
            log.info("Denied %s: no read access to the course repository", user.login)
            response = page(
                403,
                "No access yet",
                f"You are signed in to GitHub as <b>@{html.escape(user.login)}</b>, but this account cannot read "
                "the course repository. Accept the invitation to the course repository (GitHub notifications "
                f'or email), then {again} again. Wrong account? <a href="https://github.com/logout">Sign out of '
                "GitHub</a> first.",
            )
            response.delete_cookie(STATE_COOKIE, path="/auth")
            return response
        log.info("Signed in %s", user.login)
        response = RedirectResponse(safe_next(str(data.get("next", "/"))), status_code=303)
        value = sessions.dumps({"login": user.login, "id": user.id}, session_ttl)
        response.set_cookie(SESSION_COOKIE, value, max_age=session_ttl, path="/", **cookie)
        response.delete_cookie(STATE_COOKIE, path="/auth")
        return response

    @app.get("/auth/logout")
    def logout_page() -> Response:
        # Signing out is a POST: a GET link would let crawlers, prefetchers or another site end the session.
        form = '<form method="post" action="/auth/logout"><button type="submit">Sign out</button></form>'
        return page(200, "Sign out", f"Sign out of the course website on this browser.{form}")

    @app.post("/auth/logout")
    def logout() -> Response:
        response = page(200, "Signed out", '<a href="/auth/login">Sign in again</a>')
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    def view(run: Run) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": run.id,
            "week": run.week,
            "week_title": WEEK_TITLES[run.week],
            "target": run.target,
            "status": run.status,
            "current": run.current,
            "completed": run.completed,
            "total": run.total,
            "position": runs.position(run) if run.status == "queued" else 0,
            "error": run.error,
            "links": week_links(run.week),
        }
        if run.report is not None:
            body["report"] = run.report
            body["advice"] = advice(run.report)
        return body

    @app.get("/api/me")
    def me(request: Request) -> dict[str, Any]:
        return {"login": request.state.user.login, "weeks": WEEK_TITLES}

    @app.post("/api/runs", status_code=202)
    def start_run(body: RunRequest, request: Request) -> Any:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != public_origin:
            return JSONResponse({"detail": "Cross-site request refused."}, status_code=403)
        try:
            url = validate_target(body.url, settings.suffixes, blocked=(public.hostname or "",), resolve=resolve)
            run = runs.submit(request.state.user.login, url, body.week, body.api_key or None)
        except TargetError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=422)
        except RunRejected as exc:
            return JSONResponse({"detail": str(exc)}, status_code=exc.status)
        return view(run)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, request: Request) -> Any:
        run = runs.get(request.state.user.login, run_id)
        if run is None:
            return JSONResponse({"detail": "No such run."}, status_code=404)
        return view(run)

    @app.get("/score")
    def score_redirect() -> Response:
        return RedirectResponse("/score/", status_code=308)

    @app.get("/score/")
    def score_page(request: Request) -> Response:
        score = Page(
            title="Score your service",
            path="/score/",
            kicker="Online harness",
            lede="Paste the URL of your deployed service and choose the week. The site runs the same checks as "
            "the harness on your laptop, then shows every check, its evidence, and what to try next.",
            crumbs=[("Course home", "/")],
            body_html=(STATIC / "score-body.html").read_text(encoding="utf-8"),
            toc=False,
            track=False,
            prose=False,
            scripts=["/_site/score.js"],
        )
        return HTMLResponse(shell.render(score, request.state.user))

    @app.get("/_site/search.json")
    def search_index() -> Response:
        return JSONResponse(site.search_index, headers={"Cache-Control": "private, max-age=300"})

    @app.get("/_site/{name}")
    def site_asset(name: str) -> Response:
        if name in SITE_FILES:
            return FileResponse(SITE_FILES[name])
        vendor = VENDOR_FILES.get(name)
        if vendor is not None and vendor.is_file():
            # Versioned file name: browsers may keep it for a week.
            return FileResponse(vendor, headers={"Cache-Control": "private, max-age=604800, immutable"})
        return page(404, "Not found", '<a href="/">Course home</a>')

    @app.get("/")
    def home(request: Request) -> Response:
        return HTMLResponse(shell.render(shell.home(date.today()), request.state.user))

    @app.get("/index.html")
    def old_home() -> Response:
        return RedirectResponse("/", status_code=308)

    @app.get("/{path:path}")
    def site_file(path: str, request: Request, download: bool = False) -> Response:
        file = site.file(path)
        if file is not None:
            rendered = site.render(file)
            return HTMLResponse(rendered) if rendered is not None else FileResponse(file)
        content = site.content(path)
        if content is not None:
            if download:
                return FileResponse(content, filename=content.name, content_disposition_type="attachment")
            return HTMLResponse(shell.render(site.document(content), request.state.user))
        folder = site.folder(path)
        if folder is not None:
            if not path.endswith("/"):
                return RedirectResponse(f"/{path}/", status_code=308)
            return HTMLResponse(shell.render(site.listing(folder), request.state.user))
        source = None if path.startswith(("api/", "_site/")) else site.source_url(path)
        if source:
            return RedirectResponse(source, status_code=302)
        return page(404, "Not found", '<a href="/">Course home</a>')

    return app
