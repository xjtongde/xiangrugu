"""Explicit source-mode selection, exercised only against artificial fixtures."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_task_control import task_args, readonly_request, batch_request, canary_args, args, allow_unit_mounts
from test_readonly_batch import bind, renew
from test_candidate_supervisor import lease


@pytest.fixture
def project_task_args(task_args):
    request = json.loads(task_args['request_file'].read_text())
    request['source_mode'] = 'project_snapshot'
    scope_path = Path(request['scope_file'])
    scope = json.loads(scope_path.read_text())
    scope.pop('synthetic_data_authorized')
    scope['source_read_authorized'] = True
    request['scope_sha256'] = bind(scope_path, scope)
    approval_path = Path(request['approval_file'])
    approval = json.loads(approval_path.read_text())
    approval.update(source_mode='project_snapshot', source_read_authorized=True,
                    synthetic_data_authorized=False)
    bind(approval_path, approval)
    renew(request)
    task_args['request_file'].write_text(json.dumps(request))
    task_args['expected_request_sha256'] = hashlib.sha256(task_args['request_file'].read_bytes()).hexdigest()
    task_args['expected_approval_sha256'] = request['approval_sha256']
    task_args['authorized_source_mode'] = 'project_snapshot'
    return task_args


def test_explicit_project_mode_stages_fake_source_only_result(project_task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    stage = task_control.execute_controlled_batch(**project_task_args)
    result = json.loads(stage.read_text())
    assert result['complete'] and result['synthetic_only'] is False
    assert result['source_mode'] == 'project_snapshot'
    assert result['controller_request_sha256'] == project_task_args['expected_request_sha256']
    assert result['file_digest_passes'] == 2
    assert not result['postgresql_connected'] and not result['ready_for_import']
    assert not stage.with_name('observation.json').exists()


@pytest.mark.parametrize('mode', [None, True, 1, '', 'nas'])
def test_bad_external_source_selection_precedes_descriptor_reads(task_args, monkeypatch, mode):
    from xiangrugu_datamgmt import task_control
    monkeypatch.setattr(task_control, 'read_metadata', lambda *a: pytest.fail('descriptor read'))
    with pytest.raises(ValueError, match='controller_source_mode'):
        task_control.execute_controlled_batch(**task_args, authorized_source_mode=mode)


def test_external_project_selection_does_not_accept_artificial_request(task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    monkeypatch.setattr(task_control, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source read'))
    with pytest.raises(ValueError, match='controller_source_mode'):
        task_control.execute_controlled_batch(**task_args, authorized_source_mode='project_snapshot')


@pytest.mark.parametrize('pin', ['expected_request_sha256', 'expected_approval_sha256', 'expected_roots_sha256'])
def test_project_external_pins_precede_source(project_task_args, monkeypatch, pin):
    from xiangrugu_datamgmt import task_control
    project_task_args[pin] = '0'*64
    monkeypatch.setattr(task_control, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source read'))
    with pytest.raises(ValueError):
        task_control.execute_controlled_batch(**project_task_args)


def test_project_descriptor_requires_actual_readonly_mount(project_task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    monkeypatch.setattr(task_control, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source read'))
    with pytest.raises(ValueError, match='readonly_mount'):
        task_control.execute_controlled_batch(**project_task_args)


@pytest.mark.parametrize('change', ['source', 'writer', 'postgres', 'import'])
def test_project_approval_still_closes_other_authorities(project_task_args, monkeypatch, change):
    from xiangrugu_datamgmt import task_control, readonly_batch
    allow_unit_mounts(monkeypatch)
    request = json.loads(project_task_args['request_file'].read_text())
    approval_path = Path(request['approval_file'])
    approval = json.loads(approval_path.read_text())
    field = {'source': 'source_read_authorized', 'writer': 'stationary_readonly_window',
             'postgres': 'postgresql_authorized', 'import': 'ready_for_import'}[change]
    approval[field] = not approval[field]
    request['approval_sha256'] = bind(approval_path, approval)
    project_task_args['request_file'].write_text(json.dumps(request))
    project_task_args['expected_request_sha256'] = hashlib.sha256(project_task_args['request_file'].read_bytes()).hexdigest()
    project_task_args['expected_approval_sha256'] = request['approval_sha256']
    monkeypatch.setattr(readonly_batch, 'verify_snapshot', lambda *a, **k: pytest.fail('snapshot read'))
    with pytest.raises(ValueError, match='approval'):
        task_control.execute_controlled_batch(**project_task_args)


def fake_project_stage(tmp_path):
    final = tmp_path / 'batch.json'
    stage = final.with_name('.batch.json.incomplete')
    result = dict(complete=True, synthetic_only=False, ready_for_import=False,
                  postgresql_connected=False, source_mode='project_snapshot',
                  execution_kind='approved-readonly-batch-v1', controller_request_sha256='1'*64)
    stage.write_text(json.dumps(result))
    return stage, final, result


def test_explicit_project_publication_requires_external_request_pin(tmp_path):
    from xiangrugu_datamgmt.batch_execution import publish_batch
    stage, final, result = fake_project_stage(tmp_path)
    publish_batch(stage, final, authorized_source_mode='project_snapshot', expected_request_sha256='1'*64)
    assert json.loads(final.read_text()) == result
    assert stage.exists()


@pytest.mark.parametrize('change', ['pin', 'missing_pin', 'mode', 'synthetic', 'kind', 'db', 'import'])
def test_project_publication_rejects_wrong_identity_or_authority(tmp_path, change):
    from xiangrugu_datamgmt.batch_execution import publish_batch
    stage, final, result = fake_project_stage(tmp_path)
    pin = '1'*64
    if change == 'pin':
        pin = '2'*64
    elif change == 'missing_pin':
        pin = None
    else:
        field = {'mode': 'source_mode', 'synthetic': 'synthetic_only', 'kind': 'execution_kind',
                 'db': 'postgresql_connected', 'import': 'ready_for_import'}[change]
        result[field] = True if change in ('synthetic', 'db', 'import') else 'wrong'
        stage.write_text(json.dumps(result))
    with pytest.raises(ValueError):
        publish_batch(stage, final, authorized_source_mode='project_snapshot', expected_request_sha256=pin)
    assert not final.exists()


def test_project_result_cannot_use_default_artificial_publication(tmp_path):
    from xiangrugu_datamgmt.batch_execution import publish_batch
    stage, final, _ = fake_project_stage(tmp_path)
    with pytest.raises(ValueError, match='invalid_staging'):
        publish_batch(stage, final)
    assert not final.exists()


def test_supervisor_project_publication_is_explicit_and_source_only(tmp_path):
    from xiangrugu_datamgmt import candidate_supervisor
    stage, final, result = fake_project_stage(tmp_path)
    lease_path = tmp_path / 'lease'
    lease(lease_path)
    monitored = candidate_supervisor.supervise([sys.executable, '-c', 'pass'],
        lease=lease_path, evidence=tmp_path / 'monitor.json', max_seconds=5,
        authorized_source_mode='project_snapshot', expected_request_sha256='1'*64,
        final=final, poll_seconds=0.02)
    assert monitored['status'] == 'SOURCE_ONLY_WORKER_COMPLETED'
    assert monitored['synthetic_only'] is False and not monitored['ready_for_import']
    assert json.loads(final.read_text()) == result


def test_project_supervisor_requires_pin_before_starting_worker(tmp_path):
    from xiangrugu_datamgmt import candidate_supervisor
    with pytest.raises(ValueError, match='controller_source_mode'):
        candidate_supervisor.supervise([sys.executable, '-c', 'raise SystemExit(99)'],
            lease=tmp_path / 'absent', evidence=tmp_path / 'monitor.json',
            authorized_source_mode='project_snapshot')
    assert not (tmp_path / 'monitor.json').exists()


def test_control_cli_forwards_explicit_source_selection(monkeypatch, tmp_path):
    from xiangrugu_datamgmt import task_control
    received = []
    monkeypatch.setattr(task_control, 'execute_controlled_batch', lambda **kw: received.append(kw))
    monkeypatch.setattr(sys, 'argv', ['task-control', '--request', str(tmp_path / 'request'),
        '--request-sha256', '1'*64, '--approval-sha256', '2'*64, '--roots-sha256', '3'*64,
        '--image-id', 'sha256:'+'4'*64, '--git-revision', '5'*40, '--image-user', '10001:10001',
        '--source-status', 'dirty', '--lifecycle-seconds', '1800',
        '--authorized-source-mode', 'project_snapshot'])
    assert task_control.main() == 0
    assert received[0]['authorized_source_mode'] == 'project_snapshot'


def test_project_cli_failure_is_labeled_source_only(monkeypatch, tmp_path, capsys):
    from xiangrugu_datamgmt import task_control
    def deny(**kw):
        raise ValueError('controller_pin')
    monkeypatch.setattr(task_control, 'execute_controlled_batch', deny)
    monkeypatch.setattr(sys, 'argv', ['task-control', '--request', str(tmp_path / 'request'),
        '--request-sha256', '1'*64, '--approval-sha256', '2'*64, '--roots-sha256', '3'*64,
        '--image-id', 'sha256:'+'4'*64, '--git-revision', '5'*40, '--image-user', '10001:10001',
        '--source-status', 'dirty', '--lifecycle-seconds', '1800',
        '--authorized-source-mode', 'project_snapshot'])
    assert task_control.main() == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'CONTROLLED_SOURCE_ONLY_TASK_FAILED'
