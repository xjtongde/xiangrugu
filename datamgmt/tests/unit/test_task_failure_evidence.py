"""B-18: preserve safe worker diagnostics independently of supervision stops."""
import hashlib
import json
from pathlib import Path
import sys
import sqlite3

import pytest

from test_task_control import task_args, readonly_request, batch_request, canary_args, args, renew, allow_unit_mounts
from test_candidate_supervisor import lease


def cli_args(task):
    image = task['actual_image']
    return ['task-control', '--request', str(task['request_file']),
        '--request-sha256', task['expected_request_sha256'],
        '--approval-sha256', task['expected_approval_sha256'],
        '--roots-sha256', task['expected_roots_sha256'],
        '--image-id', image['image_id'], '--git-revision', image['git_revision'],
        '--image-user', image['user'], '--source-status', image['source_status'],
        '--lifecycle-seconds', '1800']


def test_control_preflight_failure_has_safe_stage(task_args, monkeypatch, capsys):
    from xiangrugu_datamgmt import task_control
    argv = cli_args(task_args)
    argv[argv.index('--request-sha256') + 1] = '0'*64
    monkeypatch.setattr(sys, 'argv', argv)
    assert task_control.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result['failure']['stage'] == 'task_preflight'
    assert result['failure']['code'] == 'controller_request_identity'
    assert result['failure']['domain'] == 'control'
    assert result['failure']['object_index'] is None


def test_snapshot_mismatch_reports_stage_without_source_text(task_args, monkeypatch, capsys):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    request = json.loads(task_args['request_file'].read_text())
    from xiangrugu_datamgmt.config import load_config
    config = load_config(Path(request['roots']), environ={})
    selected = config.snapshot_root / request['snapshot_id'] / request['relative_path']
    selected.write_bytes(b'PRIVATE-ARTIFICIAL-VALUE')
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    assert task_control.main() == 1
    raw = capsys.readouterr().out
    result = json.loads(raw)
    assert result['failure']['stage'] == 'snapshot_verify'
    assert result['failure']['domain'] == 'snapshot'
    assert 'PRIVATE-ARTIFICIAL-VALUE' not in raw
    assert str(selected) not in raw
    assert not Path(request['output']).exists()


@pytest.mark.parametrize('error,domain,code', [
    ('read', 'sqlite', 'row_or_cell_limit'), ('sort', 'sort', 'budget'),
    ('unknown', 'internal', 'controlled_task_failed'),
    ('os', 'os', 'io_error')])
def test_internal_errors_are_static_not_raw(task_args, monkeypatch, capsys, error, domain, code):
    from xiangrugu_datamgmt import task_control, readonly_batch
    from xiangrugu_datamgmt.sqlite_values import SQLiteValueReadError
    from xiangrugu_datamgmt.unordered_values import UnorderedValueError
    allow_unit_mounts(monkeypatch)
    def fail(*a, **kw):
        if error == 'read':
            raise SQLiteValueReadError('row_or_cell_limit', column_key='PRIVATE-COLUMN')
        if error == 'sort':
            raise UnorderedValueError('budget', column_key='PRIVATE-COLUMN')
        if error == 'os':
            raise OSError('PRIVATE-EXCEPTION /private/source')
        raise ValueError('PRIVATE-EXCEPTION /private/source')
    monkeypatch.setattr(readonly_batch, 'summarize_sqlite_batch', fail)
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    assert task_control.main() == 1
    raw = capsys.readouterr().out
    failure = json.loads(raw)['failure']
    assert (failure['domain'], failure['code']) == (domain, code)
    assert failure['stage'] == 'batch_preflight'
    assert 'PRIVATE' not in raw


