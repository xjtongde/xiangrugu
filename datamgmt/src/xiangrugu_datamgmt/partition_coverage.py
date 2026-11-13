"""Offline artificial partition coverage; no source, snapshot or database I/O."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal

import yaml

from .batch_execution import read_metadata, _json
from .snapshots import canonical_json, digest, write_json_exclusive
from .unordered_values import UnorderedSchema, UnorderedColumn, schema_bytes
from .readonly_batch import _group_limits


ROLES = {'preparation','partition_selection','draft_scope','draft_budget','draft_request',
         'request','approval','roots','certificate','scope','budget','batch','monitor',
         'limits','host_config','container_state','container_id','removal',
         'parent_scope','parent_budget','descriptor'}


def require(condition):
    if not condition:
        raise ValueError('coverage_identity')


def hashed(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def same(left, right):
    return canonical_json(left) == canonical_json(right)


def safe_path(value):
    require(type(value) is str)
    path = Path(value)
    require(path.is_absolute() and str(path) == value and '..' not in path.parts
            and not any(p.is_symlink() for p in (path, *path.parents)))
    return path


def verify_partition_coverage(*, selection_file, expected_selection_sha256, output_dir,
                              cancelled=lambda: False):
    inputs = {}

    def check_cancel():
        if cancelled():
            raise ValueError('cancelled')

    def raw(description):
        check_cancel()
        require(type(description) is dict and description.keys() == {'path','sha256'}
                and hashed(description['sha256']))
        path = safe_path(description['path'])
        value = read_metadata(path)
        require(hashlib.sha256(value).hexdigest() == description['sha256'])
        if path in inputs:
            require(inputs[path] == value)
        inputs[path] = value
        return value

    def load(description):
        value = _json(raw(description))
        require(type(value) is dict)
        return value

    chosen = load(dict(path=str(selection_file),sha256=expected_selection_sha256))
    require(chosen.keys() == {'version','status','source_mode','parent_scope','parent_budget','golden','entries','comparison_attempts'}
            and type(chosen['version']) is int and chosen['version'] == 1
            and chosen['status'] == 'SELECTED_ARTIFICIAL_PARTITION_EVIDENCE'
            and chosen['source_mode'] == 'artificial'
            and type(chosen['entries']) is list and 1 <= len(chosen['entries']) <= 10
            and type(chosen['comparison_attempts']) is list and len(chosen['comparison_attempts']) <= 10)
    parent = load(chosen['parent_scope'])
    parent_budget = load(chosen['parent_budget'])
    golden = load(chosen['golden'])
    flags = ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import')
    require(all(parent.get(flag) is False for flag in flags)
            and parent_budget.get('group') == 'large' and parent_budget.get('max_seconds') == 1800
            and type(parent.get('objects')) is list and len(parent['objects']) == 10
            and type(parent_budget.get('objects')) is list and len(parent_budget['objects']) == 10
            and golden.get('synthetic_only') is True and golden.get('real_source_read') is False
            and type(golden.get('objects')) is list and len(golden['objects']) == 10)
    identities = [o['source_object_id'] for o in parent['objects']]
    require(len(set(identities)) == 10 and all(hashed(v) for v in identities)
            and len({o['source_object_name'] for o in parent['objects']}) == 10
            and sum(len(o['columns']) for o in parent['objects']) == 235)
    require({o['source_object_id'] for o in golden['objects']} == set(identities))
    require(type(parent_budget.get('max_seconds')) is int)
    for obj,cap in zip(parent['objects'],parent_budget['objects'],strict=True):
        require(cap.get('source_object_id') == obj['source_object_id'])
        read_limits,sort_limits=_group_limits(cap,'large')
        require(len(obj['columns']) <= min(read_limits.max_columns,sort_limits.max_columns))
    gold = {o['source_object_id']: o for o in golden['objects']}
    common = None

    def attempt(entry):
        nonlocal common
        require(type(entry) is dict and entry.keys() == {'partition_id','attempt_id','files'}
                and type(entry['partition_id']) is str and re.fullmatch(r'large-p(?:0[1-9]|10)',entry['partition_id'])
                and type(entry['attempt_id']) is str and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',entry['attempt_id'])
                and type(entry['files']) is dict and entry['files'].keys() == ROLES)
        f = entry['files']
        require(len({d['path'] for d in f.values()}) == len(ROLES))
        index = int(entry['partition_id'][-2:]) - 1
        obj, cap = parent['objects'][index], parent_budget['objects'][index]
        require(cap['source_object_id'] == obj['source_object_id'])
        docs = {role: load(desc) for role,desc in f.items() if role not in ('roots','container_id','removal')}
        require(f['parent_scope']['sha256'] == chosen['parent_scope']['sha256']
                and f['parent_budget']['sha256'] == chosen['parent_budget']['sha256']
                and docs['descriptor'].get('artificial_only') is True
                and docs['descriptor'].get('fixture') == 'fixed-ten-single-table-v1')
        roots = yaml.safe_load(raw(f['roots']))
        require(type(roots) is dict and roots['roots']['usedata']['host'] == 'synthetic'
                and type(roots['roots']['usedata']['path']) is str
                and Path(roots['roots']['usedata']['path']).name == 'authority-never-read')
        cid, removed = raw(f['container_id']).decode('ascii').strip(), raw(f['removal']).decode('ascii').strip()
        require(hashed(cid) and removed == cid)
        record, selection, request = docs['preparation'], docs['partition_selection'], docs['request']
        scope, budget, batch = docs['scope'], docs['budget'], docs['batch']
        require(record.get('status') == 'DRAFT_PARTITION_METADATA_PREPARATION'
                and all(record.get(flag) is False for flag in flags)
                and record.get('partition_id') == entry['partition_id'] and record.get('parent_objects') == 10
                and record.get('parent_columns') == 235 and record.get('objects') == 1
                and record.get('columns') == len(obj['columns']) and record.get('source_bytes_read') is False
                and record.get('source_expectations_generated') is False)
        generated = {'parent.scope.draft.json':chosen['parent_scope']['sha256'],
                     'parent.budget.draft.json':chosen['parent_budget']['sha256'],
                     'partition.selection.draft.json':f['partition_selection']['sha256'],
                     'scope.draft.json':f['draft_scope']['sha256'],
                     'budget.draft.json':f['draft_budget']['sha256'],
                     'request.draft.json':f['draft_request']['sha256']}
        require(same(record.get('generated'),generated)
                and selection.get('partition_id') == entry['partition_id']
                and selection.get('source_object_id') == obj['source_object_id']
                and selection.get('parent_review_sha256') == record.get('parent_review_sha256')
                and selection.get('parent_scope_sha256') == chosen['parent_scope']['sha256']
                and selection.get('parent_budget_sha256') == chosen['parent_budget']['sha256']
                and all(selection.get(flag) is False for flag in flags))
        for role in ('draft_scope','draft_request'):
            require(all(docs[role].get(flag) is False for flag in flags))
        draft=docs['draft_request']
        require(draft.get('status') == 'DRAFT_REQUEST_TEMPLATE' and draft.get('source_mode') == 'project_snapshot'
                and draft.get('stationary_readonly_window_confirmed') is False
                and hashed(record.get('parent_review_sha256'))
                and all(draft.get(k) is None for k in ('roots','certificate','certificate_sha256','manifest_sha256',
                    'approval_file','approval_sha256','output','scratch_parent','scope_file','scope_sha256','budget_file','budget_sha256')))
        for key in ('snapshot_id','relative_path','expected_sha256','expected_size','rule_id','image_id','git_revision','lifecycle_seconds','roots_sha256'):
            require(same(draft.get(key),request.get(key)))
        require(record.get('roots_sha256') == request.get('roots_sha256')
                and same(record.get('controller_checked_candidate_identity'),batch.get('controller_verified_image')))
        require(same(docs['draft_scope'].get('objects'),[obj])
                and same(docs['draft_budget'].get('objects'),[cap])
                and same(scope.get('objects'),[obj]) and same(budget.get('objects'),[cap])
                and budget.get('group') == 'large' and budget.get('max_seconds') == 1800)
        require(request.get('source_mode') == 'artificial' and scope.get('source_read_authorized') is False
                and scope.get('synthetic_data_authorized') is True and scope.get('postgresql_authorized') is False
                and scope.get('ready_for_import') is False and request.get('lifecycle_seconds') == 1800)
        require(request.get('snapshot_id') == parent['snapshot_id'] == scope.get('snapshot_id')
                and request.get('relative_path') == parent['source']['path']
                and same(request.get('expected_size'),parent['source']['size'])
                and request.get('expected_sha256') == parent['source']['sha256']
                and request.get('rule_id') == parent['rule_id'] == scope.get('rule_id')
                and same(scope.get('source'),parent['source']))
        for role,key in (('roots','roots'),('certificate','certificate'),('scope','scope_file'),('budget','budget_file'),('approval','approval_file')):
            pin_key = {'scope_file':'scope_sha256','budget_file':'budget_sha256','approval_file':'approval_sha256'}.get(key,key+'_sha256')
            require(request.get(pin_key) == f[role]['sha256'] and request.get(key) == f[role]['path'])
            require(batch.get(pin_key) == request[pin_key])
        bindings = request.get('bindings')
        require(type(bindings) is dict and bindings.keys() == {'parent_scope','parent_budget','partition_selection','descriptor'})
        required = {'parent_scope':chosen['parent_scope']['sha256'],'parent_budget':chosen['parent_budget']['sha256'],
                    'partition_selection':f['partition_selection']['sha256'],'descriptor':f['descriptor']['sha256']}
        for role,pin in required.items():
            require(same(bindings.get(role),f[role]))
        require(type(draft.get('bindings')) is dict and draft['bindings'].keys() == {'parent_scope','parent_budget','partition_selection'})
        for role in draft['bindings']:
            description=draft['bindings'][role]
            require(type(description) is dict and description.keys() == {'path','sha256'}
                    and type(description['path']) is str and Path(description['path']).is_absolute()
                    and '..' not in Path(description['path']).parts and description['sha256'] == required[role])
        require(same(scope.get('bindings'),{k:v['sha256'] for k,v in bindings.items()})
                and same(batch.get('bindings'),scope['bindings']))
        approval = dict(version=1,status='APPROVED_READONLY_BATCH',source_mode='artificial',source_read_authorized=False,
            synthetic_data_authorized=True,stationary_readonly_window=True,postgresql_authorized=False,ready_for_import=False,
            request_sha256=digest({k:v for k,v in request.items() if k not in ('approval_file','approval_sha256')}))
        require(same(docs['approval'],approval))
        cert = docs['certificate']
        require(cert.get('status') == 'VERIFIED' and cert.get('snapshot_id') == parent['snapshot_id']
                and cert.get('source_path') == roots['roots']['usedata']['path']
                and type(cert.get('members')) is list and digest(cert['members']) == request.get('manifest_sha256')
                and cert.get('manifest_sha256') == request['manifest_sha256']
                and [m for m in cert['members'] if m.get('path') == parent['source']['path']] == [parent['source']])
        require(batch.get('complete') is True and batch.get('synthetic_only') is True and batch.get('source_mode') == 'artificial'
                and batch.get('postgresql_connected') is False and batch.get('ready_for_import') is False
                and batch.get('contract_frozen') is False and type(batch.get('file_digest_passes')) is int
                and batch['file_digest_passes'] == 2 and batch.get('full_snapshot_verified_this_run') is True
                and batch.get('controller_request_sha256') == f['request']['sha256']
                and batch.get('source_sha256_before') == request['expected_sha256'] == batch.get('source_sha256_after')
                and batch.get('manifest_sha256') == request['manifest_sha256']
                and batch.get('image_id') == request.get('image_id')
                and batch.get('git_revision') == request.get('git_revision'))
        identity = batch.get('controller_verified_image')
        require(type(identity) is dict and identity.get('image_id') == request['image_id']
                and identity.get('git_revision') == request['git_revision'] and identity.get('user') == '10001:10001'
                and identity.get('source_status') in ('dirty','clean')
                and type(request['image_id']) is str and re.fullmatch(r'sha256:[0-9a-f]{64}',request['image_id'])
                and type(request['git_revision']) is str and re.fullmatch(r'[0-9a-f]{40}',request['git_revision']))
        cohort = {k:request[k] for k in ('image_id','git_revision','snapshot_id','relative_path','expected_sha256','expected_size','roots_sha256','certificate_sha256','manifest_sha256','rule_id')}
        if common is None:
            common = cohort
        require(same(cohort,common))
        objects = batch.get('objects')
        require(type(objects) is list and len(objects) == 1)
        result = objects[0]
        schema = hashlib.sha256(schema_bytes(UnorderedSchema(obj['source_object_id'],tuple(UnorderedColumn(**c) for c in obj['columns'])))).hexdigest()
        for key in ('source_object_id','source_object_name','schema_hash','expected_count','field_count','expected_sha256'):
            require(key in result and same(result[key],gold[obj['source_object_id']][key]))
        require(result['schema_hash'] == schema and hashed(result['expected_sha256'])
                and type(result['expected_count']) is int and result['expected_count'] >= 0
                and type(result['field_count']) is int and result['field_count'] == result['expected_count']*len(obj['columns'])
                and result.get('cleanup_complete') is True and result['source_read'].get('values_complete') is True
                and same(result['source_read'].get('rows_read'),result['expected_count'])
                and same(result['source_read'].get('cells_read'),result['field_count'])
                and result['source_read'].get('postgresql_connected') is False)
        monitor, limits, host, state = (docs[k] for k in ('monitor','limits','host_config','container_state'))
        require(monitor.get('status') == 'SYNTHETIC_WORKER_COMPLETED' and monitor.get('source_mode') == 'artificial'
                and monitor.get('synthetic_only') is True and monitor.get('reason') is None
                and type(monitor.get('worker_exit_code')) is int and monitor['worker_exit_code'] == 0
                and monitor.get('process_group_gone') is True
                and monitor['cgroup_stats'].get('memory.swap.current') == '0'
                and 0 <= int(monitor['cgroup_stats']['memory.peak']) <= 805306368
                and type(monitor.get('samples')) is list and len(monitor['samples']) >= 1
                and all(s.get('services_healthy') is True and type(s.get('swap_out_pages')) is int and s['swap_out_pages'] == 0 for s in monitor['samples']))
        for key,value in {'cpu.max':'50000 100000','memory.max':'805306368','memory.swap.max':'0','worker_nice':19,'worker_ionice':'idle'}.items():
            require(same(limits.get(key),value))
        for key,value in dict(NanoCpus=500000000,Memory=805306368,MemorySwap=805306368,NetworkMode='none',ReadonlyRootfs=True).items():
            require(same(host.get(key),value))
        require(state.get('Running') is False and state.get('OOMKilled') is False
                and type(state.get('ExitCode')) is int and state['ExitCode'] == 0)
        return {k:result[k] for k in ('source_object_id','source_object_name','schema_hash','expected_count','field_count','expected_sha256')}

    selected = {}
    for entry in chosen['entries']:
        check_cancel()
        require(entry.get('partition_id') not in selected)
        selected[entry['partition_id']] = attempt(entry)
    for entry in chosen['comparison_attempts']:
        result = attempt(entry)
        require(entry['partition_id'] in selected and same(result,selected[entry['partition_id']]))
    missing = [f'large-p{i+1:02d}' for i in range(10) if f'large-p{i+1:02d}' not in selected]
    output = safe_path(str(output_dir))
    require(output.parent.is_dir() and not any(output == p or output in p.parents for p in inputs))
    output.mkdir()
    name = 'coverage.incomplete.json' if missing else 'coverage.json'
    record = dict(version=1,status='INCOMPLETE_PARTITION_COVERAGE' if missing else 'DRAFT_PARTITION_COVERAGE_COMPLETE',
        complete=not missing,synthetic_only=True,source_mode='artificial',**{flag:False for flag in flags},
        postgresql_connected=False,task8_complete=False,objects=len(selected),columns=sum(len(parent['objects'][int(k[-2:])-1]['columns']) for k in selected),
        verified_partitions=list(selected),missing_partitions=missing,source_identity=common,
        selection_sha256=expected_selection_sha256,objects_evidence=list(selected.values()))
    stage = output / ('.'+name+'.incomplete')
    write_json_exclusive(stage,record)
    for path,value in inputs.items():
        check_cancel()
        require(read_metadata(path) == value)
    require(read_metadata(stage) == (canonical_json(record)+'\n').encode('utf-8'))
    check_cancel()
    final = output / name
    os.link(stage,final)
    return final


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--selection-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    stopped=False
    def stop(*unused):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        marker=verify_partition_coverage(selection_file=args.selection,expected_selection_sha256=args.selection_sha256,
            output_dir=args.output_dir,cancelled=lambda:stopped)
        print(json.dumps(dict(status='ARTIFICIAL_OFFLINE_COVERAGE_VERIFIED',marker=str(marker),ready_for_import=False)))
        return 0
    except Exception:
        print(json.dumps(dict(status='ARTIFICIAL_OFFLINE_COVERAGE_REJECTED',ready_for_import=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
