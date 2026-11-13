"""Project-shaped owned metadata exercises both gates without source access."""
import json
from pathlib import Path

import pytest

from test_project_partition import large, metadata, project_data, materialize, review, pin, save


@pytest.fixture
def execution(project_data,monkeypatch):
    from xiangrugu_datamgmt import readonly_batch,task_control
    path=materialize(project_data,review(project_data));request=json.loads(path.read_text())
    Path(request['scratch_parent']).mkdir()
    monkeypatch.setattr(readonly_batch,'_require_readonly_mount',lambda path:None)
    monkeypatch.setattr(task_control,'_require_readonly_mount',lambda path:None)
    calls=[]
    monkeypatch.setattr(readonly_batch,'verify_snapshot',lambda *a,**kw:calls.append('snapshot'))
    def summarize(*a,**kw):
        calls.append('values')
        if kw.get('progress'):kw['progress']('object_read_sort',object_index=0)
        return dict(complete=True)
    monkeypatch.setattr(readonly_batch,'summarize_sqlite_batch',summarize)
    evidence=dict(controller_request_sha256=pin(path)['sha256'],controller_verified_image=project_data['image'],controller_lifecycle_seconds=1800)
    args=dict(request_file=path,expected_request_sha256=pin(path)['sha256'],expected_approval_sha256=request['approval_sha256'],
        expected_roots_sha256=request['roots_sha256'],actual_image=project_data['image'],authorized_source_mode='project_snapshot')
    return dict(data=project_data,path=path,request=request,evidence=evidence,args=args,calls=calls)


@pytest.mark.parametrize('entry',['control','bottom'])
def test_project_large_single_partition_reaches_owned_source_spy(execution,entry):
    from xiangrugu_datamgmt import readonly_batch,task_control
    if entry=='control':stage=task_control.execute_controlled_batch(**execution['args'])
    else:stage=readonly_batch.execute_readonly_batch(execution['request'],controller_evidence=execution['evidence'])
    assert execution['calls']==['snapshot','values']
    result=json.loads(stage.read_text())
    assert result['source_mode']=='project_snapshot' and not result['synthetic_only']
    assert result['bindings'].keys()=={'parent_scope','parent_budget','partition_selection','descriptor'}


def test_control_preflight_denies_bad_chain_before_bottom_entry(execution,monkeypatch):
    from xiangrugu_datamgmt import task_control
    Path(execution['request']['bindings']['descriptor']['path']).write_text('{}')
    monkeypatch.setattr(task_control,'execute_readonly_batch',lambda *a,**kw:pytest.fail('bottom entry reached'))
    with pytest.raises(ValueError):task_control.execute_controlled_batch(**execution['args'])
    assert execution['calls']==[]


def test_project_large_direct_call_without_controller_rejected(execution):
    from xiangrugu_datamgmt import readonly_batch
    with pytest.raises(ValueError):readonly_batch.execute_readonly_batch(execution['request'])
    assert execution['calls']==[]


@pytest.mark.parametrize('count',[2,10])
def test_project_large_rejects_full_ten_and_two_objects(execution,count):
    from xiangrugu_datamgmt import readonly_batch
    from xiangrugu_datamgmt.snapshots import digest
    request=execution['request'];files=execution['data']['selection']['files']
    for role,key,parent_role in [('scope','scope_file','parent_scope'),('budget','budget_file','parent_budget')]:
        path=Path(request[key]);doc=json.loads(path.read_text())
        doc['objects']=json.loads(Path(files[parent_role]['path']).read_text())['objects'][:count]
        request[role+'_sha256']=save(path,doc)['sha256']
    approval_path=Path(request['approval_file']);approval=json.loads(approval_path.read_text())
    approval['request_sha256']=digest({k:v for k,v in request.items() if k not in ('approval_file','approval_sha256')})
    request['approval_sha256']=save(approval_path,approval)['sha256']
    with pytest.raises(ValueError):readonly_batch.execute_readonly_batch(request,controller_evidence=execution['evidence'])
    assert execution['calls']==[]


@pytest.mark.parametrize('role',['descriptor','parent_review'])
def test_partition_metadata_changed_before_stage_stops(execution,role):
    from xiangrugu_datamgmt import readonly_batch
    target=execution['request']['bindings']['descriptor'] if role=='descriptor' else execution['data']['selection']['files'][role]
    def progress(stage,**details):
        if stage=='stage_save':Path(target['path']).write_text('{}')
    with pytest.raises(ValueError):readonly_batch.execute_readonly_batch(execution['request'],controller_evidence=execution['evidence'],progress=progress)
    output=Path(execution['request']['output'])
    assert execution['calls']==['snapshot','values'] and not output.with_name('.'+output.name+'.incomplete').exists()


