"""Closed single-table preparation using only artificial repository metadata."""
import hashlib
import json
from dataclasses import asdict

import pytest

from test_task_preparation import metadata, renew
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedLimits


@pytest.fixture
def large(metadata):
    docs=metadata['documents']
    review=docs['original_scope_review']
    review['group']='large'
    review['objects']=review['objects'][:10]
    for role in ('preparation','mapping','remaining_budget'):
        docs[role]['objects']=docs[role]['objects'][:10]
    for i,width in enumerate([8,11,34,6,29,42,12,10,28,55]):
        obj=review['objects'][i]
        names=[f'column_{n}' for n in range(width)]
        allocated=allocate_columns(names,object_id=obj['source_object_id'])
        cols=[dict(source_ordinal=n,column_key=allocated[n].identity,pg_type='text',allow_null_value=True) for n in range(width)]
        schema=hashlib.sha256(json.dumps([[c['source_ordinal'],c['column_key'],c['pg_type'],c['allow_null_value']] for c in cols],separators=(',',':')).encode()).hexdigest()
        obj.update(source_columns=names,columns=cols,schema_hash=schema,
            read_limits=asdict(SQLiteValueLimits(max_file_bytes=2**30,max_columns=64,max_rows=2000000,max_cells=40000000,max_cell_bytes=2**20,max_value_bytes=256*2**20,max_vm_steps=1000000000,max_seconds=1800)),
            sort_limits=asdict(UnorderedLimits(max_rows=2000000,max_columns=64,max_field_bytes=2**20,max_row_bytes=2**20,max_stream_bytes=256*2**20,chunk_bytes=2*2**20,chunk_rows=4096,merge_fan_in=16,max_temp_bytes=2**30,max_temp_files=1024,max_seconds=1800,workers=1)))
        docs['preparation']['objects'][i].update(columns=cols,schema_hash=schema)
        docs['mapping']['objects'][i]['columns']=[dict(source_name=name,source_ordinal=n,column_identity=cols[n]['column_key'],approved_type='text') for n,name in enumerate(names)]
        docs['remaining_budget']['objects'][i]['proposed_group']='large'
    metadata['packet']['scope'].update(objects=10,columns=235)
    for role in docs: renew(metadata,role)
    return metadata


def call(data,partition='large-p01'):
    from xiangrugu_datamgmt.task_partition import prepare_partition_task
    return prepare_partition_task(**data['call'],partition_id=partition)


@pytest.mark.parametrize('index',range(10))
def test_exact_projection_and_six_digest_bindings(large,index,monkeypatch):
    import sqlite3
    from xiangrugu_datamgmt import snapshots,readonly_batch
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('SQLite opened'))
    monkeypatch.setattr(snapshots,'verify_snapshot',lambda *a,**k:pytest.fail('snapshot opened'))
    monkeypatch.setattr(readonly_batch,'execute_readonly_batch',lambda *a,**k:pytest.fail('execution attempted'))
    marker=call(large,f'large-p{index+1:02d}')
    record=json.loads(marker.read_text())
    documents={name:json.loads((marker.parent/name).read_text()) for name in record['generated']}
    assert len(documents)==6 and record['parent_objects']==10 and record['parent_columns']==235
    assert record['objects']==1 and record['columns']==len(large['documents']['original_scope_review']['objects'][index]['columns'])
    assert len(documents['parent.scope.draft.json']['objects'])==10
    obj=large['documents']['original_scope_review']['objects'][index]
    assert documents['scope.draft.json']['objects']==[{k:obj[k] for k in ('source_object_id','source_object_name','source_columns','columns')}]
    assert documents['budget.draft.json']['objects']==[{k:obj[k] for k in ('source_object_id','read_limits','sort_limits')}]
    selection=documents['partition.selection.draft.json']
    assert selection['parent_review_sha256']==large['call']['expected_review_sha256']
    assert selection['parent_scope_sha256']==record['generated']['parent.scope.draft.json']
    assert selection['parent_budget_sha256']==record['generated']['parent.budget.draft.json']
    for role,name in [('parent_scope','parent.scope.draft.json'),('parent_budget','parent.budget.draft.json'),('partition_selection','partition.selection.draft.json')]:
        assert documents['scope.draft.json']['bindings'][role]==record['generated'][name]
        assert documents['request.draft.json']['bindings'][role]==dict(path=str(marker.parent/name),sha256=record['generated'][name])
    for name,pin in record['generated'].items():
        assert hashlib.sha256((marker.parent/name).read_bytes()).hexdigest()==pin
    for document in (record,documents['scope.draft.json'],documents['request.draft.json'],selection):
        for flag in ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import'): assert document[flag] is False
    assert not (marker.parent/'approval.json').exists()
    from xiangrugu_datamgmt.task_control import execute_controlled_batch
    request=marker.parent/'request.draft.json'
    with pytest.raises(ValueError,match='real_execution_closed'):
        execute_controlled_batch(request_file=request,expected_request_sha256=record['generated'][request.name],expected_roots_sha256=large['call']['expected_roots_sha256'],expected_approval_sha256='0'*64,actual_image=large['call']['actual_image'])


