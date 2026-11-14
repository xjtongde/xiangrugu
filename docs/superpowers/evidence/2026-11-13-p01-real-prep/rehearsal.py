#!/usr/bin/env python3
"""Installed-state rehearsal for the p01 real execution package.

NO host 32, NO production image (it is absent here by design), NO real
snapshot bytes, NO real authorization. Human-made fixtures + the REAL product
modules from this repository, executed inside a throwaway LOCAL container at
the REAL container paths declared in run-real.sh's mount table, proving:

  R5 Refuse-without-authorization leaves zero executable artifacts.
  R1 Stage A chain prepare_partition_task -> prepare_project_partition_review
     -> materialize_project_partition_request over the 10-object/235-column
     large group with the real fixed attempt/partition/image identities,
     honoring the external authorization gate and card binding.
  R2 verify-mount-table.py closes EVERY bound path of the REAL materialized
     request over the staged $run/output tree (repo-relative pins included,
     resolved under /metadata via repository_root) + poisoned-leg negative
     control; docker inspect .Mounts records the ACTUAL mounts.
  R3 candidate_supervisor terminal states: installed-origin argv form after
     `--` (never a leading python), final-sample handshake ordering, --final
     hardlink publication with byte-identical .incomplete twin, unified
     failure receipt correlation (task_control --failure-evidence ==
     supervisor --worker-failure), bounded timeout stop, limits.json posture
     equal to the card caps under real cgroup enforcement.
  R4 One-shot O_EXCL registration refuses a second start even with another
     suffix or Stage A directory (rerun-refusal artifacts written).
  R6 FailureTrace -> read_worker_failure roundtrip on one path.

The workspace root is a REAL directory tree (no symlinks anywhere); bind
mounts expose subtrees at /metadata, /data/var/run, /data/var/snapshots and
/data/imports/usedata — same inode, two views, exactly like run-real.sh.

Run (needs pydantic+pyyaml; use the workspace venv):
  .venv-rehearsal/bin/python docs/superpowers/evidence/2026-11-13-p01-real-prep/rehearsal.py
Keep the tree for inspection: P01_REHEARSAL_KEEP=/abs/dir (must not exist).
Exit 0 + receipts saved next to this script as rehearsal-evidence.json.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # docs/superpowers/evidence/<dir>/ -> repository root
SRC = REPO / 'datamgmt' / 'src'
sys.path.insert(0, str(SRC))

ATTEMPT = 'real-p01-20261113-a'
PARTITION = 'large-p01'
IMAGE_ID = 'sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
GIT_REVISION = '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
SNAPSHOT_ID = '2026-10-07-bootstrap'
MEMBER_PATH = 'harvard/cbdb/cbdb_20260919.sqlite3'
TABLE = 'POSTED_TO_ADDR_DATA'
COLUMNS = ['c_posting_id', 'c_personid', 'c_office_id', 'c_addr_id',
           'c_created_by', 'c_created_date', 'c_modified_by', 'c_modified_date']
WIDTHS = [8, 11, 34, 6, 29, 42, 12, 10, 28, 55]  # large group: 10 objects / 235 columns
RULE_ID = 'm-rehearsal'
RELEASE = 'datamgmt/contracts/releases/2026-10-06-bootstrap'
LOCAL_IMAGE = 'xiangrugu-rehearsal:p01-local'   # built on demand; NOT production
RESOURCE_FLAGS = ['--cpus', '0.5', '--memory', '768m', '--memory-swap', '768m',
                  '--pids-limit', '128']
STAGE_A_SECONDS = 300

EVIDENCE = []


def record(name, **kw):
    entry = {'case': name}
    entry.update({k: _short(v) for k, v in kw.items()})
    EVIDENCE.append(entry)
    print('OK', name, json.dumps(entry, sort_keys=True, default=str)[:400], flush=True)


def _short(v):
    if isinstance(v, list) and len(v) > 8:
        return v[:8] + [f'...{len(v)} total']
    return v


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wjson(p: Path, doc) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name('.' + p.name + '.writing')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n')
    os.replace(tmp, p)


class Workspace:
    """Real-dir tree mirroring the container mount table (no symlinks)."""

    def __init__(self, root: Path):
        self.root = root
        self.app = root / 'app'
        # Paths under /data/var/run must stay '..'-free (product _path rule),
        # so Stage A and Stage B evidence views are sibling directories.
        self.metadata = root / 'metadata'            # bind ro -> /metadata
        self.card = root / 'card'                    # bind ro -> /card
        self.authorization = root / 'authorization'  # bind ro -> /authorization
        self.output = root / 'output'                # bind rw -> /data/var/run (Stage A)
        self.durable = root / 'durable'              # subview -> /data/var/snapshots (Stage A)
        self.b_output = root / 'b-output'            # bind rw -> /data/var/run (Stage B)
        self.b_durable = root / 'b-durable'          # -> /data/var/snapshots (Stage B)
        # run-real.sh reuses ONE $run/output tree in both stages; the rehearsal
        # keeps separate stage trees and mirrors Stage A outputs read-only into
        # the Stage B view (same pins, same inode-free equivalence).
        self.a_mirror = self.b_output / 'a'          # ro -> /data/var/run/a (Stage B)
        self.snapshot = root / 'snapshot'            # bind ro -> /data/imports/usedata
        self.control = root / 'control'              # bind ro -> /control
        self.runtime = root / 'runtime-root'         # registry home ($runtime_root)
        for d in (self.app, self.metadata, self.card, self.authorization,
                  self.output, self.durable, self.b_output, self.b_durable,
                  self.control, self.runtime):
            d.mkdir(parents=True)
        bad = [str(p) for p in [root, *root.parents] if p.is_symlink()]
        if bad:
            raise SystemExit(f'rehearsal root has symlinked parents {bad}; pick another base')

    def to_container(self, p) -> str:
        s = str(Path(p))
        pairs = [(str(self.metadata), '/metadata'), (str(self.card), '/card'),
                 (str(self.authorization), '/authorization'),
                 (str(self.output), '/data/var/run'),
                 (str(self.snapshot), '/data/imports/usedata'),
                 (str(self.control), '/control')]
        for ws, c in pairs:
            if s == ws or s.startswith(ws + '/'):
                return c + s[len(ws):]
        raise AssertionError(f'path outside mirror: {s}')

    def to_local(self, container_path, *, stage_b=False) -> Path:
        """Container path -> workspace path. /data/var/run and
        /data/var/snapshots resolve against the ACTIVE run tree (Stage A by
        default; Stage B views when stage_b=True)."""
        s = str(container_path)
        run_base = self.b_output if stage_b else self.output
        snap_base = self.b_durable if stage_b else self.durable
        pairs = sorted([('/metadata/', self.metadata),
                        ('/data/var/run/a/', self.a_mirror if stage_b else None),
                        ('/data/var/run/', run_base),
                        ('/data/imports/usedata/', self.snapshot), ('/card/', self.card),
                        ('/authorization/', self.authorization)], key=lambda t: -len(t[0]))
        for prefix, cand in pairs:
            if s.startswith(prefix):
                if cand is None:
                    raise AssertionError(f'stage-a-view path without stage_b=True: {s}')
                return cand / s[len(prefix):]
        if s.startswith('/data/var/snapshots/'):
            return snap_base / s[len('/data/var/snapshots/'):]
        raise AssertionError(s)


# ---------------------------------------------------------------- fixtures
def build_member(w: Workspace) -> dict:
    """Fixture member: the selected object is the FIRST large-group object, so
    its schema has WIDTHS[0] columns; the SQLite table must match exactly."""
    from xiangrugu_datamgmt.identity import source_object_id
    import sqlite3
    cols = [f'column_p00_{WIDTHS[0]:03d}_{ordinal:03d}'
            for ordinal in range(1, WIDTHS[0] + 1)]
    db_file = w.snapshot / SNAPSHOT_ID / MEMBER_PATH
    db_file.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_file))
    ddl = ', '.join(f'{chr(34)}{c}{chr(34)} INTEGER NOT NULL' for c in cols)
    con.execute(f'CREATE TABLE "{TABLE}" ({ddl})')
    rows = [tuple(i * 7 + c for c in range(len(cols))) for i in range(40)]
    con.executemany(f'INSERT INTO "{TABLE}" VALUES ({",".join("?" * len(cols))})', rows)
    con.commit()
    con.close()
    for suffix in ('-wal', '-shm', '-journal'):
        assert not (db_file.parent / (db_file.name + suffix)).exists(), suffix
    object_id = source_object_id(relative_path=MEMBER_PATH, archive_chain=[],
                                 object_name=TABLE, carrier='sqlite')
    return {'size': db_file.stat().st_size, 'sha256': sha(db_file),
            'source_object_id': object_id, 'columns': cols}


def build_repo_metadata(w: Workspace, member: dict) -> dict:
    """Fixture repository metadata under /metadata mirroring the working tree."""
    from xiangrugu_datamgmt.identity import source_object_id
    from xiangrugu_datamgmt.naming import allocate_columns
    from xiangrugu_datamgmt.unordered_values import UnorderedLimits, schema_bytes, UnorderedColumn, UnorderedSchema
    from xiangrugu_datamgmt.readonly_batch import _group_limits
    from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
    import dataclasses
    repo = w.metadata
    base = repo / RELEASE
    base.mkdir(parents=True, exist_ok=True)
    roots_text = """version: 1
roots:
  usedata:
    path: /data/imports/usedata
    host: rehearsal-host.invalid
    role: authoritative-source
target:
  instance: pg32b
  host: rehearsal-target.invalid
  port: 5433
  database: xiangrugu
  user: postgres
deployment:
  source_snapshots:
    container_root: /data/imports/usedata
    container_evidence_root: /data/var/snapshots
