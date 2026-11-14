#!/usr/bin/env python3
"""Pre-launch Stage B closure check on host 32 (host-side, before docker create).

Proves from the REAL materialized documents that every path the product will
open inside the container resolves to digest-matching bytes through exactly
the mounts run-real.sh declares, and that publication destinations are fresh:

  request.json / approval / scope / budget / descriptor
      -> /data/var/snapshots/materialization/**        (ro bind of Stage A dir)
  absolute /metadata/** pins (incl. repository-relative preparation reads)
      -> $run/output/metadata/...                      (ro bind at /metadata)
  /data/var/run/** pins                              -> $run/output/...       (rw evidence)
  batch output + scratch                               -> executions/<attempt>/ (fresh)

Exit non-zero WITHOUT touching anything if any leg fails; because registration
happens first but container creation does not, a failure here consumes nothing
runnable — the attempt stays unconsumed until a candidate is created. This is
a runner sanity gate; it never replaces the product's own pin checks.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--materialization', required=True)
    ap.add_argument('--request-sha256', required=True)
    ap.add_argument('--approval-sha256', required=True)
    ap.add_argument('--roots-sha256', required=True)
    ap.add_argument('--run-output', required=True)
    ap.add_argument('--table', required=True)
    ap.add_argument('--snapshot-id', required=True)
    args = ap.parse_args()

    mat = Path(args.materialization)
    out = Path(args.run_output)
    table = Path(args.table)
    checked = set()

    def fail(msg: str):
        raise SystemExit(f'MOUNT_TABLE_INVALID: {msg}')

    if not re.fullmatch(r'[0-9a-f]{64}', args.request_sha256):
        fail('request pin format')
    request_file = mat / 'request.json'
    if not request_file.is_file() or sha(request_file) != args.request_sha256:
        fail('request pin mismatch')
    request = json.loads(request_file.read_text())
    if request['approval_sha256'] != args.approval_sha256:
        fail('request does not bind the operator approval pin')
    if request['roots_sha256'] != args.roots_sha256:
        fail('request does not bind the operator roots pin')
    if request['source_mode'] != 'project_snapshot' or request['lifecycle_seconds'] != 1800:
        fail('request mode/lifecycle')

    # Table maps container absolute paths to staged bytes under $run/output.
    rows = {}
    for line in table.read_text().splitlines():
        if line.startswith('#'):
            continue
        want, cp, sp = line.split('\t')
        rows[cp] = (want, sp)

    def local_for(container_path: str) -> Path:
        if container_path.startswith('/metadata/'):
            return out / 'metadata' / container_path[len('/metadata/'):]
        if container_path.startswith('/data/var/run/a/'):
            # Rehearsal layout: Stage A evidence mirrored under <out>/a when
            # checking the Stage B view (run-real.sh reuses one $run/output
            # tree; here it is a sibling subtree). Paths stay '..'-free.
            return out / 'a' / container_path[len('/data/var/run/a/'):]
        if container_path.startswith('/data/var/run/') and (out / 'a').is_dir():
            # Stage B view: Stage A evidence lives under <out>/a; the direct
            # path is reserved for Stage B's own outputs (never Stage A pins).
            mirror = out / 'a' / container_path[len('/data/var/run/'):]
            if mirror.exists():
                return mirror
        if container_path.startswith('/data/var/run/'):
            direct = out / container_path[len('/data/var/run/'):]
            if not direct.exists() and (out / 'a').is_dir():
                mirrored = out / 'a' / container_path[len('/data/var/run/'):]
                if mirrored.exists():
                    return mirrored
            return direct
        fail(f'container path outside declared closures: {container_path}')

    def expect_readable(container_path: str, want: str, how: str):
        p = local_for(container_path)
        if not p.is_file() or p.is_symlink():
            fail(f'{how}: missing staged file for {container_path}')
        if sha(p) != want:
            fail(f'{how}: digest drift for {container_path}')
        checked.add(how)

    # 1) request top-level bound inputs. Materialization-tree paths come from
    #    the ro Stage A mount; everything else must be staged by the table.
    for key, sk in (('roots', 'roots_sha256'), ('certificate', 'certificate_sha256'),
                    ('scope_file', 'scope_sha256'), ('budget_file', 'budget_sha256'),
                    ('approval_file', 'approval_sha256')):
        path, want = request[key], request[sk]
        if path.startswith('/data/var/snapshots/materialization/'):
            rel = path[len('/data/var/snapshots/materialization/'):]
            f = mat / rel
            if not f.is_file() or sha(f) != want:
                fail(f'request binding drift {key}')
            checked.add('request.' + key)
        else:
            expect_readable(path, want, 'request.' + key)

    # 2) partition bindings (descriptor + three drafts) and their transitive
    #    closure: descriptor -> preparation record + parent review; preparation
    #    -> its generated drafts; parent review -> 14 repository-relative pins
    #    resolved as <repository_root>/<relative> == /metadata/<relative>.
    for role, desc in request['bindings'].items():
        if desc['path'].startswith('/data/var/snapshots/materialization/'):
            fail('partition binding unexpectedly inside materialization')
        expect_readable(desc['path'], desc['sha256'], f'binding.{role}')
    descriptor = json.loads(local_for(request['bindings']['descriptor']['path']).read_text())
    for role in ('preparation', 'parent_review'):
        d = descriptor[role]
        expect_readable(d['path'], d['sha256'], f'descriptor.{role}')
    prep = json.loads(local_for(descriptor['preparation']['path']).read_text())
    base = str(Path(descriptor['preparation']['path']).parent)
    for name, pin in prep['generated'].items():
        expect_readable(base + '/' + name, pin, f'preparation.generated.{name}')
    parent_rel = Path(descriptor['parent_review']['path'])
    parent = json.loads(local_for(str(parent_rel)).read_text())
    if parent['status'] != 'METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE':
        fail('parent review status')
    roots_relative = parent['bindings']['roots']['path']
    if not str(parent_rel).startswith('/metadata/'):
        fail('parent review outside the repository metadata mount')
    # Repository-relative pins resolve under the mounted repository root,
    # derived lexically exactly like the product derives it from the bound
    # roots.yaml path (here: /metadata + '/' + relative).
    repository_root = '/metadata'
    if not str(parent_rel).startswith(repository_root + '/'):
        fail('repository root derivation')
    for role, b in parent['bindings'].items():
        repo_path = repository_root + '/' + b['path']
        expect_readable(repo_path, b['sha256'], f'parent.binding.{role}')
    checked.add('repository.root.derivation')

    # 3) publication destinations: fresh, distinct, under attempt execution dir.
    exec_dir = out / 'durable/executions'
    attempt = descriptor['attempt_id']
    if not re.fullmatch(r'real-p01-[0-9]{8}-[a-z]', attempt):
        fail(f'unexpected attempt id {attempt}')
    expected_prefix = f'/data/var/snapshots/executions/{attempt}/'
    for key in ('output', 'scratch_parent'):
        v = request[key]
        if not v.startswith(expected_prefix):
            fail(f'request {key} outside attempt execution dir')
        rel = v[len(expected_prefix):]
        local = exec_dir / attempt / rel
        if local.exists():
            fail(f'{key} destination already exists: {v}')
    checked.update(('destination.output', 'destination.scratch_parent'))

    # 4) snapshot identity chain (version dir itself is mounted by the runner
    #    from SNAPSHOT_HOST_ROOT; contents verified only by the product).
    cert = json.loads(local_for(request['certificate']).read_text())
    if cert['snapshot_id'] != request['snapshot_id'] or request['snapshot_id'] != args.snapshot_id:
        fail('snapshot id chain')
    members = [m for m in cert['members'] if m['path'] == request['relative_path']]
    if len(members) != 1 or members[0]['sha256'] != request['expected_sha256'] \
            or members[0]['size'] != request['expected_size']:
        fail('certificate member vs request')
    checked.add('snapshot.identity.chain')

    print(json.dumps({'status': 'MOUNT_TABLE_VERIFIED', 'snapshot_id': request['snapshot_id'],
                      'attempt_id': attempt, 'checked_legs': sorted(checked)}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
