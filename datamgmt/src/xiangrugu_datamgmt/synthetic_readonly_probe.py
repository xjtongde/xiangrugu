"""Fixed artificial probe for the approved read-only entry, never real inputs."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal

import yaml

from .batch_execution import read_metadata, _json
from .readonly_batch import execute_readonly_batch
from .snapshots import digest, write_json_exclusive
from .sqlite_values import SQLiteValueLimits
from .unordered_values import UnorderedLimits
from .synthetic_batch_probe import build_fixture


def prepare(root, *, image_id, git_revision, fixture_mount=None):
    root = Path(root)
    fixture = root / 'fixture'
    fixture.mkdir()
    request = build_fixture(fixture, image_id=image_id, git_revision=git_revision)
    mount = fixture if fixture_mount is None else Path(fixture_mount)
    config = yaml.safe_load(Path(request['roots']).read_text())
    config['roots']['usedata']['path'] = str(mount / 'authority-never-read')
    config['deployment']['source_snapshots'].update(container_root=str(mount / 'snapshots'),
                                                   container_evidence_root=str(root))
    roots_path = fixture / 'readonly-roots.yaml'
    roots_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    request['roots'] = str(mount / roots_path.name)
    request['roots_sha256'] = hashlib.sha256(roots_path.read_bytes()).hexdigest()
    certificate = _json(read_metadata(Path(request['certificate'])))
    certificate['source_path'] = config['roots']['usedata']['path']
    scope = _json(read_metadata(Path(request['scope_file'])))
    descriptor = fixture / 'descriptor.json'
    write_json_exclusive(descriptor, dict(version=1, artificial_only=True, fixture='fixed-two-table-v1'))
    descriptor_hash = hashlib.sha256(descriptor.read_bytes()).hexdigest()
    request['bindings'] = {'descriptor': dict(path=str(mount / descriptor.name), sha256=descriptor_hash)}
    scope['bindings'] = {'descriptor': descriptor_hash}
    budgets = []
    for obj, row_cap in zip(scope['objects'], (10, 1), strict=True):
        budgets.append(dict(source_object_id=obj['source_object_id'],
            read_limits=asdict(SQLiteValueLimits(max_file_bytes=1048576, max_columns=64,
                max_rows=row_cap, max_cells=50000, max_value_bytes=8388608,
                max_vm_steps=20000000, max_seconds=60)),
            sort_limits=asdict(UnorderedLimits(max_rows=row_cap, max_columns=64,
                max_row_bytes=1048576, max_stream_bytes=8388608, chunk_bytes=2097152,
                max_temp_bytes=67108864, max_seconds=60))))
    budget = dict(version=2, group='small', max_seconds=60, objects=budgets)
    for key, document in (('certificate', certificate), ('scope_file', scope), ('budget_file', budget)):
        path = fixture / ('readonly-'+key+'.json')
        write_json_exclusive(path, document)
        request[key] = str(mount / path.name)
        hash_key = {'certificate': 'certificate_sha256', 'scope_file': 'scope_sha256',
                    'budget_file': 'budget_sha256'}[key]
        request[hash_key] = hashlib.sha256(path.read_bytes()).hexdigest()
    request.pop('synthetic_root')
    request.pop('synthetic_only')
    request.update(source_mode='artificial', lifecycle_seconds=1800, output=str(root / 'batch.json'),
                   scratch_parent=str(root / 'scratch'))
    (root / 'scratch').mkdir(exist_ok=True)
    approval = dict(version=1, status='APPROVED_READONLY_BATCH', source_mode='artificial',
        source_read_authorized=False, synthetic_data_authorized=True,
        stationary_readonly_window=True, postgresql_authorized=False, ready_for_import=False,
        request_sha256=digest(request))
    approval_path = fixture / 'approval.json'
    write_json_exclusive(approval_path, approval)
    request.update(approval_file=str(mount / approval_path.name),
                   approval_sha256=hashlib.sha256(approval_path.read_bytes()).hexdigest())
    write_json_exclusive(fixture / 'readonly-request.json', request)
    return request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'execute'))
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--git-revision', required=True)
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if args.mode == 'prepare':
            prepare(Path('/data/var/run'), fixture_mount=Path('/data/var/input'),
                    image_id=args.image_id, git_revision=args.git_revision)
        else:
            # No arbitrary request/source path and no real mode are exposed.
            request = _json(read_metadata(Path('/data/var/input/readonly-request.json')))
            if (request['source_mode'] != 'artificial' or request['image_id'] != args.image_id
                    or request['git_revision'] != args.git_revision):
                raise ValueError('probe_identity')
            execute_readonly_batch(request, cancelled=lambda: stopped)
        print(json.dumps(dict(status='ARTIFICIAL_READONLY_PROBE_COMPLETED', mode=args.mode)))
        return 0
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) and str(error) in {
            'readonly_mount', 'approval', 'probe_identity', 'cancelled'} else 'entry_failed'
        print(json.dumps(dict(status='ARTIFICIAL_READONLY_PROBE_FAILED', reason=reason)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
