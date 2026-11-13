"""Owned metadata only: project protocol does not grant human authority."""
import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

from test_task_partition import large, metadata
from test_task_preparation import renew
from xiangrugu_datamgmt.snapshots import digest


def pin(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def save(path,document):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(document))
    return pin(path)


def api():
    return importlib.import_module('xiangrugu_datamgmt.project_partition')


@pytest.fixture
def project_data(large):
    from xiangrugu_datamgmt.task_partition import prepare_partition_task
    roots=large['repo']/'datamgmt/config/roots.yaml'
    config=yaml.safe_load(roots.read_text());config['roots']['usedata']['host']='owned-protocol-fixture'
    roots.write_text(yaml.safe_dump(config))
    root_pin=pin(roots)['sha256'];large['packet']['bindings']['roots']['sha256']=root_pin
    large['call']['expected_roots_sha256']=root_pin;renew(large)
    marker=prepare_partition_task(**large['call'],partition_id='large-p01')
    base=large['repo'].parent/'project';base.mkdir()
    files={role:pin(marker.parent/name) for role,name in [('preparation','preparation.json'),
        ('parent_scope','parent.scope.draft.json'),('parent_budget','parent.budget.draft.json'),
        ('partition_selection','partition.selection.draft.json'),('draft_scope','scope.draft.json'),
        ('draft_budget','budget.draft.json'),('draft_request','request.draft.json')]}
    files['parent_review']=pin(large['repo']/large['call']['review_file']);files['roots']=pin(roots)
    parent=json.loads(Path(files['parent_scope']['path']).read_text())
    cert=dict(version=1,status='VERIFIED',snapshot_id=parent['snapshot_id'],
        source_path=config['roots']['usedata']['path'],members=[parent['source']],manifest_sha256=digest([parent['source']]))
    files['certificate']=save(base/'certificate.json',cert)
    selection=dict(version=1,status='SELECTED_PROJECT_PARTITION_REVIEW_METADATA',source_mode='project_snapshot',
        partition_id='large-p01',attempt_id='owned-attempt',files=files,expected_manifest_sha256=cert['manifest_sha256'])
    return dict(base=base,selection=selection,selection_path=base/'selection.json',image=large['call']['actual_image'],
        output=base/'review',evidence=Path(config['deployment']['source_snapshots']['container_evidence_root']),large=large)


def review(data,**kwargs):
    chosen=save(data['selection_path'],data['selection'])
    return api().prepare_project_partition_review(selection_file=Path(chosen['path']),expected_selection_sha256=chosen['sha256'],
        actual_image=data['image'],output_dir=data['output'],**kwargs)


def materialize(data,marker):
    return api().materialize_project_partition_request(review_file=marker,expected_review_sha256=pin(marker)['sha256'],
        actual_image=data['image'],output_dir=data['base']/'execution',result_file=data['evidence']/'batch.json',
        scratch_parent=data['evidence']/'disk-scratch')


def test_review_complete_identity_still_not_executable(project_data,monkeypatch):
    import sqlite3
    from xiangrugu_datamgmt import snapshots
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('source opened'))
    monkeypatch.setattr(snapshots,'verify_snapshot',lambda *a,**k:pytest.fail('snapshot opened'))
    marker=review(project_data);doc=json.loads(marker.read_text())
    assert doc['status']=='DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE' and doc['missing']==[]
    for flag in ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import'):assert doc[flag] is False
    assert not (marker.parent/'approval.json').exists()


@pytest.mark.parametrize('missing',['certificate','manifest','image'])
def test_review_stays_closed_with_missing_identity(project_data,missing):
    data=project_data
    if missing=='certificate':data['selection']['files']['certificate']=None
    elif missing=='manifest':data['selection']['expected_manifest_sha256']=None
    else:data['image']=None
    marker=review(data);doc=json.loads(marker.read_text())
    assert missing in doc['missing']
    with pytest.raises(ValueError):materialize(data,marker)
    assert not (data['base']/'execution/request.json').exists()


