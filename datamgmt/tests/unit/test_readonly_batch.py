"""The new entry must reject unapproved reads before touching a snapshot."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from test_batch_execution import batch_request, canary_args, args, bind
from xiangrugu_datamgmt.snapshots import digest


def implementation():
    from xiangrugu_datamgmt import readonly_batch
    return readonly_batch


def renew(request):
    path = Path(request['approval_file'])
    approval = json.loads(path.read_text())
    approval['request_sha256'] = digest({k: v for k, v in request.items()
                                        if k not in ('approval_file', 'approval_sha256')})
    request['approval_sha256'] = bind(path, approval)


@pytest.fixture
def readonly_request(batch_request):
    request = copy.deepcopy(batch_request)
    root = Path(request.pop('synthetic_root'))
    request.pop('synthetic_only')
    request['source_mode'] = 'artificial'
    descriptor = root / 'descriptor.json'
    request['bindings'] = {'descriptor': {'path': str(descriptor),
                                         'sha256': bind(descriptor, {'version': 1})}}
    scope_path = Path(request['scope_file'])
    scope = json.loads(scope_path.read_text())
    scope['bindings'] = {k: v['sha256'] for k, v in request['bindings'].items()}
    request['scope_sha256'] = bind(scope_path, scope)
    budget_path = Path(request['budget_file'])
    old = json.loads(budget_path.read_text())
    old['read_limits'].update(max_columns=64, max_rows=100, max_cells=50000,
                             max_value_bytes=8388608, max_vm_steps=20000000)
    old['sort_limits'].update(max_columns=64, max_row_bytes=1048576,
                             max_stream_bytes=8388608, chunk_bytes=2097152)
    budget = dict(version=2, group='small', max_seconds=60, objects=[
        dict(source_object_id=o['source_object_id'], read_limits=old['read_limits'],
             sort_limits=old['sort_limits']) for o in scope['objects']])
    request['budget_sha256'] = bind(budget_path, budget)
    request['approval_file'] = str(root / 'approval.json')
    approval = dict(version=1, status='APPROVED_READONLY_BATCH', source_mode='artificial',
        source_read_authorized=False, synthetic_data_authorized=True,
        stationary_readonly_window=True, postgresql_authorized=False, ready_for_import=False,
        request_sha256='0'*64)
    bind(Path(request['approval_file']), approval)
    renew(request)
    return request


def allow_artificial_mounts(monkeypatch):
    # Unit fixtures live on a writable test filesystem. Real mount checks are
    # exercised separately and by the candidate's actual read-only bind.
    monkeypatch.setattr(implementation(), '_require_readonly_mount', lambda path: None)


def test_bound_request_stages_complete_source_only_result(readonly_request, monkeypatch):
    allow_artificial_mounts(monkeypatch)
    staged = implementation().execute_readonly_batch(readonly_request)
    assert not Path(readonly_request['output']).exists()
    result = json.loads(staged.read_text())
    assert result['execution_kind'] == 'approved-readonly-batch-v1'
    assert result['synthetic_only'] and result['complete']
    assert result['approval_sha256'] == readonly_request['approval_sha256']
    assert result['file_digest_passes'] == 2
    assert result['objects'][0]['expected_count'] == 0
    assert not result['ready_for_import'] and not result['postgresql_connected']


@pytest.mark.parametrize('field', ['image_id', 'git_revision', 'scratch_parent', 'output'])
def test_approval_binds_runtime_and_destinations(readonly_request, field, monkeypatch):
    module = implementation()
    if field == 'image_id':
        readonly_request[field] = 'sha256:'+'3'*64
    elif field == 'git_revision':
        readonly_request[field] = '3'*40
    else:
        readonly_request[field] += '-different'
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


@pytest.mark.parametrize('change', ['denied', 'db', 'import', 'writer', 'mode', 'boolean', 'extra'])
def test_bad_approval_fails_before_source(readonly_request, change, monkeypatch):
    module = implementation()
    path = Path(readonly_request['approval_file'])
    approval = json.loads(path.read_text())
    if change == 'denied':
        approval['status'] = 'DRAFT'
    elif change == 'db':
        approval['postgresql_authorized'] = True
    elif change == 'import':
        approval['ready_for_import'] = True
    elif change == 'writer':
        approval['stationary_readonly_window'] = False
    elif change == 'mode':
        approval['source_mode'] = 'project_snapshot'
    elif change == 'boolean':
        approval['version'] = True
    else:
        approval['extra'] = True
    readonly_request['approval_sha256'] = bind(path, approval)
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'extra_object', 'large', 'huge', 'time'])
def test_exact_per_object_budget_required(readonly_request, change, monkeypatch):
    module = implementation()
    path = Path(readonly_request['budget_file'])
    budget = json.loads(path.read_text())
    if change == 'missing':
        budget['objects'] = []
    elif change == 'duplicate':
        budget['objects'].append(copy.deepcopy(budget['objects'][0]))
    elif change == 'extra_object':
        budget['objects'][0]['source_object_id'] = '4'*64
    elif change == 'large':
        budget['group'] = 'large'
    elif change == 'huge':
        budget['objects'][0]['sort_limits']['max_temp_bytes'] = 2**30
    else:
        budget['max_seconds'] = 1801
    readonly_request['budget_sha256'] = bind(path, budget)
    renew(readonly_request)
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


@pytest.mark.parametrize('change', ['changed_file', 'wrong_scope', 'alias'])
def test_related_documents_are_bound(readonly_request, change, monkeypatch):
    module = implementation()
    descriptor = Path(readonly_request['bindings']['descriptor']['path'])
    if change == 'changed_file':
        descriptor.write_text('{}')
    elif change == 'wrong_scope':
        path = Path(readonly_request['scope_file'])
        scope = json.loads(path.read_text())
        scope['bindings']['descriptor'] = '5'*64
        readonly_request['scope_sha256'] = bind(path, scope)
        renew(readonly_request)
    else:
        readonly_request['bindings']['descriptor']['path'] = readonly_request['scope_file']
        readonly_request['bindings']['descriptor']['sha256'] = readonly_request['scope_sha256']
        renew(readonly_request)
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


def test_writable_snapshot_is_rejected(readonly_request, monkeypatch):
    module = implementation()
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError, match='readonly_mount'):
        module.execute_readonly_batch(readonly_request)


def test_snapshot_failure_never_stages(readonly_request, monkeypatch):
    allow_artificial_mounts(monkeypatch)
    snapshot = Path(readonly_request['roots']).parent / 'snapshots' / readonly_request['snapshot_id']
    (snapshot / 'extra').write_text('artificial')
    with pytest.raises(ValueError):
        implementation().execute_readonly_batch(readonly_request)
    assert not Path(readonly_request['output']).exists()


def test_binding_change_after_queries_never_stages(readonly_request, monkeypatch):
    allow_artificial_mounts(monkeypatch)
    module = implementation()
    original = module.summarize_sqlite_batch
    def changing(*a, **kw):
        result = original(*a, **kw)
        Path(readonly_request['bindings']['descriptor']['path']).write_text('{}')
        return result
    monkeypatch.setattr(module, 'summarize_sqlite_batch', changing)
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)
    assert not Path(readonly_request['output']).exists()


def test_cancelled_request_never_stages(readonly_request, monkeypatch):
    allow_artificial_mounts(monkeypatch)
    with pytest.raises(ValueError, match='cancelled'):
        implementation().execute_readonly_batch(readonly_request, cancelled=lambda: True)
    assert not Path(readonly_request['output']).exists()


def test_request_cannot_promote_artificial_config_to_real(readonly_request, monkeypatch):
    module = implementation()
    readonly_request['source_mode'] = 'project_snapshot'
    approval_path = Path(readonly_request['approval_file'])
    approval = json.loads(approval_path.read_text())
    approval.update(source_mode='project_snapshot', source_read_authorized=True,
                    synthetic_data_authorized=False)
    bind(approval_path, approval)
    renew(readonly_request)
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


def test_fixed_probe_exercises_two_tables_and_distinct_budgets(tmp_path, monkeypatch):
    from xiangrugu_datamgmt import synthetic_readonly_probe
    allow_artificial_mounts(monkeypatch)
    request = synthetic_readonly_probe.prepare(tmp_path, image_id='sha256:'+'1'*64,
                                             git_revision='2'*40)
    budget = json.loads(Path(request['budget_file']).read_text())
    assert [o['read_limits']['max_rows'] for o in budget['objects']] == [10, 1]
    staged = implementation().execute_readonly_batch(request)
    report = json.loads(staged.read_text())
    assert [o['expected_count'] for o in report['objects']] == [5, 0]
    assert [o['read_limits']['max_rows'] for o in report['objects']] == [10, 1]


def test_per_table_budget_is_enforced_during_actual_read(tmp_path, monkeypatch):
    from xiangrugu_datamgmt import synthetic_readonly_probe
    allow_artificial_mounts(monkeypatch)
    request = synthetic_readonly_probe.prepare(tmp_path, image_id='sha256:'+'1'*64,
                                             git_revision='2'*40)
    path = Path(request['budget_file'])
    budget = json.loads(path.read_text())
    budget['objects'][0]['read_limits']['max_rows'] = 2
    request['budget_sha256'] = bind(path, budget)
    renew(request)
    with pytest.raises(ValueError):
        implementation().execute_readonly_batch(request)
    assert not Path(request['output']).exists()
    assert not Path(request['output']).with_name('.batch.json.incomplete').exists()


def test_runner_has_artificial_only_mount_modes():
    script = Path(__file__).resolve().parents[3] / 'scripts' / 'run-synthetic-batch.sh'
    text = script.read_text()
    assert 'readonly-prepare' in text and 'readonly-writable' in text
    assert 'dst=/data/var/input,readonly' in text
    assert 'synthetic_readonly_probe' in text


@pytest.mark.parametrize('change', ['kind', 'size', 'hash', 'extra', 'duplicate', 'unsorted', 'absolute'])
def test_all_certificate_descriptors_checked_before_source(readonly_request, change, monkeypatch):
    module = implementation()
    allow_artificial_mounts(monkeypatch)
    path = Path(readonly_request['certificate'])
    certificate = json.loads(path.read_text())
    member = dict(path='z.txt', kind='file', size=0, sha256='0'*64)
    if change == 'kind':
        member['kind'] = 'socket'
    elif change == 'size':
        member['size'] = True
    elif change == 'hash':
        member['sha256'] = 'invalid'
    elif change == 'extra':
        member['extra'] = True
    elif change == 'absolute':
        member['path'] = '/z.txt'
    elif change == 'duplicate':
        member = copy.deepcopy(certificate['members'][0])
    certificate['members'].append(member)
    if change == 'unsorted':
        certificate['members'].reverse()
    certificate['manifest_sha256'] = digest(certificate['members'])
    readonly_request['manifest_sha256'] = certificate['manifest_sha256']
    readonly_request['certificate_sha256'] = bind(path, certificate)
    renew(readonly_request)
    monkeypatch.setattr(module, 'verify_snapshot', lambda *a, **k: pytest.fail('source touched'))
    with pytest.raises(ValueError):
        module.execute_readonly_batch(readonly_request)


def test_late_cancel_retains_incomplete_evidence_without_publication(readonly_request, monkeypatch):
    allow_artificial_mounts(monkeypatch)
    module = implementation()
    original = module.write_json_exclusive
    stopped = False
    def writing(*a, **kw):
        nonlocal stopped
        original(*a, **kw)
        stopped = True
    monkeypatch.setattr(module, 'write_json_exclusive', writing)
    with pytest.raises(ValueError, match='cancelled'):
        module.execute_readonly_batch(readonly_request, cancelled=lambda: stopped)
    final = Path(readonly_request['output'])
    assert not final.exists()
    assert final.with_name('.'+final.name+'.incomplete').is_file()
