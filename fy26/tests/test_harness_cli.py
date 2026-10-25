"""The harness command line: list the checks, score a service, reject a malformed URL."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main
import harness.__main__ as cli
from harness.checks import CORE, WEEKS
from harness.client import Target
from tests.conftest import offline_settings


def test_list_prints_every_week_and_check(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["list"]) == 0

    out = capsys.readouterr().out
    for week, checks in WEEKS.items():
        assert f"Week {week}" in out
        assert all(check.id in out for check in [*CORE, *checks])


def test_check_in_process_writes_the_report_and_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real_create_app = app.main.create_app
    monkeypatch.setattr(app.main, "create_app", lambda: real_create_app(offline_settings()))

    assert cli.main(["check", "--week", "5", "--in-process", "--out", str(tmp_path)]) == 0

    assert "Report:" in capsys.readouterr().out
    assert list(tmp_path.glob("*.md"))
    assert list(tmp_path.glob("*.json"))


def test_check_url_scores_the_given_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    targets: list[str] = []

    def target(url: str, *, api_key: str | None, timeout: float) -> Target:
        targets.append(url)
        return Target(client=client, api_key=api_key)

    monkeypatch.setattr(cli, "Target", target)

    assert cli.main(["check", "--week", "5", "--url", "https://example.test", "--out", str(tmp_path)]) == 0
    assert targets == ["https://example.test"]


def test_check_rejects_a_url_without_a_scheme(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["check", "--week", "5", "--url", "my-app.azurecontainerapps.io"])

    assert exit_info.value.code == 2
    assert "--url must start with http:// or https://" in capsys.readouterr().err
