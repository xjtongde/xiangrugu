"""Offline metadata preparation must never become source-read authority."""
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from xiangrugu_datamgmt.snapshots import digest
from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedLimits
from dataclasses import asdict


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def metadata(tmp_path):
    repo=tmp_path/'repository'
    repo.mkdir()
    prefix='datamgmt/contracts/artificial/'
    roots_path='datamgmt/config/roots.yaml'
    roots=repo/roots_path
    roots.parent.mkdir(parents=True)
    roots.write_text(yaml.safe_dump(dict(version=1,
        roots=dict(usedata=dict(path=str(tmp_path/'authority-never-open'),host='synthetic',role='authoritative-source')),
        target=dict(instance='pg32b',host='never-connect',port=5433,database='xiangrugu',user='postgres'),
        deployment=dict(source_snapshots=dict(container_root=str(tmp_path/'snapshot-never-open'),
            container_evidence_root=str(tmp_path/'output'))))),encoding='utf-8')
    (tmp_path/'output').mkdir()
    objects=[]; schemas=[]; mapping=[]; budgets=[]
    for index in range(55):
        identity=source_object_id(relative_path='artificial.sqlite3',archive_chain=[],object_name='artificial_'+str(index),carrier='sqlite')
        names=['column_'+str(n) for n in range(2 if index==0 else 6)]
        allocated=allocate_columns(names,object_id=identity)
        columns=[dict(source_ordinal=n,column_key=allocated[n].identity,
                      pg_type='text',allow_null_value=True) for n in range(len(names))]
        schema_hash=hashlib.sha256(json.dumps([[c['source_ordinal'],c['column_key'],c['pg_type'],c['allow_null_value']]
            for c in columns],separators=(',',':')).encode('ascii')).hexdigest()
        objects.append(dict(source_object_id=identity,source_object_name='artificial_'+str(index),
            source_columns=names,columns=columns,schema_hash=schema_hash,expected_count=None,expected_sha256=None,
            read_limits=asdict(SQLiteValueLimits(max_file_bytes=2**30,max_rows=4000,max_cells=50000,max_columns=64,
                max_cell_bytes=2**20,max_value_bytes=8*2**20,max_vm_steps=20000000,max_seconds=300)),
            sort_limits=asdict(UnorderedLimits(max_rows=4000,max_columns=64,max_field_bytes=2**20,
                max_row_bytes=2**20,max_stream_bytes=8*2**20,chunk_bytes=2*2**20,chunk_rows=4096,
                merge_fan_in=16,max_temp_bytes=64*2**20,max_temp_files=1024,max_differences=100,
                max_seconds=300,workers=1))))
        schemas.append(dict(source_object_id=identity,source_object_name='artificial_'+str(index),columns=columns,schema_hash=schema_hash))
        mapping.append(dict(source_object_id=identity,source_object_name='artificial_'+str(index),
            columns=[dict(source_name=name,source_ordinal=n,column_identity=columns[n]['column_key'],approved_type='text') for n,name in enumerate(names)]))
        budgets.append(dict(source_object_id=identity,name='artificial_'+str(index),proposed_group='small'))
    packet=dict(version=1,status='METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE',git_revision='a'*40,
        source_read_authorized=False,postgresql_authorized=False,contract_frozen=False,ready_for_import=False,
        scope=dict(snapshot_id='artificial-snapshot',member=dict(path='artificial.sqlite3',kind='file',size=100,sha256='1'*64),objects=55,columns=326),
        verified_artificial_deadlines=dict(candidate_seconds=1800,host_seconds=1830,transport_seconds=1880,real_mode_activated=False),bindings={})
    documents={'original_scope_review':dict(group='small',rule_id='synthetic',scope=packet['scope'],objects=objects,
        source_read_authorized=False,postgresql_authorized=False,contract_frozen=False,ready_for_import=False),
        'preparation':dict(objects=schemas),'mapping':dict(objects=mapping),'remaining_budget':dict(objects=budgets)}
    for role, document in documents.items():
        relative=prefix+role+'.json'
        packet['bindings'][role]=dict(path=relative,sha256=save(repo/relative,document))
    roots_hash=hashlib.sha256(roots.read_bytes()).hexdigest()
    packet['bindings']['roots']=dict(path=roots_path,sha256=roots_hash)
    review_file=prefix+'review.json'
    pin=save(repo/review_file,packet)
    return dict(repo=repo,packet=packet,documents=documents,call=dict(repository_root=repo,review_file=review_file,
        expected_review_sha256=pin,expected_roots_sha256=roots_hash,expected_image_id='sha256:'+'2'*64,
        actual_image=dict(image_id='sha256:'+'2'*64,git_revision='a'*40,user='10001:10001',source_status='dirty'),
        output_dir=tmp_path/'output'/'new-task'))


def renew(metadata, role=None):
    if role:
        binding=metadata['packet']['bindings'][role]
        binding['sha256']=save(metadata['repo']/binding['path'],metadata['documents'][role])
    metadata['call']['expected_review_sha256']=save(metadata['repo']/metadata['call']['review_file'],metadata['packet'])


def prepare(metadata):
    from xiangrugu_datamgmt.task_preparation import prepare_task
    return prepare_task(**metadata['call'])


