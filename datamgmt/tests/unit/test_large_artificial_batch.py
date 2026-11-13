"""Large metadata/limits support must not authorize real snapshot execution."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

from test_medium_batch import medium_limits
from test_project_task_control import project_task_args
from test_task_control import task_args, readonly_request, batch_request, canary_args, args, allow_unit_mounts
from test_readonly_batch import bind, renew
from test_task_preparation import metadata, prepare, renew as renew_metadata
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema, schema_bytes


def large_limits(identity='0'*64):
    result=medium_limits(identity)
    result['read_limits'].update(max_rows=2000000,max_cells=40000000,
        max_value_bytes=256*2**20,max_vm_steps=1000000000,max_seconds=1800)
    result['sort_limits'].update(max_rows=2000000,max_stream_bytes=256*2**20,
        max_temp_bytes=2**30,max_seconds=1800)
    return result


def test_large_caps_keep_chunk_cpu_independent_and_lifecycle_bound():
    from xiangrugu_datamgmt.readonly_batch import _group_limits
    read,sort=_group_limits(large_limits(),'large')
    assert read.max_rows==2000000 and read.max_cells==40000000
    assert read.max_seconds==1800 and sort.max_seconds==1800
    assert sort.max_temp_bytes==2**30 and sort.chunk_bytes==2*2**20 and sort.workers==1
    for group in ('small','medium'):
        with pytest.raises(ValueError): _group_limits(large_limits(),group)


@pytest.mark.parametrize('area,key,value',[
    ('read_limits','max_rows',2000001),('read_limits','max_cells',40000001),
    ('read_limits','max_value_bytes',268435457),('read_limits','max_vm_steps',1000000001),
    ('read_limits','max_seconds',1801),('read_limits','max_columns',65),
    ('read_limits','max_file_bytes',1073741825),('read_limits','max_cell_bytes',1048577),
    ('sort_limits','max_rows',2000001),('sort_limits','max_columns',65),
    ('sort_limits','max_stream_bytes',268435457),('sort_limits','max_temp_bytes',1073741825),
    ('sort_limits','chunk_bytes',2097153),('sort_limits','chunk_rows',4097),
    ('sort_limits','merge_fan_in',17),('sort_limits','workers',2),
    ('sort_limits','max_temp_files',1025),('sort_limits','max_seconds',1801),
    ('sort_limits','max_field_bytes',1048577),('sort_limits','max_row_bytes',1048577)])
def test_large_cannot_raise_any_cap(area,key,value):
    from xiangrugu_datamgmt.readonly_batch import _group_limits
    limits=large_limits(); limits[area][key]=value
    with pytest.raises(ValueError): _group_limits(limits,'large')


def select_large(call):
    request=json.loads(call['request_file'].read_text())
    path=Path(request['budget_file']); budget=json.loads(path.read_text())
    budget.update(group='large',objects=[large_limits(o['source_object_id']) for o in budget['objects']])
    request['budget_sha256']=bind(path,budget); renew(request)
    call['request_file'].write_text(json.dumps(request))
    call['expected_request_sha256']=hashlib.sha256(call['request_file'].read_bytes()).hexdigest()
    call['expected_approval_sha256']=request['approval_sha256']
    return request,budget


def test_large_artificial_control_retains_complete_two_hash_batch(task_args,monkeypatch):
    from xiangrugu_datamgmt import task_control
    select_large(task_args); allow_unit_mounts(monkeypatch)
    stage=task_control.execute_controlled_batch(**task_args)
    result=json.loads(stage.read_text())
    assert result['complete'] and result['group']=='large' and result['synthetic_only']
    assert result['file_digest_passes']==2 and result['full_snapshot_verified_this_run']
    assert not result['postgresql_connected'] and not result['ready_for_import']


def test_large_real_request_is_closed_before_snapshot_bytes(project_task_args,monkeypatch):
    from xiangrugu_datamgmt import task_control,readonly_batch
    request,_=select_large(project_task_args); allow_unit_mounts(monkeypatch)
    monkeypatch.setattr(readonly_batch,'verify_snapshot',lambda *a,**k:pytest.fail('source bytes read'))
    with pytest.raises(ValueError,match='large_real_disabled'):
        task_control.execute_controlled_batch(**project_task_args)
    assert not Path(request['output']).exists()


@pytest.fixture
def large_metadata(metadata):
    documents=metadata['documents']; objects=[]; prepared=[]; mapped=[]
    for index,obj in enumerate(documents['original_scope_review']['objects'][:10]):
        identity=obj['source_object_id']; names=['large_column_'+str(n) for n in range(19 if index==0 else 24)]
        allocated=allocate_columns(names,object_id=identity)
        columns=[dict(source_ordinal=n,column_key=allocated[n].identity,pg_type='text',allow_null_value=True) for n in range(len(names))]
        digest=hashlib.sha256(schema_bytes(UnorderedSchema(identity,tuple(UnorderedColumn(**c) for c in columns)))).hexdigest()
        limits=large_limits(identity)
        objects.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],source_columns=names,
            columns=columns,schema_hash=digest,expected_count=None,expected_sha256=None,
            read_limits=limits['read_limits'],sort_limits=limits['sort_limits']))
        prepared.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],columns=columns,schema_hash=digest))
        mapped.append(dict(source_object_id=identity,source_object_name=obj['source_object_name'],columns=[dict(source_name=name,
            source_ordinal=n,column_identity=columns[n]['column_key'],approved_type='text') for n,name in enumerate(names)]))
    metadata['packet']['scope'].update(objects=10,columns=235)
    documents['original_scope_review'].update(group='large',objects=objects)
    documents['preparation']['objects']=prepared; documents['mapping']['objects']=mapped
    for obj in documents['remaining_budget']['objects'][:10]: obj['proposed_group']='large'
    for role in documents: renew_metadata(metadata,role)
    return metadata


def test_large_preparation_is_exact_draft_without_source_or_approval(large_metadata,monkeypatch):
    import sqlite3
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('source opened'))
    marker=prepare(large_metadata); result=json.loads(marker.read_text())
    budget=json.loads((marker.parent/'budget.draft.json').read_text())
    request=json.loads((marker.parent/'request.draft.json').read_text())
    assert result['objects']==10 and result['columns']==235
    assert budget['group']=='large' and budget['max_seconds']==1800
    assert budget['objects'][0]['sort_limits']['max_temp_bytes']==2**30
    assert not result['source_bytes_read'] and not result['source_read_authorized']
    assert not result['real_execution_ready'] and request['approval_file'] is None


@pytest.mark.parametrize('fault',['missing','order','columns','unsafe_budget'])
def test_large_preparation_rejects_changed_scope(large_metadata,fault):
    review=large_metadata['documents']['original_scope_review']
    if fault=='missing': review['objects'].pop()
    elif fault=='order': review['objects'].reverse()
    elif fault=='columns': large_metadata['packet']['scope']['columns']=234
    else: review['objects'][0]['sort_limits']['max_temp_bytes']=2**30+1
    renew_metadata(large_metadata,'original_scope_review')
    with pytest.raises(ValueError): prepare(large_metadata)
    assert not large_metadata['call']['output_dir'].exists()