def test_reader_row_limit_survives_sort_wrapper(task_args, monkeypatch, capsys):
    from xiangrugu_datamgmt import task_control
    from test_batch_execution import bind
    from xiangrugu_datamgmt.snapshots import write_json_exclusive, digest
    from xiangrugu_datamgmt.config import load_config
    allow_unit_mounts(monkeypatch)
    request = json.loads(task_args['request_file'].read_text())
    budget_path = Path(request['budget_file'])
    budget = json.loads(budget_path.read_text())
    config = load_config(Path(request['roots']), environ={})
    selected = config.snapshot_root / request['snapshot_id'] / request['relative_path']
    with sqlite3.connect(selected) as db:
        db.executemany('INSERT INTO example VALUES (?)', [('private-one',), ('private-two',)])
    request['expected_size'] = selected.stat().st_size
    request['expected_sha256'] = hashlib.sha256(selected.read_bytes()).hexdigest()
    cert_path = Path(request['certificate'])
    cert = json.loads(cert_path.read_text())
    member = next(m for m in cert['members'] if m['path'] == request['relative_path'])
    member.update(size=request['expected_size'], sha256=request['expected_sha256'])
    cert['manifest_sha256'] = digest(cert['members'])
    request['manifest_sha256'] = cert['manifest_sha256']
    request['certificate_sha256'] = bind(cert_path, cert)
    scope_path = Path(request['scope_file'])
    scope = json.loads(scope_path.read_text())
    scope['source'] = member
    request['scope_sha256'] = bind(scope_path, scope)
    budget['objects'][0]['read_limits']['max_rows'] = 1
    request['budget_sha256'] = bind(budget_path, budget)
    renew(request)
    task_args['expected_approval_sha256'] = request['approval_sha256']
    task_args['request_file'].unlink()
    write_json_exclusive(task_args['request_file'], request)
    task_args['expected_request_sha256'] = hashlib.sha256(task_args['request_file'].read_bytes()).hexdigest()
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    assert task_control.main() == 1
    failure = json.loads(capsys.readouterr().out)['failure']
    assert (failure['domain'], failure['code']) == ('sqlite', 'row_or_cell_limit')
    assert failure['stage'] == 'object_read_sort'
    assert failure['object_index'] == 1
    assert failure['completed_objects'] == 0
    assert not Path(request['output']).exists()


def failure_document(pin='a'*64):
    return dict(version=1, status='CONTROLLED_TASK_FAILURE', request_sha256=pin,
        source_mode='artificial', domain='sqlite', code='row_or_cell_limit',
        stage='object_read_sort', object_index=2, completed_objects=1,
        ready_for_import=False, raw_values_emitted=False)


@pytest.mark.parametrize('cancel', [False, True])
def test_worker_failure_and_supervision_stop_both_retained(tmp_path, cancel):
    from xiangrugu_datamgmt import candidate_supervisor
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    failure_path = tmp_path / 'worker-failure.json'
    doc = failure_document()
    code = (f'import pathlib,json,time; pathlib.Path({str(failure_path)!r}).write_text({json.dumps(doc)!r}); '
            + ('time.sleep(20)' if cancel else 'raise SystemExit(1)'))
    def cancelled():
        return cancel and failure_path.exists()
    result = candidate_supervisor.supervise([sys.executable, '-c', code],
        lease=lease_path, evidence=tmp_path / 'monitor.json', poll_seconds=0.02,
        max_seconds=5, cancelled=cancelled, worker_failure=failure_path,
        worker_request_sha256='a'*64)
    assert result['reason'] == ('cancelled' if cancel else 'worker_exit')
    assert result['worker_failure'] == doc
    assert result['worker_failure_sha256'] == hashlib.sha256(failure_path.read_bytes()).hexdigest()
    assert result['process_group_gone']
    assert json.loads((tmp_path / 'monitor.json').read_text())['worker_failure'] == doc


