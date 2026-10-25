"""GitHub sign-in: signed values, PKCE, and the three GitHub calls (against a mock transport)."""

import json

import httpx2
import pytest

from web.auth import GitHub, GitHubError, Signer, User, pkce_challenge

REDIRECT = "https://site.test/auth/callback"


def github(handler) -> GitHub:
    """A GitHub client whose HTTP calls go to `handler` instead of the network."""
    client = GitHub("client-id", "client-secret")
    client._http = httpx2.Client(transport=httpx2.MockTransport(handler))
    return client


def test_signer_needs_a_secret() -> None:
    with pytest.raises(ValueError, match="secret"):
        Signer(b"", "session")


@pytest.mark.parametrize("token", [None, "", "no-dot", "a.b.c", "bm90IGpzb24.sig"])
def test_signer_rejects_malformed_tokens(token: str | None) -> None:
    assert Signer(b"k", "session").loads(token) is None


def test_signer_rejects_a_signed_payload_that_is_not_json() -> None:
    signer = Signer(b"k", "session")
    payload = "bm90IGpzb24"  # base64url of "not json"
    assert signer.loads(f"{payload}.{signer._sign(payload)}") is None


def test_signer_keys_differ_by_purpose_and_expire() -> None:
    session = Signer(b"k", "session")
    token = session.dumps({"login": "octocat"}, ttl_s=60)

    assert session.loads(token)["login"] == "octocat"
    assert Signer(b"k", "state").loads(token) is None
    assert session.loads(session.dumps({"login": "octocat"}, ttl_s=-1)) is None


def test_pkce_challenge_matches_rfc_7636_appendix_b() -> None:
    assert (
        pkce_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_authorize_url_asks_for_s256_pkce_and_no_sign_up() -> None:
    url = GitHub("client-id", "secret").authorize_url(REDIRECT, "state-1", "challenge-1")
    query = httpx2.URL(url).params

    assert url.startswith("https://github.com/login/oauth/authorize?")
    assert query["client_id"] == "client-id"
    assert query["redirect_uri"] == REDIRECT
    assert query["code_challenge_method"] == "S256"
    assert query["allow_signup"] == "false"
    assert "secret" not in url


def test_exchange_sends_the_verifier_and_returns_the_token() -> None:
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json={"access_token": "gho_token"})

    assert github(handler).exchange("code-1", REDIRECT, "verifier-1") == "gho_token"
    form = dict(httpx2.QueryParams(sent[0].content.decode()))
    assert form["code"] == "code-1"
    assert form["code_verifier"] == "verifier-1"
    assert form["client_secret"] == "client-secret"


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(200, json={"error": "bad_verification_code"}),
        httpx2.Response(200, text="not json"),
        httpx2.Response(500, json={"access_token": "gho_token"}),
    ],
)
def test_exchange_fails_without_a_token(response: httpx2.Response) -> None:
    with pytest.raises(GitHubError, match="did not issue a token"):
        github(lambda _: response).exchange("code-1", REDIRECT, "verifier-1")


def test_user_reads_login_and_id_with_the_bearer_token() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        assert request.headers["Authorization"] == "Bearer gho_token"
        return httpx2.Response(200, json={"login": "octocat", "id": 1})

    assert github(handler).user("gho_token") == User(login="octocat", id=1)


@pytest.mark.parametrize(
    "response",
    [httpx2.Response(401, json={"message": "Bad credentials"}), httpx2.Response(200, json=["not", "a", "user"])],
)
def test_user_fails_on_an_unexpected_answer(response: httpx2.Response) -> None:
    with pytest.raises(GitHubError, match="did not return the user"):
        github(lambda _: response).user("gho_token")


@pytest.mark.parametrize(("code", "allowed"), [(200, True), (403, False), (404, False)])
def test_can_read_maps_the_repository_answer(code: int, allowed: bool) -> None:
    assert github(lambda _: httpx2.Response(code, text=json.dumps({}))).can_read("gho_token", "org/repo") is allowed


def test_can_read_raises_when_github_fails() -> None:
    with pytest.raises(GitHubError, match="503"):
        github(lambda _: httpx2.Response(503)).can_read("gho_token", "org/repo")


def test_can_read_follows_a_renamed_repository() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/repos/org/old-name":
            return httpx2.Response(301, headers={"Location": "https://api.github.com/repositories/42"})
        assert request.headers["Authorization"] == "Bearer gho_token"
        return httpx2.Response(200, json={"full_name": "org/new-name"})

    assert github(handler).can_read("gho_token", "org/old-name") is True
