"""Explicit project-shaped receipts; offline validation never reads source."""
import copy
import hashlib
import importlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from test_project_partition import large,metadata,project_data,pin,save,review,api
from xiangrugu_datamgmt.unordered_values import UnorderedSchema,UnorderedColumn,schema_bytes


@pytest.fixture
def project_receipts(project_data,request):
    from xiangrugu_datamgmt.task_partition import prepare_partition_task
    data=project_data;entries=[];mixed_image=getattr(request,'param',False)
    for i in range(10):
        part=f'large-p{i+1:02d}';base=data['base']/part;base.mkdir()
        part_image=dict(data['image'],source_status='clean') if mixed_image and i==9 else data['image']
        marker=prepare_partition_task(**dict(data['large']['call'],output_dir=base/'preparation',actual_image=part_image),partition_id=part)
        files=dict(data['selection']['files'])
        files.update({role:pin(marker.parent/name) for role,name in api().GENERATED.items()})
        files['preparation']=pin(marker)
        selection=dict(data['selection'],partition_id=part,attempt_id=f'owned-{i}',files=files)
        item=dict(data,base=base,selection=selection,selection_path=base/'selection.json',output=base/'review',image=part_image)
        reviewed=review(item)
        request_path=api().materialize_project_partition_request(review_file=reviewed,expected_review_sha256=pin(reviewed)['sha256'],
            actual_image=part_image,output_dir=base/'execution',result_file=data['evidence']/part/'batch.json',scratch_parent=data['evidence']/part/'scratch')
        request=json.loads(request_path.read_text());scope=json.loads(Path(request['scope_file']).read_text());obj=scope['objects'][0]
        expected=dict(source_object_id=obj['source_object_id'],source_object_name=obj['source_object_name'],
            schema_hash=hashlib.sha256(schema_bytes(UnorderedSchema(obj['source_object_id'],tuple(UnorderedColumn(**c) for c in obj['columns'])))).hexdigest(),
            expected_count=2,field_count=2*len(obj['columns']),expected_sha256=f'{i+1:064x}')
        from xiangrugu_datamgmt.readonly_batch import _group_limits
        read_cap,sort_cap=_group_limits(json.loads(Path(request['budget_file']).read_text())['objects'][0],'large')
        expected.update(read_limits=asdict(read_cap),sort_limits=asdict(sort_cap),stream_bytes=1000,
            sort_stats=dict(peak_temp_bytes=2000,peak_chunk_bytes=1000,peak_chunk_rows=2,peak_temp_files=1,elapsed_seconds=1.0))
        batch=dict(version=1,status='DRAFT_BATCH_SOURCE_EXPECTATIONS',execution_kind='approved-readonly-batch-v1',
            complete=True,synthetic_only=False,source_mode='project_snapshot',postgresql_connected=False,ready_for_import=False,
            contract_frozen=False,raw_values_emitted=False,group='large',file_digest_passes=2,full_snapshot_verified_this_run=True,
            source_sha256_before=request['expected_sha256'],source_sha256_after=request['expected_sha256'],
            objects=[dict(expected,cleanup_complete=True,source_read=dict(values_complete=True,rows_read=2,cells_read=expected['field_count'],value_bytes=100,postgresql_connected=False))],
            controller_request_sha256=pin(request_path)['sha256'],controller_lifecycle_seconds=1800,
            image_id=request['image_id'],git_revision=request['git_revision'],snapshot_id=request['snapshot_id'],rule_id=request['rule_id'],
            manifest_sha256=request['manifest_sha256'],bindings={k:v['sha256'] for k,v in request['bindings'].items()},controller_verified_image=part_image)
        for key in ('roots_sha256','certificate_sha256','scope_sha256','budget_sha256','approval_sha256'):batch[key]=request[key]
        files.update(descriptor=request['bindings']['descriptor'],request=pin(request_path))
        for role,key in [('approval','approval_file'),('scope','scope_file'),('budget','budget_file')]:files[role]=pin(Path(request[key]))
        monitor=dict(status='SOURCE_ONLY_WORKER_COMPLETED',reason=None,source_mode='project_snapshot',synthetic_only=False,
            max_seconds=1800,worker_exit_code=0,process_group_gone=True,ready_for_import=False,
            worker_failure=None,worker_failure_state='not_requested',worker_failure_sha256=None,
            cgroup_stats={'memory.swap.current':'0','memory.peak':'100000'},
            samples=[dict(sequence=n,elapsed_seconds=n,swap_out_pages=0,services_healthy=True,
                available_memory=4*2**30,disk_available=32*2**30,load_1min=0,io_some_avg10=0,memory_some_avg10=0) for n in (1,2)],
            final_sample_after_sequence=1,final_sample_sequence=2)
        limits={'cpu.max':'50000 100000','memory.max':'805306368','memory.swap.max':'0','worker_nice':19,'worker_ionice':'idle'}
        host=dict(NanoCpus=500000000,Memory=805306368,MemorySwap=805306368,NetworkMode='none',ReadonlyRootfs=True)
        for role,doc in [('batch',batch),('monitor',monitor),('limits',limits),('host_config',host),('container_state',dict(Running=False,ExitCode=0,OOMKilled=False))]:files[role]=save(base/(role+'.json'),doc)
        for role in ('container_id','removal'):
            path=base/(role+'.txt');path.write_text(f'{100+i:064x}\n');files[role]=pin(path)
        path=base/'pins.txt';path.write_text('\n'.join([files['request']['sha256'],files['approval']['sha256'],files['roots']['sha256']])+'\n')
        files['controller_pins']=pin(path)
        entries.append(dict(partition_id=part,attempt_id=f'owned-{i}',files=files))
    chosen=dict(version=1,status='SELECTED_PROJECT_PARTITION_EVIDENCE',source_mode='project_snapshot',
        parent_scope=entries[0]['files']['parent_scope'],parent_budget=entries[0]['files']['parent_budget'],entries=entries,comparison_attempts=[])
    return dict(base=data['base'],selection=chosen,path=data['base']/'coverage-selection.json',output=data['base']/'coverage')


