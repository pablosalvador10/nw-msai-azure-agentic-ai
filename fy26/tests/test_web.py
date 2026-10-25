"""The course website (web/): GitHub sign-in, what it serves, and the online harness. Offline: GitHub is faked."""

import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from harness.checks import CORE, WEEKS
from web.auth import Signer, User
from web.catalog import Catalog
from web.config import FY26, Settings
from web.hints import HINTS, WEEK_DIRS
from web.main import SESSION_COOKIE, create_app, safe_next
from web.runs import RunQueue, TargetError, validate_target
from web.shell import Shell
from web.site import Site, published_files

REPO = "teacher/course"
PUBLIC = ("20.1.2.3",)


class FakeGitHub:
    """Stands in for GitHub: code 'good' signs in as the given user; access says whether they can read the repo."""

    def __init__(self, login: str = "octocat", access: bool = True) -> None:
        self.login, self.access = login, access
        self.client_id = "client-id"

    def authorize_url(self, redirect_uri: str, state: str, challenge: str) -> str:
        return f"https://github.com/login/oauth/authorize?client_id=client-id&state={state}&code_challenge={challenge}"

    def exchange(self, code: str, redirect_uri: str, verifier: str) -> str:
        from web.auth import GitHubError

        if code != "good" or not verifier:
            raise GitHubError("bad code")
        return "user-token"

    def user(self, token: str) -> User:
        return User(login=self.login, id=42)

    def can_read(self, token: str, repo: str) -> bool:
        return self.access and repo == REPO


def fake_report(week: int, score: float = 87.5) -> dict:
    checks = [*CORE, *WEEKS[week]]
    return {
        "harness_version": "test",
        "week": week,
        "target": "https://ca-x.env.eastus2.azurecontainerapps.io",
        "service": {"student_id": "tester", "version": "v1"},
        "started_at": "2026-10-23T10:00:00+00:00",
        "duration_s": 1.0,
        "score": score,
        "checks": [
            {
                "id": c.id,
                "title": c.title,
                "weight": c.weight,
                "score": 0.5,
                "passed": False,
                "detail": "",
                "exchanges": [],
            }
            for c in checks
        ],
        "digest": "sha256:test",
    }


class FakeRunner:
    def __init__(self, delay: float = 0.0) -> None:
        self.calls: list[tuple[str, int, str | None]] = []
        self.delay = delay

    def __call__(self, url, week, api_key, progress):
        self.calls.append((url, week, api_key))
        for check in [*CORE, *WEEKS[week]]:
            progress(check.id)
            time.sleep(self.delay)
        return fake_report(week)


README_MD = """# Week 5 overview

**Date:** Oct 27 · **Lab:** [lab.ipynb](lab.ipynb)

Intro with a [lab](lab.ipynb), [setup](../setup/README.md), [agents](../../.github/READMEGC.md#help),
[example env](../.env.example), [lecture](docs/lecture.html) and [the web](https://learn.microsoft.com).

<script>alert(1)</script>

## Part one

| Check | Weight |
|---|---|
| w05.chat | 1 |

```mermaid
flowchart LR
  A["Learn<br/>notebook"] --> B
```

```python
print("hi")
```

## Part one

A repeated heading gets its own anchor.
"""