def test_materialized_request_exact_projection(project_data):
    data=project_data;request_path=materialize(data,review(data));request=json.loads(request_path.read_text())
    scope=json.loads(Path(request['scope_file']).read_text());budget=json.loads(Path(request['budget_file']).read_text())
    parent=json.loads(Path(data['selection']['files']['parent_scope']['path']).read_text())
    assert scope['objects']==parent['objects'][:1] and budget['group']=='large' and len(budget['objects'])==1
    assert request['source_mode']=='project_snapshot' and scope['source_read_authorized'] is True
    assert scope['synthetic_data_authorized'] is False and scope['postgresql_authorized'] is False
    assert set(request['bindings'])=={'parent_scope','parent_budget','partition_selection','descriptor'}
    assert scope['bindings']=={k:v['sha256'] for k,v in request['bindings'].items()}
    evidence=dict(controller_request_sha256=pin(request_path)['sha256'],controller_verified_image=data['image'],controller_lifecycle_seconds=1800)
    checked=api().validate_project_partition_request(request=request,controller_evidence=evidence)
    assert checked.partition_id=='large-p01' and checked.attempt_id=='owned-attempt'
    api().recheck_project_partition_metadata(checked)


@pytest.mark.parametrize('role',['parent_scope','parent_budget','partition_selection','draft_scope','draft_budget','draft_request','parent_review','preparation','roots','certificate'])
def test_rehashed_semantic_replacement_rejected(project_data,role):
    old=project_data['selection']['files'][role]
    project_data['selection']['files'][role]=save(project_data['base']/(role+'-bad.json'),{})
    with pytest.raises(ValueError):review(project_data)
    assert not (project_data['output']/'review.json').exists()


@pytest.mark.parametrize('field,value',[('partition_id','large-p11'),('attempt_id','../escape'),('version',True),('source_mode','artificial'),('extra',1)])
def test_selection_unknown_or_wrong_type_rejected(project_data,field,value):
    project_data['selection'][field]=value
    with pytest.raises(ValueError):review(project_data)


def test_metadata_changed_after_validation_rejected(project_data):
    path=materialize(project_data,review(project_data));request=json.loads(path.read_text())
    checked=api().validate_project_partition_request(request=request,controller_evidence=dict(
        controller_request_sha256=pin(path)['sha256'],controller_verified_image=project_data['image'],controller_lifecycle_seconds=1800))
    Path(project_data['selection']['files']['parent_review']['path']).write_text('{}')
    with pytest.raises(ValueError):api().recheck_project_partition_metadata(checked)


def test_direct_call_without_controller_rejected(project_data):
    path=materialize(project_data,review(project_data))
    with pytest.raises(ValueError):api().validate_project_partition_request(request=json.loads(path.read_text()),controller_evidence=None)


def test_existing_review_not_overwritten(project_data):
    marker=review(project_data);before=marker.read_bytes()
    with pytest.raises(FileExistsError):review(project_data)
    assert marker.read_bytes()==before


def test_cancel_before_publish_has_no_marker(project_data):
    with pytest.raises(ValueError):review(project_data,cancelled=lambda:True)
    assert not (project_data['output']/'review.json').exists()


@pytest.mark.parametrize('change',['id','column_order','budget'])
def test_same_ten_scope_semantic_change_rejected(project_data,change):
    role='parent_budget' if change=='budget' else 'parent_scope'
    desc=project_data['selection']['files'][role];path=Path(desc['path']);doc=json.loads(path.read_text())
    if change=='id':doc['objects'][0]['source_object_id']='f'*64
    elif change=='column_order':doc['objects'][0]['columns'].reverse()
    else:doc['objects'][0]['sort_limits']['max_temp_bytes']-=1
    project_data['selection']['files'][role]=save(path,doc)
    with pytest.raises(ValueError):review(project_data)


@pytest.mark.parametrize('change',['input','stage'])
def test_metadata_or_stage_changed_before_link(project_data,monkeypatch,change):
    module=api();original=module.write_json_exclusive
    def write(path,doc):
        original(path,doc)
        if path.name=='.review.json.incomplete':
            target=Path(project_data['selection']['files']['parent_review']['path']) if change=='input' else path
            target.write_text('{}')
    monkeypatch.setattr(module,'write_json_exclusive',write)
    with pytest.raises(ValueError):review(project_data)
    assert not (project_data['output']/'review.json').exists()


def test_symlink_output_rejected_without_creation(project_data):
    target=project_data['base']/'target';target.mkdir()
    alias=project_data['base']/'alias';alias.symlink_to(target,target_is_directory=True)
    project_data['output']=alias/'review'
    with pytest.raises(ValueError):review(project_data)
    assert list(target.iterdir())==[]