def run(data,**kw):
    module=importlib.import_module('xiangrugu_datamgmt.project_partition_coverage')
    chosen=save(data['path'],data['selection'])
    return module.verify_project_partition_coverage(selection_file=data['path'],expected_selection_sha256=chosen['sha256'],output_dir=data['output'],**kw)


def change(data,role,key,value):
    desc=data['selection']['entries'][0]['files'][role];path=Path(desc['path']);doc=json.loads(path.read_text());doc[key]=value
    data['selection']['entries'][0]['files'][role]=save(path,doc)


def test_exact_ten_project_partitions_complete(project_receipts,monkeypatch):
    import sqlite3
    from xiangrugu_datamgmt import snapshots,readonly_batch
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**kw:pytest.fail('source'))
    monkeypatch.setattr(snapshots,'verify_snapshot',lambda *a,**kw:pytest.fail('snapshot'))
    monkeypatch.setattr(readonly_batch,'execute_readonly_batch',lambda *a,**kw:pytest.fail('execution'))
    result=json.loads(run(project_receipts).read_text())
    assert result['status']=='DRAFT_PROJECT_PARTITION_COVERAGE_COMPLETE' and result['complete']
    assert result['objects']==10 and result['columns']==235 and result['synthetic_only'] is False
    for key in ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import','postgresql_connected','task8_complete'):assert result[key] is False


def test_nine_project_partitions_incomplete(project_receipts):
    project_receipts['selection']['entries'].pop()
    path=run(project_receipts);result=json.loads(path.read_text())
    assert result['status']=='INCOMPLETE_PROJECT_PARTITION_COVERAGE' and not result['complete']
    assert result['missing_partitions']==['large-p10'] and not (path.parent/'coverage.json').exists()


@pytest.mark.parametrize('role,key,value',[
    ('batch','complete',False),('batch','synthetic_only',True),('batch','source_mode','artificial'),
    ('batch','source_sha256_after','f'*64),('batch','controller_request_sha256','f'*64),
    ('monitor','status','SOURCE_ONLY_WORKER_STOPPED'),('monitor','final_sample_sequence',None),
    ('monitor','reason','cancelled'),('container_state','OOMKilled',True),('host_config','MemorySwap',-1),
    ('descriptor','attempt_id','other-attempt'),('descriptor','artificial_only',True),('preparation','objects',True)])
def test_rehashed_bad_receipt_rejected(project_receipts,role,key,value):
    change(project_receipts,role,key,value)
    with pytest.raises(ValueError):run(project_receipts)


@pytest.mark.parametrize('field,value',[('expected_count',True),('expected_count',-1),('field_count',1),('schema_hash','f'*64)])
def test_result_count_and_schema_semantics(project_receipts,field,value):
    f=project_receipts['selection']['entries'][0]['files'];path=Path(f['batch']['path']);batch=json.loads(path.read_text())
    batch['objects'][0][field]=value;f['batch']=save(path,batch)
    with pytest.raises(ValueError):run(project_receipts)


