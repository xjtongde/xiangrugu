"""Approved source-only batch entry; human authorization remains external.

This module reads a stationary, read-only project snapshot, never the NAS or
PostgreSQL. An approval file is a digest-bound execution descriptor, not proof
that a human issued it. The trusted controller must select its expected digest.
Small/medium support project snapshots. Large project tasks additionally require
a pinned complete single-partition metadata chain and explicit controller evidence.
"""
from dataclasses import fields
import hashlib
import os
from pathlib import Path
import re
import time

from .batch_execution import read_metadata, _json, _check_cancel
from .config import load_config
from .snapshots import digest, verify_snapshot, write_json_exclusive
from .sqlite_expectations import summarize_sqlite_batch
from .sqlite_values import SQLiteValueLimits, _validate_scope
from .unordered_values import UnorderedColumn, UnorderedSchema, UnorderedLimits


def _path(value):
    if type(value) is not str:
        raise ValueError('path')
    path = Path(value)
    if (not path.is_absolute() or '..' in path.parts or str(path) != value
            or any(p.is_symlink() for p in (path, *path.parents))):
        raise ValueError('path')
    return path


def _require_readonly_mount(path):
    # statvfs includes the per-mount read-only flag on Linux (including binds).
    # This does not prevent a privileged writer through a different mount.
    if not os.statvfs(path).f_flag & os.ST_RDONLY:
        raise ValueError('readonly_mount')


