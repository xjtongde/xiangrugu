"""Prepare draft task metadata from repository files; never read source bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from .batch_execution import read_metadata, _json
from .config import load_config
from .readonly_batch import _path, _hash, _group_limits
from .snapshots import write_json_exclusive
from .sqlite_values import _validate_scope
from .unordered_values import UnorderedSchema, UnorderedColumn, schema_bytes


def _validate_preparation(*, repository_root, review_file, expected_review_sha256,
        expected_roots_sha256, expected_image_id, actual_image, output_dir):
    """Validate a complete group and assemble closed draft documents without writes.

    Digest pins and actual image identity are selected by the external caller.
    Image identity checks do not prove regression success; tested candidate
    references in the review describe history, not an allowed-image list.
    Input reads are confined to bounded repository metadata, not configured
    source/snapshot roots. Callers own exclusive persistence and completion
    publication. No approval document or execution authority is assembled.
    """
    root = _path(str(repository_root))
    if not root.is_dir() or not _hash(expected_review_sha256) or not _hash(expected_roots_sha256):
        raise ValueError('preparation_identity')
    inputs = {}
    def read(relative, expected):
        if (type(relative) is not str or relative.startswith('/') or '\\' in relative
                or any(part in ('', '.', '..') for part in relative.split('/'))
                or not relative.startswith(('datamgmt/contracts/', 'datamgmt/config/',
                    'datamgmt/src/', 'datamgmt/tests/', 'docs/superpowers/evidence/', 'scripts/'))
                or not _hash(expected)):
            raise ValueError('repository_metadata_path')
        path = _path(str(root / relative))
        raw = read_metadata(path)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('preparation_identity')
        inputs[path] = raw
        return raw

    packet = _json(read(review_file, expected_review_sha256))
    authority_keys = ('source_read_authorized', 'postgresql_authorized', 'contract_frozen', 'ready_for_import')
    def closed(document):
        if type(document) is not dict or any(document.get(key) is not False for key in authority_keys):
            raise ValueError('preparation_authority')
    closed(packet)
    if (packet.get('status') != 'METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE'
            or type(packet.get('version')) is not int or packet['version'] != 1
            or type(packet.get('git_revision')) is not str
            or not re.fullmatch(r'[0-9a-f]{40}', packet['git_revision'])):
        raise ValueError('preparation_review')
    if (not re.fullmatch(r'sha256:[0-9a-f]{64}', expected_image_id or '')
            or type(actual_image) is not dict
            or actual_image.keys() != {'image_id', 'git_revision', 'user', 'source_status'}
            or actual_image['image_id'] != expected_image_id
            or actual_image['git_revision'] != packet['git_revision']
            or actual_image['user'] != '10001:10001'
            or actual_image['source_status'] not in ('clean', 'dirty')):
        raise ValueError('preparation_image')
    deadlines = packet.get('verified_artificial_deadlines')
    expected_deadlines = dict(candidate_seconds=1800, host_seconds=1830,
                              transport_seconds=1880, real_mode_activated=False)
    if (deadlines != expected_deadlines or any(type(deadlines[k]) is not type(v)
            for k, v in expected_deadlines.items())):
        raise ValueError('preparation_deadline')
    bindings = packet.get('bindings')
    needed = {'roots', 'original_scope_review', 'preparation', 'mapping', 'remaining_budget'}
    if type(bindings) is not dict or not needed <= bindings.keys() or not 5 <= len(bindings) <= 32:
        raise ValueError('preparation_bindings')
    documents = {}
    for role, description in bindings.items():
        if (type(role) is not str or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', role)
                or type(description) is not dict or description.keys() != {'path', 'sha256'}):
            raise ValueError('preparation_bindings')
        raw = read(description['path'], description['sha256'])
        if role in needed - {'roots'}:
            documents[role] = _json(raw)
    if bindings['roots']['sha256'] != expected_roots_sha256:
        raise ValueError('preparation_roots')
    config = load_config(root / bindings['roots']['path'], environ={})
    review = documents['original_scope_review']
    closed(review)
    group = review.get('group')
    if type(group) is not str or group not in ('small', 'medium', 'large'):
        raise ValueError('preparation_scope')
    expected_objects, expected_columns = {'small': (55, 326), 'medium': (10, 156),
                                          'large': (10, 235)}[group]
    scope = packet.get('scope')
    if (type(scope) is not dict or review.get('scope') != scope
            or type(scope.get('objects')) is not int or scope['objects'] != expected_objects
            or type(scope.get('columns')) is not int or scope['columns'] != expected_columns
            or type(scope.get('snapshot_id')) is not str
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', scope['snapshot_id'])
            or type(review.get('rule_id')) is not str or not review['rule_id']):
        raise ValueError('preparation_scope')
    member = scope.get('member')
    if (type(member) is not dict or member.keys() != {'path', 'kind', 'size', 'sha256'}
            or member['kind'] != 'file' or type(member['path']) is not str
            or '\\' in member['path'] or member['path'].startswith('/')
            or any(p in ('', '.', '..') for p in member['path'].split('/'))):
        raise ValueError('preparation_member')
    objects = review.get('objects')
    selected = [obj for obj in documents['remaining_budget']['objects'] if obj.get('proposed_group') == group]
    if (type(objects) is not list or len(objects) != expected_objects or len(selected) != expected_objects
            or len({obj['source_object_id'] for obj in objects}) != expected_objects
            or len({obj['source_object_name'] for obj in objects}) != expected_objects):
        raise ValueError('preparation_scope')
    prepared = documents['preparation']['objects']
    mapped = documents['mapping']['objects']
    draft_objects, draft_budgets = [], []
    columns = 0
    for obj, historic in zip(objects, selected, strict=True):
        matches = [p for p in prepared if p['source_object_id'] == obj['source_object_id']]
        names = [p for p in mapped if p['source_object_id'] == obj['source_object_id']]
        if (obj.get('expected_count') is not None or obj.get('expected_sha256') is not None
                or historic['source_object_id'] != obj['source_object_id']
                or historic['name'] != obj['source_object_name'] or len(matches) != 1 or len(names) != 1
                or matches[0]['source_object_name'] != obj['source_object_name']
                or names[0]['source_object_name'] != obj['source_object_name']
                or matches[0]['columns'] != obj['columns'] or matches[0]['schema_hash'] != obj['schema_hash']
                or [c['source_name'] for c in names[0]['columns']] != obj['source_columns']
                or len(names[0]['columns']) != len(obj['columns'])
                or any(m['source_ordinal'] != c['source_ordinal']
                    or m['column_identity'] != c['column_key'] or m['approved_type'] != c['pg_type']
                    for m, c in zip(names[0]['columns'], obj['columns'], strict=True))):
            raise ValueError('preparation_columns')
        budget = dict(source_object_id=obj['source_object_id'], read_limits=obj['read_limits'], sort_limits=obj['sort_limits'])
        read_limits, sort_limits = _group_limits(budget, group)
        schema = UnorderedSchema(obj['source_object_id'], tuple(UnorderedColumn(**c) for c in obj['columns']))
        if (hashlib.sha256(schema_bytes(schema)).hexdigest() != obj['schema_hash']
                or type(member['size']) is not int or member['size'] > read_limits.max_file_bytes
                or len(schema.columns) > sort_limits.max_columns):
            raise ValueError('preparation_schema')
        _validate_scope(expected_size=member['size'], expected_sha256=member['sha256'],
            relative_path=member['path'], table=obj['source_object_name'], source_columns=tuple(obj['source_columns']),
            schema=schema, limits=read_limits, cancelled=lambda: False)
        draft_objects.append({k: obj[k] for k in ('source_object_id', 'source_object_name', 'source_columns', 'columns')})
        draft_budgets.append(budget)
        columns += len(schema.columns)
    if columns != expected_columns:
        raise ValueError('preparation_columns')
    output = Path(output_dir)
    # Reject configured source/snapshot destinations lexically, before any stat.
    if (not output.is_absolute() or any(output == p or p in output.parents for p in
            (root, config.source.path, config.snapshot_root))):
        raise ValueError('preparation_output')
    output = _path(str(output))
    if not output.parent.is_dir():
        raise ValueError('preparation_output')
    for path, raw in inputs.items():
        if read_metadata(path) != raw:
            raise ValueError('preparation_input_changed')
    authority = dict(source_read_authorized=False, postgresql_authorized=False,
                     contract_frozen=False, ready_for_import=False)
    scope_draft = dict(version=1, status='DRAFT_SCOPE_NOT_AUTHORIZED', **authority,
        snapshot_id=scope['snapshot_id'], source=member, rule_id=review['rule_id'],
        bindings={k: bindings[k]['sha256'] for k in ('original_scope_review', 'preparation', 'mapping', 'remaining_budget')}, objects=draft_objects)
    budget_draft = dict(version=2, status='DRAFT_BUDGET_NOT_EXECUTION_READY', group=group, max_seconds=1800, objects=draft_budgets)
    request_draft = dict(version=1, status='DRAFT_REQUEST_TEMPLATE', **authority,
        source_mode='project_snapshot', snapshot_id=scope['snapshot_id'], relative_path=member['path'],
        expected_size=member['size'], expected_sha256=member['sha256'], rule_id=review['rule_id'],
        lifecycle_seconds=1800, image_id=actual_image['image_id'], git_revision=actual_image['git_revision'],
        roots=None, roots_sha256=expected_roots_sha256, certificate=None, certificate_sha256=None,
        manifest_sha256=None, approval_file=None, approval_sha256=None, output=None, scratch_parent=None,
        scope_file=None, scope_sha256=None, budget_file=None, budget_sha256=None,
        stationary_readonly_window_confirmed=False)
    record = dict(version=1, status='DRAFT_METADATA_TASK_PREPARATION', **authority,
        real_execution_ready=False, controller_real_mode_enabled=False, objects=expected_objects, columns=expected_columns,
        review_sha256=expected_review_sha256, roots_sha256=expected_roots_sha256,
        controller_checked_candidate_identity=dict(actual_image), host_deadline_seconds=1830, transport_deadline_seconds=1880,
        bindings=bindings, generated={}, source_bytes_read=False, source_expectations_generated=False)
    return dict(scope=scope_draft, budget=budget_draft, request=request_draft,
                record=record, inputs=inputs, output=output)


def prepare_task(*, repository_root, review_file, expected_review_sha256,
        expected_roots_sha256, expected_image_id, actual_image, output_dir):
    """Publish an exclusively created complete-group, non-executable draft."""
    validated = _validate_preparation(repository_root=repository_root, review_file=review_file,
        expected_review_sha256=expected_review_sha256, expected_roots_sha256=expected_roots_sha256,
        expected_image_id=expected_image_id, actual_image=actual_image, output_dir=output_dir)
    output = validated['output']
    output.mkdir()
    generated = {}
    for name, key in (('scope.draft.json', 'scope'), ('budget.draft.json', 'budget'), ('request.draft.json', 'request')):
        path = output / name
        write_json_exclusive(path, validated[key])
        generated[name] = hashlib.sha256(read_metadata(path)).hexdigest()
    marker = output / 'preparation.json'
    stage = output / '.preparation.incomplete'
    validated['record']['generated'] = generated
    write_json_exclusive(stage, validated['record'])
    os.link(stage, marker)
    return marker

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--review-sha256', required=True)
    parser.add_argument('--roots-sha256', required=True)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--actual-image-id', required=True)
    parser.add_argument('--git-revision', required=True)
    parser.add_argument('--image-user', required=True)
    parser.add_argument('--source-status', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        marker = prepare_task(repository_root=args.repository_root, review_file=args.review,
            expected_review_sha256=args.review_sha256, expected_roots_sha256=args.roots_sha256,
            expected_image_id=args.image_id, actual_image=dict(image_id=args.actual_image_id,
                git_revision=args.git_revision, user=args.image_user, source_status=args.source_status),
            output_dir=args.output_dir)
        print(json.dumps(dict(status='DRAFT_METADATA_TASK_PREPARATION', marker=str(marker), real_execution_ready=False)))
        return 0
    except Exception:
        print(json.dumps(dict(status='TASK_PREPARATION_FAILED', real_execution_ready=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
