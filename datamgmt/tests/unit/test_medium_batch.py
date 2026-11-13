"""Medium approval must not open large budgets or weaken small/default gates."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

from test_task_preparation import metadata, renew as renew_metadata, prepare
from test_project_task_control import project_task_args
from test_task_control import task_args, readonly_request, batch_request, canary_args, args, allow_unit_mounts
from test_readonly_batch import bind, renew
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedLimits, UnorderedSchema, UnorderedColumn, schema_bytes


def medium_limits(identity='0'*64):
    return dict(source_object_id=identity,
        read_limits=asdict(SQLiteValueLimits(max_file_bytes=2**30,max_columns=64,
            max_rows=100000,max_cells=2000000,max_cell_bytes=2**20,
            max_value_bytes=32*2**20,max_vm_steps=100000000,max_seconds=600)),
        sort_limits=asdict(UnorderedLimits(max_rows=100000,max_columns=64,
            max_field_bytes=2**20,max_row_bytes=2**20,max_stream_bytes=32*2**20,
            chunk_bytes=2*2**20,chunk_rows=4096,merge_fan_in=16,
            max_temp_bytes=64*2**20,max_temp_files=1024,max_differences=100,
            max_seconds=600,workers=1)))


def select_limits(description,group='medium'):
    from xiangrugu_datamgmt import readonly_batch
    assert hasattr(readonly_batch,'_group_limits'), 'Group-bound caps are missing'
    return readonly_batch._group_limits(description,group)


def test_medium_caps_are_bounded_and_small_caps_stay_closed():
    read,sort=select_limits(medium_limits())
    assert read.max_rows==100000 and read.max_cells==2000000 and read.max_seconds==600
    assert sort.max_temp_bytes==67108864 and sort.chunk_bytes==2097152 and sort.workers==1
    with pytest.raises(ValueError): select_limits(medium_limits(),'small')


@pytest.mark.parametrize('area,key,value',[
    ('read_limits','max_rows',100001),('read_limits','max_cells',2000001),
    ('read_limits','max_value_bytes',33554433),('read_limits','max_vm_steps',100000001),
    ('read_limits','max_seconds',601),('read_limits','max_columns',65),
    ('read_limits','max_file_bytes',1073741825),('read_limits','max_cell_bytes',1048577),
    ('sort_limits','max_rows',100001),('sort_limits','max_columns',65),
    ('sort_limits','max_stream_bytes',33554433),('sort_limits','max_temp_bytes',67108865),
    ('sort_limits','chunk_bytes',2097153),('sort_limits','chunk_rows',4097),
    ('sort_limits','merge_fan_in',17),('sort_limits','workers',2),
    ('sort_limits','max_temp_files',1025),('sort_limits','max_seconds',601),
    ('sort_limits','max_field_bytes',1048577),('sort_limits','max_row_bytes',1048577)])
def test_medium_cannot_raise_any_cap(area,key,value):
    description=medium_limits()
    description[area][key]=value
    with pytest.raises(ValueError): select_limits(description)


@pytest.mark.parametrize('group',['unknown',None,True,[]])
def test_unknown_and_malformed_groups_are_not_supported(group):
    with pytest.raises(ValueError): select_limits(medium_limits(),group)


def medium_task(project_task_args):
    request=json.loads(project_task_args['request_file'].read_text())
    path=Path(request['budget_file'])
    budget=json.loads(path.read_text())
    budget.update(group='medium',objects=[medium_limits(o['source_object_id']) for o in budget['objects']])
    request['budget_sha256']=bind(path,budget)
    renew(request)
    project_task_args['request_file'].write_text(json.dumps(request))
    project_task_args['expected_request_sha256']=hashlib.sha256(project_task_args['request_file'].read_bytes()).hexdigest()
    project_task_args['expected_approval_sha256']=request['approval_sha256']
    return request,budget


def test_approved_medium_fixture_keeps_full_verification_and_source_only_status(project_task_args,monkeypatch):
    from xiangrugu_datamgmt import task_control
    medium_task(project_task_args)
    allow_unit_mounts(monkeypatch)
    stage=task_control.execute_controlled_batch(**project_task_args)
    result=json.loads(stage.read_text())
    assert result['group']=='medium' and result['complete']
    assert result['file_digest_passes']==2 and result['full_snapshot_verified_this_run']
    assert result['read_cache']['window_bytes']==67108864
    assert not result['postgresql_connected'] and not result['ready_for_import']


@pytest.mark.parametrize('fault',['eleven_objects','large','temp','lifecycle'])
def test_invalid_medium_scope_rejects_before_source(project_task_args,monkeypatch,fault):
    from xiangrugu_datamgmt import task_control,readonly_batch
    request,budget=medium_task(project_task_args)
    if fault=='eleven_objects':
        scope=json.loads(Path(request['scope_file']).read_text())
        while len(scope['objects'])<11:
            scope['objects'].append(dict(scope['objects'][0]))
            budget['objects'].append(dict(budget['objects'][0]))
        request['scope_sha256']=bind(Path(request['scope_file']),scope)
    elif fault=='large': budget['group']='large'
    elif fault=='temp': budget['objects'][0]['sort_limits']['max_temp_bytes']=67108865
    else: budget['max_seconds']=1801
    request['budget_sha256']=bind(Path(request['budget_file']),budget)
    renew(request)
    project_task_args['request_file'].write_text(json.dumps(request))
    project_task_args['expected_request_sha256']=hashlib.sha256(project_task_args['request_file'].read_bytes()).hexdigest()
    project_task_args['expected_approval_sha256']=request['approval_sha256']
    allow_unit_mounts(monkeypatch)
    monkeypatch.setattr(readonly_batch,'verify_snapshot',lambda *a,**k:pytest.fail('source touched'))
    with pytest.raises(ValueError): task_control.execute_controlled_batch(**project_task_args)
    assert not Path(request['output']).exists()


@pytest.fixture
def medium_metadata(metadata):
    documents=metadata['documents']
    objects=[];prepared=[];mapped=[]
    for i,obj in enumerate(documents['original_scope_review']['objects'][:10]):
        identity=obj['source_object_id']
        names=['medium_column_'+str(n) for n in range(12 if i==0 else 16)]
        allocated=allocate_columns(names,object_id=identity)
        columns=[dict(source_ordinal=n,column_key=allocated[n].identity,pg_type='text',allow_null_value=True)
                 for n in range(len(names))]
        schema=UnorderedSchema(identity,tuple(UnorderedColumn(**c) for c in columns))
        digest=hashlib.sha256(schema_bytes(schema)).hexdigest()
        limits=medium_limits(identity)
        objects.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],
            source_columns=names,columns=columns,schema_hash=digest,expected_count=None,expected_sha256=None,
            read_limits=limits['read_limits'],sort_limits=limits['sort_limits']))
        prepared.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],columns=columns,schema_hash=digest))
        mapped.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],
            columns=[dict(source_name=name,source_ordinal=n,column_identity=columns[n]['column_key'],approved_type='text')
                     for n,name in enumerate(names)]))
    metadata['packet']['scope'].update(objects=10,columns=156)
    documents['original_scope_review'].update(group='medium',objects=objects)
    documents['preparation']['objects']=prepared
    documents['mapping']['objects']=mapped
    for obj in documents['remaining_budget']['objects'][:10]: obj['proposed_group']='medium'
    for role in documents: renew_metadata(metadata,role)
    return metadata


def test_medium_preparation_preserves_exact_10_156_and_does_not_authorize_reads(medium_metadata,monkeypatch):
    import sqlite3
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('source opened'))
    marker=prepare(medium_metadata)
    result=json.loads(marker.read_text())
    budget=json.loads((marker.parent/'budget.draft.json').read_text())
    request=json.loads((marker.parent/'request.draft.json').read_text())
    assert result['objects']==10 and result['columns']==156
    assert budget['group']=='medium' and len(budget['objects'])==10 and budget['max_seconds']==1800
    assert budget['objects'][0]['read_limits']['max_seconds']==600
    assert not result['source_bytes_read'] and not result['source_read_authorized']
    assert not result['real_execution_ready'] and request['approval_file'] is None


@pytest.mark.parametrize('fault',['missing','order','columns','large','unsafe_budget'])
def test_medium_preparation_rejects_changed_scope_without_output(medium_metadata,fault):
    review=medium_metadata['documents']['original_scope_review']
    if fault=='missing': review['objects'].pop()
    elif fault=='order': review['objects'].reverse()
    elif fault=='columns': medium_metadata['packet']['scope']['columns']=155
    elif fault=='large': review['group']='large'
    else: review['objects'][0]['sort_limits']['max_temp_bytes']=67108865
    renew_metadata(medium_metadata,'original_scope_review')
    with pytest.raises(ValueError): prepare(medium_metadata)
    assert not medium_metadata['call']['output_dir'].exists()
