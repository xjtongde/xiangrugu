"""Artificial pinned receipts; offline coverage must never touch source bytes."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from test_task_partition import large, metadata
from xiangrugu_datamgmt.snapshots import digest
from xiangrugu_datamgmt.unordered_values import UnorderedSchema, UnorderedColumn, schema_bytes


def save(path, doc):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc))
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())


@pytest.fixture
def receipts(large):
    from xiangrugu_datamgmt.task_partition import prepare_partition_task
    base=large['repo'].parent/'receipts';base.mkdir()
    roots_source=large['repo']/'datamgmt/config/roots.yaml'
    config=yaml.safe_load(roots_source.read_text())
    config['roots']['usedata']['path']=str(large['repo'].parent/'authority-never-read')
    roots_source.write_text(yaml.safe_dump(config))
    root_pin=hashlib.sha256(roots_source.read_bytes()).hexdigest()
    large['packet']['bindings']['roots']['sha256']=root_pin;large['call']['expected_roots_sha256']=root_pin
    from test_task_preparation import renew
    renew(large)
    parts=[];gold=[]
    descriptor=save(base/'descriptor.json',dict(version=1,artificial_only=True,fixture='fixed-ten-single-table-v1'))
    for i in range(10):
        args=dict(large['call'],output_dir=large['call']['output_dir'].with_name(f'part-{i}'))
        marker=prepare_partition_task(**args,partition_id=f'large-p{i+1:02d}')
        parent=json.loads((marker.parent/'parent.scope.draft.json').read_text())
        ds=json.loads((marker.parent/'scope.draft.json').read_text())
        db=json.loads((marker.parent/'budget.draft.json').read_text())
        obj=ds['objects'][0];schema_hash=hashlib.sha256(schema_bytes(UnorderedSchema(obj['source_object_id'],tuple(UnorderedColumn(**c) for c in obj['columns'])))).hexdigest()
        expected=dict(source_object_id=obj['source_object_id'],source_object_name=obj['source_object_name'],schema_hash=schema_hash,expected_count=2,field_count=2*len(obj['columns']),expected_sha256=f'{i+1:064x}')
        gold.append(expected)
        root=base/f'attempt-{i}';root.mkdir()
        def pin(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        binding={role:pin(marker.parent/name) for role,name in [('parent_scope','parent.scope.draft.json'),('parent_budget','parent.budget.draft.json'),('partition_selection','partition.selection.draft.json')]}
        binding['descriptor']=descriptor
        scope={k:v for k,v in ds.items() if k not in ('status','contract_frozen')};scope.update(synthetic_data_authorized=True,bindings={k:v['sha256'] for k,v in binding.items()})
        roots=dict(roots=dict(usedata=dict(host='synthetic',path='/fake/authority-never-read')),deployment=dict(source_snapshots=dict(container_root='/fake/snapshots',container_evidence_root='/fake/evidence')))
        roots_path=root/'roots.yaml';roots_path.write_bytes(roots_source.read_bytes())
        cert=dict(version=1,status='VERIFIED',snapshot_id=parent['snapshot_id'],source_path=config['roots']['usedata']['path'],members=[parent['source']],manifest_sha256=digest([parent['source']]))
        files={role:save(root/f'{role}.json',value) for role,value in [('scope',scope),('budget',db),('certificate',cert)]}
        files['roots']=pin(roots_path)
        request=dict(source_mode='artificial',snapshot_id=parent['snapshot_id'],relative_path=parent['source']['path'],expected_sha256=parent['source']['sha256'],expected_size=parent['source']['size'],rule_id=parent['rule_id'],image_id=args['expected_image_id'],git_revision=args['actual_image']['git_revision'],lifecycle_seconds=1800,manifest_sha256=cert['manifest_sha256'],bindings=binding,output=f'/fake/run-{i}/batch.json',scratch_parent=f'/fake/run-{i}/disk-scratch')
        for role,key in [('roots','roots'),('certificate','certificate'),('scope','scope_file'),('budget','budget_file')]:
            request[key]=files[role]['path'];request[{'scope_file':'scope_sha256','budget_file':'budget_sha256'}.get(key,key+'_sha256')]=files[role]['sha256']
        approval=dict(version=1,status='APPROVED_READONLY_BATCH',source_mode='artificial',source_read_authorized=False,synthetic_data_authorized=True,stationary_readonly_window=True,postgresql_authorized=False,ready_for_import=False,request_sha256=digest(request))
        files['approval']=save(root/'approval.json',approval)
        request.update(approval_file=files['approval']['path'],approval_sha256=files['approval']['sha256'])
        files['request']=save(root/'request.json',request)
        batch=dict(version=1,status='DRAFT_BATCH_SOURCE_EXPECTATIONS',complete=True,synthetic_only=True,source_mode='artificial',postgresql_connected=False,ready_for_import=False,contract_frozen=False,file_digest_passes=2,full_snapshot_verified_this_run=True,source_sha256_before=request['expected_sha256'],source_sha256_after=request['expected_sha256'],objects=[dict(expected,cleanup_complete=True,source_read=dict(values_complete=True,rows_read=2,cells_read=expected['field_count'],postgresql_connected=False))],controller_request_sha256=files['request']['sha256'],controller_lifecycle_seconds=1800,image_id=request['image_id'],git_revision=request['git_revision'],snapshot_id=parent['snapshot_id'],rule_id=parent['rule_id'],manifest_sha256=cert['manifest_sha256'],bindings={k:v['sha256'] for k,v in binding.items()},controller_verified_image=dict(args['actual_image']))
        for key in ('roots_sha256','certificate_sha256','scope_sha256','budget_sha256','approval_sha256'):batch[key]=request[key]
        monitor=dict(status='SYNTHETIC_WORKER_COMPLETED',reason=None,source_mode='artificial',synthetic_only=True,worker_exit_code=0,process_group_gone=True,cgroup_stats={'memory.swap.current':'0','memory.peak':'100000'},samples=[dict(swap_out_pages=0,services_healthy=True)])
        limits={'cpu.max':'50000 100000','memory.max':'805306368','memory.swap.max':'0','worker_nice':19,'worker_ionice':'idle'}
        host=dict(NanoCpus=500000000,Memory=805306368,MemorySwap=805306368,NetworkMode='none',ReadonlyRootfs=True)
        state=dict(Running=False,ExitCode=0,OOMKilled=False)
        for role,value in [('batch',batch),('monitor',monitor),('limits',limits),('host_config',host),('container_state',state)]:files[role]=save(root/f'{role}.json',value)
        for role in ('container_id','removal'):
            p=root/f'{role}.txt';p.write_text(f'{i+100:064x}\n');files[role]=pin(p)
        files.update(preparation=pin(marker),partition_selection=pin(marker.parent/'partition.selection.draft.json'),draft_scope=pin(marker.parent/'scope.draft.json'),draft_budget=pin(marker.parent/'budget.draft.json'),draft_request=pin(marker.parent/'request.draft.json'),parent_scope=pin(marker.parent/'parent.scope.draft.json'),parent_budget=pin(marker.parent/'parent.budget.draft.json'),descriptor=descriptor)
        parts.append(dict(partition_id=f'large-p{i+1:02d}',attempt_id=f'artificial-{i}',files=files))
    selection=dict(version=1,status='SELECTED_ARTIFICIAL_PARTITION_EVIDENCE',source_mode='artificial',parent_scope=pin(marker.parent/'parent.scope.draft.json'),parent_budget=pin(marker.parent/'parent.budget.draft.json'),golden=save(base/'golden.json',dict(synthetic_only=True,real_source_read=False,objects=gold)),entries=parts,comparison_attempts=[])
    return dict(base=base,selection=selection,path=base/'selection.json',output=base/'coverage')


def run(data,**kwargs):
    from xiangrugu_datamgmt.partition_coverage import verify_partition_coverage
    chosen=save(data['path'],data['selection'])
    return verify_partition_coverage(selection_file=data['path'],expected_selection_sha256=chosen['sha256'],output_dir=data['output'],**kwargs)


def change(data,role,key,value,index=0):
    desc=data['selection']['entries'][index]['files'][role]
    doc=json.loads(Path(desc['path']).read_text());doc[key]=value
    data['selection']['entries'][index]['files'][role]=save(data['base']/f'changed-{role}-{index}.json',doc)


def test_exact_ten_and_no_source_access(receipts,monkeypatch):
    import sqlite3
    from xiangrugu_datamgmt import snapshots,readonly_batch
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('source opened'))
    monkeypatch.setattr(snapshots,'verify_snapshot',lambda *a,**k:pytest.fail('snapshot opened'))
    monkeypatch.setattr(readonly_batch,'execute_readonly_batch',lambda *a,**k:pytest.fail('execution'))
    result=json.loads(run(receipts).read_text())
    assert result['complete'] is True and result['objects']==10 and result['columns']==235
    assert result['source_mode']=='artificial' and result['synthetic_only'] is True
    for key in ('source_read_authorized','postgresql_authorized','ready_for_import','contract_frozen','task8_complete','postgresql_connected'):assert result[key] is False


def test_missing_partition_diagnostic(receipts):
    receipts['selection']['entries'].pop()
    marker=run(receipts);doc=json.loads(marker.read_text())
    assert marker.name=='coverage.incomplete.json' and doc['complete'] is False and doc['missing_partitions']==['large-p10']
    assert not (marker.parent/'coverage.json').exists()


@pytest.mark.parametrize('fault',['duplicate','unknown','real','extra','bool_version'])
def test_selection_rejected(receipts,fault):
    s=receipts['selection']
    if fault=='duplicate':s['entries'][-1]=s['entries'][0]
    if fault=='unknown':s['entries'][0]['partition_id']='large-p11'
    if fault=='real':s['source_mode']='project_snapshot'
    if fault=='extra':s['entries'].append(s['entries'][0])
    if fault=='bool_version':s['version']=True
    with pytest.raises(ValueError):run(receipts)


@pytest.mark.parametrize('role,key,value',[
    ('batch','complete',False),('batch','file_digest_passes',True),('batch','full_snapshot_verified_this_run',False),
    ('batch','source_sha256_after','0'*64),('batch','image_id','sha256:'+'0'*64),
    ('batch','controller_request_sha256','0'*64),('batch','source_mode','project_snapshot'),
    ('batch','roots_sha256','0'*64),('batch','certificate_sha256','0'*64),('batch','manifest_sha256','0'*64),
    ('monitor','reason','cancelled'),('monitor','worker_exit_code',1),('monitor','process_group_gone',False),
    ('monitor','samples',[]),('container_state','OOMKilled',True),('container_state','Running',True),
    ('limits','memory.swap.max','1'),('host_config','Memory',999),('host_config','NetworkMode','host')])
def test_failed_or_mixed_receipt_rejected(receipts,role,key,value):
    change(receipts,role,key,value)
    with pytest.raises(ValueError):run(receipts)


@pytest.mark.parametrize('fault',['id','schema','count','digest','cleanup'])
def test_object_semantics(receipts,fault):
    d=receipts['selection']['entries'][0]['files']['batch'];b=json.loads(Path(d['path']).read_text());obj=b['objects'][0]
    key,value={'id':('source_object_id','0'*64),'schema':('schema_hash','0'*64),'count':('expected_count',True),'digest':('expected_sha256','0'*64),'cleanup':('cleanup_complete',False)}[fault]
    obj[key]=value
    receipts['selection']['entries'][0]['files']['batch']=save(receipts['base']/'object-fault.json',b)
    with pytest.raises(ValueError):run(receipts)


def test_missing_monitor(receipts):
    del receipts['selection']['entries'][0]['files']['monitor']
    with pytest.raises(ValueError):run(receipts)


def test_removal_id_mismatch(receipts):
    d=receipts['selection']['entries'][0]['files']['removal'];Path(d['path']).write_text('0'*64)
    d['sha256']=hashlib.sha256(Path(d['path']).read_bytes()).hexdigest()
    with pytest.raises(ValueError):run(receipts)


def test_existing_output_no_clobber(receipts):
    receipts['output'].mkdir();p=receipts['output']/'keep';p.write_text('keep')
    with pytest.raises(FileExistsError):run(receipts)
    assert p.read_text()=='keep'


def test_cancelled_before_publish(receipts):
    with pytest.raises(ValueError,match='cancelled'):run(receipts,cancelled=lambda:True)
    assert not (receipts['output']/'coverage.json').exists()


@pytest.mark.parametrize('target',['input','stage'])
def test_final_change_no_complete(receipts,monkeypatch,target):
    from xiangrugu_datamgmt import partition_coverage
    original=partition_coverage.write_json_exclusive
    def write(path,value):
        original(path,value)
        if path.name.startswith('.'):
            p=receipts['path'] if target=='input' else path
            p.write_text('{}')
    monkeypatch.setattr(partition_coverage,'write_json_exclusive',write)
    with pytest.raises(ValueError):run(receipts)
    assert not (receipts['output']/'coverage.json').exists()


def test_provided_conflicting_attempt_rejected(receipts):
    comparison=copy.deepcopy(receipts['selection']['entries'][0]);comparison['attempt_id']='other'
    desc=comparison['files']['batch'];batch=json.loads(Path(desc['path']).read_text())
    batch['objects'][0]['expected_sha256']='f'*64
    comparison['files']['batch']=save(receipts['base']/'conflict.json',batch)
    receipts['selection']['comparison_attempts']=[comparison]
    with pytest.raises(ValueError):run(receipts)


def test_same_success_comparison_is_allowed(receipts):
    comparison=copy.deepcopy(receipts['selection']['entries'][0]);comparison['attempt_id']='other'
    receipts['selection']['comparison_attempts']=[comparison]
    assert json.loads(run(receipts).read_text())['complete'] is True


def test_explicit_metadata_symlink_is_rejected(receipts):
    desc=receipts['selection']['golden'];link=receipts['base']/'alias.json';link.symlink_to(desc['path']);desc['path']=str(link)
    with pytest.raises(ValueError):run(receipts)


def test_metadata_role_alias_is_rejected(receipts):
    files=receipts['selection']['entries'][0]['files'];files['monitor']=files['batch']
    with pytest.raises(ValueError):run(receipts)


@pytest.mark.parametrize('key,value',[('snapshot_id','different'),('image_id','sha256:'+'0'*64),('lifecycle_seconds',1830)])
def test_repin_invalid_draft_request_still_rejected(receipts,key,value):
    f=receipts['selection']['entries'][0]['files']
    draft=json.loads(Path(f['draft_request']['path']).read_text());draft[key]=value
    f['draft_request']=save(Path(f['draft_request']['path']),draft)
    record=json.loads(Path(f['preparation']['path']).read_text());record['generated']['request.draft.json']=f['draft_request']['sha256']
    f['preparation']=save(Path(f['preparation']['path']),record)
    with pytest.raises(ValueError):run(receipts)


def test_extra_binding_requires_independent_original(receipts):
    del receipts['selection']['entries'][0]['files']['descriptor']
    with pytest.raises(ValueError):run(receipts)


@pytest.mark.parametrize('limit,value',[('max_temp_bytes',2**31),('max_stream_bytes',512*2**20)])
def test_repin_over_budget_still_rejected(receipts,limit,value):
    s=receipts['selection'];parent=json.loads(Path(s['parent_budget']['path']).read_text())
    parent['objects'][0]['sort_limits'][limit]=value
    s['parent_budget']=save(Path(s['parent_budget']['path']),parent)
    for index,entry in enumerate(s['entries']):
        f=entry['files'];selection=json.loads(Path(f['partition_selection']['path']).read_text())
        f['parent_budget']=save(Path(f['parent_budget']['path']),parent)
        selection['parent_budget_sha256']=s['parent_budget']['sha256'];f['partition_selection']=save(Path(f['partition_selection']['path']),selection)
        for role in ('draft_scope','draft_request','scope','request'):
            doc=json.loads(Path(f[role]['path']).read_text())
            if role in ('draft_scope','scope'):
                doc['bindings']['parent_budget']=s['parent_budget']['sha256'];doc['bindings']['partition_selection']=f['partition_selection']['sha256']
            else:
                doc['bindings']['parent_budget']['sha256']=s['parent_budget']['sha256'];doc['bindings']['partition_selection']['sha256']=f['partition_selection']['sha256']
            f[role]=save(Path(f[role]['path']),doc)
        for role in ('draft_budget','budget'):
            doc=json.loads(Path(f[role]['path']).read_text());doc['objects']=[parent['objects'][index]];f[role]=save(Path(f[role]['path']),doc)
        record=json.loads(Path(f['preparation']['path']).read_text());record['generated'].update({'parent.budget.draft.json':s['parent_budget']['sha256'],'partition.selection.draft.json':f['partition_selection']['sha256'],'scope.draft.json':f['draft_scope']['sha256'],'budget.draft.json':f['draft_budget']['sha256'],'request.draft.json':f['draft_request']['sha256']});f['preparation']=save(Path(f['preparation']['path']),record)
        req=json.loads(Path(f['request']['path']).read_text());req['scope_sha256']=f['scope']['sha256'];req['budget_sha256']=f['budget']['sha256']
        approval=json.loads(Path(f['approval']['path']).read_text());approval['request_sha256']=digest({k:v for k,v in req.items() if k not in ('approval_file','approval_sha256')});f['approval']=save(Path(f['approval']['path']),approval)
        req['approval_sha256']=f['approval']['sha256'];f['request']=save(Path(f['request']['path']),req)
        batch=json.loads(Path(f['batch']['path']).read_text());batch.update(scope_sha256=req['scope_sha256'],budget_sha256=req['budget_sha256'],approval_sha256=req['approval_sha256'],controller_request_sha256=f['request']['sha256']);batch['bindings']['parent_budget']=s['parent_budget']['sha256'];batch['bindings']['partition_selection']=f['partition_selection']['sha256'];f['batch']=save(Path(f['batch']['path']),batch)
    with pytest.raises(ValueError):run(receipts)