@pytest.mark.parametrize('change', ['pin', 'code', 'stage', 'extra', 'boolean', 'oversize'])
def test_invalid_failure_file_never_leaks_or_relabels_stop(tmp_path, change):
    from xiangrugu_datamgmt import candidate_supervisor
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    path = tmp_path / 'worker-failure.json'
    doc = failure_document()
    if change == 'pin': doc['request_sha256'] = 'b'*64
    elif change == 'code': doc['code'] = 'PRIVATE-EXCEPTION'
    elif change == 'stage': doc['stage'] = 'PRIVATE-SOURCE'
    elif change == 'extra': doc['raw'] = 'PRIVATE-VALUE'
    elif change == 'boolean': doc['object_index'] = True
    raw = json.dumps(doc) if change != 'oversize' else 'PRIVATE'*200000
    # Write after launch; a preexisting diagnostic must be rejected separately.
    code = f'import pathlib; pathlib.Path({str(path)!r}).write_text({raw!r}); raise SystemExit(1)'
    if change == 'oversize':
        code = f'import pathlib; pathlib.Path({str(path)!r}).write_text("PRIVATE"*200000); raise SystemExit(1)'
    result = candidate_supervisor.supervise([sys.executable, '-c', code], lease=lease_path,
        evidence=tmp_path / 'monitor.json', max_seconds=5, poll_seconds=0.02,
        worker_failure=path, worker_request_sha256='a'*64)
    assert result['reason'] == 'worker_exit'
    assert result['worker_failure'] is None
    assert result['worker_failure_state'] == 'invalid'
    assert 'PRIVATE' not in (tmp_path / 'monitor.json').read_text()


def test_preexisting_failure_blocks_worker(tmp_path):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'worker-failure.json'
    path.write_text(json.dumps(failure_document()))
    marker = tmp_path / 'started'
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    with pytest.raises(ValueError, match='worker_diagnostic_exists'):
        candidate_supervisor.supervise([sys.executable, '-c', f'open({str(marker)!r},"w").close()'],
            lease=lease_path, evidence=tmp_path / 'monitor.json', worker_failure=path,
            worker_request_sha256='a'*64)
    assert not marker.exists()


def test_relative_diagnostic_path_is_rejected_without_writing(task_args, monkeypatch, tmp_path, capsys):
    from xiangrugu_datamgmt import task_control
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', cli_args(task_args) + ['--failure-evidence', 'relative.json'])
    assert task_control.main() == 1
    assert not (tmp_path / 'relative.json').exists()
    assert json.loads(capsys.readouterr().out)['diagnostic_saved'] is False


def test_invalid_external_pin_is_not_echoed(task_args, monkeypatch, capsys):
    from xiangrugu_datamgmt import task_control
    argv = cli_args(task_args)
    argv[argv.index('--request-sha256') + 1] = 'PRIVATE-INVALID-PIN'
    monkeypatch.setattr(sys, 'argv', argv)
    assert task_control.main() == 1
    raw = capsys.readouterr().out
    assert 'PRIVATE' not in raw
    assert json.loads(raw)['failure']['request_sha256'] is None


def test_failure_file_is_saved_and_existing_evidence_not_overwritten(task_args, monkeypatch, tmp_path, capsys):
    from xiangrugu_datamgmt import task_control
    path = tmp_path / 'failure.json'
    argv = cli_args(task_args) + ['--failure-evidence', str(path)]
    argv[argv.index('--request-sha256') + 1] = '0'*64
    monkeypatch.setattr(sys, 'argv', argv)
    assert task_control.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result['diagnostic_saved'] is True
    assert json.loads(path.read_text()) == result['failure']
    raw = path.read_bytes()
    assert task_control.main() == 1
    assert path.read_bytes() == raw
    assert json.loads(capsys.readouterr().out)['diagnostic_saved'] is False


def test_stage_save_failure_does_not_publish(task_args, monkeypatch, capsys):
    from xiangrugu_datamgmt import task_control, readonly_batch
    allow_unit_mounts(monkeypatch)
    def fail(*a, **kw):
        raise OSError('PRIVATE-SAVE-ERROR')
    monkeypatch.setattr(readonly_batch, 'write_json_exclusive', fail)
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    assert task_control.main() == 1
    failure = json.loads(capsys.readouterr().out)['failure']
    assert failure['stage'] == 'stage_save'
    assert (failure['domain'], failure['code']) == ('os', 'io_error')
    assert failure['completed_objects'] == 1
    assert failure['object_index'] is None


