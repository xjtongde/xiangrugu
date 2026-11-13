"""Externally selected pins must reject a task before its source is opened."""
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from test_readonly_batch import readonly_request, batch_request, canary_args, args, renew
from xiangrugu_datamgmt.snapshots import write_json_exclusive


def implementation():
    from xiangrugu_datamgmt import task_control
    return task_control


@pytest.fixture
def task_args(readonly_request):
    readonly_request['lifecycle_seconds'] = 1800
    renew(readonly_request)
    path = Path(readonly_request['roots']).parent / 'controlled-request.json'
    write_json_exclusive(path, readonly_request)
    return dict(request_file=path,
        expected_request_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_approval_sha256=readonly_request['approval_sha256'],
        expected_roots_sha256=readonly_request['roots_sha256'],
        actual_image=dict(image_id=readonly_request['image_id'], git_revision=readonly_request['git_revision'],
                          user='10001:10001', source_status='dirty'))


def allow_unit_mounts(monkeypatch):
    module = implementation()
    from xiangrugu_datamgmt import readonly_batch
    monkeypatch.setattr(readonly_batch, '_require_readonly_mount', lambda path: None)
    monkeypatch.setattr(module, '_require_readonly_mount', lambda path: None)


def test_controlled_task_stages_with_external_pins(task_args, monkeypatch):
    allow_unit_mounts(monkeypatch)
    staged = implementation().execute_controlled_batch(**task_args)
    result = json.loads(staged.read_text())
    assert result['complete'] and result['synthetic_only']
    assert result['controller_request_sha256'] == task_args['expected_request_sha256']
    assert result['controller_verified_image'] == task_args['actual_image']
    assert not staged.with_name('observation.json').exists()


@pytest.mark.parametrize('pin', ['expected_request_sha256','expected_approval_sha256','expected_roots_sha256'])
def test_wrong_external_pin_blocks_execution(task_args, pin, monkeypatch):
    module = implementation()
    monkeypatch.setattr(module, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    task_args[pin] = '0'*64
    with pytest.raises(ValueError):
        module.execute_controlled_batch(**task_args)


@pytest.mark.parametrize('field,value', [('image_id','sha256:'+'4'*64),('git_revision','4'*40),
    ('user','0:0'),('source_status','unknown'),('extra',True)])
def test_actual_image_identity_is_checked(task_args, field, value, monkeypatch):
    module = implementation()
    monkeypatch.setattr(module, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    task_args['actual_image'][field] = value
    with pytest.raises(ValueError):
        module.execute_controlled_batch(**task_args)


def test_request_changed_after_pin_selection_is_denied(task_args, monkeypatch):
    module = implementation()
    document = json.loads(task_args['request_file'].read_text())
    document['output'] += '-different'
    task_args['request_file'].write_text(json.dumps(document))
    monkeypatch.setattr(module, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError):
        module.execute_controlled_batch(**task_args)


def test_real_mode_stays_closed_even_with_matching_pins(task_args, monkeypatch):
    module = implementation()
    document = json.loads(task_args['request_file'].read_text())
    document['source_mode'] = 'project_snapshot'
    task_args['request_file'].write_text(json.dumps(document))
    task_args['expected_request_sha256'] = hashlib.sha256(task_args['request_file'].read_bytes()).hexdigest()
    monkeypatch.setattr(module, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError, match='real_execution_closed'):
        module.execute_controlled_batch(**task_args)


def test_writable_task_descriptor_is_denied(task_args, monkeypatch):
    module = implementation()
    monkeypatch.setattr(module, 'execute_readonly_batch', lambda *a, **k: pytest.fail('source opened'))
    with pytest.raises(ValueError, match='readonly_mount'):
        module.execute_controlled_batch(**task_args)


def test_business_roots_are_not_hardcoded_in_entry():
    from xiangrugu_datamgmt import readonly_batch
    source = inspect.getsource(readonly_batch)
    assert '/mnt/wd61workmetadata/usedata' not in source
    assert '/data/imports/usedata' not in source


def test_task_descriptor_change_during_queries_blocks_staging(task_args, monkeypatch):
    allow_unit_mounts(monkeypatch)
    from xiangrugu_datamgmt import readonly_batch
    original = readonly_batch.summarize_sqlite_batch
    def changing(*a, **kw):
        result = original(*a, **kw)
        task_args['request_file'].write_text('{}')
        return result
    monkeypatch.setattr(readonly_batch, 'summarize_sqlite_batch', changing)
    request = json.loads(task_args['request_file'].read_text())
    with pytest.raises(ValueError, match='controller_request_changed'):
        implementation().execute_controlled_batch(**task_args)
    assert not Path(request['output']).exists()
    assert not Path(request['output']).with_name('.'+Path(request['output']).name+'.incomplete').exists()
