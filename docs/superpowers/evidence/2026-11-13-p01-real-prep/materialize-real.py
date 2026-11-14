#!/usr/bin/env python3
"""Stage A worker: authorization-gated request materialization for p01 real run.

Runs inside the verified runtime image as uid 10001 with repository metadata
and the accepted run outputs mounted read-only. NO snapshot, NO NAS, NO
database is reachable in this container. Refuses before any write unless an
external authorization file binds the accepted task card SHA-256 and attempt.

Usage (inside container): python /materialize-real.py <image_id> <git_revision>
The host runner has already compared these arguments against docker inspect.
"""
import hashlib
import json
import sys
from pathlib import Path

IMAGE_ID = 'sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
GIT_REVISION = '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
CARD_SHA = '41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69'
REVIEW_SHA = 'a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d'
ATTEMPT = 'real-p01-20261113-a'
PARTITION = 'large-p01'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: materialize-real.py <image_id> <git_revision>')
    actual_image = {
        'image_id': sys.argv[1],
        'git_revision': sys.argv[2],
        'user': '10001:10001',
        'source_status': 'dirty',
    }
    if sys.argv[1] != IMAGE_ID or sys.argv[2] != GIT_REVISION:
        raise ValueError('runtime_identity')

    # Accepted card must be byte-exact and closed; we bind to it, never edit it.
    card_file = Path('/card/task-card.closed.json')
    if sha(card_file) != CARD_SHA:
        raise ValueError('task_card_identity')
    card = json.loads(card_file.read_text())
    if not (card['status'] == 'CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE'
            and card['attempt_id'] == ATTEMPT and card['partition_id'] == PARTITION
            and card['source_read_authorized'] is False
            and card['deadlines']['candidate_seconds'] == 1800
            and card['resources']['cpus'] == 0.5
            and card['resources']['memory_bytes'] == 805306368):
        raise ValueError('task_card_shape')

    # External human authorization gate. Absent or unbound => refuse BEFORE
    # any materialize call or write. The card itself can never enable this.
    auth_file = Path('/authorization/authorization.json')
    if not auth_file.is_file():
        raise ValueError('real_execution_closed')
    auth_raw = auth_file.read_bytes()
    auth = json.loads(auth_raw)
    if not (auth.get('version') == 1
            and auth.get('status') == 'AUTHORIZED_REAL_P01_SINGLE_ATTEMPT'
            and auth.get('attempt_id') == ATTEMPT
            and auth.get('task_card_sha256') == CARD_SHA
            and auth.get('one_attempt_only') is True
            and isinstance(auth.get('granted_by'), str) and auth.get('granted_by')):
        raise ValueError('authorization_binding')

    # Review input must be the accepted closed review bytes, staged by the
    # pin table at its recorded container path (rw evidence mount).
    review_file = Path('/data/var/run/review/review.json')
    if sha(review_file) != REVIEW_SHA:
        raise ValueError('review_identity')
    review = json.loads(review_file.read_text())
    if review['status'] != 'DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE' or review['missing'] != []:
        raise ValueError('review_not_closed')

    from xiangrugu_datamgmt.project_partition import materialize_project_partition_request
    from xiangrugu_datamgmt.snapshots import write_json_exclusive

    out_dir = Path('/data/var/snapshots/materialization')
    exec_dir = Path('/data/var/snapshots/executions') / ATTEMPT
    # Host pre-created exec_dir/{,scratch} owned by 10001; readonly_batch will
    # later require output.parent and scratch directories to exist.
    materialize_project_partition_request(
        review_file=review_file,
        expected_review_sha256=REVIEW_SHA,
        actual_image=actual_image,
        output_dir=out_dir,
        result_file=exec_dir / 'batch.staged.json',
        scratch_parent=exec_dir / 'scratch',
    )

    published = {}
    for name in ('request.json', 'approval.json', 'scope.json', 'budget.json'):
        path = out_dir / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('published_shape')
        published[name] = sha(path)
    request = json.loads((out_dir / 'request.json').read_text())
    if not (request['source_mode'] == 'project_snapshot' and request['lifecycle_seconds'] == 1800
            and request['image_id'] == IMAGE_ID and request['git_revision'] == GIT_REVISION
            and request['snapshot_id'] == card['snapshot']['snapshot_id']
            and request['expected_size'] == card['snapshot']['member']['size']
            and request['expected_sha256'] == card['snapshot']['member']['sha256']
            and request['manifest_sha256'] == card['snapshot']['manifest_sha256']
            and request['rule_id'] == card['source_object']['rule_id']):
        raise ValueError('request_vs_card')

    receipt = out_dir / 'materialize-receipt.json'
    write_json_exclusive(receipt, {
        'version': 1,
        'status': 'REAL_REQUEST_MATERIALIZED_UNDER_AUTHORIZATION',
        'attempt_id': ATTEMPT,
        'partition_id': PARTITION,
        'task_card_sha256': CARD_SHA,
        'closed_review_sha256': REVIEW_SHA,
        'authorization_sha256': sha(auth_file),
        'granted_by': auth['granted_by'],
        'published_sha256': published,
        'request_output': request['output'],
        'request_scratch_parent': request['scratch_parent'],
        'real_source_read': False,
        'source_bytes_read': False,
        'postgresql_connected': False,
        'ready_for_import': False,
    })
    print('MATERIALIZE_REAL_REQUEST_OK', json.dumps(published, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
