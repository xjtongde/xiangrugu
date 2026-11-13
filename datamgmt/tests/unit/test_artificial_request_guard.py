"""Artificial-only metadata scheduling and externally pinned publication fences."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_task_control import task_args, readonly_request, batch_request, canary_args, args, allow_unit_mounts
from test_project_task_control import project_task_args
from test_candidate_supervisor import lease


def guard_case(check=None, cancelled=lambda: False):
    from xiangrugu_datamgmt.task_control import _ArtificialRequestGuard
    clock = [0.0]
    calls = []
    def check_metadata():
        calls.append(clock[0])
        if check is not None:
            check()
    guard = _ArtificialRequestGuard(check_metadata=check_metadata, cancelled=cancelled,
        started=0.0, lifecycle_seconds=1, clock=lambda: clock[0])
    return guard, clock, calls


def test_high_frequency_reads_are_bounded_and_due_or_forced_reads_are_actual():
    guard, clock, calls = guard_case()
    for _ in range(1000):
        assert guard() is False
    assert len(calls) == 1
    clock[0] = 0.099
    guard()
    assert len(calls) == 1
    clock[0] = 0.101
    guard()
    assert len(calls) == 2
    guard(force=True)
    assert len(calls) == 3


def test_failed_check_does_not_extend_cached_window():
    rejected = [True]
    def check():
        if rejected[0]:
            raise ValueError('controller_request_changed')
    guard, clock, calls = guard_case(check)
    with pytest.raises(ValueError, match='controller_request_changed'):
        guard()
    rejected[0] = False
    clock[0] = 0.01
    guard()
    assert len(calls) == 2


@pytest.mark.parametrize('case', ['cancel', 'deadline', 'cancel_during_check', 'deadline_during_check'])
def test_light_gates_are_not_cached(case):
    cancelled = [False]
    guard, clock, calls = guard_case(cancelled=lambda: cancelled[0])
    guard()
    if case == 'cancel':
        cancelled[0] = True
    elif case == 'deadline':
        clock[0] = 1.0
    else:
        def check():
            if case == 'cancel_during_check':
                cancelled[0] = True
            else:
                clock[0] = 1.0
        guard.check_metadata = check
    expected = 'cancelled' if 'cancel' in case else 'lifecycle_timeout'
    with pytest.raises(ValueError, match=expected):
        guard(force=case.endswith('during_check'))


@pytest.mark.parametrize('clock_value', [-1.0, float('nan'), float('inf'), True, '0'])
def test_invalid_or_backwards_clock_fails_closed(clock_value):
    guard, clock, _ = guard_case()
    guard()
    clock[0] = clock_value
    with pytest.raises(ValueError, match='input_error'):
        guard()


@pytest.mark.parametrize('value', [None, 0, 1, 'false'])
def test_non_boolean_cancel_fails_closed(value):
    guard, _, _ = guard_case(cancelled=lambda: value)
    with pytest.raises(ValueError, match='input_error'):
        guard()


def test_stage_boundary_rechecks_even_inside_cache_window(task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    monkeypatch.setattr(task_control.time, 'monotonic', lambda: 0.0)
    def execute(request, *, cancelled, progress=None, **kw):
        cancelled()
        task_args['request_file'].write_text('{}')
        if progress is not None:
            progress('stage_save')
        pytest.fail('stage saved after request changed')
    monkeypatch.setattr(task_control, 'execute_readonly_batch', execute)
    with pytest.raises(ValueError, match='controller_request_changed'):
        task_control.execute_controlled_batch(**task_args)


def test_artificial_control_reduces_actual_request_reads(task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    monkeypatch.setattr(task_control.time, 'monotonic', lambda: 0.0)
    original = task_control.read_metadata
    reads = []
    def read(path):
        reads.append(path)
        return original(path)
    monkeypatch.setattr(task_control, 'read_metadata', read)
    def execute(request, *, cancelled, **kw):
        for _ in range(1000):
            cancelled()
        return Path('/unused-stage')
    monkeypatch.setattr(task_control, 'execute_readonly_batch', execute)
    task_control.execute_controlled_batch(**task_args)
    assert len(reads) <= 4


def test_project_mode_keeps_per_call_request_check(project_task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    monkeypatch.setattr(task_control.time, 'monotonic', lambda: 0.0)
    def execute(request, *, cancelled, **kw):
        cancelled()
        project_task_args['request_file'].write_text('{}')
        cancelled()
        pytest.fail('project guard was cached')
    monkeypatch.setattr(task_control, 'execute_readonly_batch', execute)
    with pytest.raises(ValueError, match='controller_request_changed'):
        task_control.execute_controlled_batch(**project_task_args)


@pytest.mark.parametrize('change', ['bytes', 'symlink', 'writable'])
def test_due_check_rejects_descriptor_change(task_args, monkeypatch, change):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    clock = [0.0]
    monkeypatch.setattr(task_control.time, 'monotonic', lambda: clock[0])
    def execute(request, *, cancelled, **kw):
        cancelled()
        path = task_args['request_file']
        if change == 'bytes':
            path.write_text('{}')
        elif change == 'symlink':
            target = path.with_name('replacement.json')
            target.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(target)
        else:
            def writable(path):
                raise ValueError('readonly_mount')
            monkeypatch.setattr(task_control, '_require_readonly_mount', writable)
        clock[0] = 0.101
        cancelled()
        pytest.fail('changed descriptor accepted')
    monkeypatch.setattr(task_control, 'execute_readonly_batch', execute)
    with pytest.raises(ValueError):
        task_control.execute_controlled_batch(**task_args)


@pytest.mark.parametrize('mutated', [False, True])
def test_publication_rechecks_external_descriptor(tmp_path, monkeypatch, mutated):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'request.json'
    path.write_text('{}')
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    final = tmp_path / 'batch.json'
    stage = final.with_name('.batch.json.incomplete')
    stage.write_text(json.dumps(dict(complete=True, synthetic_only=True,
        ready_for_import=False, postgresql_connected=False)))
    monkeypatch.setattr(candidate_supervisor, '_require_readonly_mount', lambda path: None, raising=False)
    code = 'from pathlib import Path; Path('+repr(str(path))+').write_text("changed")' if mutated else 'pass'
    result = candidate_supervisor.supervise([sys.executable, '-c', code], lease=lease_path,
        evidence=tmp_path / 'monitor.json', max_seconds=5, poll_seconds=0.01,
        final=final, controller_request_file=path, controller_request_sha256=pin)
    assert final.exists() is (not mutated)
    if mutated:
        assert result['reason'] == 'publication_failed'


def test_bad_publication_pin_precedes_worker(tmp_path, monkeypatch):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'request.json'
    path.write_text('{}')
    monkeypatch.setattr(candidate_supervisor, '_require_readonly_mount', lambda path: None, raising=False)
    with pytest.raises(ValueError):
        candidate_supervisor.supervise([sys.executable, '-c', 'raise SystemExit(99)'],
            lease=tmp_path / 'absent', evidence=tmp_path / 'monitor.json',
            controller_request_file=path, controller_request_sha256='1'*64,
            final=tmp_path / 'batch.json')
    assert not (tmp_path / 'monitor.json').exists()


@pytest.mark.parametrize('stop', ['cancelled', 'timeout'])
def test_stop_during_last_heavy_publication_check_cannot_publish(tmp_path, monkeypatch, stop):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'request.json'
    path.write_text('{}')
    pin = hashlib.sha256(path.read_bytes()).hexdigest()
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    final = tmp_path / 'batch.json'
    stage = final.with_name('.batch.json.incomplete')
    stage.write_text(json.dumps(dict(complete=True, synthetic_only=True,
        ready_for_import=False, postgresql_connected=False)))
    clock, cancelled, reads = [0.0], [False], []
    monkeypatch.setattr(candidate_supervisor.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(candidate_supervisor, '_require_readonly_mount', lambda path: None)
    original = candidate_supervisor.read_metadata
    def read(file):
        raw = original(file)
        if file == path:
            reads.append(file)
            # Preflight, explicit pre-publication check, then the final link fence.
            if len(reads) == 3:
                if stop == 'cancelled':
                    cancelled[0] = True
                else:
                    clock[0] = 6.0
        return raw
    monkeypatch.setattr(candidate_supervisor, 'read_metadata', read)
    result = candidate_supervisor.supervise([sys.executable, '-c', 'pass'], lease=lease_path,
        evidence=tmp_path / 'monitor.json', max_seconds=5, poll_seconds=0.01,
        cancelled=lambda: cancelled[0], final=final,
        controller_request_file=path, controller_request_sha256=pin)
    assert len(reads) == 3
    assert not final.exists()
    assert stage.exists()
    assert result['reason'] == stop