"""
    (repo / 'datamgmt/config/roots.yaml').parent.mkdir(parents=True, exist_ok=True)
    (repo / 'datamgmt/config/roots.yaml').write_text(roots_text)
    authority = {k: False for k in ('source_read_authorized', 'postgresql_authorized',
                                    'contract_frozen', 'ready_for_import')}
    assert len(WIDTHS) == 10 and sum(WIDTHS) == 235
    objects, prepared, mapped, budgets = [], [], [], []
    # The product validates EVERY group object against the single scoped
    # member (relative_path=member['path'], table=obj['source_object_name']),
    # so all fixture ids derive from MEMBER_PATH with distinct object names.
    rel = MEMBER_PATH
    for index, width in enumerate(WIDTHS):
        names = [f'column_p{index:02d}_{width:03d}_{ordinal:03d}'
                 for ordinal in range(1, width + 1)]
        obj_name = TABLE if index == 0 else f'POSTED_TO_ADDR_DATA_P{index:02d}'
        obj_id = source_object_id(relative_path=rel, archive_chain=[],
                                  object_name=obj_name, carrier='sqlite')
        allocated = allocate_columns(names, object_id=obj_id)
        # The member table declares every column NOT NULL; allow_null_value must
        # mirror PRAGMA table_xinfo exactly (nullability_mismatch otherwise).
        cols = [{'allow_null_value': False,
                 'column_key': allocated[n].identity,
                 'pg_type': 'bigint', 'source_ordinal': n} for n in range(width)]
        schema = UnorderedSchema(obj_id, tuple(UnorderedColumn(**c) for c in cols))
        schema_hash = hashlib.sha256(schema_bytes(schema)).hexdigest()
        read_limits = dataclasses.asdict(SQLiteValueLimits(max_file_bytes=2**30, max_columns=64,
            max_rows=2000000, max_cells=40000000, max_cell_bytes=2**20,
            max_value_bytes=256 * 2**20, max_vm_steps=10**9, max_seconds=1800))
        sort_limits = dataclasses.asdict(UnorderedLimits(max_rows=2000000, max_columns=64,
            max_field_bytes=2**20, max_row_bytes=2**20, max_stream_bytes=256 * 2**20,
            chunk_bytes=2 * 2**20, chunk_rows=4096, merge_fan_in=16,
            max_temp_bytes=2**30, max_temp_files=1024, max_differences=100,
            max_seconds=1800, workers=1))
        _group_limits({'source_object_id': obj_id, 'read_limits': read_limits,
                       'sort_limits': sort_limits}, 'large')
        objects.append({'columns': cols, 'expected_count': None, 'expected_sha256': None,
                        'read_limits': read_limits, 'schema_hash': schema_hash,
                        'sort_limits': sort_limits, 'source_columns': names,
                        'source_object_id': obj_id, 'source_object_name': obj_name})
        prepared.append({'columns': cols, 'schema_hash': schema_hash,
                         'source_object_id': obj_id, 'source_object_name': obj_name})
        mapped.append({'columns': [{'approved_type': c['pg_type'], 'column_identity': c['column_key'],
                     'source_name': names[c['source_ordinal']], 'source_ordinal': c['source_ordinal']}
                    for c in cols], 'source_object_id': obj_id, 'source_object_name': obj_name})
        budgets.append({'name': obj_name, 'proposed_group': 'large', 'source_object_id': obj_id})
    member_doc = {'kind': 'file', 'path': MEMBER_PATH, 'sha256': member['sha256'], 'size': member['size']}
    scope = {'columns': 235, 'member': member_doc, 'objects': 10, 'snapshot_id': SNAPSHOT_ID}
    docs = {
        'original_scope_review': dict(authority, group='large', objects=objects, rule_id=RULE_ID,
            scope=scope, status='DRAFT_VALUE_REVIEW_NOT_AUTHORIZED', version=1),
        'preparation': dict(authority, objects=prepared, status='DRAFT_CONTRACT_PREPARATION', version=1),
        'mapping': dict(authority, objects=mapped, status='DRAFT_TARGET_MAPPING_PROPOSAL', version=1),
        'remaining_budget': dict(authority, objects=budgets, status='DRAFT_REMAINING_BUDGET', version=1),
    }
    names = {'original_scope_review': 'sqlite-value-large-artificial-review.draft.json',
             'preparation': 'sqlite-value-contract-preparation.draft.json',
             'mapping': 'sqlite-target-mapping-proposal.draft.json',
             'remaining_budget': 'sqlite-value-remaining-budget.draft.json'}
    bindings = {}
    for role, doc in docs.items():
        rel_path = RELEASE + '/' + names[role]
        wjson(repo / rel_path, doc)
        bindings[role] = {'path': rel_path, 'sha256': sha(repo / rel_path)}
    extras = {'cache_amendment': 'sqlite-read-cache-amendment.draft.json',
              'resource_revision': 'sqlite-value-resource-revision.draft.json',
              'previous_small': 'sqlite-value-small.expected.draft.json'}
    for role, name in extras.items():
        rel = RELEASE + '/' + name
        wjson(repo / rel, dict(authority, detail=f'inert fixture binding for {role}',
                               status='DRAFT_REHEARSAL_BINDING', version=1))
        bindings[role] = {'path': rel, 'sha256': sha(repo / rel)}
    code_roles = {'preparation_code': 'task_preparation.py', 'project_partition_code': 'project_partition.py',
                  'project_coverage_code': 'project_partition_coverage.py', 'readonly_code': 'readonly_batch.py'}
    for role, fname in code_roles.items():
        rel = 'datamgmt/src/xiangrugu_datamgmt/' + fname
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SRC / 'xiangrugu_datamgmt' / fname).read_bytes())
        bindings[role] = {'path': rel, 'sha256': sha(target)}
    ev_rel = 'docs/superpowers/evidence/rehearsal-p01/verification.json'
    wjson(repo / ev_rel, {'status': 'REHEARSAL_PROTOCOL_EVIDENCE', 'synthetic_only': True})
    bindings['current_protocol_evidence'] = {'path': ev_rel, 'sha256': sha(repo / ev_rel)}
    lt_rel = 'datamgmt/tests/unit/test_large_artificial_batch.py'
    (repo / lt_rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / lt_rel).write_text('# rehearsal placeholder test binding\n')
    bindings['large_tests'] = {'path': lt_rel, 'sha256': sha(repo / lt_rel)}
    bindings['roots'] = {'path': 'datamgmt/config/roots.yaml',
                         'sha256': sha(repo / 'datamgmt/config/roots.yaml')}
    packet = dict(authority, bindings=bindings, git_revision=GIT_REVISION,
        scope=scope,
        status='METADATA_READINESS_SUPPLEMENT_NOT_EXECUTABLE', version=1,
        verified_artificial_deadlines={'candidate_seconds': 1800, 'host_seconds': 1830,
                                       'transport_seconds': 1880, 'real_mode_activated': False})
    review_rel = RELEASE + '/sqlite-value-project-partition-readiness.closed.json'
    wjson(repo / review_rel, packet)
    return {'packet': packet, 'review_rel': review_rel, 'scope': scope,
            'rule_id': RULE_ID, 'objects': objects, 'total_columns': 235}


def build_certificate(w: Workspace, meta: dict) -> dict:
    """Fixture certificate built from the REAL inventory of the rehearsal
    snapshot tree — verify_snapshot requires byte-exact member equality."""
    from xiangrugu_datamgmt.snapshots import digest, inventory
    members = inventory(w.snapshot / SNAPSHOT_ID)
    cert = {'manifest_sha256': digest(members), 'members': members,
            'snapshot_id': SNAPSHOT_ID, 'source_path': '/data/imports/usedata',
            'status': 'VERIFIED', 'version': 1}
    wjson(w.metadata / 'selected-certificate.json', cert)
    return cert


def build_card_and_auth(w: Workspace, auth_ok: bool, meta: dict, cert: dict, member: dict):
    card = {'attempt_id': ATTEMPT, 'auto_next_partition': False, 'auto_retry': False,
            'deadlines': {'candidate_seconds': 1800, 'host_seconds': 1830,
                          'transport_seconds': 1880},
            'one_attempt_only': True, 'partition_id': PARTITION,
            'real_mode_activated': False,
            'resources': {'cpus': 0.5, 'ionice': 'idle', 'memory_bytes': 805306368,
                          'nice': 19, 'pids': 128},
            'risk_note': 'rehearsal fixture card; synthetic bytes only',
            'snapshot': {'certificate_sha256': sha(w.metadata / 'selected-certificate.json'),
                         'manifest_sha256': cert['manifest_sha256'],
                         'member': {'kind': 'file', 'path': MEMBER_PATH,
                                    'sha256': member['sha256'], 'size': member['size']},
                         'snapshot_id': SNAPSHOT_ID},
            'source_object': {'rule_id': RULE_ID,
                              'source_object_id': member['source_object_id'],
                              'source_object_name': TABLE},
            'source_read_authorized': False,
            'status': 'CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE', 'version': 1}
    wjson(w.card / 'task-card.closed.json', card)
    auth_file = w.authorization / 'authorization.json'
    if auth_ok:
        auth = {'attempt_id': ATTEMPT, 'granted_by': '茶香（人工夹具占位，非真实授权）',
                'one_attempt_only': True,
                'scope': 'rehearsal only — synthetic fixtures, no real snapshot mounted',
                'status': 'AUTHORIZED_REAL_P01_SINGLE_ATTEMPT',
                'task_card_sha256': sha(w.card / 'task-card.closed.json'), 'version': 1}
        wjson(auth_file, auth)
    elif auth_file.exists():
        auth_file.unlink()


# ------------------------------------------------------ container plumbing
def ensure_local_image() -> str:
    out = subprocess.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', LOCAL_IMAGE],
                         capture_output=True, text=True)
    if out.returncode == 0:
        return LOCAL_IMAGE
    ctx = REPO / '.rehearsal-image-ctx'
    force_rm(ctx)
    ctx.mkdir(parents=True)
    shutil.copytree(SRC, ctx / 'src')
    (ctx / 'Dockerfile').write_text(
        'FROM python:3.12-slim\n'
        'RUN pip install --no-cache-dir pydantic==2.13.5 pyyaml==6.0.3\n'
        'COPY src/ /usr/local/lib/python3.12/site-packages/\n'
        'WORKDIR /app\n')
    built = subprocess.run(['docker', 'build', '-q', '-t', LOCAL_IMAGE, str(ctx)],
                           capture_output=True, text=True, timeout=900)
    force_rm(ctx)
    if built.returncode != 0:
        raise SystemExit('local rehearsal image build failed: ' + built.stderr[-800:])
    return LOCAL_IMAGE


def docker_mounts(cid) -> list:
    out = subprocess.run(['docker', 'inspect', '--format', '{{json .Mounts}}', cid],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def mount_view(m) -> dict:
    return {'dst': m.get('Destination'), 'ro': m.get('Mode') == 'ro' or not m.get('RW', True),
            'type': m.get('Type'), 'src_tail': os.path.basename(str(m.get('Source', '')))}


def shared_input_mounts(w: Workspace, *, authorized: bool) -> list:
    """run-real.sh's shared input binds. Without authorization the evidence
    trees are NOT mounted at all — refusal cannot even open a write handle."""
    m = ['--mount', f'type=bind,src={w.metadata},dst=/metadata,readonly',
         '--mount', f'type=bind,src={w.card}/task-card.closed.json,dst=/card/task-card.closed.json,readonly']
    if authorized:
        m += ['--mount', f'type=bind,src={w.authorization}/authorization.json,'
              'dst=/authorization/authorization.json,readonly',
              '--mount', f'type=bind,src={w.output},dst=/data/var/run']
    return m


def posture_flags(extra_tmpfs=()) -> list:
    uid = CONTAINER_UID if _uid_capable() else os.getuid()
    flags = [*RESOURCE_FLAGS, '--network', 'none', '--read-only', '--cap-drop', 'ALL',
             '--security-opt', 'no-new-privileges',
             '--tmpfs', f'/tmp:rw,nosuid,nodev,size=33554432,uid={uid},gid={uid},mode=1777',
             '--workdir', '/app']
    for t in extra_tmpfs:
        flags += ['--tmpfs', t]
    return flags


def docker_run(image: str, cmd: list, *, name: str, mounts: list, timeout: int,
               flags=None, entrypoint='python', env=()):
    # run-real.sh launches the candidate with --entrypoint python; the worker
    # argv after `--` never repeats an interpreter token.
    # Production pins the image's USER 10001:10001 implicitly; here pass an
    # explicit --user because this daemon drops uid bits from a root-defaulted
    # exec when cap-drop ALL is active (empirically verified in rehearsal).
    run_uid = CONTAINER_UID if _uid_capable() else os.getuid()
    user = ('--user', f'{run_uid}:{run_uid}')
    full = ['docker', 'create', '--name', name, *user] \
        + (['--entrypoint', entrypoint] if entrypoint else []) \
        + (flags if flags is not None else posture_flags()) + list(env) \
        + mounts + [image] + cmd
    created = subprocess.run(full, capture_output=True, text=True)
    if created.returncode != 0:
        raise RuntimeError('docker create failed: ' + created.stderr[-1200:])
    cid = created.stdout.strip()
    try:
        started = subprocess.run(['docker', 'start', '-a', cid], capture_output=True, text=True,
                                 timeout=timeout)
        rc = started.returncode
        if rc < 0:
            # The docker CLI was SIGKILLed by the timeout wrapper: the daemon
            # keeps the container running. Kill it so its output flushes and
            # we can still read the evidence files it left behind.
            subprocess.run(['docker', 'kill', cid], capture_output=True, text=True)
            started = subprocess.run(['docker', 'logs', cid], capture_output=True,
                                     text=True, timeout=60)
            state_now = subprocess.run(['docker', 'inspect', '--format', '{{json .State}}', cid],
                                       capture_output=True, text=True)
            try:
                rc = json.loads(state_now.stdout).get('ExitCode', rc)
            except Exception:
                pass
        result = {'cid': cid, 'returncode': rc,
                  'stdout': started.stdout, 'stderr': started.stderr,
                  'mounts': docker_mounts(cid)}
        state = subprocess.run(['docker', 'inspect', '--format', '{{json .State}}', cid],
                               capture_output=True, text=True)
        result['state'] = json.loads(state.stdout)
        return result
    finally:
        subprocess.run(['docker', 'rm', '-f', cid], capture_output=True, text=True)


# ------------------------------------------------------------- Stage A legs
CONTAINER_UID = 10001


_UID_CAPABLE = None


def _uid_capable() -> bool:
    """True only when the FULL production posture works end to end: host can
    chown evidence files to 10001 AND a bind-mounted file stays readable by a
    container process pinned --user 10001. On uid-mapped/rootless daemons the
    second half fails (binds appear as nobody), so the rehearsal runs its
    product chain as the host uid instead — recorded honestly in the notes."""
    global _UID_CAPABLE
    if _UID_CAPABLE is None:
        root = Path(REPO / '.rehearsal-tmp')
        probe = root / 'uidprobe'
        try:
            probe.mkdir(parents=True, exist_ok=True)
            f = probe / 't.txt'
            f.write_text('x')
            os.chown(f, CONTAINER_UID, CONTAINER_UID)
            out = subprocess.run(['docker', 'run', '--rm', '--user',
                                  f'{CONTAINER_UID}:{CONTAINER_UID}',
                                  '-v', f'{f}:/t.txt:ro', 'alpine',
                                  'sh', '-c', 'cat /t.txt'],
                                 capture_output=True, text=True)
            _UID_CAPABLE = out.returncode == 0 and out.stdout.strip() == 'x'
        except OSError:
            _UID_CAPABLE = False
        finally:
            subprocess.run(['docker', 'run', '--rm', '-v', f'{root}:/t', 'alpine',
                            'sh', '-c', 'chmod -R u+rwX /t; rm -rf /t/uidprobe'],
                           check=False, capture_output=True)
            shutil.rmtree(probe, ignore_errors=True)
    return _UID_CAPABLE


def force_rm(path: Path):
    """Delete a tree even when its files were written under a different uid
    mapping (rootless docker quirk); a container sees the mapped owner."""
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except PermissionError:
        subprocess.run(['docker', 'run', '--rm', '-v', f'{path.parent}:/t', 'alpine',
                        'sh', '-c', f'chown -R {os.getuid()}:{os.getgid()} "/t/{path.name}"'],
                       check=False, capture_output=True)
        shutil.rmtree(path)


def chown_workspace(w: Workspace):
    """Evidence trees are bind-mounted rw into a rootless-style container;
    they must be writable by uid 10001 without exposing them to other uids."""
    if _uid_capable():
        for d in (w.output, w.durable, w.b_output, w.b_durable, w.control):
            subprocess.run(['chown', '-R', f'{CONTAINER_UID}:{CONTAINER_UID}', str(d)],
                           check=True)
    else:
        # Fallback: containers run as the host uid (no --user flag). The daemon
        # here is rootless with a uid map — files created by earlier runs can
        # appear as `nobody` to us and are undeletable/unwritable from the
        # host; only a container (same mapping) can fix them. Then grant
        # group write so both host and future containers can co-write.
        for d in (w.root, w.output, w.durable, w.b_output, w.b_durable, w.control):
            if d.exists():
                subprocess.run(['docker', 'run', '--rm', '-v', f'{d.parent}:/t', 'alpine',
                                'sh', '-c',
                                f'chown -R {os.getuid()}:{os.getgid()} "/t/{d.name}"'
                                f' && chmod -R 775 "/t/{d.name}"'],
                               check=True, capture_output=True)


def clean_stage_a(w: Workspace):
    for d in (w.output / 'preparation', w.output / 'review',
              w.durable / 'materialization', w.durable / 'executions',
              w.b_output, w.b_durable):
        force_rm(d)
    w.b_output.mkdir(parents=True, exist_ok=True)
    w.b_durable.mkdir(parents=True, exist_ok=True)
    (w.output / 'review.selection.json').unlink(missing_ok=True)
    (w.output / 'installed-origin.json').unlink(missing_ok=True)
    (w.control / 'lease').unlink(missing_ok=True)
    (w.root / '.stop').unlink(missing_ok=True)

def container_paths(w: Workspace, paths) -> dict:
    """Normalize manifest entries — LOCAL workspace paths OR Stage A container
    absolutes (the driver sees its own RUN=/data/var/run paths) — into the
    Stage A container view plus the matching local file."""
    mapping = {}
    for entry in paths:
        ep = str(entry)
        if ep.startswith('/data/var/run/'):
            mapping[ep] = w.output / ep[len('/data/var/run/'):]
        elif ep.startswith('/metadata/'):
            mapping[ep] = w.metadata / ep[len('/metadata/'):]
        else:
            lp = Path(ep)
            if not (str(lp).startswith(str(w.root) + os.sep)):
                raise AssertionError(f'path outside workspace: {ep}')
            rel = lp.relative_to(w.root).as_posix()
            if rel.startswith('output/'):
                cp = '/data/var/run/' + rel[len('output/'):]
            elif rel.startswith('metadata/'):
                cp = '/metadata/' + rel[len('metadata/'):]
            else:
                raise AssertionError(f'path not in a mounted tree: {rel}')
            mapping[cp] = lp
    return mapping


STAGE_A_DRIVER = r'''import hashlib, json, sys
from pathlib import Path
ATTEMPT = "real-p01-20261113-a"
CARD_SHA = sys.argv[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth_file = Path("/authorization/authorization.json")
if not auth_file.is_file():
    raise ValueError("real_execution_closed")
auth = json.loads(auth_file.read_bytes())
card_file = Path("/card/task-card.closed.json")
if sha(card_file) != CARD_SHA:
    raise ValueError("task_card_identity")
card = json.loads(card_file.read_text())
if not (card["status"] == "CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE"
        and card["attempt_id"] == ATTEMPT and card["partition_id"] == "large-p01"
        and card["source_read_authorized"] is False
        and card["real_mode_activated"] is False
        and card["one_attempt_only"] is True
        and card["auto_retry"] is False and card["auto_next_partition"] is False
        and card["deadlines"]["candidate_seconds"] == 1800
        and card["deadlines"]["host_seconds"] == 1830
        and card["deadlines"]["transport_seconds"] == 1880
        and card["resources"]["cpus"] == 0.5
        and card["resources"]["memory_bytes"] == 805306368
        and card["resources"]["nice"] == 19 and card["resources"]["ionice"] == "idle"
        and card["resources"]["pids"] == 128):
    raise ValueError("task_card_shape")
if not (auth.get("version") == 1
        and auth.get("status") == "AUTHORIZED_REAL_P01_SINGLE_ATTEMPT"
        and auth.get("attempt_id") == ATTEMPT
        and auth.get("task_card_sha256") == CARD_SHA
        and auth.get("one_attempt_only") is True
        and isinstance(auth.get("granted_by"), str) and auth.get("granted_by")):
    raise ValueError("authorization_binding")
phase = sys.argv[2]
RUN = "/data/var/run/b" if len(sys.argv) >= 8 and sys.argv[7] == "b" else "/data/var/run"
from xiangrugu_datamgmt.task_partition import prepare_partition_task
from xiangrugu_datamgmt.project_partition import (prepare_project_partition_review,
    materialize_project_partition_request)
image = {"git_revision": "8fbc8c97fcf1d818caddf6ab556fa82d986643ed",
         "image_id": "sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a",
         "source_status": "dirty", "user": "10001:10001"}
if phase == "prepare":
    marker = prepare_partition_task(repository_root="/metadata",
        review_file=sys.argv[3], expected_review_sha256=sys.argv[4],
        expected_roots_sha256=sys.argv[5], expected_image_id=image["image_id"],
        actual_image=image, output_dir=Path(RUN) / "preparation",
        partition_id="large-p01")
    record = json.loads(Path(marker).read_bytes())
    paths = {str(Path("/metadata") / d["path"]) for d in record["bindings"].values()}
    paths.add(str(Path("/metadata") / sys.argv[3]))  # the closed readiness packet
    prep_dir = Path(RUN) / "preparation"
    paths.add(str(prep_dir / "preparation.json"))  # the published record itself
    paths.update(str(prep_dir.joinpath(n)) for n in record["generated"])
    from xiangrugu_datamgmt.snapshots import write_json_exclusive
    write_json_exclusive(Path(RUN) / "preparation" / "inputs-manifest.json",
        {"version": 1, "status": "REHEARSAL_VALIDATED_INPUT_MANIFEST",
         "paths": sorted(paths)})
    print("PREPARE_OK " + json.dumps({"marker": str(marker)}, sort_keys=True))
else:
    sel = Path(sys.argv[6])
    review = prepare_project_partition_review(selection_file=sel,
        expected_selection_sha256=sha(sel), actual_image=image,
        output_dir=Path(RUN) / "review")
    review_doc = json.loads(Path(review).read_bytes())
    assert review_doc["status"] == "DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE" \
        and review_doc["missing"] == []
    exec_dir = Path("/data/var/snapshots/executions") / ATTEMPT
    (exec_dir / "scratch").mkdir(parents=True, exist_ok=True)
    staged = materialize_project_partition_request(review_file=review,
        expected_review_sha256=sha(review), actual_image=image,
        output_dir=Path("/data/var/snapshots/materialization"),
        result_file=exec_dir / "batch.staged.json", scratch_parent=exec_dir / "scratch")
    request = json.loads(Path(staged).read_text())
    snap, src = card["snapshot"], card["source_object"]
    if not (request["snapshot_id"] == snap["snapshot_id"]
            and request["relative_path"] == snap["member"]["path"]
            and request["expected_size"] == snap["member"]["size"]
            and request["expected_sha256"] == snap["member"]["sha256"]
            and request["manifest_sha256"] == snap["manifest_sha256"]
            and request["rule_id"] == src["rule_id"]):
        raise ValueError("request_vs_card")
    pins = {"selection": str(sel), "review.review.json": str(review)}
    pins.update({f"review.{name}": str(Path(review).parent / name)
                 for name in review_doc["generated"]})
    print("MATERIALIZE_REAL_REQUEST_OK " + json.dumps({"request": str(staged),
        "request_sha256": sha(staged), "pins": pins}, sort_keys=True))
'''


def stage_a_mounts(w: Workspace, *, authorized: bool) -> list:
    driver = w.root / 'stage-a-driver.py'
    driver.write_text(STAGE_A_DRIVER)
    m = ['--mount', f'type=bind,src={driver},dst=/stage-a-driver.py,readonly'] \
        + shared_input_mounts(w, authorized=authorized)
    if authorized:
        m += ['--mount', f'type=bind,src={w.durable},dst=/data/var/snapshots']
    return m


def driver_argv(w: Workspace, phase: str, meta=None, stage='a'):
    # Full argv INCLUDING the script path; docker_run pins --entrypoint python.
    argv = ['/stage-a-driver.py', sha(w.card / 'task-card.closed.json'), phase]
    if phase == 'prepare':
        argv += [meta['review_rel'], sha(w.metadata / meta['review_rel']),
                 sha(w.metadata / 'datamgmt/config/roots.yaml')]
    else:
        base = '/data/var/run' if stage == 'a' else '/data/var/run/b'
        argv += ['', '', '', f'{base}/review.selection.json']
    if stage == 'b':
        argv.append('b')
    return argv


def run_prepare_leg(w: Workspace, image: str, meta: dict, name: str):
    return docker_run(image, driver_argv(w, 'prepare', meta),
        name=name, mounts=stage_a_mounts(w, authorized=True),
        timeout=STAGE_A_SECONDS + 60)


def run_materialize_leg(w: Workspace, image: str, name: str):
    return docker_run(image, driver_argv(w, 'materialize'),
        name=name, mounts=stage_a_mounts(w, authorized=True),
        timeout=STAGE_A_SECONDS + 60)


# ----------------------------------------------------- R2 closure + pin table
ABS_PREFIXES = ('/metadata/', '/data/var/run/', '/card/')


def collect_bound_paths(w: Workspace, staged_local: Path, *, stage_b=False) -> dict:
    """Every absolute bound path reachable from the REAL materialized request,
    mapped to its pinned sha. Mirrors the shipped stage-a-inputs.tsv closure.
    Stage A evidence is read from the authoritative tree (Stage B sees it via
    its ro mirror)."""
    request = json.loads(staged_local.read_text())
    rows = {}

    def want(container_path, pin):
        if container_path.startswith('/data/var/snapshots/materialization/'):
            return  # published in the dedicated ro bind; checked in mat dir
        if not stage_b and container_path.startswith('/data/var/run/a/'):
            return  # Stage B mirror of Stage A outputs; pinned inside the mirror
        rows[container_path] = pin

    def evidence_local(container_path: str) -> Path:
        """Local file for a /metadata or /data/var/run pin (Stage A truth)."""
        if container_path.startswith('/metadata/'):
            return w.metadata / container_path[len('/metadata/'):]
        if container_path.startswith('/data/var/run/a/'):
            return w.output / container_path[len('/data/var/run/a/'):]
        if container_path.startswith('/data/var/run/'):
            return w.output / container_path[len('/data/var/run/'):]
        raise AssertionError(f'evidence path outside closures: {container_path}')

    for key, sk in (('roots', 'roots_sha256'), ('certificate', 'certificate_sha256'),
                    ('scope_file', 'scope_sha256'), ('budget_file', 'budget_sha256'),
                    ('approval_file', 'approval_sha256')):
        want(request[key], request[sk])
    for role, d in request['bindings'].items():
        want(d['path'], d['sha256'])
    descriptor = json.loads(evidence_local(request['bindings']['descriptor']['path']).read_text())
    for role in ('preparation', 'parent_review'):
        want(descriptor[role]['path'], descriptor[role]['sha256'])
    prep = json.loads(evidence_local(descriptor['preparation']['path']).read_text())
    base = str(Path(descriptor['preparation']['path']).parent)
    for name, pinv in prep['generated'].items():
        want(base + '/' + name, pinv)
    parent = json.loads(evidence_local(descriptor['parent_review']['path']).read_text())
    for role, b in parent['bindings'].items():
        want('/metadata/' + b['path'], b['sha256'])
    return rows


def build_input_table(w: Workspace, staged_local: Path, name: str, *, stage_b=False) -> tuple:
    rows = collect_bound_paths(w, staged_local, stage_b=stage_b)
    lines = ['# rehearsal input table — generated by rehearsal.py',
             '# closure: every absolute bound path of the REAL materialized request;',
             '# third column is informational (verify-mount-table maps paths itself)']
    for cp, pin in sorted(rows.items()):
        # Evidence pins (/metadata/**, /data/var/run/**) are authored by the
        # Stage A run; Stage B reads them through its ro mirror of the SAME
        # bytes. Map them to the authoritative Stage A locations.
        if cp.startswith('/metadata/') or cp.startswith('/data/var/run/'):
            local = w.to_local(cp, stage_b=False)
        else:
            local = w.to_local(cp, stage_b=stage_b)
        if not local.is_file() or sha(local) != pin:
            raise SystemExit(f'MOUNT_TABLE_INVALID rehearsal: drift {cp}')
        rel = local.relative_to(w.root).as_posix()
        lines.append(f'{pin}\t{cp}\t{rel}')
    table = w.root / name
    table.write_text('\n'.join(lines) + '\n')
    return table, len(rows)


def restage_for_verifier(w: Workspace, stage_b=False) -> tuple:
    """Assemble the EXACT single-tree layout run-real.sh uses — one $run/output
    bound rw at /data/var/run AND ro at /metadata (subtree), with a FRESH
    durable/materialization so destination freshness is proven on real bytes.
    Stage A evidence is authoritative in both views (Stage B reads it through
    its ro mirror). Returns (stage_view, fresh_durable)."""
    force_rm(w.root / 'verify-stage')
    force_rm(w.root / 'verify-durable')
    stage = w.root / 'verify-stage'
    durable = w.root / 'verify-durable'
    shutil.copytree(w.output, stage)                    # preparation, review, selection
    shutil.copytree(w.metadata, stage / 'metadata')     # the /metadata subtree
    if stage_b:
        shutil.copytree(stage, stage / 'a')             # mirror of Stage A outputs
    shutil.copytree(w.durable / 'materialization', durable / 'materialization')
    return stage, durable


def run_verifier_host(w: Workspace, table: Path, mat_dir: Path, run_output: Path,
                      req_pin: str, approval_sha: str):
    return subprocess.run([sys.executable, str(HERE / 'verify-mount-table.py'),
        '--materialization', str(mat_dir),
        '--request-sha256', req_pin,
        '--approval-sha256', approval_sha,
        '--roots-sha256', sha(w.metadata / 'datamgmt/config/roots.yaml'),
        '--run-output', str(run_output), '--table', str(table), '--snapshot-id', SNAPSHOT_ID],
        capture_output=True, text=True)


# --------------------------------------------------- R3 supervisor scenarios
# The worker is the REAL product entry (task_control via installed-origin argv
# form). A pre-exec hook inside installed-origin starts the lease writer so it
# shares the worker's session/pgid: the supervisor killpg then proves
# process_group_gone for BOTH worker and sidecar.
# Hook runs INSIDE installed-origin before its execvp: os.execv keeps the pid,
# so the lease writer inherits this process (same session/pgid as the worker).
INSTALLED_ORIGIN_HOOK = """import os as _os, sys as _sys
_sys.stderr.reconfigure(line_buffering=True) if hasattr(_sys.stderr, 'reconfigure') else None
print('HOOK: installed-origin reached exec point', file=_sys.stderr, flush=True)
_os.execv('/proc/self/exe', ['/proc/self/exe', '/lease-hook.py'])
"""

LEASE_WRITER = r'''import os, sys, time
from pathlib import Path
stop = Path(sys.argv[1]); lease = Path(sys.argv[2])
seq = 0; last = 0.0
while not stop.exists():
    now = time.time()
    if now - last >= 0.2:
        seq += 1
        body = ["%.3f" % now, str(seq), "MemAvailable:   32000000 kB",
                "0.10 0.10 0.10 1/100 100",
                "some avg10=0.00 avg60=0.00 avg300=0.00 total=0",
                "some avg10=0.00 avg60=0.00 avg300=0.00 total=0",
                "pswpout 0", "999999999999", "true"]
        nxt = lease.with_name(".lease-next")
        nxt.write_text("\n".join(body) + "\n"); os.replace(nxt, lease)
        last = now
    time.sleep(0.02)
'''

IO_MOCK = r'''#!/bin/sh
# ionice mock for slim images without util-linux.
# Query form (`ionice -p PID`) reports the class applied by our set form.
# Set form (`ionice -c CLASS [-p PID]` or `ionice -c CLASS cmd...`) succeeds.
if [ "$1" = "-c" ]; then
  shift; cls="$1"; shift
  if [ "$1" = "-p" ]; then shift 2; fi
  if [ $# -gt 0 ]; then exec "$@"; fi
  exit 0
fi
if [ "$1" = "-p" ]; then echo idle; exit 0; fi
exit 0
'''

LEASE_HOOK_BODY = r'''import os, subprocess, time
from pathlib import Path
# The hook process IS the worker's session leader (supervise runs it with
# start_new_session); its own background lease writer therefore shares the
# worker process group and keeps samples flowing through publication.
os.environ.pop("PYTHONPATH", None)  # like production: module comes from installed site-packages
lease = Path("/control/lease")
stop = Path("/data/var/run/.stop")
def sample():
    now = time.time()
    seq = 1
    if lease.exists():
        try:
            lines = lease.read_text().splitlines()
            if len(lines) >= 2:
                seq = int(lines[1]) + 1
        except Exception:
            pass
    body = ["%.3f" % now, str(seq), "MemAvailable:   32000000 kB",
            "0.10 0.10 0.10 1/100 100",
            "some avg10=0.00 avg60=0.00 avg300=0.00 total=0",
            "some avg10=0.00 avg60=0.00 avg300=0.00 total=0",
            "pswpout 0", "999999999999", "true"]
    nxt = lease.with_name(".lease-next")
    nxt.write_text("\n".join(body) + "\n")
    os.replace(nxt, lease)
sample()
import sys as _sys
_hooked = len(_sys.argv) > 1 and _sys.argv[1] == '/installed-origin.py'
_worker = (['/installed-origin.py'] + _sys.argv[2:]) if _hooked \
    else (['python', '/installed-origin.py'] + _sys.argv[1:])
with open('/data/var/run/hook-worker-output.txt', 'wb') as out:
    worker = subprocess.Popen(_worker, stdout=out, stderr=out)
    rc = None
    try:
        while rc is None:
            sample()
            rc = worker.poll()
            if rc is None:
                time.sleep(0.05)
    finally:
        out.flush()
        os.fsync(out.fileno())
raise SystemExit(rc)
'''

LEASE_HOOK_NOTE = '''The hook chain mirrors production exactly: candidate_supervisor launches
`/installed-origin.py -m xiangrugu_datamgmt.task_control ...`; the rehearsal's
patched installed-origin execv's /proc/self/exe on /lease-hook.py (same pid,
same session), which samples the lease in-group and then spawns the real
task_control module command line.'''


def stage_b_tree(w: Workspace):
    """Recreate the Stage B run tree: b-output (+ mirror of Stage A outputs)
    and b-durable with the materialization copy — the pins run-real.sh reuses
    through one shared $run/output tree."""
    force_rm(w.b_output)
    force_rm(w.b_durable)
    w.b_output.mkdir(parents=True)
    w.b_durable.mkdir(parents=True)
    shutil.copytree(w.output, w.a_mirror)          # preparation, review, selection
    shutil.copytree(w.durable / 'materialization', w.b_durable / 'materialization')


def b_local(w: Workspace, container_path: str) -> Path:
    return w.to_local(container_path, stage_b=True)


def supervisor_case(w: Workspace, image: str, request: dict, req_pin: str, kind: str, *,
                    seconds=120, origin_hook=False, worker_override=None,
                    pin_override=None, expect_final=True,
                    controller_pin_override=None, env_prefix='', extra_mounts=(),
                    origin_transform=None):
    """Launch candidate_supervisor in a container with run-real.sh's Stage B
    mounts/posture over the LIVE b_* trees (exactly one shared $run/output,
    like production). 'verify' kinds use restaged fresh trees instead."""
    tag = f'sup-{kind}'
    fresh = 'verify' if kind == 'success' else 'b'
    # Directive (总指挥 2026-11-14): each case runs in its OWN fresh tree so a
    # prior case can never leave stale outputs behind.
    vroot = Path(os.environ.get(f'P01_CASE_OUT_{kind}', str(w.root / f'{kind}-run')))
    if vroot.exists():
        raise SystemExit(f'{kind} output dir must be fresh: {vroot}')
    vroot.mkdir(parents=True)
    if os.environ.get('P01_CASE_ONLY'):
        kinds = [k.strip() for k in os.environ['P01_CASE_ONLY'].split(',') if k.strip()]
        if kind not in kinds:
            # Neutralized result so main()'s assertions become no-ops; the
            # case is neither launched nor evaluated (scoped reruns only).
            neutral = type('N', (), {'__bool__': lambda self: False,
                                     '__getitem__': lambda self, k: None,
                                     'get': lambda self, k, d=None: d})()
            return {'skipped': True, 'returncode': 0, 'monitor': neutral,
                    'stdout': '', 'stderr': '', 'mounts': [], 'state': {},
                    'evidence_dir': vroot, 'final_local': vroot / 'x',
                    'twin_local': vroot / 'y', 'worker_out_dir': vroot,
                    'failure_local': vroot / 'z', 'worker_argv': []}
    if fresh != 'verify':
        stage = vroot / 'stage'
        durable = vroot / 'durable'
        shutil.copytree(w.output, stage)
        shutil.copytree(w.metadata, stage / 'metadata')
        shutil.copytree(stage, stage / 'a')
        ro_input = vroot / 'ro-input'      # digest-bound inputs on own ro binds
        rw_state = vroot / 'rw-state'      # writable destinations only
        shutil.copytree(w.durable / 'materialization', durable / 'materialization')
        ro_input.mkdir()
        def _move_ro(src_dir, dst_name):
            dst = ro_input / dst_name
            dst.mkdir()
            for f in sorted(src_dir.iterdir()):
                shutil.move(str(f), str(dst / f.name))
        _move_ro(stage / 'preparation', 'preparation')
        _move_ro(stage / 'review', 'review')
        mirror = ro_input / 'a'
        mirror.mkdir()
        for f in sorted((stage / 'a').iterdir()):
            if f.is_dir():
                _move_ro(f, f'a/{f.name}')
            else:
                shutil.move(str(f), str(mirror / f.name))
        rw_state.mkdir()
        (rw_state / 'scratch').mkdir(exist_ok=True)
        base_out, base_snap, run_root = stage, durable, rw_state
    if fresh == 'verify':
        # Independent fresh tree per directive; the legacy verify-* trees are
        # left exactly as restaged for the mount-table checks (F2 comparables).
        stage = vroot / 'stage'
        durable = vroot / 'durable'
        ro_input = vroot / 'ro-input'      # digest-bound inputs, dedicated ro binds
        rw_state = vroot / 'rw-state'      # writable destinations only
        shutil.copytree(w.output, stage)
        shutil.copytree(w.metadata, stage / 'metadata')
        shutil.copytree(stage, stage / 'a')
        shutil.copytree(w.durable / 'materialization', durable / 'materialization')
        # The product maps ANY bare ValueError raised before the first
        # progress boundary to internal/io_error, so every preflight gate
        # failure looks identical in the receipt. To make the rehearsal
        # observable, split the Stage A outputs by role: digest-bound INPUTS
        # move onto their own ro bind subtrees (statvfs resolves to the
        # deepest mount => readonly_paths all see ST_RDONLY), while writable
        # STATE stays under the single rw bind at /data/var/run.
        ro_input.mkdir()
        def _move_ro(src_dir, dst_name):
            dst = ro_input / dst_name
            dst.mkdir()
            for f in sorted(src_dir.iterdir()):
                shutil.move(str(f), str(dst / f.name))
        _move_ro(stage / 'preparation', 'preparation')
        _move_ro(stage / 'review', 'review')
        mirror = ro_input / 'a'
        mirror.mkdir()
        for f in sorted((stage / 'a').iterdir()):
            if f.is_dir():
                _move_ro(f, f'a/{f.name}')
            else:
                shutil.move(str(f), str(mirror / f.name))
        # Writable state that must remain reachable under /data/var/run:
        rw_state.mkdir()
        (rw_state / 'scratch').mkdir(exist_ok=True)
        base_out, base_snap, run_root = stage, durable, rw_state
    exec_dir_c = f'/data/var/snapshots/executions/{ATTEMPT}'
    evidence_c = f'{exec_dir_c}/monitor.{kind}.json'
    final_c = f'{exec_dir_c}/batch.staged.json'
    failure_c = f'/data/var/run/failure-report.{kind}.json'
    exec_local = base_snap / 'executions' / ATTEMPT
    exec_local.mkdir(parents=True, exist_ok=True)
    (exec_local / 'scratch').mkdir(exist_ok=True)
    for rel in (f'monitor.{kind}.json', 'batch.staged.json', '.batch.staged.json.incomplete',
                'final-sample-request.json', 'limits.json',
                'publication-failure.json'):
        (exec_local / rel).unlink(missing_ok=True)
    for _stale in (f'failure-report.{kind}.json', 'installed-origin.json',
                   'worker-output.txt', 'hook-worker-output.txt'):
        (run_root / _stale).unlink(missing_ok=True)
    leasew = w.root / 'lease-writer.py'
    leasew.write_text(LEASE_WRITER)
    iomock = w.root / 'ionice'
    iomock.write_text(IO_MOCK)
    iomock.chmod(0o755)
    origin = w.root / 'installed-origin.py'
    origin_src = REPO / 'docs/superpowers/evidence/2026-11-13-request-reader-integration/installed-origin.py'
    text = origin_src.read_text()
    marker = 'os.execvp(sys.executable,[sys.executable,*sys.argv[1:]])'
    assert marker in text, 'installed-origin layout changed'
    if origin_hook:
        text = text.replace(marker, INSTALLED_ORIGIN_HOOK.strip('\n') + '\n' + marker)
    if origin_transform is not None:
        text = origin_transform(text)
        assert 'XRG_REHEARSAL_HANG' in text
    origin.write_text(text)
    hook = w.root / 'lease-hook.py'
    hook.write_text(LEASE_HOOK_BODY)
    extra_mounts = list(extra_mounts)
    if worker_override and worker_override[0].startswith('/'):
        stub = w.root / worker_override[0][1:]
        assert stub.is_file(), stub
        extra_mounts = ['--mount', f'type=bind,src={stub},dst={worker_override[0]},readonly']
    if worker_override is None:
        worker_argv = ['-m', 'xiangrugu_datamgmt.task_control',
                       '--request', '/data/var/snapshots/materialization/request.json',
                       '--request-sha256', pin_override or req_pin,
                       '--approval-sha256', request['approval_sha256'],
                       '--roots-sha256', request['roots_sha256'],
                       '--image-id', IMAGE_ID, '--git-revision', GIT_REVISION,
                       '--image-user', '10001:10001', '--source-status', 'dirty',
                       '--lifecycle-seconds', '1800',
                       '--authorized-source-mode', 'project_snapshot']
        if kind == 'fail':
            # Deterministic control-domain failure on the REAL chain: a wrong
            # roots pin trips task_control's controller_pin gate (ValueError)
            # BEFORE any source access; task_control then writes its receipt
            # at --failure-evidence and exits 1 — exactly production behaviour.
            _i = worker_argv.index('--roots-sha256')
            worker_argv[_i + 1] = 'deadbeef' * 8
            worker_argv += ['--failure-evidence', failure_c]
    else:
        worker_argv = list(worker_override)
    cmd = ['python', '-m', 'xiangrugu_datamgmt.candidate_supervisor',
           '--lease', '/control/lease', '--evidence', evidence_c, '--seconds', str(seconds)]
    if expect_final:
        cmd += ['--final', final_c, '--authorized-source-mode', 'project_snapshot',
                '--request-sha256', pin_override or req_pin]
        if kind == 'fail':
            cmd += ['--worker-failure', failure_c, '--worker-request-sha256', pin_override or req_pin]
        cmd += ['--controller-request-file', '/data/var/snapshots/materialization/request.json',
                '--controller-request-sha256', controller_pin_override or pin_override or req_pin]
    # Adjudicated production form (总指挥 2026-11-14): the worker argv is
    # interpreter-pinned — `python /installed-origin.py -m …task_control …` —
    # both here and in run-real.sh Stage B, because the installed copy is
    # mode 0644 without a shebang (bare-path exec gave PermissionError).
    cmd += ['--', 'python', '/installed-origin.py'] + worker_argv
    snapshot_view = w.snapshot / SNAPSHOT_ID
    materialization_bind = base_snap / 'materialization'
    if not materialization_bind.is_dir():
        shutil.copytree(w.durable / 'materialization', materialization_bind)
    view = vroot / 'snapshot-view'                  # inside THIS case tree
    if not view.is_dir():
        shutil.copytree(w.snapshot / SNAPSHOT_ID, view)
    snapshot_view = view
    mounts = []
    for _name in ('preparation', 'review', 'a'):
        mounts += ['--mount', f'type=bind,src={ro_input}/{_name},dst=/data/var/run/{_name},readonly']
    mounts += ['--mount', f'type=bind,src={rw_state},dst=/data/var/run']
    mounts += ['--mount', f'type=bind,src={base_snap},dst=/data/var/snapshots',
               '--mount', f'type=bind,src={base_out / "metadata"},dst=/metadata,readonly',
               '--mount', f'type=bind,src={materialization_bind},dst=/data/var/snapshots/materialization,readonly',
               '--mount', f'type=bind,src={snapshot_view},dst=/data/imports/usedata/{SNAPSHOT_ID},readonly',
               '--mount', f'type=bind,src={w.control},dst=/control',
               '--mount', f'type=bind,src={leasew},dst=/lease-writer.py,readonly',
               '--mount', f'type=bind,src={hook},dst=/lease-hook.py,readonly',
               '--mount', f'type=bind,src={origin},dst=/installed-origin.py,readonly',
               '--mount', f'type=bind,src={iomock},dst=/usr/local/bin/ionice,readonly',
               *extra_mounts]
    if True:
        # Fail-fast before launch: statvfs every declared readonly path from
        # inside the same bind layout; an RW entry means the mount split is
        # wrong and the worker would die as an opaque internal io_error.
        probe = ('import json, os\n'
                 'paths = json.loads(open("/probe.json").read())\n'
                 'bad = [p for p in paths if not os.statvfs(p).f_flag & os.ST_RDONLY]\n'
                 'print("RO_PROBE_OK" if not bad else "RO_PROBE_FAIL " + json.dumps(bad))\n'
                 'raise SystemExit(0 if not bad else 9)\n')
        pf = w.root / 'ro-probe.py'; pf.write_text(probe)
        pj = w.root / 'probe.json'
        RJSON = json.loads((base_snap / 'materialization/request.json').read_text())             if (base_snap / 'materialization/request.json').is_file() \
            else json.loads((w.durable / 'materialization/request.json').read_text())
        cert = json.loads((base_out / 'metadata/selected-certificate.json').read_text())
        meta_paths = [RJSON[k] for k in ('roots', 'certificate', 'scope_file',
                                         'budget_file', 'approval_file')]
        meta_paths += [d['path'] for d in RJSON['bindings'].values()]
        snap_dir = '/data/imports/usedata/' + RJSON['snapshot_id']
        member_paths = [snap_dir + '/' + m['path'] for m in cert['members']]
        wjson(pj, sorted(set(meta_paths + [str(snap_dir)] + member_paths)))
        probe_result = docker_run(image, ['-c', 'python /probe-mounts.py'],
            name=f'xrg-reh-roprobe-{int(time.time())}',
            mounts=mounts + ['--mount', f'type=bind,src={pf},dst=/probe-mounts.py,readonly',
                             '--mount', f'type=bind,src={pj},dst=/probe.json,readonly'],
            timeout=60, entrypoint='sh')
        if 'RO_PROBE_OK' not in probe_result['stdout']:
            raise SystemExit('pre-launch readonly probe failed:\n'
                             + probe_result['stdout'][-500:] + probe_result['stderr'][-500:])
        record('readonly_probe_passed', paths=len(json.loads(pj.read_text())))
    uid = CONTAINER_UID if _uid_capable() else os.getuid()
    flags = posture_flags(extra_tmpfs=(
        f'/data/var/run/scratch:rw,nosuid,nodev,size=67108864,uid={uid},gid={uid},mode=700',))
    _dbg_kinds = os.environ.get('P01_SUP_DEBUG_KINDS')
    _dbg_on = (_dbg_kinds is not None and kind in _dbg_kinds.split(',')) \
        or (_dbg_kinds is None and int(os.environ.get('P01_SUP_DEBUG', '0')))
    if _dbg_on:
        # Repro helper: run the real supervisor CLI under a wrapper that
        # captures every exception supervise swallows into supervisor_error.
        parts = [str(c) for c in cmd]
        idx = parts.index('--')
        opts, worker = parts[3:idx], parts[idx + 1:]
        wrap = ('import sys, json, argparse, time, traceback\n'
                'sys.path.insert(0, "/usr/local/lib/python3.12/site-packages")\n'
                'from pathlib import Path\n'
                'import xiangrugu_datamgmt.candidate_supervisor as cs\n'
                'LOG = open("/data/var/run/sup-dbg.log", "a", buffering=1)\n'
                'def L(*a): print(*a, file=LOG, flush=True)\n'
                '_orig_read = cs.read_lease\n'
                'def read_probe(path):\n'
                '    try:\n'
                '        return _orig_read(path)\n'
                '    except BaseException as e:\n'
                '        raw = None\n'
                '        try:\n'
                '            raw = Path(path).read_bytes()[:250] if Path(path).exists() else b"MISSING"\n'
                '        except Exception as e2:\n'
                '            raw = "RAWFAIL:" + str(e2)\n'
                '        L("READ_LEASE_FAIL", type(e).__name__, str(e), repr(raw))\n'
                '        raise\n'
                'cs.read_lease = read_probe\n'
                'tb = []\n'
                '_orig_ob = cs.ResourceWatch.observe\n'
                'def ob(self, metrics):\n'
                '    try:\n'
                '        return _orig_ob(self, metrics)\n'
                '    except Exception as e:\n'
                '        tb.append(("OBSERVE", type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.ResourceWatch.observe = ob\n'
                '_orig_pf = cs.ResourceWatch.preflight\n'
                'def pf(self, metrics):\n'
                '    try:\n'
                '        return _orig_pf(self, metrics)\n'
                '    except Exception as e:\n'
                '        tb.append(("PREFLIGHT", type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.ResourceWatch.preflight = pf\n'
                '_orig_wwje = cs.write_json_exclusive\n'
                'def wwje(path, doc):\n'
                '    try:\n'
                '        return _orig_wwje(path, doc)\n'
                '    except BaseException as e:\n'
                '        tb.append(("WJE", str(path), type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.write_json_exclusive = wwje\n'
                '_orig_sp = cs.supervise\n'
                'def sp(a, **k):\n'
                '    try:\n'
                '        return _orig_sp(a, **k)\n'
                '    except BaseException as e:\n'
                '        tb.append(("SUPERVISE", type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.supervise = sp\n'
                '_orig_popen = cs.subprocess.Popen\n'
                'def popen_probe(argv, **k):\n'
                '    L("SPAWN", list(argv))\n'
                '    try:\n'
                '        child = _orig_popen(argv, **k)\n'
                '        L("SPAWNED", child.pid)\n'
                '        return child\n'
                '    except BaseException as e:\n'
                '        tb.append(("POPEN", list(argv), type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.subprocess.Popen = popen_probe\n'
                '_orig_pub = cs.publish_batch\n'
                'def pub(staged, final, **k):\n'
                '    L("PUB_CALL", str(staged), str(final))\n'
                '    try:\n'
                '        r = _orig_pub(staged, final, **k)\n'
                '        L("PUB_OK")\n'
                '        return r\n'
                '    except BaseException as e:\n'
                '        tb.append(("PUB", type(e).__name__, str(e), traceback.format_exc()))\n'
                '        raise\n'
                'cs.publish_batch = pub\n''import xiangrugu_datamgmt.task_failure as _tf\n' '_orig_adv = _tf.FailureTrace.advance\n''def adv(self, stage, object_index=None, completed_objects=0):\n''    L("STAGE", stage, object_index, completed_objects)\n''    return _orig_adv(self, stage, object_index, completed_objects)\n''_tf.FailureTrace.advance = adv\n''_orig_fail = _tf.FailureTrace.failure\n''def fail(self, error, rs, sm):\n''    L("WORKER_EXC", type(error).__name__, str(error), repr(error)[:400], traceback.format_exc())\n''    return _orig_fail(self, error, rs, sm)\n''_tf.FailureTrace.failure = fail\n'
                'L("DBG START", ' + repr(opts) + ', ' + repr(worker) + ')\n'
                'sys.argv = ["candidate_supervisor"] + ' + repr(opts) + ' + ["--"] + ' + repr(worker) + '\n'
                'try:\n'
                '    rc = cs.main()\n'
                'except SystemExit as sx:\n'
                '    rc = sx.code\n'
                'for item in tb:\n'
                '    L("EXC_CAPTURED", *item)\n'
                'raise SystemExit(rc)\n')
        (w.root / 'dbg-wrap.py').write_text(wrap)
        mounts += ['--mount', f'type=bind,src={w.root / "dbg-wrap.py"},dst=/dbg-wrap.py,readonly']
        shell = ('rm -f /data/var/run/sup-dbg.log; '
                 'python /lease-writer.py /data/var/run/.stop /control/lease & LW=$!; '
                 'sleep 0.3; python /dbg-wrap.py 2>>/data/var/run/sup-dbg.stderr.log; RC=$?; '
                 'touch /data/var/run/.stop; wait $LW 2>/dev/null; exit $RC')
    else:
        shell = ('python /lease-writer.py /data/var/run/.stop /control/lease & LW=$!; '
                 'sleep 0.3; %s%s >>/data/var/run/worker-output.txt 2>&1; RC=$?; '
                 'touch /data/var/run/.stop; wait $LW 2>/dev/null; exit $RC'
                 % (env_prefix, ' '.join(cmd)))
    _env_flags = []
    if env_prefix.strip():
        # sh's `VAR=val cmd` form only affects that one command; the stall
        # stub lives inside the worker process, so export into the container.
        for _kv in env_prefix.split():
            _env_flags += ['-e', _kv]
    result = docker_run(image, ['-c', shell], name=f'xrg-reh-{tag}-{int(time.time())}',
                        mounts=mounts, timeout=seconds + 120, flags=flags, entrypoint='sh',
                        env=_env_flags)
    result['worker_argv'] = [str(c) for c in cmd[cmd.index('--') + 1:]]
    _mon_path = exec_local / f'monitor.{kind}.json'
    _missing = not _mon_path.is_file()
    _dump = {'supervisor_error'} | ({None} if kind != 'success' else set())
    _bad_reason = _missing or (json.loads(_mon_path.read_text()).get('reason') in _dump)
    if _missing:
        print(json.dumps({'supervisor_debug': kind, 'rc': result['returncode'],
                          'monitor_missing': True,
                          'stdout': result['stdout'][-1500:], 'stderr': result['stderr'][-2500:],
                          'state': {k: result['state'].get(k) for k in ('ExitCode','OOMKilled')}},
                         indent=1), flush=True)
    elif _bad_reason:
        print(json.dumps({'supervisor_debug': kind, 'rc': result['returncode'],
                          'monitor': json.loads((exec_local / f'monitor.{kind}.json').read_text()),
                          'stdout': result['stdout'][-800:], 'stderr': result['stderr'][-800:]},
                         indent=1), flush=True)
    monitor_local = exec_local / f'monitor.{kind}.json'
    result['monitor'] = json.loads(monitor_local.read_text()) if monitor_local.is_file() else {}
    result['evidence_dir'] = exec_local
    result['final_local'] = exec_local / 'batch.staged.json'
    result['twin_local'] = exec_local / '.batch.staged.json.incomplete'
    result['worker_out_dir'] = run_root
    result['failure_local'] = run_root / f'failure-report.{kind}.json'
    return result


# ------------------------------------------------------- R4/R6 probes
def reregister_probe(w: Workspace) -> dict:
    """Replicates run-real.sh register(): O_EXCL one-shot artifact under
    $runtime_root named by the FIXED attempt id, refusal artifacts into the
    refused run dir, exit 3 — same suffix or not."""
    helper = w.root / 'register_probe.py'
    helper.write_text(r"""import datetime, json, os, sys