def test_review_cli_rejects_execution_options(project_data):
    import subprocess
    import sys
    chosen=save(project_data['selection_path'],project_data['selection'])
    result=subprocess.run([sys.executable,'-m','xiangrugu_datamgmt.project_partition','--selection',chosen['path'],
        '--selection-sha256',chosen['sha256'],'--output-dir',str(project_data['output']),'--materialize'],capture_output=True,text=True)
    assert result.returncode==2 and not project_data['output'].exists()


def test_closed_review_cannot_run(project_data,monkeypatch):
    from xiangrugu_datamgmt import task_control
    marker=review(project_data)
    monkeypatch.setattr(task_control,'execute_readonly_batch',lambda *a,**k:pytest.fail('source execution'))
    with pytest.raises(ValueError):task_control.execute_controlled_batch(request_file=marker,
        expected_request_sha256=pin(marker)['sha256'],expected_approval_sha256='a'*64,
        expected_roots_sha256=project_data['selection']['files']['roots']['sha256'],actual_image=project_data['image'],
        authorized_source_mode='project_snapshot')


def test_rehashed_review_template_authority_rejected(project_data):
    marker=review(project_data);record=json.loads(marker.read_text())
    path=marker.parent/'request.review.json';template=json.loads(path.read_text());template['source_read_authorized']=True
    record['generated']['request.review.json']=save(path,template)['sha256'];save(marker,record)
    with pytest.raises(ValueError):materialize(project_data,marker)


@pytest.mark.parametrize('field',['objects','columns','parent_objects','parent_columns'])
def test_preparation_counts_are_strict_integers(project_data,field):
    desc=project_data['selection']['files']['preparation'];path=Path(desc['path'])
    doc=json.loads(path.read_text());doc[field]=True if field=='objects' else float(doc[field])
    project_data['selection']['files']['preparation']=save(path,doc)
    with pytest.raises(ValueError):review(project_data)


@pytest.mark.parametrize('change',['extra','destination'])
def test_reapproved_invalid_request_rejected(project_data,change):
    path=materialize(project_data,review(project_data));request=json.loads(path.read_text())
    if change=='extra':request['unselected_field']=True
    else:request['output']='/outside-evidence/batch.json'
    approval_path=Path(request['approval_file']);approval=json.loads(approval_path.read_text())
    approval['request_sha256']=digest({k:v for k,v in request.items() if k not in ('approval_file','approval_sha256')})
    request['approval_sha256']=save(approval_path,approval)['sha256'];save(path,request)
    with pytest.raises(ValueError):api().validate_project_partition_request(request=request,controller_evidence=dict(
        controller_request_sha256=pin(path)['sha256'],controller_verified_image=project_data['image'],controller_lifecycle_seconds=1800))


@pytest.mark.parametrize('change',['missing','extra','duplicate','schema','image','manifest','certificate','alias'])
def test_rehashed_complete_identity_rejects_semantic_replacement(project_data,change):
    data=project_data;role='parent_scope';desc=data['selection']['files'][role]
    doc=json.loads(Path(desc['path']).read_text())
    if change=='missing':doc['objects'].pop()
    elif change=='extra':doc['objects'].append(copy.deepcopy(doc['objects'][0]))
    elif change=='duplicate':doc['objects'][-1]=copy.deepcopy(doc['objects'][0])
    elif change=='schema':doc['objects'][0]['columns'][0]['pg_type']='bigint'
    elif change=='image':data['image']=dict(data['image'],image_id='sha256:'+'f'*64)
    elif change=='manifest':data['selection']['expected_manifest_sha256']='f'*64
    elif change=='certificate':
        role='certificate';desc=data['selection']['files'][role];doc=json.loads(Path(desc['path']).read_text());doc['snapshot_id']='other'
    elif change=='alias':data['selection']['files']['draft_scope']=desc
    if change not in ('image','manifest','alias'):data['selection']['files'][role]=save(Path(desc['path']),doc)
    with pytest.raises(ValueError):review(data)


def test_rehashed_unknown_preparation_field_rejected(project_data):
    desc=project_data['selection']['files']['preparation'];path=Path(desc['path']);doc=json.loads(path.read_text())
    doc['unselected_authority']=True;project_data['selection']['files']['preparation']=save(path,doc)
    with pytest.raises(ValueError):review(project_data)
