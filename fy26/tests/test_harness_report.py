"""Repeated grading runs must preserve every proof, including runs in the same second."""

import json
from datetime import datetime
from unittest.mock import Mock

from harness import report as reporting
from harness.engine import Report


def test_saving_two_reports_at_the_same_time_keeps_both(tmp_path, monkeypatch):
    clock = Mock()
    clock.now.return_value = datetime(2026, 10, 22, 12, 0, 0)
    monkeypatch.setattr(reporting, "datetime", clock)
    first = Report(5, "https://first.invalid", "2026-10-22T12:00:00Z", 0.1, [], {})
    second = Report(5, "https://second.invalid", "2026-10-22T12:00:00Z", 0.1, [], {})

    first_json, first_md = reporting.save(first, tmp_path)
    second_json, second_md = reporting.save(second, tmp_path)

    assert first_json != second_json
    assert first_md != second_md
    assert json.loads(first_json.read_text())["target"] == first.target
    assert json.loads(second_json.read_text())["target"] == second.target
    assert first.target in first_md.read_text()
    assert second.target in second_md.read_text()
