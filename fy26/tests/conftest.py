"""Shared fixtures. Every test runs offline: no Azure, no network."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import LLMMode, Settings


def offline_settings(**overrides) -> Settings:
    values = {"llm_mode": LLMMode.OFFLINE, "student_id": "tester", "app_version": "test", "_env_file": None}
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ignore service settings exported to the shell (a notebook loads .env into os.environ)."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")


@pytest.fixture
def client() -> Iterator[TestClient]:
    from app.main import create_app

    with TestClient(create_app(offline_settings()), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_with_key() -> Iterator[TestClient]:
    from app.main import create_app

    settings = offline_settings(service_api_key=SecretStr("s3cret"))
    with TestClient(create_app(settings), raise_server_exceptions=False) as c:
        yield c
