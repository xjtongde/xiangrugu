"""Lease loss must stop the whole artificial process group, without Docker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


def implementation():
    from xiangrugu_datamgmt import candidate_supervisor
    return candidate_supervisor


def lease(path, seq=1):
    path.write_text(f"{time.time()}\n{seq}\nMemAvailable: 6000000 kB\n0.1 0.1 0.1 1/100 1\n"
        "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
        "some avg10=0.00 avg60=0.00 avg300=0.00 total=0\npswpout 0\n20000000000\ntrue\n")


@pytest.mark.parametrize("bad", ["", "{}", "nan\n1", "0\n1", "-1\n1"])
def test_invalid_lease_stops_before_worker(tmp_path, bad):
    path = tmp_path / "lease"
    path.write_text(bad)
    with pytest.raises(ValueError):
        implementation().read_lease(path)


def test_real_short_worker_is_monitored(tmp_path):
    module = implementation()
    path = tmp_path / "lease"
    lease(path)
    result = module.supervise([sys.executable, "-c", "pass"], lease=path,
        evidence=tmp_path / "monitor.json", max_seconds=5, lease_seconds=0.5, poll_seconds=0.02)
    assert result["status"] == "SYNTHETIC_WORKER_COMPLETED"
    assert result["worker_exit_code"] == 0
    assert result["samples"] and not result["ready_for_import"]
    assert int(result["cgroup_stats"]["memory.peak"]) > 0
    assert "nr_throttled" in result["cgroup_stats"]["cpu.stat"]


def test_failed_worker_cannot_publish(tmp_path):
    path = tmp_path / "lease"
    lease(path)
    result = implementation().supervise([sys.executable, "-c", "raise SystemExit(7)"],
        lease=path, evidence=tmp_path / "monitor.json", max_seconds=5, poll_seconds=0.02)
    assert result["status"] == "SYNTHETIC_WORKER_STOPPED"
    assert result["reason"] == "worker_exit"
    assert result["worker_exit_code"] == 7


@pytest.mark.parametrize("cause", ["lease", "timeout", "cancel"])
def test_monitor_loss_timeout_and_cancel_kill_descendants(tmp_path, cause):
    path = tmp_path / "lease"
    lease(path)
    child_pid = tmp_path / "child.pid"
    code = ("import subprocess,sys,time,pathlib; "
        "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        f"pathlib.Path({str(child_pid)!r}).write_text(str(p.pid)); "
        "p.wait()")
    started = time.monotonic()
    result = implementation().supervise([sys.executable, "-c", code], lease=path,
        evidence=tmp_path / "monitor.json", max_seconds=0.8 if cause == "timeout" else 5,
        lease_seconds=0.8 if cause == "lease" else 25, poll_seconds=0.02,
        cancelled=lambda: cause == "cancel" and time.monotonic()-started > 0.8)
    assert result["status"] == "SYNTHETIC_WORKER_STOPPED"
    assert result["reason"] == {"lease": "monitor_lost", "timeout": "timeout", "cancel": "cancelled"}[cause]
    assert result["process_group_gone"]
    pid = int(child_pid.read_text())
    assert not Path(f"/proc/{pid}").exists()


def test_live_cgroup_limits_are_required(tmp_path):
    root = tmp_path / "cgroup"
    root.mkdir()
    for name, value in {"cpu.max": "50000 100000", "memory.max": "805306368",
            "memory.swap.max": "0", "pids.max": "128"}.items():
        (root/name).write_text(value)
    result = implementation().check_limits(root)
    assert result["cpu.max"] == "50000 100000"
    (root/"memory.swap.max").write_text("max")
    with pytest.raises(ValueError):
        implementation().check_limits(root)


def test_same_sequence_cannot_change_metrics(tmp_path):
    module = implementation()
    path = tmp_path / "lease"
    lease(path)
    def corrupt():
        raw = path.read_text()
        path.write_text(raw.replace("20000000000", "1000000000"))
        return False
    result = module.supervise([sys.executable, "-c", "import time; time.sleep(10)"],
        lease=path, evidence=tmp_path / "monitor.json", cancelled=corrupt, poll_seconds=0.02)
    assert result["reason"] == "monitor_invalid"


@pytest.mark.parametrize("cause", ["io", "swap", "service", "disk"])
def test_actual_loop_stops_on_host_pressure_samples(tmp_path, cause):
    module = implementation()
    path = tmp_path / "lease"
    lease(path)
    seq = 1
    def update():
        nonlocal seq
        seq += 1
        lease(path, seq)
        raw = path.read_text()
        if cause == "io":
            raw = raw.replace("some avg10=0.00", "some avg10=12.00", 1)
        elif cause == "swap":
            raw = raw.replace("pswpout 0", f"pswpout {seq}")
        elif cause == "service":
            raw = raw.replace("true", "false")
        else:
            raw = raw.replace("20000000000", "1000000000")
        path.write_text(raw)
        return False
    result = module.supervise([sys.executable, "-c", "import time; time.sleep(10)"],
        lease=path, evidence=tmp_path / "monitor.json", cancelled=update, poll_seconds=0.02)
    assert result["reason"] == {"io": "io_pressure", "swap": "swap_pressure",
        "service": "service_unhealthy", "disk": "disk_floor"}[cause]
    assert result["process_group_gone"]


def test_host_runner_rejects_alias_before_docker(tmp_path):
    path = Path(__file__).resolve().parents[3] / "scripts/run-synthetic-batch.sh"
    assert path.exists(), "missing host sampling runner"
    result = subprocess.run(["bash", str(path), "xiangrugu:test", "bad", str(tmp_path), "full"],
        capture_output=True, text=True)
    assert result.returncode == 2
    assert "immutable candidate image" in result.stderr


@pytest.mark.parametrize("condition", ["healthy", "unhealthy", "lost"])
def test_final_publication_requires_new_post_worker_host_sample(tmp_path, condition):
    module = implementation()
    path = tmp_path / "lease"
    lease(path)
    final = tmp_path / "batch.json"
    staged = tmp_path / ".batch.json.incomplete"
    staged.write_text(json.dumps(dict(complete=True, synthetic_only=True,
                                     ready_for_import=False, postgresql_connected=False)))
    renewed = False
    def controller():
        nonlocal renewed
        if (tmp_path / "final-sample-request.json").exists() and not renewed and condition != "lost":
            lease(path, 2)
            if condition == "unhealthy":
                path.write_text(path.read_text().replace("true", "false"))
            renewed = True
        return False
    result = module.supervise([sys.executable, "-c", "pass"], lease=path,
        evidence=tmp_path / "monitor.json", final=final, require_final_sample=True,
        lease_seconds=0.8, poll_seconds=0.02, cancelled=controller)
    assert final.exists() == (condition == "healthy")
    if condition == "healthy":
        assert result["samples"][-1]["sequence"] == 2
    else:
        assert result["reason"] == {"unhealthy": "service_unhealthy", "lost": "monitor_lost"}[condition]
