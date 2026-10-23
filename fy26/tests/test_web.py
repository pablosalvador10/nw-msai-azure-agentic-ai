"""The course website (web/): GitHub sign-in, what it serves, and the online harness. Offline: GitHub is faked."""

import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from harness.checks import CORE, WEEKS
from web.auth import Signer, User
from web.config import FY26, Settings
from web.hints import HINTS, WEEK_DIRS
from web.main import SESSION_COOKIE, create_app, safe_next
from web.runs import RunQueue, TargetError, validate_target
from web.site import INDEX_MARKER, published_files

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


@pytest.fixture
def site_dir(tmp_path: Path) -> Path:
    files = {
        "index.html": f"<html><body>{INDEX_MARKER}</body></html>",
        "assets/lecture.css": "body{}",
        "week05-fundamentals-of-azure-ai/docs/lecture.html": "<h1>Week 5</h1>",
        "week05-fundamentals-of-azure-ai/lab.ipynb": "{}",
        ".env": "SECRET=1",
        "app/main.py": "print('code')",
        "infra/terraform.tfvars": "subscription_id = 'x'",
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
    assert 'href="score/"' in home.text
    assert home.headers["x-content-type-options"] == "nosniff"
    lecture = client.get("/week05-fundamentals-of-azure-ai/docs/lecture.html").text
    assert lecture.startswith("<h1>Week 5</h1>") and '<script src="/score/site.js"></script>' in lecture
    assert client.get("/assets/lecture.css").text == "body{}"
    assert client.get("/score/").status_code == 200
    assert client.get("/score/score.js").status_code == 200
    assert client.get("/score/site.js").status_code == 200
    assert client.get("/score/missing.js").status_code == 404


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


def test_only_published_pages_are_served_and_code_links_open_on_github(site_dir: Path) -> None:
    client = sign_in(make_client(site_dir))
    for secret in ("/.env", "/%2eenv", "/week05-fundamentals-of-azure-ai/docs/../../.env", "/infra/terraform.tfvars"):
        response = client.get(secret)
        assert "SECRET" not in response.text and "subscription_id" not in response.text
        assert response.status_code in (302, 404)
    assert client.get("/.env").status_code == 404

    lab = client.get("/week05-fundamentals-of-azure-ai/lab.ipynb")
    assert lab.status_code == 302
    assert lab.headers["location"] == (
        f"https://github.com/{REPO}/blob/main/fy26/week05-fundamentals-of-azure-ai/lab.ipynb"
    )
    folder = client.get("/app/data/handbook/")
    assert folder.headers["location"] == f"https://github.com/{REPO}/tree/main/fy26/app/data/handbook/"
    assert client.get("/api/unknown").status_code == 404


def test_published_files_of_the_real_course() -> None:
    files = published_files(FY26)
    assert "index.html" in files and "assets/lecture.css" in files and "foundations/docs/primers.html" in files
    for folder in WEEK_DIRS.values():
        assert f"{folder}/docs/lecture.html" in files
        assert f"{folder}/docs/slides.html" in files
    assert not [f for f in files if re.search(r"\.(ipynb|md|py|tf|tfvars|env|json|jsonl)$", f)]
    # The score link is injected next to this anchor; if the home page changes, update web/site.py.
    assert INDEX_MARKER in (FY26 / "index.html").read_text(encoding="utf-8")


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
