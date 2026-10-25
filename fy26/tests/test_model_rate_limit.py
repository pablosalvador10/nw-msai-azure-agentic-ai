"""A model deployment at its tokens-per-minute limit must surface as 503 + Retry-After, not as a 500."""

import pytest
from fastapi.testclient import TestClient

from app.middleware import is_model_rate_limited
from app.services import chat
from tests.conftest import offline_settings


class RateLimitError(Exception):
    """Stand-in with the same name and message shape as openai.RateLimitError."""


def test_rate_limit_is_found_through_the_exception_chain():
    def agent_run():
        try:
            raise RateLimitError("Error code: 429 - rate_limit_exceeded")
        except RateLimitError as inner:
            raise RuntimeError("agent run failed") from inner

    with pytest.raises(RuntimeError) as outer:
        agent_run()
    assert is_model_rate_limited(outer.value)
    assert not is_model_rate_limited(ValueError("bad input"))


def test_model_at_capacity_returns_503_with_retry_after(monkeypatch):
    from app.main import create_app

    async def at_capacity(state, request):
        raise RateLimitError("Error code: 429 - rate_limit_exceeded")

    monkeypatch.setattr(chat, "chat", at_capacity)
    with TestClient(create_app(offline_settings()), raise_server_exceptions=False) as client:
        response = client.post("/v1/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert response.headers["retry-after"] == "10"
    assert response.headers["x-request-id"]