@pytest.mark.parametrize('entry',['control','bottom'])
def test_partition_metadata_changed_at_boundary_stops(execution,entry):
    from xiangrugu_datamgmt import readonly_batch,task_control
    def progress(stage,**details):
        if stage=='object_read_sort':Path(execution['data']['selection']['files']['parent_review']['path']).write_text('{}')
    with pytest.raises(ValueError):
        if entry=='control':task_control.execute_controlled_batch(**execution['args'],progress=progress)
        else:readonly_batch.execute_readonly_batch(execution['request'],controller_evidence=execution['evidence'],progress=progress)
    output=Path(execution['request']['output'])
    assert not output.exists() and not output.with_name('.'+output.name+'.incomplete').exists()


def test_real_request_guard_remains_per_call(execution,monkeypatch):
    from xiangrugu_datamgmt import task_control
    original=task_control.read_request;reads=[];mounts=[]
    def read(path):
        if path==execution['path']:reads.append(path)
        return original(path)
    monkeypatch.setattr(task_control,'read_request',read)
    monkeypatch.setattr(task_control,'_require_readonly_mount',mounts.append)
    def worker(request,*,cancelled,**kw):
        before=len(reads)
        before_mounts=len(mounts)
        for _ in range(5):assert cancelled() is False
        assert len(reads)-before==5
        assert len(mounts)-before_mounts==5
        return Path(request['output'])
    monkeypatch.setattr(task_control,'execute_readonly_batch',worker)
    task_control.execute_controlled_batch(**execution['args'])


@pytest.mark.parametrize('replace',[False,True])
def test_project_supervisor_rechecks_raw_request_at_publication(tmp_path,monkeypatch,replace):
    import sys
    from test_candidate_supervisor import lease
    from xiangrugu_datamgmt import candidate_supervisor
    request=tmp_path/'request.json';request.write_text('{}');request_pin=pin(request)['sha256']
    final=tmp_path/'batch.json';final.with_name('.batch.json.incomplete').write_text(json.dumps(dict(
        complete=True,synthetic_only=False,source_mode='project_snapshot',execution_kind='approved-readonly-batch-v1',
        ready_for_import=False,postgresql_connected=False,controller_request_sha256=request_pin)))
    lease_path=tmp_path/'lease';lease(lease_path)
    renewed=False
    def controller():
        nonlocal renewed
        if (tmp_path/'final-sample-request.json').exists() and not renewed:
            lease(lease_path,2);renewed=True
            if replace:request.write_text('{"changed":true}')
        return False
    monkeypatch.setattr(candidate_supervisor,'_require_readonly_mount',lambda path:None)
    result=candidate_supervisor.supervise([sys.executable,'-c','pass'],lease=lease_path,evidence=tmp_path/'monitor.json',
        final=final,authorized_source_mode='project_snapshot',expected_request_sha256=request_pin,
        controller_request_file=request,controller_request_sha256=request_pin,require_final_sample=True,
        lease_seconds=1,poll_seconds=.02,cancelled=controller)
    assert final.exists() is not replace
    assert result['final_sample_after_sequence']==1 and result['final_sample_sequence']==2
    if replace:assert result['status']=='SOURCE_ONLY_WORKER_STOPPED'


@pytest.mark.parametrize('group',['small','medium'])
def test_project_small_medium_do_not_enter_partition_validator(execution,monkeypatch,group):
    from xiangrugu_datamgmt import task_control,project_partition
    request=execution['request'];path=Path(request['budget_file']);budget=json.loads(path.read_text());budget['group']=group
    request['budget_sha256']=save(path,budget)['sha256'];save(execution['path'],request)
    execution['args']['expected_request_sha256']=pin(execution['path'])['sha256']
    monkeypatch.setattr(project_partition,'validate_project_partition_request',lambda **kw:pytest.fail('partition validator'))
    monkeypatch.setattr(task_control,'execute_readonly_batch',lambda *a,**kw:Path(request['output']))
    task_control.execute_controlled_batch(**execution['args'])


def test_metadata_changed_at_task_staged_boundary_stops(execution):
    from xiangrugu_datamgmt import task_control
    def progress(stage,**details):
        if stage=='task_staged':Path(execution['data']['selection']['files']['parent_review']['path']).write_text('{}')
    with pytest.raises(ValueError):task_control.execute_controlled_batch(**execution['args'],progress=progress)
    assert not Path(execution['request']['output']).exists()


@pytest.mark.parametrize('fault',['artificial_descriptor','validation_token'])
def test_artificial_binding_cannot_authorize_project_large(execution,fault):
    from xiangrugu_datamgmt import readonly_batch
    request=execution['request'];evidence=execution['evidence']
    if fault=='artificial_descriptor':
        path=Path(request['bindings']['descriptor']['path']);path.write_text('{"version":1,"artificial_only":true}')
    else:evidence=dict(evidence,validated=True)
    with pytest.raises(ValueError):readonly_batch.execute_readonly_batch(request,controller_evidence=evidence)
    assert execution['calls']==[]