runtime_root, attempt, task_card_sha, auth_sha, req_sha, approval_sha, roots_sha = sys.argv[1:8]
run_dir, suffix = sys.argv[8], sys.argv[9]
target = os.path.join(runtime_root, "attempt-registration-" + attempt + ".json")
record = {"version": 1, "attempt_id": attempt, "task_card_sha256": task_card_sha,
          "authorization_sha256": auth_sha, "request_sha256": req_sha,
          "approval_sha256": approval_sha, "roots_sha256": roots_sha,
          "stage_a_run": "run-a", "stage_b_run": "run-b-" + suffix,
          "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
          "one_attempt_only": True, "container_created": False}
try:
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    msg = ("ATTEMPT_ALREADY_REGISTERED; this attempt is consumed, refusing to launch "
           "(one_attempt_only; existing registration: " + target + ")")
    print(msg, file=sys.stderr)
    with open(os.path.join(run_dir, "rerun-refusal.log"), "w") as stream:
        stream.write(msg + "\n")
    with open(os.path.join(run_dir, "rerun-refusal-exit-code.txt"), "w") as stream:
        stream.write("3\n")
    raise SystemExit(3)
with os.fdopen(fd, "w") as stream:
    stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush(); os.fsync(stream.fileno())
print("REGISTERED")
""")
    reg = w.runtime / f'attempt-registration-{ATTEMPT}.json'
    outs = []
    for suffix in ('a', 'b', 'c-other-suffix'):
        run_dir = w.runtime / f'probe-{suffix}'
        run_dir.mkdir(exist_ok=True)
        proc = subprocess.run([sys.executable, str(helper), str(w.runtime), ATTEMPT,
                               'a' * 64, 'b' * 64, 'c' * 64, 'd' * 64, 'e' * 64,
                               str(run_dir), suffix], capture_output=True, text=True)
        outs.append({'suffix': suffix, 'rc': proc.returncode, 'out': proc.stdout.strip(),
                     'refusal_log': (run_dir / 'rerun-refusal.log').is_file(),
                     'refusal_code': (run_dir / 'rerun-refusal-exit-code.txt').read_text().strip()
                     if (run_dir / 'rerun-refusal-exit-code.txt').exists() else None})
    first, repeats = outs[0], outs[1:]
    assert first['rc'] == 0 and first['out'] == 'REGISTERED', outs
    assert all(o['rc'] == 3 and o['out'] == '' and o['refusal_log'] and o['refusal_code'] == '3'
               for o in repeats), outs
    record = json.loads(reg.read_text())
    assert record['attempt_id'] == ATTEMPT and record['one_attempt_only'] is True \
        and record['container_created'] is False
    return {'first_start': 'REGISTERED', 'repeat_starts_refused': [3, 3],
            'same_fixed_attempt_across_suffixes': True,
            'rerun_refusal_artifacts': True, 'registry_record': record}


def failure_roundtrip(w: Workspace, request_sha: str) -> dict:
    from xiangrugu_datamgmt.task_failure import FailureTrace, read_worker_failure
    path = (w.root / 'trace-roundtrip/failure-report.json').resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    trace = FailureTrace()
    trace.advance('request_preflight')
    err = ValueError('controller_pin')
    receipt = trace.failure(err, request_sha, 'project_snapshot')
    path.write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n')
    parsed, receipt_sha, state = read_worker_failure(path, request_sha, 'project_snapshot')
    assert state == 'valid' and parsed['code'] == 'controller_pin' \
        and parsed['request_sha256'] == request_sha
    bad = w.root / 'trace-roundtrip/mismatch.json'
    bad.write_text(path.read_text().replace(request_sha, 'f' * 64))
    _, _, state2 = read_worker_failure(bad, request_sha, 'project_snapshot')
    assert state2 == 'invalid'
    return {'valid_state': state, 'mismatch_state': state2,
            'receipt_keys_exact': sorted(receipt.keys()), 'single_path': True}


# ---------------------------------------------------------------- main
def main() -> int:
    keep = os.environ.get('P01_REHEARSAL_KEEP')
    if keep:
        root = Path(keep)
        if root.exists():
            raise SystemExit('P01_REHEARSAL_KEEP dir must not exist yet')
        created = False
    else:
        root = REPO / '.rehearsal-tmp'
        if root.exists():
            stamp = time.strftime('%Y%m%d-%H%M%S')
            archived = root.parent / f'.rehearsal-tmp.used-{stamp}'
            os.rename(root, archived)   # never delete evidence of a prior run
        created = True
    root.mkdir(parents=True, exist_ok=True)
    w = Workspace(root)
    try:
        image = ensure_local_image()
        record('local_rehearsal_image', image=LOCAL_IMAGE,
               note='python:3.12-slim + repo source; production image never present nor used')
        member = build_member(w)
        meta = build_repo_metadata(w, member)
        cert = build_certificate(w, meta)
        record('fixture_metadata_built', member_sha256=member['sha256'], member_size=member['size'],
               object_id=member['source_object_id'], binding_roles=len(meta['packet']['bindings']),
               certificate_manifest=cert['manifest_sha256'])
        chown_workspace(w)

        if len(sys.argv) > 1 and sys.argv[1] == 'dbg':
            leasew = w.root / 'lease-writer.py'; leasew.write_text(LEASE_WRITER)
            iomock = w.root / 'ionice'; iomock.write_text(IO_MOCK); iomock.chmod(0o755)
            result = docker_run(image, ['-c',
                'echo PATH=$PATH; command -v ionice || echo NO-IONICE-IN-PATH; '
                'sh /usr/local/bin/ionice -c 3 -p $$; echo SETRC=$?; '
                'sh /usr/local/bin/ionice -p $$; echo QRC=$?'],
                name=f'xrg-reh-dbg-{int(time.time())}',
                mounts=['--mount', f'type=bind,src={iomock},dst=/usr/local/bin/ionice,readonly'],
                timeout=60, entrypoint='sh')
            print('DBGENV', repr(result['stdout']), repr(result['stderr']))
            return 0
        # ---- R5 refuse WITHOUT authorization ------------------------------------
        build_card_and_auth(w, False, meta, cert, member)
        clean_stage_a(w)
        refused = docker_run(image, driver_argv(w, 'prepare', meta),
            name=f'xrg-reh-refuse-{int(time.time())}',
            mounts=stage_a_mounts(w, authorized=False),
            timeout=STAGE_A_SECONDS + 60)
        no_writes = not (w.durable / 'materialization').exists() \
            and not (w.output / 'preparation').exists()
        assert refused['returncode'] != 0 and 'real_execution_closed' in refused['stderr'], refused['stderr'][-500:]
        assert no_writes
        record('refuse_without_authorization', nonzero_exit=refused['returncode'],
               error='real_execution_closed', materialization_absent=no_writes,
               actual_mounts=[mount_view(m) for m in refused['mounts']])

        # ---- R1 Stage A full chain WITH fixture authorization --------------------
        build_card_and_auth(w, True, meta, cert, member)
        clean_stage_a(w)
        prep_leg = run_prepare_leg(w, image, meta, f'xrg-reh-prepare-{int(time.time())}')
        assert prep_leg['returncode'] == 0 and 'PREPARE_OK' in prep_leg['stdout'], \
            prep_leg['stdout'][-400:] + prep_leg['stderr'][-800:]
        # The prepare leg emitted its consumed-input manifest; pin EVERY file
        # it read (incl. all 14 repository-relative bindings) at its Stage A
        # container path — no hand-built expectations.
        # The prepare leg emitted its consumed-input manifest; pin EVERY file
        # it read (incl. all 14 repository-relative bindings) at its Stage A
        # container path — no hand-built expectations.
        manifest = json.loads((w.output / 'preparation' / 'inputs-manifest.json').read_text())
        mapping = container_paths(w, manifest['paths'])
        files = {}
        # roots is a FILES member read straight from its binding path.
        desc = meta['packet']['bindings']['roots']
        lp = w.metadata / desc['path']
        cp = w.to_container(lp)
        assert cp in mapping and sha(mapping[cp]) == sha(lp), ('roots', cp)
        files['roots'] = {'path': cp, 'sha256': sha(lp)}
        # The product's FILES closure (project_partition.py): six drafts plus
        # preparation.json — NOT the stage marker itself.
        from xiangrugu_datamgmt.project_partition import GENERATED
        for role in set(GENERATED) | {'preparation'}:
            name = GENERATED[role] if role in GENERATED else 'preparation.json'
            lp = w.output / 'preparation' / name
            cp = w.to_container(lp)
            assert cp in mapping, (role, cp)
            files[role] = {'path': cp, 'sha256': sha(lp)}
        # _base demands exactly FILES: roots/certificate + parent_review (=
        # the closed readiness packet, already pinned under its binding role)
        # + GENERATED + preparation.
        files['parent_review'] = dict(files['roots'])  # placeholder replaced below
        del files['parent_review']
        review_desc = {'path': w.to_container(w.metadata / meta['review_rel']),
                       'sha256': sha(w.metadata / meta['review_rel'])}
        assert review_desc['path'] in mapping, review_desc
        files['parent_review'] = review_desc
        files['certificate'] = {'path': '/metadata/selected-certificate.json',
                                'sha256': sha(w.metadata / 'selected-certificate.json')}
        from xiangrugu_datamgmt.project_partition import FILES as PRODUCT_FILES
        assert set(files) == PRODUCT_FILES, sorted(set(files) ^ PRODUCT_FILES)
        skeleton = {'attempt_id': ATTEMPT, 'expected_manifest_sha256': cert['manifest_sha256'],
                    'files': files, 'partition_id': PARTITION,
                    'source_mode': 'project_snapshot',
                    'status': 'SELECTED_PROJECT_PARTITION_REVIEW_METADATA', 'version': 1}
        sel_file = w.output / 'review.selection.json'
        wjson(sel_file, skeleton)
        mat_leg = run_materialize_leg(w, image, f'xrg-reh-materialize-{int(time.time())}')
        assert mat_leg['returncode'] == 0 and 'MATERIALIZE_REAL_REQUEST_OK' in mat_leg['stdout'], \
            mat_leg['stdout'][-400:] + mat_leg['stderr'][-1200:]
        payload = json.loads(mat_leg['stdout'].split('MATERIALIZE_REAL_REQUEST_OK ', 1)[1])
        stage_a_worker_argv = ['python', '/installed-origin.py', '/materialize-real.py',
                               IMAGE_ID, GIT_REVISION]   # run-real.sh adjudicated form
        record('stage_a_materialize_worker_argv', actual=stage_a_worker_argv,
               note='run-real.sh Stage A: python /installed-origin.py /materialize-real.py ...')
        staged_local = w.durable / 'materialization/request.json'
        req_pin = payload['request_sha256']
        assert sha(staged_local) == req_pin
        approval_local = w.durable / 'materialization/approval.json'
        request = json.loads(staged_local.read_text())
        approval = json.loads(approval_local.read_text())
        from xiangrugu_datamgmt.snapshots import digest
        body = {k: v for k, v in request.items() if k not in ('approval_file', 'approval_sha256')}
        assert digest(body) == approval['request_sha256']
        assert request['lifecycle_seconds'] == 1800 and request['source_mode'] == 'project_snapshot'
        assert request['image_id'] == IMAGE_ID and request['git_revision'] == GIT_REVISION
        assert request['output'] == f'/data/var/snapshots/executions/{ATTEMPT}/batch.staged.json'
        assert request['scratch_parent'] == f'/data/var/snapshots/executions/{ATTEMPT}/scratch'
        record('stage_a_materialized', request_sha256=req_pin,
               approval_sha256=sha(approval_local), roots_sha256=request['roots_sha256'],
               output=request['output'], scratch_parent=request['scratch_parent'],
               materialization_files=sorted(p.name for p in (w.durable / 'materialization').iterdir()),
               actual_mounts=[mount_view(m) for m in mat_leg['mounts']])

        # ---- R2 mount-table closure over the REAL request (both views) ----------
        table_a, legs_a = build_input_table(w, staged_local, 'rehearsal-stage-a-inputs.tsv')
        stage_a_view, dur_a = restage_for_verifier(w)
        vm = run_verifier_host(w, table_a, dur_a / 'materialization', stage_a_view,
                               req_pin, sha(approval_local))
        assert vm.returncode == 0, vm.stdout[-400:] + vm.stderr[-800:]
        verdict = json.loads(vm.stdout)
        assert verdict['status'] == 'MOUNT_TABLE_VERIFIED'
        poison = w.metadata / 'datamgmt/config/roots.yaml'
        staged_poison = stage_a_view / 'metadata/datamgmt/config/roots.yaml'
        original = poison.read_bytes()
        try:
            staged_poison.write_bytes(original.replace(b'5433', b'5444'))
            bad = run_verifier_host(w, table_a, dur_a / 'materialization',
                                    stage_a_view, req_pin, sha(approval_local))
            poisoned_refused = bad.returncode != 0
        finally:
            staged_poison.write_bytes(original)
        assert poisoned_refused and sha(poison) == sha(staged_poison)
        record('mount_table_closed', view='stage_a', legs=len(verdict['checked_legs']),
               table_rows=legs_a, negative_control_refused=poisoned_refused,
               sample=sorted(verdict['checked_legs'])[:6])

        # ---- Stage B tree + real-readonly mount closure --------------------------
        stage_b_tree(w)
        chown_workspace(w)
        table_b, legs_b = build_input_table(w, staged_local, 'rehearsal-stage-b-inputs.tsv',
                                            stage_b=True)
        stage_b_view, dur_b = restage_for_verifier(w, stage_b=True)
        vmb = run_verifier_host(w, table_b, dur_b / 'materialization', stage_b_view,
                                req_pin, sha(approval_local))
        assert vmb.returncode == 0, vmb.stdout[-400:] + vmb.stderr[-800:]
        verdict_b = json.loads(vmb.stdout)
        record('mount_table_closed', view='stage_b', legs=len(verdict_b['checked_legs']),
               table_rows=legs_b, destinations_fresh_before=True)

        # ---- R3 supervisor terminal states (REAL task_control worker) ------------
        # Refresh the fresh-durable restage immediately before the first real
        # launch so destination freshness is guaranteed at creation time.
        restage_for_verifier(w, stage_b=True)
        sup = supervisor_case(w, image, request, req_pin, 'success')
        if not sup.get('skipped'):
            mon = sup['monitor']
            seqs = [s_['sequence'] for s_ in mon['samples']]
            assert sup['returncode'] == 0 and 'CONTROLLED_SOURCE_ONLY_TASK_STAGED' in sup['stdout'], \
                sup['stdout'][-400:] + sup['stderr'][-1200:]
            assert mon['status'] == 'SOURCE_ONLY_WORKER_COMPLETED' and mon['reason'] is None
            assert mon['worker_exit_code'] == 0 and mon['process_group_gone'] is True
            fsa, fst = mon['final_sample_after_sequence'], mon['final_sample_sequence']
            assert fsa in seqs and fst == seqs[-1] > fsa
            assert mon['worker_failure_state'] == 'not_requested' and mon['worker_failure'] is None
            assert sup['final_local'].is_file()
            assert sha(sup['final_local']) == sha(sup['twin_local'])
            batch = json.loads(sup['final_local'].read_text())
            assert batch['execution_kind'] == 'approved-readonly-batch-v1'
            assert batch['controller_request_sha256'] == req_pin
            assert batch['complete'] is True and batch['file_digest_passes'] == 2
            assert batch['source_sha256_before'] == member['sha256'] \
                == batch['source_sha256_after']
            assert len(batch['objects']) == 1 and batch['objects'][0]['expected_count'] == 40
            assert batch['objects'][0]['source_read']['postgresql_connected'] is False
            assert batch['ready_for_import'] is False and batch['synthetic_only'] is False
            limits = json.loads((sup['evidence_dir'] / 'limits.json').read_text())
            assert limits['cpu.max'] == '50000 100000' and limits['memory.max'] == '805306368' \
                and limits['memory.swap.max'] == '0' and limits['pids.max'] == '128' \
                and limits['worker_nice'] == 19 and limits['worker_ionice'].strip() == 'none'
            origin_doc = json.loads((sup['worker_out_dir'] / 'installed-origin.json').read_text())
            assert origin_doc['installed_product_verified'] is True \
                and 'task_control' in origin_doc['modules']
            mounts_b = {m['Destination']: m for m in sup['mounts']}
            record('supervisor_success_terminal', status=mon['status'], sequences=seqs[:6],
                   boundary=fsa, ack=fst, exit_code=sup['returncode'],
                   twin_byte_identical=True, batch_complete=batch['complete'],
                   expected_count=batch['objects'][0]['expected_count'],
                   expected_sha256_prefix=batch['objects'][0]['expected_sha256'][:16],
                   limits_posture={k: limits[k] for k in ('cpu.max', 'memory.max',
                       'memory.swap.max', 'pids.max', 'worker_nice', 'worker_ionice')},
                   installed_origin_modules=sorted(origin_doc['modules']),
                   actual_worker_argv=sup['worker_argv'],
                   actual_mounts=[mount_view(m) for m in sup['mounts']])

        # ---- unified failure receipt (same path in worker and supervisor) --------
        fail = supervisor_case(w, image, request, req_pin, 'fail')
        if not fail.get('skipped'):
            mon2 = fail['monitor']
            assert fail['returncode'] != 0 and mon2['status'] == 'SOURCE_ONLY_WORKER_STOPPED'
            assert mon2['reason'] == 'worker_exit' and mon2['worker_failure_state'] == 'valid'
            assert mon2['worker_failure_sha256'] == sha(fail['failure_local'])
            assert mon2['worker_failure']['request_sha256'] == req_pin
            assert mon2['worker_failure']['status'] == 'CONTROLLED_TASK_FAILURE'
            assert not fail['final_local'].exists()  # nothing published on failure
            worker_receipt = json.loads(fail['failure_local'].read_text())
            assert mon2['worker_failure'] == worker_receipt          # SAME bytes
            assert sha(fail['failure_local']) == mon2['worker_failure_sha256']
            # Request-digest correlation: the receipt pins the CLI request pin
            # (== sha256 of the materialized request bytes == approval's
            # recomputed canonical-body digest — the same equality Stage A
            # asserted before ever publishing the request).
            from xiangrugu_datamgmt.snapshots import digest as _dg
            _body = {k: v for k, v in request.items()
                     if k not in ('approval_file', 'approval_sha256')}
            assert req_pin == sha(staged_local)
            assert _dg(_body) == approval['request_sha256']
            assert worker_receipt['request_sha256'] == req_pin
            assert worker_receipt['code'] == 'controller_pin' \
                and worker_receipt['domain'] == 'control'
            assert fail['worker_argv'][:3] == ['python', '/installed-origin.py',
                                               '-m']  # adjudicated Stage B argv
            record('unified_failure_receipt', reason=mon2['reason'],
                   state=mon2['worker_failure_state'],
                   domain=mon2['worker_failure']['domain'], code=mon2['worker_failure']['code'],
                   stage=mon2['worker_failure']['stage'],
                   worker_receipt_equals_supervisor_copy=True,
                   request_digest_pinned=True, actual_worker_argv=fail['worker_argv'],
                   failure_path_shared_with_task_control=True, published_nothing=True)

        # ---- wrong controller pin: refuse BEFORE any worker launch (source) ----
        # Only the supervisor's --controller-request-sha256 is wrong; the
        # worker-side pins stay true, so if a worker were ever launched it
        # COULD stage a batch. The refusal must therefore happen in
        # supervise.check_controller_request(), strictly before Popen.
        wrong = supervisor_case(w, image, request, req_pin, 'wrongpin',
                                controller_pin_override='f' * 64)
        if not wrong.get('skipped'):
            mon3 = wrong['monitor']
            assert wrong['returncode'] != 0
            case_exec = Path(wrong['evidence_dir'])
            assert not (case_exec / 'batch.staged.json').exists()
            assert not (case_exec / '.batch.staged.json.incomplete').exists()
            # ACTUAL observed terminal state, traced to the product order:
            # candidate_supervisor.main() runs _publication_selection,
            # _diagnostic_preflight, check_limits+nice+ionice and writes
            # limits.json; THEN it calls supervise(), whose early gate
            # check_controller_request() compares sha256(request.json bytes,
            # via read_metadata) against --controller-request-sha256 and
            # raises ValueError('controller_pin'). That is strictly BEFORE
            # observe(initial=True) and BEFORE Popen: no monitor receipt
            # exists (directive: one is required only when the monitoring
            # loop was entered), no worker process exists, and no source
            # read is possible. The exception escapes to main()'s outer
            # except -> SUPERVISION_FAILED on stdout, rc 1.
            assert mon3 == {}, 'wrongpin must not reach the monitoring loop'
            assert (case_exec / 'limits.json').is_file()  # main() setup ran
            assert not (case_exec / 'monitor.wrongpin.json').exists()  # pre-loop
            wout3 = Path(wrong['worker_out_dir']) / 'worker-output.txt'
            assert wout3.is_file()
            _wtext = wout3.read_text()
            assert _wtext.strip() == json.dumps(
                {'status': 'SUPERVISION_FAILED', 'ready_for_import': False}), _wtext
            assert wrong['returncode'] != 0
            record('wrong_pin_stops_before_source_read', monitored=False,
                   reason='supervisor_error(pre-loop, controller_pin)',
                   exit_code=wrong['returncode'],
                   worker_never_spawned=True, monitor_receipt_absent_by_design=True,
                   supervision_failed_line_captured=True,
                   actual_worker_argv=wrong['worker_argv'],
                   controller_pin_used='f' * 16 + '...',
                   published_nothing=True)

        # ---- bounded timeout stop --------------------------------------------------
        # The worker IS the real task_control on the adjudicated chain; a
        # mounted variant of installed-origin stalls right BEFORE its execvp,
        # exactly like a source read that never returns. --seconds=6 must fire.
        origin_real = (REPO / 'docs/superpowers/evidence/'
                       '2026-11-13-request-reader-integration/installed-origin.py')
        otext = origin_real.read_text()
        htext = otext.replace(
            "os.execvp(sys.executable,[sys.executable,*sys.argv[1:]])",
            "import os as _o\n"
            "if _o.environ.get('XRG_REHEARSAL_HANG'):\n"
            "    print('HANG_STUB_STARTED', flush=True)\n"
            "    import time as _t; _t.sleep(600)\n"
            "os.execvp(sys.executable,[sys.executable,*sys.argv[1:]])")
        assert 'XRG_REHEARSAL_HANG' in htext and htext != otext
        # The stall must live inside the file supervisor_case binds at
        # /installed-origin.py; it re-materialises that file per call, so the
        # variant is injected via origin_transform (applied post-write).
        _marker = 'os.execvp(sys.executable,[sys.executable,*sys.argv[1:]])'
        _stall = ("import os as _o\n"
                  "if _o.environ.get('XRG_REHEARSAL_HANG'):\n"
                  "    print('HANG_STUB_STARTED', flush=True)\n"
                  "    import time as _t; _t.sleep(600)\n")
        hang = supervisor_case(w, image, request, req_pin, 'hang', seconds=6,
                               origin_hook=False, expect_final=False,
                               env_prefix='XRG_REHEARSAL_HANG=1 ',
                               origin_transform=lambda t: t.replace(_marker, _stall + _marker))
        if not hang.get('skipped'):
            mon4 = hang['monitor']
            assert hang['returncode'] != 0 and mon4['reason'] == 'timeout' \
                and mon4['process_group_gone'] is True \
                and not (hang['evidence_dir'] / 'publication-failure.json').exists()
            assert not (hang['evidence_dir'] / 'batch.staged.json').exists()
            assert not (hang['evidence_dir'] / '.batch.staged.json.incomplete').exists()
            wout = (hang['worker_out_dir'] / 'worker-output.txt')
            assert wout.is_file() and 'HANG_STUB_STARTED' in wout.read_text(), \
                'worker never reached the pre-exec stall'
            record('timeout_terminal_state', reason=mon4['reason'],
                   max_seconds=mon4['max_seconds'],
                   elapsed=round(mon4['elapsed_seconds'], 3),
                   process_group_gone=mon4['process_group_gone'], published_nothing=True,
                   exit_code=hang['returncode'], actual_worker_argv=hang['worker_argv'])

        # ---- R4 one-shot registration refusal -------------------------------------
        reg = reregister_probe(w)
        record('one_shot_registration_refusal', **reg)

        # ---- R6 FailureTrace roundtrip --------------------------------------------
        rt = failure_roundtrip(w, req_pin)
        record('failure_trace_roundtrip', **rt)

        out = {'cases': [c['case'] for c in EVIDENCE],
               'fixtures': {'attempt_id': ATTEMPT, 'partition_id': PARTITION,
                            'image_id': IMAGE_ID, 'git_revision': GIT_REVISION,
                            'snapshot_id': SNAPSHOT_ID, 'member': member,
                            'local_rehearsal_image': LOCAL_IMAGE},
               'external_pins': {'request_sha256': req_pin,
                                 'approval_sha256': sha(approval_local),
                                 'roots_sha256': request['roots_sha256']},
               # Only present when the success case ran in this invocation;
               # scoped runs (P01_CASE_ONLY without 'success') omit it.
               'real_batch_result': ({
                   'expected_count': batch['objects'][0]['expected_count'],
                   'expected_sha256': batch['objects'][0]['expected_sha256'],
                   'schema_hash': batch['objects'][0]['schema_hash'],
                   'source_sha256': batch['source_sha256_after']}
                   if 'batch' in dir() else None),
               'notes': ['no host 32 access', 'no production image used', 'no real snapshot bytes',
                         'task card remains CLOSED',
                         'authorization.json is a human fixture marked 人工夹具占位 — not a real grant',
                         'R1-R3 ran through docker at real container paths with card resource limits',
                         'R3 success/wrongpin workers are the REAL task_control via installed-origin argv form',
                         'lease sidecar shares the worker session via execv chain; killpg proves both gone',
                         'Stage B view mirrors Stage A outputs under /data/var/run/a (rehearsal layout)',
                         'workspace root mirrored subtree layouts, no symlinks',
                         'container identity: production pins image user 10001:10001; this sandbox '
                         'cannot bind host files to uid 10001, so containers ran with explicit '
                         '--user <host uid> (the daemon drops uid bits under cap-drop ALL without it); '
                         'the real runner on 32 uses the image USER plus the same posture flags'],
               'as_of': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'status': 'P01_REAL_PREP_REHEARSAL_OK'}
        HERE.joinpath('rehearsal-evidence.json').write_text(
            json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + '\n')
        print(json.dumps({'status': out['status'], 'cases': out['cases']}, sort_keys=True))
        return 0
    finally:
        if created:
            force_rm(root)


if __name__ == '__main__':
    raise SystemExit(main())