@pytest.mark.parametrize('partition',['large-p1','large-p00','large-p11','LARGE-p01','large-p01 ',True,None])
def test_invalid_partition(large,partition):
    with pytest.raises(ValueError,match='preparation_partition'): call(large,partition)
    assert not large['call']['output_dir'].exists()


def test_small_parent_rejected(metadata):
    with pytest.raises(ValueError,match='preparation_partition_group'): call(metadata)


@pytest.mark.parametrize('fault',['duplicate','schema','budget','expectation'])
def test_unselected_parent_object_must_be_valid(large,fault):
    objects=large['documents']['original_scope_review']['objects']
    if fault=='duplicate': objects[-1]=objects[0]
    if fault=='schema': objects[-1]['schema_hash']='0'*64
    if fault=='budget': objects[-1]['sort_limits']['workers']=2
    if fault=='expectation': objects[-1]['expected_count']=1
    renew(large,'original_scope_review')
    with pytest.raises(ValueError): call(large)
    assert not large['call']['output_dir'].exists()


@pytest.mark.parametrize('field',['expected_review_sha256','expected_roots_sha256','expected_image_id'])
def test_external_identity_pin_mismatch(large,field):
    large['call'][field]=('sha256:' if field=='expected_image_id' else '')+'0'*64
    with pytest.raises(ValueError): call(large)


def test_existing_output_preserved(large):
    output=large['call']['output_dir'];output.mkdir();sentinel=output/'keep';sentinel.write_text('retained')
    with pytest.raises(FileExistsError): call(large)
    assert sentinel.read_text()=='retained'


@pytest.mark.parametrize('target',['repo','source','snapshot'])
def test_output_roots_forbidden(large,target):
    large['call']['output_dir']={'repo':large['repo'],'source':large['repo'].parent/'authority-never-open','snapshot':large['repo'].parent/'snapshot-never-open'}[target]
    with pytest.raises(ValueError): call(large)


@pytest.mark.parametrize('change',['input','generated','stage'])
def test_change_before_completion_leaves_no_marker(large,monkeypatch,change):
    from xiangrugu_datamgmt import task_partition
    original=task_partition.write_json_exclusive
    def write(path,value):
        original(path,value)
        if path.name=='.preparation.incomplete':
            changed=(large['repo']/large['call']['review_file'] if change=='input' else path if change=='stage' else path.parent/'partition.selection.draft.json')
            changed.write_text('{}')
    monkeypatch.setattr(task_partition,'write_json_exclusive',write)
    with pytest.raises(ValueError,match='preparation_.*_changed'): call(large)
    assert not (large['call']['output_dir']/'preparation.json').exists()


def test_cli_requires_explicit_selection():
    import subprocess
    import sys
    result=subprocess.run([sys.executable,'-m','xiangrugu_datamgmt.task_partition'],capture_output=True,text=True)
    assert result.returncode==2 and '--partition-id' in result.stderr