LAB_IPYNB = {
    "cells": [
        {
            "cell_type": "markdown",
            "source": ["# Week 5 lab\n", "\n", "## Part 1 · Call a model\n", "Read [the lecture](docs/lecture.html)."],
        },
        {"cell_type": "code", "source": ["import course\n", "course.setup()"], "outputs": [], "execution_count": None},
    ],
    "metadata": {},
    "nbformat": 4,
    "nbformat_minor": 5,
}


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    files = {
        "index.html": "<html><body>The repository's offline home page</body></html>",
        "assets/lecture.css": "body{}",
        "week05-fundamentals-of-azure-ai/docs/lecture.html": (
            '<title>Week 5 lecture</title><h1>Week 5<span class="hero-subtitle"><strong>Models, keys &amp; data.'
            "</strong></span></h1><table><tr><td>You build</td><td><code>POST /v1/classify</code>: triage</td></tr>"
            '</table><section id="s2"><h2>2 · Models</h2></section>'
        ),
        "week05-fundamentals-of-azure-ai/README.md": README_MD,
        "week05-fundamentals-of-azure-ai/lab.ipynb": json.dumps(LAB_IPYNB),
        "setup/README.md": "# Setup\n",
        "app/main.py": "print('code') if 1 < 2 else None\n",
        "app/data/handbook/rides.md": "# Rides\n\nRide rules.\n",
        "uv.lock": "lock",
        ".env": "SECRET=1",
        ".env.example": "KEY=",
        "infra/terraform.tfvars": "subscription_id = 'x'",
        "infra/terraform.tfstate": '{"secret": "state"}',
        "reports/week05-x.json": '{"secret": "report"}',
        "web/main.py": "SECRET = 'web'",
    }
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def make_settings(site_dir: Path, **overrides) -> Settings:
    values = {
        "public_url": "http://testserver",
        "github_client_id": "client-id",
        "github_client_secret": SecretStr("client-secret"),
        "course_repo": REPO,
        "course_ref": "main",
        "site_dir": site_dir,
    }
    values.update(overrides)
    return Settings(**values)


def make_client(site_dir: Path, github: FakeGitHub | None = None, runs: RunQueue | None = None, **overrides):
    app = create_app(
        make_settings(site_dir, **overrides),
        github=github or FakeGitHub(),
        runs=runs or RunQueue(FakeRunner()),
        resolve=lambda host: list(PUBLIC),
    )
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


def sign_in(client: TestClient, next_path: str = "/") -> TestClient:
    login = client.get("/auth/login", params={"next": next_path})
    assert login.status_code == 302
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    done = client.get("/auth/callback", params={"code": "good", "state": state})
    assert done.status_code == 303, done.text
    assert done.headers["location"] == next_path
    return client


# ---------------------------------------------------------------------------- sign-in


def test_unconfigured_site_refuses_everything_except_health(site_dir: Path) -> None:
    client = make_client(site_dir, github_client_secret=SecretStr(""))
    assert client.get("/healthz").json()["status"] == "ok"
    for path in ("/", "/auth/login", "/api/me"):
        response = client.get(path)
        assert response.status_code == 503
        assert "LECTURES_GITHUB_CLIENT_SECRET" in response.text


def test_anonymous_visitor_is_sent_to_github_sign_in(site_dir: Path) -> None:
    client = make_client(site_dir)
    page = client.get("/week05-fundamentals-of-azure-ai/docs/lecture.html")
    assert page.status_code == 303
    assert page.headers["location"].startswith("/auth/login?next=%2Fweek05")
    assert client.get("/api/me").status_code == 401

    login = client.get("/auth/login", params={"next": "/score/"})
    location = urlsplit(login.headers["location"])
    query = parse_qs(location.query)
    assert location.netloc == "github.com" and query["client_id"] == ["client-id"]
    assert query["state"][0] and query["code_challenge"][0]
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Path=/auth" in cookie and "samesite=lax" in cookie.lower()


def test_sign_in_sets_a_session_and_serves_the_course(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir), "/score/")
    assert client.get("/api/me").json()["login"] == "octocat"

    home = client.get("/")
    assert home.status_code == 200
    assert "Build, deploy and harden an AI support service" in home.text and 'href="/score/"' in home.text
    assert "Fundamentals of Azure AI" in home.text and "Models, keys &amp; data." in home.text
    assert "<code>POST /v1/classify</code>" in home.text and "repository's offline home page" not in home.text
    assert home.headers["x-content-type-options"] == "nosniff"
    assert client.get("/index.html").headers["location"] == "/"
    lecture = client.get("/week05-fundamentals-of-azure-ai/docs/lecture.html").text
    assert lecture.startswith("<title>Week 5") and '<script src="/_site/lecture-addon.js"></script>' in lecture
    assert client.get("/assets/lecture.css").text == "body{}"
    score = client.get("/score/").text
    assert "<h1>Score your service</h1>" in score and 'id="run-form"' in score and "/_site/score.js" in score
    for asset in ("site.js", "site.css", "score.js", "lecture-addon.js", "favicon.svg"):
        assert client.get(f"/_site/{asset}").status_code == 200, asset
    assert client.get("/_site/missing.js").status_code == 404


