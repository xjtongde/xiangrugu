"""Unit contracts for the persistent development watcher."""

from __future__ import annotations

import json
from pathlib import Path

from xiangrugu_datamgmt.devwatch import snapshot, write_status
from xiangrugu_datamgmt import devwatch


def test_change_during_test_execution_triggers_another_run(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "example.py"
    source.write_text("value = 1\n", encoding="utf-8")
    runs = []

    def fake_run(*args, **kwargs):
        runs.append(1)
        if len(runs) == 1:
            source.write_text("value = 12345\n", encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    def stop_after_second_poll(_interval):
        if polls.pop() == 1:
            raise InterruptedError("end test loop")

    polls = [1, 0]
    monkeypatch.setattr(devwatch.subprocess, "run", fake_run)
    monkeypatch.setattr(devwatch.time, "sleep", stop_after_second_poll)
    monkeypatch.setattr(devwatch.signal, "signal", lambda *args: None)
    import pytest
    with pytest.raises(InterruptedError):
        devwatch.main(["--root", str(tmp_path), "--status", str(tmp_path / "status.json")])
    assert len(runs) == 2


def test_snapshot_tracks_source_but_ignores_runtime_and_repository_state(tmp_path: Path) -> None:
    source = tmp_path / "datamgmt" / "src" / "example.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    ignored = [tmp_path / ".git" / "index", tmp_path / "data" / "state.yaml"]
    for path in ignored:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ignored\n", encoding="utf-8")

    result = snapshot(tmp_path)

    assert "datamgmt/src/example.py" in result
    assert ".git/index" not in result
    assert "data/state.yaml" not in result


def test_write_status_records_machine_readable_result(tmp_path: Path) -> None:
    status = tmp_path / "devwatch" / "status.json"

    write_status(status, run=2, returncode=1)

    payload = json.loads(status.read_text(encoding="utf-8"))
    assert payload["run"] == 2
    assert payload["returncode"] == 1
    assert payload["finished_at"].endswith("Z")