@pytest.mark.parametrize('phase', ['before', 'after'])
def test_batch_digest_failure_stage(task_args, monkeypatch, capsys, phase):
    from xiangrugu_datamgmt import task_control
    from xiangrugu_datamgmt.sqlite_values import _BatchSource, SQLiteValueReadError
    allow_unit_mounts(monkeypatch)
    original = _BatchSource._verify
    calls = 0
    def fail(self):
        nonlocal calls
        calls += 1
        if calls == (1 if phase == 'before' else 2):
            raise SQLiteValueReadError('source_changed')
        return original(self)
    monkeypatch.setattr(_BatchSource, '_verify', fail)
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    assert task_control.main() == 1
    failure = json.loads(capsys.readouterr().out)['failure']
    assert failure['stage'] == 'batch_digest_' + phase
    assert failure['code'] == 'source_changed'
    assert failure['completed_objects'] == (0 if phase == 'before' else 1)


def test_success_exit_with_failure_file_cannot_publish(tmp_path):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'failure.json'
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    final = tmp_path / 'batch.json'
    stage = tmp_path / '.batch.json.incomplete'
    stage.write_text(json.dumps(dict(complete=True, synthetic_only=True,
                                    ready_for_import=False, postgresql_connected=False)))
    code = f'import pathlib; pathlib.Path({str(path)!r}).write_text({json.dumps(failure_document())!r})'
    result = candidate_supervisor.supervise([sys.executable, '-c', code], lease=lease_path,
        evidence=tmp_path / 'monitor.json', final=final, max_seconds=5, poll_seconds=0.02,
        worker_failure=path, worker_request_sha256='a'*64)
    assert result['reason'] == 'worker_diagnostic_inconsistent'
    assert not final.exists()


@pytest.mark.parametrize('cancel', [False, True])
def test_nested_invalid_json_preserves_supervision_evidence(tmp_path, cancel):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'failure.json'
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    raw = '['*1500 + ']'*1500
    code = (f'import pathlib,time; pathlib.Path({str(path)!r}).write_text({raw!r}); '
            + ('time.sleep(20)' if cancel else 'raise SystemExit(1)'))
    result = candidate_supervisor.supervise([sys.executable, '-c', code], lease=lease_path,
        evidence=tmp_path / 'monitor.json', max_seconds=5, poll_seconds=0.02,
        cancelled=lambda: cancel and path.exists(), worker_failure=path, worker_request_sha256='a'*64)
    saved = json.loads((tmp_path / 'monitor.json').read_text())
    assert saved['reason'] == ('cancelled' if cancel else 'worker_exit')
    assert saved['worker_failure_state'] == 'invalid'
    assert saved['process_group_gone'] and result['worker_failure'] is None


@pytest.mark.parametrize('condition', ['relative', 'old', 'limits_alias'])
def test_supervisor_cli_rejects_diagnostic_before_any_write(tmp_path, monkeypatch, capsys, condition):
    from xiangrugu_datamgmt import candidate_supervisor
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    path = tmp_path / 'failure.json'
    if condition == 'relative':
        path = Path('failure.json')
        monkeypatch.chdir(tmp_path)
    elif condition == 'old':
        path.write_text(json.dumps(failure_document()))
    else:
        path = tmp_path / 'limits.json'
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    monkeypatch.setattr(sys, 'argv', ['supervisor', '--lease', str(lease_path),
        '--evidence', str(tmp_path / 'monitor.json'), '--worker-failure', str(path),
        '--worker-request-sha256', 'a'*64, '--', sys.executable, '-c', 'raise SystemExit(99)'])
    assert candidate_supervisor.main() == 1
    capsys.readouterr()
    after = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    assert after == before