def test_sign_out_needs_a_post(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    assert 'method="post" action="/auth/logout"' in client.get("/").text
    # A GET (a crawler, a prefetch, a link on another site) only shows the button.
    assert 'method="post"' in client.get("/auth/logout").text
    assert client.get("/api/me").status_code == 200
    out = client.post("/auth/logout")
    assert out.status_code == 200 and "lectures_session=" in out.headers["set-cookie"]
    assert client.get("/api/me").status_code == 401


def test_session_cookie_is_secure_on_https(site_dir: Path) -> None:
    client = make_client(site_dir, public_url="https://lectures.example")
    login = client.get("/auth/login")
    assert "Secure" in login.headers["set-cookie"]


def test_wrong_state_or_code_is_refused(site_dir: Path) -> None:
    client = make_client(site_dir)
    client.get("/auth/login")
    assert client.get("/auth/callback", params={"code": "good", "state": "forged"}).status_code == 400
    assert client.get("/auth/callback", params={"error": "access_denied"}).status_code == 403
    assert client.get("/api/me").status_code == 401


def test_user_without_repository_access_gets_no_session(site_dir: Path) -> None:
    client = make_client(site_dir, github=FakeGitHub(login="stranger", access=False))
    login = client.get("/auth/login")
    state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
    denied = client.get("/auth/callback", params={"code": "good", "state": state})
    assert denied.status_code == 403
    assert "@stranger" in denied.text and SESSION_COOKIE not in denied.headers.get("set-cookie", "")
    assert client.get("/api/me").status_code == 401


def test_forged_or_expired_session_is_rejected(site_dir: Path) -> None:
    client = make_client(site_dir)
    forged = Signer(b"another-secret", "session").dumps({"login": "admin", "id": 1}, 3600)
    client.cookies.set(SESSION_COOKIE, forged)
    assert client.get("/api/me").status_code == 401

    signer = Signer(b"client-secret", "session")
    expired = signer.dumps({"login": "octocat", "id": 42}, -10)
    assert signer.loads(expired) is None
    valid = signer.dumps({"login": "octocat", "id": 42}, 60)
    payload, signature = valid.split(".")
    assert signer.loads(payload + "x." + signature) is None
    assert signer.loads("not-a-token") is None and signer.loads("é.é") is None
    # A state cookie is signed for another purpose and cannot be replayed as a session.
    assert signer.loads(Signer(b"client-secret", "oauth-state").dumps({"login": "x", "id": 1}, 60)) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/score/?week=6", "/score/?week=6"),
        ("//evil.example", "/"),
        ("https://evil.example", "/"),
        ("/\\evil.example", "/"),
        ("/auth/logout", "/"),
        ("/ok\r\nSet-Cookie: x=1", "/"),
    ],
)
def test_after_sign_in_redirect_stays_on_site(raw: str, expected: str) -> None:
    assert safe_next(raw) == expected


# ---------------------------------------------------------------------------- what is served