@pytest.mark.parametrize('fault',['duplicate','extra','golden','pins','removal','comparison'])
def test_selection_and_raw_receipts_rejected(project_receipts,fault):
    chosen=project_receipts['selection'];f=chosen['entries'][0]['files']
    if fault=='duplicate':chosen['entries'][-1]=copy.deepcopy(chosen['entries'][0])
    elif fault=='extra':chosen['entries'][0]['files']['unknown']=f['roots']
    elif fault=='golden':chosen['golden']=f['batch']
    elif fault in ('pins','removal'):
        role='controller_pins' if fault=='pins' else 'removal';path=Path(f[role]['path']);path.write_text('f'*64+'\n');f[role]=pin(path)
    else:
        comparison=copy.deepcopy(chosen['entries'][0]);path=project_receipts['base']/'conflicting-batch.json'
        batch=json.loads(Path(f['batch']['path']).read_text());batch['objects'][0]['expected_sha256']='f'*64
        comparison['files']['batch']=save(path,batch);chosen['comparison_attempts']=[comparison]
    with pytest.raises(ValueError):run(project_receipts)


def test_same_success_comparison_accepted(project_receipts):
    project_receipts['selection']['comparison_attempts']=[copy.deepcopy(project_receipts['selection']['entries'][0])]
    assert json.loads(run(project_receipts).read_text())['complete']


@pytest.mark.parametrize('field,value',[
    ('read_limits',None),('sort_limits',None),('stream_bytes',None),('sort_stats',None),
    ('source_read.value_bytes',None),('sort_stats.peak_temp_bytes',None),('sort_stats.elapsed_seconds',None),
    ('read_limits.max_value_bytes',2**30),('sort_limits.max_stream_bytes',2**30),
    ('stream_bytes',2**28+1),('stream_bytes',True),('stream_bytes',1.0),('stream_bytes',-1),
    ('source_read.value_bytes',2**28+1),('source_read.value_bytes',True),
    ('sort_stats.peak_temp_bytes',2**30+1),('sort_stats.peak_chunk_bytes',2**21+1),
    ('sort_stats.peak_chunk_rows',4097),('sort_stats.peak_temp_files',1025),
    ('sort_stats.peak_temp_files',True),('sort_stats.elapsed_seconds',1801),
    ('sort_stats.elapsed_seconds',-1),('sort_stats.elapsed_seconds',True)])
def test_rehashed_application_resource_receipt_rejected(project_receipts,field,value):
    files=project_receipts['selection']['entries'][0]['files'];path=Path(files['batch']['path'])
    batch=json.loads(path.read_text());target=batch['objects'][0];keys=field.split('.')
    for key in keys[:-1]:target=target[key]
    if value is None:del target[keys[-1]]
    else:target[keys[-1]]=value
    files['batch']=save(path,batch)
    with pytest.raises(ValueError):run(project_receipts)


@pytest.mark.parametrize('final_swap',[500,501,499])
def test_host_swap_is_run_relative(project_receipts,final_swap):
    for entry in project_receipts['selection']['entries']:
        files=entry['files'];path=Path(files['monitor']['path']);monitor=json.loads(path.read_text())
        monitor['samples'][0]['swap_out_pages']=500;monitor['samples'][1]['swap_out_pages']=final_swap
        files['monitor']=save(path,monitor)
    if final_swap==500:assert json.loads(run(project_receipts).read_text())['complete']
    else:
        with pytest.raises(ValueError):run(project_receipts)


@pytest.mark.parametrize('project_receipts',[True],indirect=True)
def test_rehashed_mixed_actual_image_identity_rejected(project_receipts):
    with pytest.raises(ValueError):run(project_receipts)


@pytest.mark.parametrize('fault',['input','stage','cancel','symlink','exists'])
def test_offline_publication_failures_preserve_no_final(project_receipts,monkeypatch,fault):
    module=importlib.import_module('xiangrugu_datamgmt.project_partition_coverage');data=project_receipts
    if fault in ('input','stage'):
        original=module.write_json_exclusive
        def write(path,doc):
            original(path,doc)
            if path.name=='.coverage.json.incomplete':
                target=Path(data['selection']['entries'][0]['files']['parent_review']['path']) if fault=='input' else path
                target.write_text('{}')
        monkeypatch.setattr(module,'write_json_exclusive',write)
    if fault=='symlink':
        target=data['base']/'target';target.mkdir();data['output'].symlink_to(target,target_is_directory=True)
    if fault=='exists':data['output'].mkdir()
    with pytest.raises((ValueError,FileExistsError)):run(data,**({'cancelled':lambda:True} if fault=='cancel' else {}))
    assert not (data['output']/'coverage.json').exists()
