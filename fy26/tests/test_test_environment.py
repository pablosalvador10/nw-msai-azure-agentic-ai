"""Test collection must not initialize telemetry from an exported environment or .env."""

import os
import subprocess
import sys
from pathlib import Path


def test_offline_run_ignores_telemetry_even_before_fixtures(tmp_path):
    course = Path(__file__).resolve().parents[1]
    connection = "InstrumentationKey=00000000-0000-0000-0000-000000000000"
    (tmp_path / ".env").write_text(f"APPLICATIONINSIGHTS_CONNECTION_STRING={connection}\n", encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(course), "APPLICATIONINSIGHTS_CONNECTION_STRING": connection}
    code = """
import sys
import pytest
from app import telemetry

def offline_only(settings):
    assert not settings.applicationinsights_connection_string, "Test run tried to enable Azure telemetry"

telemetry.configure_telemetry = offline_only
raise SystemExit(pytest.main(["-q", "-c", sys.argv[1], *sys.argv[2:]]))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            code,
            str(course / "pyproject.toml"),
            str(course / "tests/test_api_offline.py") + "::test_health_and_ready",
            # These modules import app.main, which builds an app (and configures telemetry) at import time.
            str(course / "tests/test_harness_cli.py") + "::test_list_prints_every_week_and_check",
            str(course / "tests/test_mcp_transport.py"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