def test_secrets_and_the_website_itself_are_never_served(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    for path in (
        "/.env",
        "/%2eenv",
        "/week05-fundamentals-of-azure-ai/docs/../../.env",
        "/infra/terraform.tfvars",
        "/infra/terraform.tfstate",
        "/reports/week05-x.json",
        "/web/main.py",
        "/reports/",
        "/web/",
    ):
        response = client.get(path)
        assert response.status_code in (302, 404), path
        assert (
            "SECRET" not in response.text and "secret" not in response.text and "subscription_id" not in response.text
        )
    assert client.get("/.env").status_code == 404
    assert client.get("/uv.lock").headers["location"] == f"https://github.com/{REPO}/blob/main/fy26/uv.lock"
    assert client.get("/api/unknown").status_code == 404


def test_markdown_renders_as_a_lecture_style_page(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    page = client.get("/week05-fundamentals-of-azure-ai/README.md")
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    text = page.text
    assert "<h1>Week 5 overview</h1>" in text and "Week 5 · Fundamentals of Azure AI" in text
    assert '<h2 id="part-one">Part one</h2>' in text and '<h2 id="part-one-1">Part one</h2>' in text
    assert '<div class="table-wrap"><table>' in text and '<pre class="code"><code>print("hi")' in text
    assert '<pre class="mermaid">flowchart LR' in text and 'data-mermaid="/_site/mermaid-12.2.0.min.js"' in text
    assert "<script>alert(1)</script>" not in text  # raw HTML in Markdown is shown as text, never run
    assert 'href="/week05-fundamentals-of-azure-ai/lab.ipynb"' in text
    assert 'href="/setup/README.md"' in text and 'href="/week05-fundamentals-of-azure-ai/docs/lecture.html"' in text
    assert f'href="https://github.com/{REPO}/blob/main/.github/READMEGC.md#help"' in text
    assert f'href="https://github.com/{REPO}/blob/main/fy26/.env.example"' in text
    assert 'href="https://learn.microsoft.com"' in text
    assert f"https://github.com/{REPO}/blob/main/fy26/week05-fundamentals-of-azure-ai/README.md" in text


def test_notebooks_render_read_only_and_download(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    text = client.get("/week05-fundamentals-of-azure-ai/lab.ipynb").text
    assert "<h1>Week 5 lab</h1>" in text and "Week 5 · Main lab" in text and "Read-only copy" in text
    assert '<h2 id="part-1--call-a-model">Part 1 · Call a model</h2>' in text
    assert '<pre class="code nb-cell" data-lang="Python"><code>import course\ncourse.setup()</code></pre>' in text
    assert 'class="badge badge--required">Required</span>' in text
    # Previous / next follow the reading order: overview -> lecture -> lab -> deep dive.
    assert 'class="pager__link pager__link--prev" href="/week05-fundamentals-of-azure-ai/docs/lecture.html"' in text
    assert 'href="/week05-fundamentals-of-azure-ai/deep-dive.ipynb"' in text
    assert 'href="/week05-fundamentals-of-azure-ai/docs/lecture.html"' in text
    raw = client.get("/week05-fundamentals-of-azure-ai/lab.ipynb", params={"download": "1"})
    assert raw.headers["content-disposition"].startswith("attachment") and json.loads(raw.text) == LAB_IPYNB


def test_source_files_and_folders_render(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    code = client.get("/app/main.py").text
    assert '<pre class="code code--file" data-lang="Python"><code>print(\'code\') if 1 &lt; 2 else None' in code
    assert "fy26/app/main.py, as committed" in code

    week = client.get("/week05-fundamentals-of-azure-ai")
    assert week.status_code == 308 and week.headers["location"] == "/week05-fundamentals-of-azure-ai/"
    folder = client.get("/week05-fundamentals-of-azure-ai/").text
    assert "<h1>Week 5 overview</h1>" in folder and "In this folder" in folder
    for name in ('README.md"', 'lab.ipynb"', 'docs/"'):
        assert f'href="/week05-fundamentals-of-azure-ai/{name}' in folder
    handbook = client.get("/app/data/handbook/").text
    assert 'href="/app/data/handbook/rides.md"' in handbook
    root_app = client.get("/app/").text
    assert 'href="/app/data/"' in root_app and 'href="/app/main.py"' in root_app
    assert ".env" not in client.get("/infra/").text


def test_published_files_of_the_real_course() -> None:
    files = set(published_files(FY26))
    assert {"assets/lecture.css", "foundations/docs/primers.html", "README.md"} <= files
    assert {"setup/README.md", "setup/setup.ipynb", "app/contract.py", "infra/foundry.tf", "Dockerfile"} <= files
    for folder in WEEK_DIRS.values():
        for name in ("README.md", "lecture.md", "lab.ipynb", "docs/lecture.html", "docs/slides.html"):
            assert f"{folder}/{name}" in files
    leaked = [f for f in files if re.search(r"(^|/)(\.|web/|reports/|agent-file-memory/)|\.(tfvars|tfstate|lock)$", f)]
    assert not leaked


def test_every_real_course_document_renders_and_its_links_resolve() -> None:
    site = Site(FY26, REPO, "main", "fy26")
    shell = Shell(Catalog.load(FY26), "/_site/mermaid.js")
    broken = []
    for rel in published_files(FY26):
        if not rel.endswith((".md", ".ipynb")):
            continue
        page = site.document(FY26 / rel)
        assert page.title and page.body_html, rel
        html_page = shell.render(page, User("student", 1))
        assert "<h1>" in html_page and 'class="site-nav"' in html_page, rel
        for href in re.findall(r'href="(/[^"#?]*)', page.body_html):
            if not (FY26 / href.strip("/")).exists():
                broken.append(f"{rel} -> {href}")
    assert not broken


def test_the_real_course_map() -> None:
    catalog = Catalog.load(FY26, year=2026)
    assert [w.number for w in catalog.weeks] == list(WEEK_DIRS)
    for week in catalog.weeks:
        assert week.day is not None and week.day.year == 2026, f"Week {week.number}: no **Date:** in its README"
        assert week.tagline, f"Week {week.number}: no hero subtitle in docs/lecture.html"
        for link in week.links:
            assert (FY26 / link.href.strip("/")).exists(), link.href
    for link in catalog.sequence() + [link for _, links in catalog.sections() for link in links]:
        target = FY26 / link.href.strip("/")
        assert link.href == "/score/" or target.exists(), link.href


def test_the_sidebar_marks_where_you_are() -> None:
    shell = Shell(Catalog.load(FY26), "/_site/mermaid.js")
    week5 = "/week05-fundamentals-of-azure-ai"
    assert shell.active_href("/") is None
    assert shell.active_href(f"{week5}/lab.ipynb") == f"{week5}/lab.ipynb"
    assert shell.active_href(f"{week5}/lecture.md") == f"{week5}/docs/lecture.html"
    assert shell.active_href(f"{week5}/") == f"{week5}/README.md"
    assert shell.active_href("/setup/setup.ipynb") == "/setup/README.md"
    assert shell.active_href("/app/data/handbook/rides.md") == "/app/data/handbook/"
    assert shell.active_href("/AGENTS.md") is None


def test_week_status_follows_the_calendar(site_dir: Path) -> None:
    catalog = Catalog.load(site_dir, year=2026)
    week5 = catalog.weeks[0]
    assert week5.day == date(2026, 10, 27) and week5.builds == "POST /v1/classify"
    assert catalog.status(week5, date(2026, 10, 20)) == "next"
    assert catalog.status(week5, date(2026, 10, 29)) == "now"
    assert catalog.status(week5, date(2026, 11, 4)) == "past"
    assert catalog.focus(date(2026, 10, 29)) is week5


def test_search_index_covers_documents_headings_and_lecture_pages(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    index = client.get("/_site/search.json").json()
    by_url = {item["u"]: item for item in index}
    readme = by_url["/week05-fundamentals-of-azure-ai/README.md"]
    assert readme["t"] == "Week 5 overview" and ["Part one", "part-one"] in readme["h"]
    assert ["Part one", "part-one-1"] in readme["h"]
    assert by_url["/week05-fundamentals-of-azure-ai/docs/lecture.html"]["h"] == [["2 · Models", "s2"]]
    assert "/app/main.py" in by_url and not any("web/" in u or ".env" in u or "reports" in u for u in by_url)


# ---------------------------------------------------------------------------- online harness


def test_validate_target_allows_only_public_container_apps() -> None:
    suffixes = (".azurecontainerapps.io",)
    good = "https://ca-me-123abc.happy-1.eastus2.azurecontainerapps.io/"
    assert validate_target(good, suffixes, resolve=lambda h: list(PUBLIC)) == good.rstrip("/")
    bad = [
        "http://ca-me.env.eastus2.azurecontainerapps.io",
        "https://example.com",
        "https://azurecontainerapps.io",
        "https://evil.example/.azurecontainerapps.io",
        "https://user:pw@ca-me.env.eastus2.azurecontainerapps.io",
        "https://ca-me.env.eastus2.azurecontainerapps.io:8080",
        "https://ca-me.env.eastus2.azurecontainerapps.io/v1/info",
        "https://ca-me.env.eastus2.azurecontainerapps.io?x=1",
        "not a url",
    ]
    for url in bad:
        with pytest.raises(TargetError):
            validate_target(url, suffixes, resolve=lambda h: list(PUBLIC))
    for private in (["10.0.0.4"], ["169.254.169.254"], ["127.0.0.1"], ["20.1.2.3", "10.0.0.4"], ["fd00::1"]):
        with pytest.raises(TargetError, match="public address"):
            validate_target(good, suffixes, resolve=lambda h, a=private: a)

    def unresolvable(host: str) -> list[str]:
        raise OSError("no such host")

    with pytest.raises(TargetError, match="does not resolve"):
        validate_target(good, suffixes, resolve=unresolvable)
    with pytest.raises(TargetError, match="course website"):
        validate_target(good, suffixes, blocked=("ca-me-123abc.happy-1.eastus2.azurecontainerapps.io",))


def wait_for(client: TestClient, run_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in ("done", "failed"):
            return run
        time.sleep(0.02)
    raise AssertionError("run did not finish")


def test_a_run_scores_the_service_and_explains_what_to_fix(site_dir: Path) -> None:
    runner, github = FakeRunner(), FakeGitHub()
    client = sign_in(make_client(site_dir, github=github, runs=RunQueue(runner)))
    url = "https://ca-me.env.eastus2.azurecontainerapps.io"
    started = client.post("/api/runs", json={"url": url, "week": 6, "api_key": "k3y"})
    assert started.status_code == 202, started.text
    run = wait_for(client, started.json()["id"])

    assert run["status"] == "done" and run["completed"] == run["total"] == len(CORE) + len(WEEKS[6])
    assert run["report"]["score"] == 87.5 and run["report"]["digest"] == "sha256:test"
    assert set(run["advice"]) == {c.id for c in [*CORE, *WEEKS[6]]}
    assert all(a["hint"] for a in run["advice"].values())
    assert runner.calls == [(url, 6, "k3y")]
    assert "k3y" not in str(run)

    # Another student on the same site cannot read this run.
    github.login = "someone-else"
    other = sign_in(TestClient(client.app, raise_server_exceptions=False, follow_redirects=False))
    assert other.get("/api/me").json()["login"] == "someone-else"
    assert other.get(f"/api/runs/{run['id']}").status_code == 404
    assert client.get(f"/api/runs/{run['id']}").status_code == 200


def test_one_run_at_a_time_and_an_hourly_limit(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir, runs=RunQueue(FakeRunner(delay=0.05), per_hour=2)))
    body = {"url": "https://ca-me.env.eastus2.azurecontainerapps.io", "week": 5}
    first = client.post("/api/runs", json=body)
    assert client.post("/api/runs", json=body).status_code == 409
    wait_for(client, first.json()["id"])
    wait_for(client, client.post("/api/runs", json=body).json()["id"])
    limited = client.post("/api/runs", json=body)
    assert limited.status_code == 429 and "in-process" in limited.json()["detail"]


def test_bad_run_requests_are_refused_without_echoing_the_key(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    invalid = client.post(
        "/api/runs", json={"url": "https://ca-me.env.eastus2.azurecontainerapps.io", "week": 4, "api_key": "s3cret"}
    )
    assert invalid.status_code == 422 and "s3cret" not in invalid.text
    wrong_host = client.post("/api/runs", json={"url": "https://example.com", "week": 5})
    assert wrong_host.status_code == 422 and "azurecontainerapps.io" in wrong_host.json()["detail"]
    cross_site = client.post(
        "/api/runs",
        json={"url": "https://ca-me.env.eastus2.azurecontainerapps.io", "week": 5},
        headers={"Origin": "https://evil.example"},
    )
    assert cross_site.status_code == 403
    assert client.get("/api/runs/does-not-exist").status_code == 404


def test_every_check_has_a_hint_and_its_files_exist() -> None:
    ids = {c.id for c in CORE} | {c.id for checks in WEEKS.values() for c in checks}
    assert ids == set(HINTS)
    for hint, files in HINTS.values():
        assert hint
        for rel in files:
            assert (FY26 / rel).exists(), rel
    for folder in WEEK_DIRS.values():
        assert (FY26 / folder / "README.md").exists() and (FY26 / folder / "lab.ipynb").exists()