def _hash(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _group_limits(description, group):
    if type(group) is not str or group not in ('small', 'medium', 'large'):
        raise ValueError('budget')
    if (type(description) is not dict
            or description.keys() != {'source_object_id', 'read_limits', 'sort_limits'}
            or type(description['read_limits']) is not dict
            or type(description['sort_limits']) is not dict
            or description['read_limits'].keys() != {f.name for f in fields(SQLiteValueLimits)}
            or description['sort_limits'].keys() != {f.name for f in fields(UnorderedLimits)}):
        raise ValueError('budget')
    read = SQLiteValueLimits(**description['read_limits'])
    sort = UnorderedLimits(**description['sort_limits'])
    read_caps = dict(max_file_bytes=2**30, max_columns=64, max_rows=4000,
        max_cells=50000, max_cell_bytes=2**20, max_value_bytes=8*2**20,
        max_vm_steps=20000000, max_seconds=300)
    sort_caps = dict(max_rows=4000, max_columns=64, max_field_bytes=2**20,
        max_row_bytes=2**20, max_stream_bytes=8*2**20, chunk_bytes=2*2**20,
        chunk_rows=4096, merge_fan_in=16, max_temp_bytes=64*2**20,
        max_temp_files=1024, max_differences=100, max_seconds=300, workers=1)
    if group == 'medium':
        read_caps.update(max_rows=100000, max_cells=2000000, max_value_bytes=32*2**20,
                         max_vm_steps=100000000, max_seconds=600)
        sort_caps.update(max_rows=100000, max_stream_bytes=32*2**20, max_seconds=600)
    elif group == 'large':
        read_caps.update(max_rows=2000000, max_cells=40000000,
                         max_value_bytes=256*2**20, max_vm_steps=1000000000,
                         max_seconds=1800)
        sort_caps.update(max_rows=2000000, max_stream_bytes=256*2**20,
                         max_temp_bytes=2**30, max_seconds=1800)
    if (any(getattr(read, k) > v for k, v in read_caps.items())
            or any(getattr(sort, k) > v for k, v in sort_caps.items())):
        raise ValueError(group + '_budget')
    return read, sort


def _small_limits(description):
    """Keep the existing preparation/helper API and small-group ceilings."""
    return _group_limits(description, 'small')


def _validate_members(members):
    names = []
    for member in members:
        if type(member) is not dict:
            raise ValueError('certificate_member')
        name, kind = member.get('path'), member.get('kind')
        if (type(name) is not str or not name or name.startswith('/') or '\\' in name or '\x00' in name
                or any(p in ('', '.', '..') for p in name.split('/'))):
            raise ValueError('certificate_member')
        if kind == 'directory':
            valid = member.keys() == {'path', 'kind'}
        elif kind == 'file':
            valid = (member.keys() == {'path', 'kind', 'size', 'sha256'}
                     and type(member['size']) is int and member['size'] >= 0 and _hash(member['sha256']))
        else:
            valid = False
        if not valid:
            raise ValueError('certificate_member')
        names.append(name)
    if names != sorted(set(names)):
        raise ValueError('certificate_member')


def execute_readonly_batch(request, *, cancelled=lambda: False, controller_evidence=None, progress=None):
    """Preflight every descriptor, verify the snapshot, stage a complete batch.

    Publication belongs to the monitored controller. A staged result alone
    never authorizes another group, database work or a frozen contract.
    """
    if progress is not None:
        progress('request_preflight')
    keys = {'roots', 'snapshot_id', 'relative_path', 'expected_size', 'expected_sha256',
        'certificate', 'certificate_sha256', 'manifest_sha256', 'output', 'image_id',
        'git_revision', 'rule_id', 'scope_file', 'scope_sha256', 'scratch_parent',
        'roots_sha256', 'budget_file', 'budget_sha256', 'source_mode', 'bindings',
        'approval_file', 'approval_sha256'}
    if type(request) is not dict or request.keys() not in (keys, keys | {'lifecycle_seconds'}):
        raise ValueError('request')
    lifecycle = request.get('lifecycle_seconds')
    if 'lifecycle_seconds' in request:
        if type(lifecycle) is not int or not 1 <= lifecycle <= 1800:
            raise ValueError('lifecycle_budget')
        started, upstream_cancelled = time.monotonic(), cancelled
        def lifecycle_guard():
            if time.monotonic()-started >= lifecycle:
                raise ValueError('lifecycle_timeout')
            return upstream_cancelled()
        cancelled = lifecycle_guard
    if controller_evidence is not None and (type(controller_evidence) is not dict
            or controller_evidence.keys() != {'controller_request_sha256', 'controller_verified_image',
                                             'controller_lifecycle_seconds'}
            or not _hash(controller_evidence['controller_request_sha256'])
            or type(controller_evidence['controller_verified_image']) is not dict
            or type(controller_evidence['controller_lifecycle_seconds']) is not int
            or controller_evidence['controller_lifecycle_seconds'] != lifecycle):
        raise ValueError('controller_evidence')
    mode = request['source_mode']
    if mode not in ('artificial', 'project_snapshot'):
        raise ValueError('source_mode')
    _check_cancel(cancelled)
    metadata = {}
    paths = {}
    for key, hash_key in (('roots', 'roots_sha256'), ('certificate', 'certificate_sha256'),
            ('scope_file', 'scope_sha256'), ('budget_file', 'budget_sha256'),
            ('approval_file', 'approval_sha256')):
        paths[key] = _path(request[key])
        raw = read_metadata(paths[key])
        if not _hash(request[hash_key]) or hashlib.sha256(raw).hexdigest() != request[hash_key]:
            raise ValueError('input_identity')
        metadata[paths[key]] = raw
    approval = _json(metadata[paths['approval_file']])
    expected_approval = dict(version=1, status='APPROVED_READONLY_BATCH', source_mode=mode,
        source_read_authorized=mode == 'project_snapshot', synthetic_data_authorized=mode == 'artificial',
        stationary_readonly_window=True, postgresql_authorized=False, ready_for_import=False,
        request_sha256=digest({k: v for k, v in request.items()
                              if k not in ('approval_file', 'approval_sha256')}))
    if (type(approval) is not dict or approval != expected_approval
            or any(type(approval[k]) is not type(v) for k, v in expected_approval.items())):
        raise ValueError('approval')
    bindings = request['bindings']
    if type(bindings) is not dict or not 1 <= len(bindings) <= 16:
        raise ValueError('bindings')
    for role, description in bindings.items():
        if (type(role) is not str or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', role)
                or type(description) is not dict or description.keys() != {'path', 'sha256'}
                or not _hash(description['sha256'])):
            raise ValueError('bindings')
        path = _path(description['path'])
        if path in metadata:
            raise ValueError('path_alias')
        raw = read_metadata(path)
        if hashlib.sha256(raw).hexdigest() != description['sha256']:
            raise ValueError('binding_identity')
        metadata[path] = raw
    if len(set(paths.values())) != len(paths):
        raise ValueError('path_alias')
    output, scratch = _path(request['output']), _path(request['scratch_parent'])
    stage = output.with_name('.'+output.name+'.incomplete')
    if (output in metadata or stage in metadata or scratch in metadata or output == scratch
            or not output.parent.is_dir() or not scratch.is_dir()):
        raise ValueError('output_path')
    if output.exists() or stage.exists():
        raise FileExistsError('output_exists')
    config = load_config(paths['roots'], environ={})
    # Business roots come only from the digest-bound configuration (P-17).
    # A trusted caller must select the expected roots digest independently.
    if mode == 'artificial' and (config.source.host != 'synthetic'
            or config.source.path.name != 'authority-never-read'):
        raise ValueError('artificial_roots')
    if config.evidence_root not in output.parents or config.evidence_root not in scratch.parents:
        raise ValueError('evidence_root')
    snapshot_id, relative = request['snapshot_id'], request['relative_path']
    if (type(snapshot_id) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', snapshot_id)
            or type(relative) is not str or not relative or '\\' in relative
            or any(p in ('', '.', '..') for p in relative.split('/'))
            or type(request['rule_id']) is not str or not request['rule_id']
            or type(request['image_id']) is not str or not re.fullmatch(r'sha256:[0-9a-f]{64}', request['image_id'])
            or type(request['git_revision']) is not str or not re.fullmatch(r'[0-9a-f]{40}', request['git_revision'])):
        raise ValueError('source_identity')
    snapshot = _path(str(config.snapshot_root / snapshot_id))
    if any(p == snapshot or snapshot in p.parents for p in (output, scratch, *metadata)):
        raise ValueError('snapshot_alias')
    selected = dict(path=relative, kind='file', size=request['expected_size'], sha256=request['expected_sha256'])
    certificate = _json(metadata[paths['certificate']])
    if (type(certificate) is not dict or type(certificate.get('version')) is not int
            or certificate.get('version') != 1 or certificate.get('status') != 'VERIFIED'
            or certificate.get('snapshot_id') != snapshot_id
            or certificate.get('source_path') != str(config.source.path)
            or type(certificate.get('members')) is not list or not _hash(request['manifest_sha256'])
            or digest(certificate['members']) != request['manifest_sha256']
            or certificate.get('manifest_sha256') != request['manifest_sha256']):
        raise ValueError('certificate_scope')
    _validate_members(certificate['members'])
    if [m for m in certificate['members'] if m['path'] == relative] != [selected]:
        raise ValueError('certificate_scope')
    scope = _json(metadata[paths['scope_file']])
    scope_keys = {'version', 'source_read_authorized', 'snapshot_id', 'source', 'rule_id',
                  'postgresql_authorized', 'ready_for_import', 'bindings', 'objects'}
    if mode == 'artificial' or (type(scope) is dict and 'synthetic_data_authorized' in scope):
        scope_keys.add('synthetic_data_authorized')
    if (type(scope) is not dict or scope.keys() != scope_keys or type(scope['version']) is not int
            or scope['version'] != 1 or scope['source_read_authorized'] is not (mode == 'project_snapshot')
            or (mode == 'artificial' and scope['synthetic_data_authorized'] is not True)
            or (mode == 'project_snapshot' and scope.get('synthetic_data_authorized',False) is not False)
            or scope['postgresql_authorized'] is not False or scope['ready_for_import'] is not False
            or scope['source'] != selected or scope['snapshot_id'] != snapshot_id
            or scope['rule_id'] != request['rule_id']
            or scope['bindings'] != {k: v['sha256'] for k, v in bindings.items()}
            or type(scope['objects']) is not list or not 1 <= len(scope['objects']) <= 55):
        raise ValueError('scope_authority')
    budget = _json(metadata[paths['budget_file']])
    if (type(budget) is not dict or budget.keys() != {'version', 'group', 'max_seconds', 'objects'}
            or type(budget['version']) is not int or budget['version'] != 2
            or type(budget['group']) is not str or budget['group'] not in ('small', 'medium', 'large')
            or type(budget['max_seconds']) is not int
            or not 1 <= budget['max_seconds'] <= 1800 or type(budget['objects']) is not list
            or len(budget['objects']) != len(scope['objects'])):
        raise ValueError('budget')
    # Validate independently of the control entry, before all source access.
    if budget['group'] == 'large' and mode != 'artificial':
        from .project_partition import validate_project_partition_request,recheck_project_partition_metadata
        partition_metadata=validate_project_partition_request(request=request,
            controller_evidence=controller_evidence,cancelled=cancelled)
        for path,raw in partition_metadata.input_bytes.items():
            if path in metadata and metadata[path]!=raw:raise ValueError('metadata_changed')
            metadata[path]=raw
        upstream_progress=progress
        def boundary(stage,**details):
            if upstream_progress is not None:upstream_progress(stage,**details)
            recheck_project_partition_metadata(partition_metadata,cancelled=cancelled)
        progress=boundary
    if len(scope['objects']) > (55 if budget['group'] == 'small' else 10):
        raise ValueError('budget')
    if lifecycle is not None and budget['max_seconds'] > lifecycle:
        raise ValueError('lifecycle_budget')
    objects, names, identities = [], set(), set()
    for obj, limits in zip(scope['objects'], budget['objects'], strict=True):
        if (type(obj) is not dict or obj.keys() != {'source_object_id', 'source_object_name', 'source_columns', 'columns'}
                or type(obj['source_object_name']) is not str or type(obj['source_object_id']) is not str
                or obj['source_object_name'] in names or obj['source_object_id'] in identities
                or type(obj['source_columns']) is not list or type(obj['columns']) is not list):
            raise ValueError('scope_object')
        read, sort = _group_limits(limits, budget['group'])
        if limits['source_object_id'] != obj['source_object_id']:
            raise ValueError('budget_object')
        schema = UnorderedSchema(obj['source_object_id'], tuple(UnorderedColumn(**c) for c in obj['columns']))
        _validate_scope(expected_size=request['expected_size'], expected_sha256=request['expected_sha256'],
            relative_path=relative, table=obj['source_object_name'], source_columns=tuple(obj['source_columns']),
            schema=schema, limits=read, cancelled=cancelled)
        if request['expected_size'] > read.max_file_bytes or len(schema.columns) > sort.max_columns:
            raise ValueError('budget_object')
        names.add(obj['source_object_name'])
        identities.add(obj['source_object_id'])
        objects.append(dict(table=obj['source_object_name'], source_columns=tuple(obj['source_columns']),
                            schema=schema, read_limits=read, sort_limits=sort))
    # All descriptors and identity/budget checks precede any source-byte reads.
    readonly_paths = list(metadata) + [snapshot]
    for member in certificate['members']:
        member_path = member.get('path')
        if (type(member_path) is not str or not member_path or '\\' in member_path
                or any(p in ('', '.', '..') for p in member_path.split('/'))):
            raise ValueError('certificate_member')
        readonly_paths.append(_path(str(snapshot / member_path)))
    for path in readonly_paths:
        _require_readonly_mount(path)
    _check_cancel(cancelled)
    cache_args = {}
    if progress is not None:
        progress('snapshot_verify')
    if mode == 'project_snapshot':
        from .read_cache import ReadCachePolicy
        read_cache = ReadCachePolicy()
        cache_args = dict(read_cache=read_cache)
        verify_snapshot(snapshot, paths['certificate'], expected_source=config.source.path,
                        guard=lambda: _check_cancel(cancelled), **cache_args)
    else:
        verify_snapshot(snapshot, paths['certificate'], expected_source=config.source.path)
    _check_cancel(cancelled)
    if progress is not None:
        progress('batch_preflight')
    result = summarize_sqlite_batch(snapshot / relative, expected_size=request['expected_size'],
        expected_sha256=request['expected_sha256'], relative_path=relative, objects=tuple(objects),
        scratch_parent=scratch, cancelled=cancelled, max_seconds=budget['max_seconds'], **cache_args,
        **({} if progress is None else dict(progress=progress)))
    if cache_args:
        result['read_cache'] = read_cache.evidence()
    if progress is not None:
        progress('metadata_recheck', completed_objects=len(objects))
    for path, raw in metadata.items():
        if read_metadata(path) != raw:
            raise ValueError('metadata_changed')
    for path in readonly_paths:
        _require_readonly_mount(path)
    _check_cancel(cancelled)
    result.update(execution_kind='approved-readonly-batch-v1', source_mode=mode,
        synthetic_only=mode == 'artificial', full_snapshot_verified_this_run=True,
        approval_sha256=request['approval_sha256'], scope_sha256=request['scope_sha256'],
        budget_sha256=request['budget_sha256'], roots_sha256=request['roots_sha256'],
        certificate_sha256=request['certificate_sha256'], manifest_sha256=request['manifest_sha256'],
        bindings={k: v['sha256'] for k, v in bindings.items()}, git_revision=request['git_revision'],
        image_id=request['image_id'], source_status='dirty', raw_values_emitted=False,
        group=budget['group'], readonly_mounts_checked=len(readonly_paths))
    if controller_evidence is not None:
        result.update(controller_evidence)
    if progress is not None:
        progress('stage_save', completed_objects=len(objects))
    write_json_exclusive(stage, result)
    _check_cancel(cancelled)
    return stage
