"""Prepare closed single-table drafts after validating the entire large group."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re

from .batch_execution import read_metadata
from .snapshots import canonical_json, write_json_exclusive
from .task_preparation import _validate_preparation


def prepare_partition_task(*, repository_root, review_file, expected_review_sha256,
        expected_roots_sha256, expected_image_id, actual_image, output_dir, partition_id):
    if type(partition_id) is not str or not re.fullmatch(r'large-p(?:0[1-9]|10)', partition_id):
        raise ValueError('preparation_partition')
    validated = _validate_preparation(repository_root=repository_root, review_file=review_file,
        expected_review_sha256=expected_review_sha256, expected_roots_sha256=expected_roots_sha256,
        expected_image_id=expected_image_id, actual_image=actual_image, output_dir=output_dir)
    if validated['budget']['group'] != 'large':
        raise ValueError('preparation_partition_group')
    index = int(partition_id[-2:]) - 1
    output = validated['output']
    output.mkdir()
    generated = {}

    def save(name, document):
        path = output / name
        write_json_exclusive(path, document)
        generated[name] = hashlib.sha256(read_metadata(path)).hexdigest()
        return generated[name]

    parent_scope = save('parent.scope.draft.json', validated['scope'])
    parent_budget = save('parent.budget.draft.json', validated['budget'])
    authority = dict(source_read_authorized=False, postgresql_authorized=False,
                     contract_frozen=False, ready_for_import=False)
    selected = validated['scope']['objects'][index]
    selection = dict(version=1, status='DRAFT_PARTITION_SELECTION_NOT_AUTHORIZED', **authority,
        partition_id=partition_id, parent_review_sha256=expected_review_sha256,
        parent_scope_sha256=parent_scope, parent_budget_sha256=parent_budget,
        source_object_id=selected['source_object_id'])
    selection_pin = save('partition.selection.draft.json', selection)
    bindings = {role: dict(path=str(output / name), sha256=pin) for role, name, pin in (
        ('parent_scope', 'parent.scope.draft.json', parent_scope),
        ('parent_budget', 'parent.budget.draft.json', parent_budget),
        ('partition_selection', 'partition.selection.draft.json', selection_pin))}
    scope = copy.deepcopy(validated['scope'])
    scope['objects'] = [selected]
    scope['bindings'].update({role: entry['sha256'] for role, entry in bindings.items()})
    budget = copy.deepcopy(validated['budget'])
    budget['objects'] = [budget['objects'][index]]
    request = copy.deepcopy(validated['request'])
    request['bindings'] = bindings
    save('scope.draft.json', scope)
    save('budget.draft.json', budget)
    save('request.draft.json', request)
    record = copy.deepcopy(validated['record'])
    record.update(status='DRAFT_PARTITION_METADATA_PREPARATION', parent_objects=10, parent_columns=235,
        objects=1, columns=len(selected['columns']), partition_id=partition_id,
        parent_review_sha256=expected_review_sha256, generated=generated)
    stage = output / '.preparation.incomplete'
    marker = output / 'preparation.json'
    write_json_exclusive(stage, record)
    for path, raw in validated['inputs'].items():
        if read_metadata(path) != raw:
            raise ValueError('preparation_input_changed')
    for name, pin in generated.items():
        if hashlib.sha256(read_metadata(output / name)).hexdigest() != pin:
            raise ValueError('preparation_generated_changed')
    if read_metadata(stage) != (canonical_json(record) + '\n').encode('utf-8'):
        raise ValueError('preparation_generated_changed')
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
    parser.add_argument('--partition-id', required=True)
    args = parser.parse_args()
    try:
        marker = prepare_partition_task(repository_root=args.repository_root, review_file=args.review,
            expected_review_sha256=args.review_sha256, expected_roots_sha256=args.roots_sha256,
            expected_image_id=args.image_id, actual_image=dict(image_id=args.actual_image_id,
                git_revision=args.git_revision, user=args.image_user, source_status=args.source_status),
            output_dir=args.output_dir, partition_id=args.partition_id)
        print(json.dumps(dict(status='DRAFT_PARTITION_METADATA_PREPARATION', marker=str(marker), real_execution_ready=False)))
        return 0
    except Exception:
        print(json.dumps(dict(status='PARTITION_PREPARATION_FAILED', real_execution_ready=False)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
