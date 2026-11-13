"""Run the real Bash controller against an artificial Docker boundary, no daemon."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("cause,reason", [
    ("invalid", "invalid_heartbeat"), ("eof", "controller_eof"),
    ("idle", "controller_idle"), ("TERM", "signal"),
    ("INT", "signal"), ("HUP", "signal"),
    ("cancel", "artificial_cancel"), ("deadline", "host_deadline"),
    ("collector", "collector_failure"),
    ("active-collector", "collector_failure"),
    ("runner-error", "runner_error"),
    ("escalation", "invalid_heartbeat"),
    ("complete", None),
    ("fragment", None), ("fragment-eof", "controller_eof"),
    ("stop-unconfirmed", "invalid_heartbeat"),
    ("removal-failure", "invalid_heartbeat"),
])
def test_trigger_is_durable_before_owned_container_stop(tmp_path, cause, reason):
    runner = (ROOT / "scripts/run-synthetic-batch.sh").read_text()
    # Only redirect private filesystem locations and shorten test clocks.
    private = tmp_path / "batch-runner-controller"
    private.mkdir()
    runner = runner.replace("/opt/mydocker/xiangrugu/data/var/batch-runner-", str(tmp_path / "batch-runner-"))
    runner = runner.replace("/opt/mydocker/xiangrugu/data/var/sqlite-synthetic-batch.lock", str(tmp_path / "lock"))
    runner = runner.replace("sleep 3", "sleep 0.01")
    if cause == "deadline":
        runner = runner.replace("host_seconds=$((seconds+30))", "host_seconds=1")
    if cause == "idle":
        runner = runner.replace("last_controller=$SECONDS\nnext_sample", "last_controller=$((SECONDS-15))\nnext_sample")
    if cause == "active-collector":
        runner = runner.replace("next_sample=$((SECONDS+10))", "next_sample=$((SECONDS+1))")
    script = tmp_path / "run.sh"
    script.write_text(runner)
    for helper in (ROOT / "scripts").glob("controller-*.sh"):
        (tmp_path / helper.name).write_bytes(helper.read_bytes())
    executable = tmp_path / "docker"
    executable.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
root = pathlib.Path(os.environ['FAKE_ROOT'])
a = sys.argv[1:]
state = root / 'running'
run = root / 'batch-runner-controller' / 'probe'
if a[0] == 'create':
    state.write_text('true'); print('a'*64)
elif a[0] == 'inspect':
    fmt = a[2]
    if '.Health.Status' in fmt:
        count = root / 'sample-count'
        n = int(count.read_text())+1 if count.exists() else 1
        count.write_text(str(n))
        if os.environ['CAUSE'] == 'collector' and n == 2: sys.exit(42)
        if os.environ['CAUSE'] == 'active-collector' and n == 3: sys.exit(42)
        print('fake-pg32 running healthy\\nfake-pg32b running healthy')
    elif fmt == '{{.Id}}':
        if os.environ['CAUSE'] == 'stop-unconfirmed': sys.exit(1)
        print('a'*64)
    elif '.State.Running' in fmt:
        if os.environ['CAUSE'] == 'complete': state.write_text('false')
        if os.environ['CAUSE'] == 'fragment':
            counter = root / 'running-checks'
            n = int(counter.read_text())+1 if counter.exists() else 1
            counter.write_text(str(n))
            (root / 'read-ready').write_text('ready')
            if n >= 4: state.write_text('false')
        print(state.read_text())
    elif '.State.ExitCode' in fmt: print(0 if os.environ['CAUSE'] in ('complete', 'fragment') else 143)
    elif '.State}}' in fmt: print('{"OOMKilled":false}')
    else: print('{}')
elif a[0] == 'stop':
    record = run / 'controller-stop.json'
    (root / 'stop-observed').write_text(record.read_text() if record.exists() else 'MISSING')
    if os.environ['CAUSE'] != 'escalation': state.write_text('false')
elif a[0] == 'kill': state.write_text('false')
elif a[0] == 'start' and os.environ['CAUSE'] == 'runner-error': sys.exit(43)
elif a[0] == 'rm':
    if os.environ['CAUSE'] == 'removal-failure': sys.exit(1)
    print('a'*64)
elif a[0] == 'top': print('PID PPID COMMAND\\n1 0 python')
''')
    executable.chmod(0o755)
    mode = "cancel" if cause == "cancel" else "full"
    env = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
               FAKE_ROOT=str(tmp_path), CAUSE=cause)
    p = subprocess.Popen(["bash", str(script), "sha256:" + "b"*64, "probe",
        str(private), mode, "c"*40], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    assert p.stdin is not None
    try:
        p.stdin.write(b"tick\n"); p.stdin.flush()
        deadline = time.monotonic() + 8
        while not (private / "probe/container-id.txt").exists() and p.poll() is None:
            assert time.monotonic() < deadline
            time.sleep(0.02)
        if cause == "collector":
            pass  # Actual sample failure before worker creation.
        elif cause in ("invalid", "escalation", "stop-unconfirmed", "removal-failure"):
            p.stdin.write(b"private-heartbeat-content\n"); p.stdin.flush()
        elif cause == "eof":
            p.stdin.close(); p.stdin = None
        elif cause in ("fragment", "fragment-eof"):
            if cause == "fragment":
                while not (tmp_path / 'read-ready').exists() and p.poll() is None:
                    assert time.monotonic() < deadline
                    time.sleep(0.02)
            p.stdin.write(b"ti"); p.stdin.flush()
            time.sleep(2)  # Cross the real controller's one-second read timeout.
            if cause == "fragment":
                p.stdin.write(b"ck\n"); p.stdin.flush()
            else:
                p.stdin.close(); p.stdin = None
        elif cause in ("TERM", "INT", "HUP"):
            os.kill(p.pid, getattr(signal, "SIG" + cause))
        deadline = time.monotonic() + 12
        while p.poll() is None:
            assert time.monotonic() < deadline
            if cause in ("cancel", "deadline", "active-collector"):
                p.stdin.write(b"tick\n"); p.stdin.flush()
            time.sleep(0.1)
        out, err = p.communicate(timeout=2)
    finally:
        if p.poll() is None:
            p.kill(); p.wait()
    record = private / "probe/controller-stop.json"
    if cause in ("complete", "fragment"):
        assert p.returncode == 0, (out, err)
        assert not record.exists()
        events = [json.loads(line) for line in (private / "probe/controller-events.jsonl").read_text().splitlines()]
        assert [e["event"] for e in events] == ["runner_exit"]
        return
    assert record.exists(), (p.returncode, out, err)
    data = json.loads(record.read_text())
    assert data["reason"] == reason
    assert data["signal"] == (cause if cause in ("TERM", "INT", "HUP") else None)
    assert data["run_suffix"] == "probe"
    assert data["ready_for_import"] is False
    assert "private-heartbeat-content" not in record.read_text() + err.decode()
    events = [json.loads(line) for line in (private / "probe/controller-events.jsonl").read_text().splitlines()]
    assert events[0]["reason"] == reason
    assert events[-1]["event"] == "runner_exit"
    assert [e["sequence"] for e in events] == list(range(1, len(events)+1))
    assert "controller_evidence_unavailable" not in err.decode()
    if cause == "escalation":
        assert any(e["event"] == "kill_requested" for e in events)
    if cause == "stop-unconfirmed":
        assert not (tmp_path / "stop-observed").exists()
        assert p.returncode == 1
    elif cause != "collector":
        observed = json.loads((tmp_path / "stop-observed").read_text())
        assert observed == data
        assert data["container_id"] == "a"*64
    else:
        assert not (tmp_path / "stop-observed").exists()
        assert data["container_id"] is None
        assert p.returncode == 42


@pytest.mark.parametrize("cause", ["sync-stall", "signal-during-sync", "signal-during-format"])
def test_receipt_cannot_block_stop_or_replace_first_trigger(tmp_path, cause):
    helper = ROOT / "scripts/controller-evidence.sh"
    sync = tmp_path / "sync"
    sync.write_text("#!/bin/bash\nprintf ready > \"$SYNC_MARKER\"\nexec sleep " +
                    ("20" if cause == "sync-stall" else "0.3") + "\n")
    sync.chmod(0o755)
    script = f'''set -Eeuo pipefail
run=$1; suffix=probe; id={"a"*64}; cancel_requested=false
source "{helper}"
trap 'controller_signal TERM' TERM
format_signalled=false
if [[ "$2" == signal-during-format ]]; then
    printf() {{
        builtin printf "$@"
        if [[ "${{1:-}}" == -v ]] && ! "$format_signalled"; then
            format_signalled=true
            kill -TERM "$$"
        fi
    }}
fi
controller_note trigger invalid_heartbeat
printf stopped > "$run/stopped"
'''
    p = subprocess.Popen(["bash", "-c", script, "bash", str(tmp_path), cause],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        env=dict(os.environ, PATH=str(tmp_path)+os.pathsep+os.environ["PATH"],
                 SYNC_MARKER=str(tmp_path / "sync-ready")))
    try:
        deadline = time.monotonic()+3
        while not (tmp_path / "sync-ready").exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        if cause == "signal-during-sync": os.kill(p.pid, signal.SIGTERM)
        try:
            out, err = p.communicate(timeout=6)
        except subprocess.TimeoutExpired:
            pytest.fail("Evidence synchronization blocked the controller stop")
        assert (tmp_path / "stopped").exists(), (out, err)
        if cause in ("signal-during-sync", "signal-during-format"):
            first = json.loads((tmp_path / "controller-stop.json").read_text())
            events = [json.loads(line) for line in (tmp_path / "controller-events.jsonl").read_text().splitlines()]
            assert first == events[0]
            assert first["reason"] == "invalid_heartbeat"
    finally:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL); p.wait()
