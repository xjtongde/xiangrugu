"""Offline pinned project partition receipts; no source or database reads."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal

from .batch_execution import _json,_check_cancel,read_metadata
from .config import load_config
from .project_partition import (FLAGS,GENERATED,_read,_load,require,same,checked,
    validate_project_partition_request,recheck_project_partition_metadata)
from .readonly_batch import _path,_hash,_group_limits
from .resource_watch import ResourceWatch
from .snapshots import canonical_json,write_json_exclusive
from .unordered_values import UnorderedColumn,UnorderedSchema,schema_bytes


PROJECT_ROLES={'preparation','parent_review','parent_scope','parent_budget','partition_selection',
    'draft_scope','draft_budget','draft_request','descriptor','request','approval','roots','certificate',
    'scope','budget','batch','monitor','limits','host_config','container_state','container_id','removal','controller_pins'}


def _resources(docs):
    monitor,limits,host,state=(docs[k] for k in ('monitor','limits','host_config','container_state'))
    require(monitor.get('status')=='SOURCE_ONLY_WORKER_COMPLETED' and monitor.get('source_mode')=='project_snapshot'
        and monitor.get('synthetic_only') is False and monitor.get('ready_for_import') is False
        and monitor.get('reason') is None and type(monitor.get('worker_exit_code')) is int
        and monitor['worker_exit_code']==0 and monitor.get('process_group_gone') is True
        and monitor.get('worker_failure') is None and monitor.get('worker_failure_sha256') is None
        and monitor.get('worker_failure_state') in ('not_requested','missing')
        and type(monitor.get('max_seconds')) is int and monitor['max_seconds']==1800)
    stats=monitor['cgroup_stats']
    require(stats.get('memory.swap.current')=='0' and type(stats.get('memory.peak')) is str
        and re.fullmatch(r'[0-9]+',stats['memory.peak']) and 0<=int(stats['memory.peak'])<=805306368)
    for key,value in {'cpu.max':'50000 100000','memory.max':'805306368','memory.swap.max':'0','worker_nice':19,'worker_ionice':'idle'}.items():
        require(same(limits.get(key),value))
    for key,value in dict(NanoCpus=500000000,Memory=805306368,MemorySwap=805306368,NetworkMode='none',ReadonlyRootfs=True).items():
        require(same(host.get(key),value))
    require(state.get('Running') is False and state.get('OOMKilled') is False
        and type(state.get('ExitCode')) is int and state['ExitCode']==0)
    samples=monitor['samples'];require(type(samples) is list and len(samples)>=2)
    after,terminal=monitor.get('final_sample_after_sequence'),monitor.get('final_sample_sequence')
    require(type(after) is int and type(terminal) is int and 0<after<terminal)
    watch=ResourceWatch();previous_sequence=0;previous_time=0
    sequences=[]
    for i,sample in enumerate(samples):
        sequence=sample['sequence'];elapsed=sample['elapsed_seconds']
        require(type(sequence) is int and sequence>previous_sequence
            and type(elapsed) in (int,float) and math.isfinite(elapsed)
            and previous_time<=elapsed<=1800 and elapsed-previous_time<25
            and type(sample.get('swap_out_pages')) is int
            and sample['swap_out_pages']==samples[0]['swap_out_pages'])
        require((watch.preflight(sample) if i==0 else watch.observe(sample)) is None)
        previous_sequence,previous_time=sequence,elapsed;sequences.append(sequence)
    require(after in sequences and terminal==sequences[-1])


@checked
def verify_project_partition_coverage(*,selection_file,expected_selection_sha256,output_dir,cancelled=lambda:False):
    inputs={}
    def load(description):return _load(description,inputs,cancelled)
    def raw(description):return _read(description,inputs,cancelled)
    chosen=load(dict(path=str(selection_file),sha256=expected_selection_sha256))
    require(chosen.keys()=={'version','status','source_mode','parent_scope','parent_budget','entries','comparison_attempts'}
        and type(chosen['version']) is int and chosen['version']==1
        and chosen['status']=='SELECTED_PROJECT_PARTITION_EVIDENCE' and chosen['source_mode']=='project_snapshot'
        and type(chosen['entries']) is list and 1<=len(chosen['entries'])<=10
        and type(chosen['comparison_attempts']) is list and len(chosen['comparison_attempts'])<=10)
    parent=load(chosen['parent_scope']);budget=load(chosen['parent_budget'])
    require(type(parent.get('objects')) is list and len(parent['objects'])==10
        and sum(len(o['columns']) for o in parent['objects'])==235)
    cohort=None;business_roots=set()
    def attempt(entry):
        nonlocal cohort
        require(type(entry) is dict and entry.keys()=={'partition_id','attempt_id','files'}
            and type(entry['files']) is dict and entry['files'].keys()==PROJECT_ROLES
            and type(entry['partition_id']) is str and re.fullmatch(r'large-p(?:0[1-9]|10)',entry['partition_id'])
            and type(entry['attempt_id']) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',entry['attempt_id']))
        f=entry['files'];require(len({d['path'] for d in f.values()})==len(PROJECT_ROLES))
        docs={role:load(desc) for role,desc in f.items() if role not in ('roots','container_id','removal','controller_pins')}
        raw(f['roots'])
        config=load_config(Path(f['roots']['path']),environ={})
        business_roots.update((config.source.path,config.snapshot_root))
        for role in ('parent_scope','parent_budget'):
            require(f[role]['sha256']==chosen[role]['sha256'])
        request,batch=docs['request'],docs['batch']
        pins=raw(f['controller_pins']).decode('ascii').splitlines()
        require(pins==[f[role]['sha256'] for role in ('request','approval','roots')])
        cid=raw(f['container_id']).decode('ascii').strip();removed=raw(f['removal']).decode('ascii').strip()
        require(_hash(cid) and removed==cid)
        evidence={key:batch.get(key) for key in ('controller_request_sha256','controller_verified_image','controller_lifecycle_seconds')}
        require(evidence['controller_request_sha256']==pins[0])
        metadata=validate_project_partition_request(request=request,controller_evidence=evidence,cancelled=cancelled)
        require(metadata.partition_id==entry['partition_id'] and metadata.attempt_id==entry['attempt_id']
            and same(metadata.parent_scope,parent) and same(metadata.parent_budget,budget))
        for path,value in metadata.input_bytes.items():
            if path in inputs:require(inputs[path]==value)
            inputs[path]=value
        descriptor=docs['descriptor']
        require(same(descriptor['preparation'],f['preparation']) and same(descriptor['parent_review'],f['parent_review']))
        for role,description in request['bindings'].items():require(same(description,f[role]))
        for role,name in GENERATED.items():
            require(f[role]['path']==str(Path(f['preparation']['path']).parent/name)
                and f[role]['sha256']==docs['preparation']['generated'][name])
        for role,key in (('roots','roots'),('certificate','certificate'),('scope','scope_file'),('budget','budget_file'),('approval','approval_file')):
            pin_key={'scope_file':'scope_sha256','budget_file':'budget_sha256','approval_file':'approval_sha256'}.get(key,key+'_sha256')
            require(request[key]==f[role]['path'] and request[pin_key]==f[role]['sha256'] and batch.get(pin_key)==request[pin_key])
        require(batch.get('status')=='DRAFT_BATCH_SOURCE_EXPECTATIONS' and type(batch.get('version')) is int and batch['version']==1
            and batch.get('execution_kind')=='approved-readonly-batch-v1' and batch.get('group')=='large'
            and batch.get('complete') is True and batch.get('synthetic_only') is False and batch.get('source_mode')=='project_snapshot'
            and batch.get('postgresql_connected') is False and batch.get('ready_for_import') is False
            and batch.get('contract_frozen') is False and batch.get('raw_values_emitted') is False
            and type(batch.get('file_digest_passes')) is int and batch['file_digest_passes']==2
            and batch.get('full_snapshot_verified_this_run') is True
            and batch.get('source_sha256_before')==request['expected_sha256']==batch.get('source_sha256_after')
            and batch.get('manifest_sha256')==request['manifest_sha256']
            and same(batch.get('bindings'),{k:v['sha256'] for k,v in request['bindings'].items()}))
        for key in ('image_id','git_revision'):require(batch.get(key)==request[key])
        identity={k:request[k] for k in ('image_id','git_revision','snapshot_id','relative_path','expected_size',
            'expected_sha256','roots_sha256','certificate_sha256','manifest_sha256','rule_id')}
        identity['parent_review_sha256']=f['parent_review']['sha256']
        identity['actual_image']=batch['controller_verified_image']
        if cohort is None:cohort=identity
        require(same(identity,cohort))
        index=int(entry['partition_id'][-2:])-1;obj=parent['objects'][index];cap=budget['objects'][index]
        require(type(batch.get('objects')) is list and len(batch['objects'])==1)
        result=batch['objects'][0];require(type(result) is dict)
        schema=hashlib.sha256(schema_bytes(UnorderedSchema(obj['source_object_id'],tuple(UnorderedColumn(**c) for c in obj['columns'])))).hexdigest()
        count,fields=result.get('expected_count'),result.get('field_count')
        read,sort=_group_limits(cap,'large')
        require(result.get('source_object_id')==obj['source_object_id'] and result.get('source_object_name')==obj['source_object_name']
            and result.get('schema_hash')==schema and _hash(result.get('expected_sha256'))
            and type(count) is int and 0<=count<=min(read.max_rows,sort.max_rows)
            and type(fields) is int and fields==count*len(obj['columns']) and fields<=read.max_cells
            and result.get('cleanup_complete') is True)
        source=result['source_read']
        require(source.get('values_complete') is True and source.get('postgresql_connected') is False
            and same(source.get('rows_read'),count) and same(source.get('cells_read'),fields))
        require(same(result.get('read_limits'),asdict(read)) and same(result.get('sort_limits'),asdict(sort))
            and len(obj['columns'])<=min(read.max_columns,sort.max_columns))
        for value,ceiling in ((result.get('stream_bytes'),sort.max_stream_bytes),
                (source.get('value_bytes'),read.max_value_bytes)):
            require(type(value) is int and 0<=value<=ceiling)
        stats=result.get('sort_stats')
        require(type(stats) is dict and stats.keys()=={'peak_temp_bytes','peak_chunk_bytes',
            'peak_chunk_rows','peak_temp_files','elapsed_seconds'})
        for key,ceiling in dict(peak_temp_bytes=sort.max_temp_bytes,peak_chunk_bytes=sort.chunk_bytes,
                peak_chunk_rows=sort.chunk_rows,peak_temp_files=sort.max_temp_files).items():
            require(type(stats[key]) is int and 0<=stats[key]<=ceiling)
        elapsed=stats['elapsed_seconds']
        require(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<=elapsed<=sort.max_seconds)
        _resources(docs);recheck_project_partition_metadata(metadata,cancelled=cancelled)
        return {k:result[k] for k in ('source_object_id','source_object_name','schema_hash','expected_count','field_count','expected_sha256')}
    selected={}
    for entry in chosen['entries']:
        _check_cancel(cancelled);require(type(entry) is dict and entry.get('partition_id') not in selected)
        selected[entry['partition_id']]=attempt(entry)
    for entry in chosen['comparison_attempts']:
        result=attempt(entry);require(entry['partition_id'] in selected and same(result,selected[entry['partition_id']]))
    missing=[f'large-p{i+1:02d}' for i in range(10) if f'large-p{i+1:02d}' not in selected]
    out=Path(output_dir);require(not any(out==p or p in out.parents for p in business_roots))
    out=_path(str(out));require(out.parent.is_dir() and not any(out==p or out in p.parents for p in inputs))
    out.mkdir();name='coverage.incomplete.json' if missing else 'coverage.json'
    record=dict(version=1,status='INCOMPLETE_PROJECT_PARTITION_COVERAGE' if missing else 'DRAFT_PROJECT_PARTITION_COVERAGE_COMPLETE',
        complete=not missing,synthetic_only=False,source_mode='project_snapshot',**{key:False for key in FLAGS},
        postgresql_connected=False,task8_complete=False,objects=len(selected),
        columns=sum(len(parent['objects'][int(k[-2:])-1]['columns']) for k in selected),verified_partitions=list(selected),
        missing_partitions=missing,source_identity=cohort,selection_sha256=expected_selection_sha256,objects_evidence=list(selected.values()))
    stage=out/('.'+name+'.incomplete');write_json_exclusive(stage,record)
    for path,value in inputs.items():
        _check_cancel(cancelled);require(read_metadata(path)==value)
    require(read_metadata(stage)==(canonical_json(record)+'\n').encode('utf-8'))
    _check_cancel(cancelled);os.link(stage,out/name)
    return out/name


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True);parser.add_argument('--selection-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args();stopped=False
    def stop(*unused):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        marker=verify_project_partition_coverage(selection_file=args.selection,expected_selection_sha256=args.selection_sha256,
            output_dir=args.output_dir,cancelled=lambda:stopped)
        print(json.dumps(dict(status='PROJECT_OFFLINE_COVERAGE_VERIFIED',marker=str(marker),ready_for_import=False)));return 0
    except Exception:
        print(json.dumps(dict(status='PROJECT_OFFLINE_COVERAGE_REJECTED',ready_for_import=False)));return 1


if __name__=='__main__':raise SystemExit(main())
