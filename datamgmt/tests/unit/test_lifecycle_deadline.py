"""The approved lifecycle deadline includes preflight and publication waits."""
import hashlib
import json
from pathlib import Path
import sys
import time

import pytest

from test_readonly_batch import readonly_request, batch_request, canary_args, args, renew
from test_task_control import allow_unit_mounts
from test_candidate_supervisor import lease


def controlled(request, seconds=1800):
    request['lifecycle_seconds'] = seconds
    renew(request)
    path = Path(request['roots']).parent / 'deadline-request.json'
    path.write_text(json.dumps(request))
    return dict(request_file=path, lifecycle_seconds=seconds,
        expected_request_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_approval_sha256=request['approval_sha256'], expected_roots_sha256=request['roots_sha256'],
        actual_image=dict(image_id=request['image_id'], git_revision=request['git_revision'],
                          user='10001:10001', source_status='dirty'))


def test_bound_lifecycle_stages_with_actual_supervisor_deadline(readonly_request, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    staged = task_control.execute_controlled_batch(**controlled(readonly_request))
    assert json.loads(staged.read_text())['controller_lifecycle_seconds'] == 1800


@pytest.mark.parametrize('seconds', [True, 0, -1, 1801, '1800'])
def test_bad_actual_deadline_rejected_before_source(readonly_request, monkeypatch, seconds):
    from xiangrugu_datamgmt import task_control
    call = controlled(readonly_request)
    call['lifecycle_seconds'] = seconds
    monkeypatch.setattr(task_control, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError, match='lifecycle_budget'):
        task_control.execute_controlled_batch(**call)


def test_actual_deadline_must_match_approved_request(readonly_request, monkeypatch):
    from xiangrugu_datamgmt import task_control
    call = controlled(readonly_request)
    call['lifecycle_seconds'] = 300
    monkeypatch.setattr(task_control, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError, match='lifecycle_budget'):
        task_control.execute_controlled_batch(**call)


@pytest.mark.parametrize('phase', ['metadata', 'snapshot', 'query'])
def test_lifecycle_deadline_covers_worker_phases(readonly_request, monkeypatch, phase):
    from xiangrugu_datamgmt import readonly_batch, task_control
    call = controlled(readonly_request)
    allow_unit_mounts(monkeypatch)
    clock = [0.0]
    monkeypatch.setattr(task_control.time, 'monotonic', lambda: clock[0])
    if phase == 'metadata':
        original = task_control.read_metadata
        def delayed(*a, **kw):
            raw = original(*a, **kw)
            clock[0] = 1801.0
            return raw
        monkeypatch.setattr(task_control, 'read_metadata', delayed)
    else:
        name = 'verify_snapshot' if phase == 'snapshot' else 'summarize_sqlite_batch'
        original = getattr(readonly_batch, name)
        def delayed(*a, **kw):
            result = original(*a, **kw)
            clock[0] = 1801.0
            return result
        monkeypatch.setattr(readonly_batch, name, delayed)
    with pytest.raises(ValueError, match='lifecycle_timeout'):
        task_control.execute_controlled_batch(**call)
    output = Path(readonly_request['output'])
    assert not output.exists() and not output.with_name('.'+output.name+'.incomplete').exists()


def test_source_batch_budget_cannot_outlive_lifecycle(readonly_request, monkeypatch):
    from xiangrugu_datamgmt import readonly_batch
    readonly_request['lifecycle_seconds'] = 1
    renew(readonly_request)
    monkeypatch.setattr(readonly_batch, 'verify_snapshot', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError, match='lifecycle_budget'):
        readonly_batch.execute_readonly_batch(readonly_request)


def test_wait_for_post_completion_sample_uses_same_total_deadline(tmp_path):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'lease'
    lease(path)
    final = tmp_path / 'batch.json'
    final.with_name('.batch.json.incomplete').write_text(json.dumps(dict(
        complete=True, synthetic_only=True, ready_for_import=False, postgresql_connected=False)))
    result = candidate_supervisor.supervise([sys.executable, '-c', 'pass'], lease=path,
        evidence=tmp_path / 'monitor.json', final=final, require_final_sample=True,
        max_seconds=0.2, poll_seconds=0.01)
    assert result['reason'] == 'timeout' and result['max_seconds'] == 0.2
    assert result['process_group_gone'] and not final.exists()


def test_deadline_during_monitor_persistence_cannot_report_publication_success(tmp_path, monkeypatch):
    from xiangrugu_datamgmt import candidate_supervisor
    path = tmp_path / 'lease'
    lease(path)
    final = tmp_path / 'batch.json'
    final.with_name('.batch.json.incomplete').write_text(json.dumps(dict(
        complete=True, synthetic_only=True, ready_for_import=False, postgresql_connected=False)))
    original = candidate_supervisor.write_json_exclusive
    def slow(path, value):
        original(path, value)
        if Path(path).name == 'monitor.json':
            time.sleep(0.25)
    monkeypatch.setattr(candidate_supervisor, 'write_json_exclusive', slow)
    result = candidate_supervisor.supervise([sys.executable, '-c', 'pass'], lease=path,
        evidence=tmp_path / 'monitor.json', final=final, max_seconds=0.2, poll_seconds=0.01)
    assert result['reason'] == 'timeout' and not final.exists()
    assert json.loads((tmp_path / 'publication-failure.json').read_text())['reason'] == 'timeout'


def test_controlled_host_and_transport_deadline_contract():
    root = Path(__file__).resolve().parents[3]
    host = (root / 'scripts/run-synthetic-batch.sh').read_text()
    transport = (root / 'scripts/invoke-synthetic-batch.ps1').read_text()
    assert 'seconds=1800' in host
    assert 'host_seconds=$((seconds+30))' in host
    assert '--lifecycle-seconds "$seconds"' in host
    assert 'SECONDS-started >= host_seconds' in host
    assert "if ($Mode -eq 'readonly-controlled') { 1880 } else { 380 }" in transport
    assert '$timer.Elapsed.TotalSeconds -ge $transportSeconds' in transport