def test_preparation_preserves_55_objects_and_keeps_every_execution_gate_closed(metadata,monkeypatch):
    from xiangrugu_datamgmt import snapshots,readonly_batch
    monkeypatch.setattr(snapshots,'verify_snapshot',lambda *a,**k: pytest.fail('snapshot opened'))
    monkeypatch.setattr(readonly_batch,'execute_readonly_batch',lambda *a,**k: pytest.fail('source opened'))
    import sqlite3
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k: pytest.fail('SQLite opened'))
    marker=prepare(metadata)
    result=json.loads(marker.read_text())
    scope=json.loads((marker.parent/'scope.draft.json').read_text())
    request=json.loads((marker.parent/'request.draft.json').read_text())
    budget=json.loads((marker.parent/'budget.draft.json').read_text())
    assert result['status']=='DRAFT_METADATA_TASK_PREPARATION'
    assert result['objects']==55 and result['columns']==326
    assert [o['source_object_name'] for o in scope['objects']]==['artificial_'+str(n) for n in range(55)]
    assert scope['objects'][0]['source_columns']==['column_0','column_1']
    assert budget['objects'][0]['read_limits']['max_rows']==4000
    assert request['lifecycle_seconds']==1800 and result['host_deadline_seconds']==1830 and result['transport_deadline_seconds']==1880
    for document in (result,scope,request):
        assert document['source_read_authorized'] is False and document['postgresql_authorized'] is False
        assert document['ready_for_import'] is False
    assert request['certificate'] is None and request['manifest_sha256'] is None and request['approval_file'] is None
    assert not list(marker.parent.glob('*approved*'))
    assert not (metadata['repo'].parent/'snapshot-never-open').exists()


@pytest.mark.parametrize('field', ['expected_review_sha256','expected_roots_sha256','expected_image_id'])
def test_wrong_external_identity_creates_no_output(metadata,field):
    metadata['call'][field]=('sha256:' if field=='expected_image_id' else '')+'0'*64
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


@pytest.mark.parametrize('field,value',[('image_id','sha256:'+'3'*64),('git_revision','b'*40),('user','0:0'),('source_status','unknown')])
def test_candidate_identity_is_checked_before_output(metadata,field,value):
    metadata['call']['actual_image'][field]=value
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


@pytest.mark.parametrize('fault',['missing','duplicate','extra','reordered','columns','names','schema','source_name','budget_object'])
def test_pinned_metadata_cannot_change_exact_scope(metadata,fault):
    objects=metadata['documents']['original_scope_review']['objects']
    if fault=='missing': objects.pop()
    elif fault=='duplicate': objects[1]=objects[0]
    elif fault=='extra': objects.append(objects[0])
    elif fault=='reordered': objects.reverse()
    elif fault=='columns': objects[0]['columns'].reverse()
    elif fault=='names': objects[0]['source_columns'].reverse()
    elif fault=='schema': objects[0]['schema_hash']='0'*64
    elif fault=='source_name': objects[0]['source_object_name']='different'
    else: metadata['documents']['remaining_budget']['objects'][0]['name']='different'; renew(metadata,'remaining_budget')
    renew(metadata,'original_scope_review')
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


@pytest.mark.parametrize('area,key,value',[('read_limits','max_rows',4001),('sort_limits','max_temp_bytes',67108865),('sort_limits','workers',2),('read_limits','max_seconds',301)])
def test_small_budget_caps_are_enforced(metadata,area,key,value):
    metadata['documents']['original_scope_review']['objects'][0][area][key]=value
    renew(metadata,'original_scope_review')
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


@pytest.mark.parametrize('field', ['source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import'])
def test_readiness_review_cannot_grant_execution_authority(metadata,field):
    metadata['packet'][field]=True; renew(metadata)
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


def test_binding_escape_is_denied_without_opening_outside_file(metadata):
    metadata['packet']['bindings']['roots']['path']='../outside.yaml'; renew(metadata)
    with pytest.raises(ValueError): prepare(metadata)


def test_changed_input_digest_creates_no_output(metadata):
    path=metadata['repo']/metadata['packet']['bindings']['mapping']['path']
    path.write_text('{}')
    with pytest.raises(ValueError): prepare(metadata)
    assert not metadata['call']['output_dir'].exists()


def test_existing_output_directory_is_never_overwritten(metadata):
    directory=metadata['call']['output_dir']; directory.mkdir()
    sentinel=directory/'scope.draft.json'; sentinel.write_text('retained')
    with pytest.raises(FileExistsError): prepare(metadata)
    assert sentinel.read_text()=='retained'


def test_generated_template_is_rejected_by_existing_controller(metadata):
    from xiangrugu_datamgmt.task_control import execute_controlled_batch
    marker=prepare(metadata)
    request=marker.parent/'request.draft.json'
    with pytest.raises(ValueError,match='real_execution_closed'):
        execute_controlled_batch(request_file=request,expected_request_sha256=hashlib.sha256(request.read_bytes()).hexdigest(),
            expected_roots_sha256=metadata['call']['expected_roots_sha256'],expected_approval_sha256='0'*64,
            actual_image=metadata['call']['actual_image'])


def test_failed_draft_persistence_leaves_no_completion_marker(metadata,monkeypatch):
    from xiangrugu_datamgmt import task_preparation
    original=task_preparation.write_json_exclusive
    def fail(path,value):
        if path.name=='request.draft.json': raise OSError('artificial persistence failure')
        return original(path,value)
    monkeypatch.setattr(task_preparation,'write_json_exclusive',fail)
    with pytest.raises(OSError): prepare(metadata)
    assert metadata['call']['output_dir'].is_dir()
    assert not (metadata['call']['output_dir']/'preparation.json').exists()


def test_completion_record_fsync_failure_cannot_leave_completion_marker(metadata,monkeypatch):
    from xiangrugu_datamgmt import snapshots
    original=snapshots.os.fsync
    calls=[0]
    def fail(fd):
        calls[0]+=1
        if calls[0]==4: raise OSError('artificial completion fsync failure')
        return original(fd)
    monkeypatch.setattr(snapshots.os,'fsync',fail)
    with pytest.raises(OSError): prepare(metadata)
    assert not (metadata['call']['output_dir']/'preparation.json').exists()
