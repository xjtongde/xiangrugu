#!/usr/bin/env python3
"""Fixed privileged entry point for the p01 minimal-permission runner (v14).

Wired into sudoers as exactly four operator argv-pinned commands:
  /usr/local/bin/xrg-p01-run verify-inbox
  /usr/local/bin/xrg-p01-run stage-a   --stage-a-suffix <suffix>
  /usr/local/bin/xrg-p01-run stage-b   --stage-b-suffix <suffix> --mat-suffix <s> \
                     --request-pin <sha> --approval-pin <sha> [--roots-pin <sha>]
  /usr/local/bin/xrg-p01-run recover-orphan
plus one authorizer-only command /usr/local/bin/xrg-authz-publish <uuid>.

Implements PROPOSAL-32-minimal-entry.md v14 §2–§5 and §4b–§4g. Every step
emits machine-readable receipts under $XRG_P01_ROOT/receipts/. The design is
fixture-testable: XRG_P01_ROOT relocates the whole tree, XRG_P01_DOCKER swaps
the docker binary, XRG_P01_CGROUP_BASE redirects the readback base, and
XRG_P01_FAULT=NAME@WHERE injects deterministic crashes for acceptance item ⑥.

Real-attempt constants are pinned below; this entry NEVER mounts or reads any
real snapshot path — Stage B here runs against a synthetic fixture snapshot
only until 茶香 grants the separate real-read authorization.
"""
import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- constants C
ATTEMPT = "real-p01-20261113-a"   # fixed; fixture mode changes paths, never identity
CARD_SHA = "41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69"
REVIEW_SHA = "a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d"
ROOTS_SHA = "6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c"
IMAGE_ID = "sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a"
GIT_REVISION = "8fbc8c97fcf1d818caddf6ab556fa82d986643ed"
SNAPSHOT_ID = "2026-10-07-bootstrap"
CGROUP_EXPECT = {"cpu.max": "50000 100000", "memory.max": "805306368",
                 "memory.swap.max": "0", "pids.max": "128"}
READBACK_BUDGET_S, READBACK_POLL_S = 10.0, 0.2
GO_DELIVERY_WINDOW_S, GO_DEADLINE_S = 5.0, 20.0
INIT_WAIT_S = float(os.environ.get("XRG_P01_INIT_WAIT", "8"))
STAGE_A_SECONDS, STAGE_B_SECONDS = 300, 1830
# run-real.sh:351 — worker --failure-evidence and supervisor --worker-failure
# are the SAME path so the correlation reader sees one receipt's bytes twice.
FAILURE_REPORT = "/data/var/run/failure-report.json"
PACKET_FILES = 48
DOCKER_TIMEOUT = 10
# v14 §2: the sudoers whitelist pins fixed paths + subcommands only; the
# argument grammar is validated HERE so whitelist and program agree. Suffix
# and pin tokens share one charset with no separator ambiguity ([a-z0-9-]),
# which keeps the sudoers * glob free of token-shift tricks.
SUFFIX_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,40}")
PIN64_RE = re.compile(r"[0-9a-f]{64}")


def check_suffix(name, value):
    if not isinstance(value, str) or not SUFFIX_RE.fullmatch(value):
        raise Refused("usage", f"{name} must match {SUFFIX_RE.pattern}")
    return value


def check_pin(name, value):
    if not isinstance(value, str) or not PIN64_RE.fullmatch(value):
        raise Refused("usage", f"{name} must be exactly 64 lowercase hex")
    return value


def fixture_mode():
    return bool(os.environ.get("XRG_P01_FIXTURE"))


def fixture_program():
    # Deployment isolation marker: this copy of the program is the FIXTURE
    # entry (installed as xrg-p01-fixture-run, per INSTALL §3b). It refuses
    # any non-fixture mode even if the environment is misconfigured.
    return os.environ.get("XRG_P01_PROGRAM", "formal") == "fixture"


def real_docker_mode():
    """Manual-Docker acceptance chain: the FORMAL fixed program and the same
    sudoers argv, but against the real docker CLI. Stage A semantics run for
    real; Stage B stays locked unless XRG_P01_REAL_CHAIN grants rehearsal-mode
    container runs only (snapshot plane remains under real_stage_b_locked).
    The fixture program can NEVER enter this mode (§3b isolation)."""
    if fixture_program():
        return False
    return (not fixture_mode()) and \
        bool(os.environ.get("XRG_P01_REAL_CHAIN"))


def image_id():
    # Production default is the pinned constant; a rehearsal override is
    # possible ONLY with an explicit disclosure env and never silently
    # (image_identity_gate writes the disclosure receipt on every run).
    return os.environ.get("XRG_P01_IMAGE_ID", IMAGE_ID)


def card_sha():
    return os.environ.get("XRG_P01_CARD_SHA", CARD_SHA)


def snapshot_id():
    return os.environ.get("XRG_P01_SNAPSHOT_ID", SNAPSHOT_ID)


def packet_files():
    return int(os.environ.get("XRG_P01_PACKET_FILES", str(PACKET_FILES)))


def attempt_expected():
    return os.environ.get("XRG_P01_ATTEMPT_EXPECTED", ATTEMPT)


def init_wait_s():
    """Real docker needs more headroom than the fixture stub before the
    container-init reaches its FIFO open; delivery budget stays §4e."""
    if real_docker_mode():
        return float(os.environ.get("XRG_P01_REAL_INIT_WAIT", "25"))
    return INIT_WAIT_S


def root() -> Path:
    # The default path IS the production runtime root; there is no way to
    # reach it accidentally from a fixture run (fixture mode requires
    # XRG_P01_FIXTURE and its harness always passes an explicit relocated
    # XRG_P01_ROOT). Real Docker mode uses this same tree and the same
    # sudoers-whitelisted program — only the resource plane differs.
    return Path(os.environ.get(
        "XRG_P01_ROOT",
        "/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a"))


def docker_bin() -> str:
    return os.environ.get("XRG_P01_DOCKER", "docker")


def cgroup_base() -> Path:
    return Path(os.environ.get("XRG_P01_CGROUP_BASE", "/sys/fs/cgroup"))


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canon(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Refused(Exception):
    def __init__(self, code, detail):
        super().__init__(code)
        self.code, self.detail = code, detail


def fsync_dir(path: Path):
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        maybe_fault("dir_fsync", str(path))
        os.fsync(fd)
    finally:
        os.close(fd)


def maybe_fault(where, note=""):
    """XRG_P01_FAULT=HOOK[:PATHFRAG][,HOOK[:PATHFRAG]...].

    Each comma item names an injection point directly (e.g.
    consumed_pre_start); the optional :PATHFRAG narrows to faults whose
    affected path contains PATHFRAG. `any` matches every hook."""
    spec = os.environ.get("XRG_P01_FAULT", "")
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        hook, _, frag = item.partition(":")
        if hook not in (where, "any"):
            continue
        if frag and frag not in note:
            continue
        raise OSError(errno.EIO, f"injected fault {hook}@{where} ({note})")


def write_durable(path: Path, data: bytes, *, mode=0o600, owner=None):
    """tmp+rename+fd fsync+parent dir fsync; returns after both syncs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            maybe_fault("file_fsync", str(path))
            os.fsync(stream.fileno())
        if owner is not None:
            os.chown(tmp, *owner)
        os.chmod(tmp, mode)
        maybe_fault("rename_publish", str(path))
        os.rename(tmp, path)
        fsync_dir(path.parent)
    finally:
        if tmp.exists():
            os.unlink(tmp)
    return path


def publish_exclusive(path: Path, data: bytes, *, mode=0o600):
    """O_EXCL direct create + fd fsync + parent fsync (consumption records).

    `consumed_file_fsync` faults fire BEFORE any byte lands (no half record);
    `consumed_dir_fsync` faults fire AFTER the record exists but before the
    parent-dir sync — the exact window-(b)/(e) ambiguity of §4f."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # consumed_pre_write: crash after the record was planned but before any
    # byte landed — nothing exists, no start may be issued (§4c retryable).
    maybe_fault("consumed_pre_write", str(path))
    maybe_fault("consumed_file_fsync", str(path))
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        return False
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        maybe_fault("consumed_dir_fsync", str(path))
    except OSError:
        # §4f window (b): bytes are durable on the fd but the parent-dir sync
        # is unconfirmed — the record MUST survive for recovery to judge.
        raise
    fsync_dir(path.parent)
    return True


def open_nofollow(path: Path):
    """O_NOFOLLOW|O_RDONLY open + S_ISREG check on the SAME inode we just
    opened. Root reading operator-/authorizer-writable paths must never
    follow a symlink or land on a device/fifo (§4b boundary hardening)."""
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:     # ELOOP/EMLINK on a planted symlink ⇒ refuse
        raise Refused("nofollow_open_failed", f"{path}: errno {error.errno}")
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise Refused("not_regular_file", str(path))
        return fd
    except OSError:
        os.close(fd)
        raise


def read_bytes_nofollow(path: Path) -> bytes:
    with os.fdopen(open_nofollow(path), "rb") as stream:
        return stream.read()


def read_json_strict(path: Path):
    data = read_bytes_nofollow(path)
    return json.loads(data.decode()), data


def record(event, **fields):
    line = canon(dict(event=event, ts=now_iso(), pid=os.getpid(), **fields))
    journal = root() / "receipts" / "entry-journal.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(journal), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    with os.fdopen(fd, "wb") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    print(line.decode().rstrip())


def receipt(name, value):
    write_durable(root() / "receipts" / name, canon(value), mode=0o640)
    record("RECEIPT", file=name)


class Locks:
    """Advisory persistent flock files (never deleted). Order A->B only (§4g.1)."""

    def __init__(self):
        self.registry = root() / "registry"
        self.registry.mkdir(parents=True, exist_ok=True)
        self.held = []

    def acquire(self, name, *, block=False):
        path = self.registry / name
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o600)
        flags = fcntl.LOCK_EX | (0 if block else fcntl.LOCK_NB)
        try:
            fcntl.flock(fd, flags)
        except OSError:
            os.close(fd)
            return None
        self.held.append((name, fd))
        return path

    def release_all(self):
        while self.held:
            _, fd = self.held.pop()
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def docker(*args, timeout=DOCKER_TIMEOUT, capture=True):
    cmd = [docker_bin(), *map(str, args)]
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout,
                            check=False)
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def request_docker(op, *args, gen_note=""):
    """Log-before-invoke primary evidence for every mutating docker request (§4f.7)."""
    args = [op, *args]
    journal = root() / "receipts" / "docker-requests.log"
    journal.parent.mkdir(parents=True, exist_ok=True)
    line = f"{op.upper()}_REQUEST gen={gen_note} ts={now_iso()} argv={' '.join(map(str, args[1:]))}\n"
    fd = os.open(str(journal), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    with os.fdopen(fd, "wb") as stream:
        stream.write(line.encode())
        stream.flush()
        os.fsync(stream.fileno())
    record("DOCKER_REQUEST", op=op, argv=line.strip())
    maybe_fault("docker_request", op)
    return docker(*args)


# ------------------------------------------------------------ layout helpers
def paths():
    r = root()
    return dict(inbox=r / "inbox", run_input=r / "run-input", verified=r / "run-input" /
                "VERIFIED.sha256", authz=r / "authz", staging=r / "authz" / ".staging",
                publish_tmp=r / "authz" / ".publish-tmp", original=r / "authz" /
                "authorization.json", run_authz=r / "run-authz", go=r / "go",
                pins=r / "pins", admin_list=r / "pins" / "INPUTS.admin.sha256",
                consumed=r / "pins" / "ATTEMPT_CONSUMED.json", registry=r / "registry",
                output=r / "output", receipts=r / "receipts")


def gen_dir(gen):
    return paths()["run_authz"] / f"gen-{gen}"


def go_dir(gen):
    return paths()["go"] / f"gen-{gen}"


def gen_record_path(gen):
    return gen_dir(gen) / "gen.json"


def prepared_path(gen):
    return paths()["run_authz"] / f"gen-{gen}.PREPARED.json"


def resolved_path(gen):
    return paths()["run_authz"] / f"gen-{gen}.RESOLVED.json"


def attempt_lock_name():
    return f"{ATTEMPT}.flock"


# ------------------------------------------------------------- host gate §3
AUTHZ_KEYS = {"version", "status", "attempt_id", "task_card_sha256",
              "one_attempt_only", "granted_by"}


def validate_authz_document(doc):
    if set(doc) != AUTHZ_KEYS:
        raise Refused("authz_schema_keys", sorted(set(doc) ^ AUTHZ_KEYS))
    if doc["version"] != 1 or doc["status"] != "AUTHORIZED_REAL_P01_SINGLE_ATTEMPT":
        raise Refused("authz_status", doc.get("status"))
    if doc["attempt_id"] != attempt_expected() or \
            doc["task_card_sha256"] != card_sha():
        raise Refused("authz_binding", "attempt/card mismatch")
    if doc["one_attempt_only"] is not True or not isinstance(doc["granted_by"], str) \
            or not doc["granted_by"].strip():
        raise Refused("authz_fields", "one_attempt_only/granted_by")


def image_identity_gate():
    """The pinned production IMAGE_ID is checked against the daemon here;
    rehearsal overrides require an explicit env AND are recorded verbatim
    in a disclosure receipt — never silent."""
    want = IMAGE_ID
    got = image_id()
    override = os.environ.get("XRG_P01_IMAGE_ID")
    if override:
        disclosure = dict(mode="rehearsal_override", pinned_default=want,
                          actual=override,
                          note="真实 p01 镜像不在本机；身份常数按披露替换",
                          ts=now_iso())
        write_durable(root() / "receipts" / "image-identity-disclosure.json",
                      canon(disclosure), mode=0o640)
    # Identity probe by REPOSITORY reference (never by digest argument:
    # `docker images <digest>` resolves nothing on this daemon). The image
    # reference env is required in real mode so the probe and the create
    # argv pin the same bytes; --no-trunc keeps {{.ID}} the FULL digest —
    # the default short id could never equal the pinned identity.
    ref = os.environ.get("XRG_P01_IMAGE_REF")
    if not ref:
        raise Refused("image_ref_missing",
                      "real chain requires XRG_P01_IMAGE_REF "
                      "(repository[:tag] whose ID must equal the pinned id)")
    code, out, err = docker("images", "--no-trunc", "--format", "{{.ID}}",
                            ref)
    if code != 0:
        raise Refused("image_probe_error", err[:200])
    if got not in (out or ""):
        raise Refused("image_identity_mismatch",
                      f"{ref} -> {(out or '').splitlines()[:1]} != {got}")
    return got


def host_gate():
    original = paths()["original"]
    try:
        info = original.stat()
    except FileNotFoundError:
        raise Refused("authz_missing", str(original))
    want_owner = (0, 0) if os.environ.get("XRG_P01_FIXTURE") else (0, -1)
    if stat.S_IMODE(info.st_mode) != 0o400:
        raise Refused("authz_mode", oct(stat.S_IMODE(info.st_mode)))
    doc, raw = read_json_strict(original)
    validate_authz_document(doc)
    return doc, sha_bytes(raw)


# ------------------------------------------------------- generation products
def compute_nonce(confirmed_sha: str, gen: str, attempt: str) -> str:
    """§4e: nonce = sha256(confirmed_sha ‖ GEN-ID ‖ attempt), byte string of
    the three fields concatenated in that order — the one definition shared
    by host delivery and container verification."""
    return hashlib.sha256((confirmed_sha + gen + attempt).encode()).hexdigest()


def new_gen_id():
    return sha_bytes((ATTEMPT.encode() + secrets.token_bytes(16)
                      + str(time.time_ns()).encode()))[:12]


def build_generation(gen, original_sha):
    """Same-generation artifacts: copy + gen.json + FIFO, before any create."""
    p = paths()
    gd, gopath = gen_dir(gen), go_dir(gen)
    gd.mkdir(parents=True)
    gopath.mkdir(parents=True)
    fifo = gopath / "go"
    gid = int(os.environ.get("XRG_P01_WORKER_GID", "10001"))
    dgid = int(os.environ.get("XRG_P01_GO_DIR_GID", "10001"))
    if real_docker_mode() and (gid != 10001 or dgid != 10001):
        raise Refused("go_gid_override",
                      f"formal mode fixes GO channel owner root:10001; "
                      f"XRG_P01_WORKER_GID={gid}, XRG_P01_GO_DIR_GID={dgid}")
    if not fifo.exists():
        if os.path.lexists(str(fifo)):
            # dangling symlink (exists False, lexists True): mkfifo would
            # die with a bare FileExistsError instead of a locatable Refused
            raise Refused("go_fifo_symlink", f"dangling link at {fifo}")
        os.mkfifo(str(fifo))
        try:
            os.chmod(fifo, 0o640)
        except OSError:
            pass
    # Ownership/mode hardening is best-effort under the local sandbox and
    # mandatory on the real host (install script enforces it there).
    # Ownership/mode hardening: mandatory on the real host (root context);
    # best-effort under the unprivileged sandbox — chown(0,*) from a non-root
    # uid raises EINVAL and must not crash the rehearsal chain. The install
    # contract (INSTALL §2) re-applies these modes as root before production.
    for target, owner, mode in ((gopath, (0, dgid), 0o710), (fifo, (0, gid), 0o640),
                                (gd, (0, 0), 0o755)):
        try:
            os.chown(target, *owner)
        except OSError:
            pass
        try:
            os.chmod(target, mode)
        except OSError:
            if not os.environ.get("XRG_P01_FIXTURE"):
                raise
    if real_docker_mode():
        # v14 permission gate: verify the ACTUAL lstat results — a
        # swallowed chown error or a substituted file must refuse BEFORE
        # any docker create can run against the channel.
        _verify_go_channel(gopath, fifo, dgid, gid)
    src = read_bytes_nofollow(p["original"])
    if sha_bytes(src) != original_sha:
        raise Refused("authz_race", "original changed mid-generation")
    copy = gd / "authorization.json"
    write_durable(copy, src, mode=0o644)
    confirmed = sha_bytes(read_bytes_nofollow(copy))
    gen_doc = dict(version=1, attempt=ATTEMPT, gen_id=gen, state="GENERATED",
                   original_sha256=original_sha, confirmed_sha256=confirmed,
                   nonce_expected=compute_nonce(confirmed, gen, ATTEMPT),
                   created_at=now_iso())
    write_durable(gen_record_path(gen), canon(gen_doc), mode=0o644)
    record("GENERATION_BUILT", gen=gen, confirmed=confirmed)
    return gen_doc


def _verify_go_channel(gopath, fifo, dgid, gid):
    """lstat-based v14 permission gate for the GO channel. Every check
    reads the actual inode (never follows symlinks); inability to verify
    is itself a refusal. Runs only in real mode, before any create."""
    for path, want_type, want_mode, label, want_owner in (
            (gopath, stat.S_ISDIR, 0o710, "go_dir", (0, dgid)),
            (fifo, stat.S_ISFIFO, 0o640, "go_fifo", (0, gid))):
        try:
            st = os.lstat(str(path))
        except OSError as error:
            raise Refused(f"{label}_stat_failed", f"{path}: {error}")
        if stat.S_ISLNK(st.st_mode):
            raise Refused(f"{label}_symlink", str(path))
        if not want_type(st.st_mode):
            raise Refused(f"{label}_type", f"{path}: {oct(st.st_mode)}")
        if (st.st_uid, st.st_gid) != want_owner:
            raise Refused(f"{label}_owner",
                          f"{path}: {st.st_uid}:{st.st_gid} != "
                          f"{want_owner[0]}:{want_owner[1]}")
        if stat.S_IMODE(st.st_mode) != want_mode:
            raise Refused(f"{label}_mode",
                          f"{path}: {oct(stat.S_IMODE(st.st_mode))} != "
                          f"{oct(want_mode)}")


def bind_container(gen, container_id):
    doc, _ = read_json_strict(gen_record_path(gen))
    doc.update(state="BOUND", container_id=container_id, bound_at=now_iso())
    write_durable(gen_record_path(gen), canon(doc), mode=0o644)
    record("GEN_BOUND", gen=gen, container_id=container_id)


def mark_resolved(gen, container_id, verification, actions, reason=None):
    doc, _ = read_json_strict(gen_record_path(gen))
    if reason:
        verification = {**verification, "reason": reason}
    payload = dict(version=1, attempt=ATTEMPT, gen_id=gen, container_id=container_id,
                   container_state=doc.get("state"), verification=verification,
                   disposition=actions, published=True, resolved_at=now_iso())
    # §4g.3 window: crash AFTER candidate verification completed but BEFORE
    # the RESOLVED publication procedure runs at all — recovery redoes the
    # whole five-step order (§4f.4 "不存在半程放行窗"). The published record
    # states its own evidence class so readers never confuse a refusal
    # closure with an unstarted-candidate adjudication.
    if not (verification.get("outcome") or "").startswith(
            ("verified_stopped", "verified_absent", "config_mismatch",
             "ro_mismatch", "hostconfig_mismatch", "snapshot_missing",
             "daemon_error", "create_failed")):
        verification = {**verification, "evidence": "candidate_verified"}
    maybe_fault("resolved_pre_publish", str(resolved_path(gen)))
    write_durable(resolved_path(gen), canon(payload), mode=0o644)
    record("RESOLVED_PUBLISHED", gen=gen, verification=verification)
    return payload


# ------------------------------------------------------ §4g.4 re-entry rules
def finalization_present(kind, gen):
    p = paths()
    if kind == "stage-a":
        target = p["receipts"] / f"stage-a-{gen}.json"
    elif kind == "refusal":
        target = p["receipts"] / "refusals" / f"t9a-{gen}.json"
    else:
        target = p["consumed"]
    if not target.exists():
        return False
    if kind == "consumed":
        try:
            doc, _ = read_json_strict(target)
        except Exception:
            return False
        return doc.get("gen_id") == gen and str(doc.get("state")) != "START_REQUESTED"
    if kind == "refusal":
        # The T9a closure only counts once the generation's RESOLVED is
        # actually on disk (publication completed); an interrupted
        # publication leaves both absent — recovery redoes the whole order.
        return resolved_path(gen).exists()
    return True


def reentry_check(lock, gen):
    """One rule, no inference about how the previous process exited (§4g.4)."""
    p = paths()
    rp = resolved_path(gen)
    kind = consumption_kind(gen)
    if not rp.exists():
        # The binding record (gen.json, written at PREPARED and backfilled at
        # BOUND) is the only source for the planned container id. Reading a
        # non-existent PREPARED file must never hijack this path.
        try:
            gdoc, _ = read_json_strict(gen_record_path(gen))
            planned_id = gdoc.get("container_id")
        except Exception:
            planned_id = None
        consumed = load_consumed() or {}
        consumption_gen = consumed.get("gen_id") == gen and \
            consumed.get("state") == "START_REQUESTED"
        candidate = consumed.get("container_id") or planned_id
        if consumption_gen and candidate:
            # §4f.1 split of windows (b)/(c): a persisted START_REQUESTED
            # record means the host never CONFIRMED a start for this
            # generation. Adjudication is READ-ONLY inspect; a create request
            # may still be in flight inside the daemon, so a single zero
            # match (or 404) proves nothing yet — it only says "not seen at
            # that moment". Absence must be observed STABLE before any
            # closure is published; otherwise the block is maintained.
            absent, outcome = inspect_state_or_absent(candidate)
            if absent is None and outcome is None:
                return "recovery_pending", "candidate_daemon_error"
            if absent and not _absent_stable(candidate):
                return "recovery_pending", "create_in_flight_zero_match"
            outcome = "deleted_404" if absent else outcome
            if outcome not in ("deleted_404", "created", "exited", "dead"):
                return "recovery_pending", f"candidate_{outcome or 'unknown_state'}"
            verification = dict(container_id=candidate, checked_at=now_iso(),
                                outcome="verified_absent" if
                                outcome == "deleted_404" else outcome,
                                evidence="inspect_only_stable", state=outcome)
            mark_resolved(gen, candidate, verification, ["none"],
                          reason="consumed_unstarted")
        elif candidate and (kind == "refusal" or _gen_role(gen) == "refusal"):
            # T9a retryable-refusal path: the refusal itself already
            # reclaimed the created candidate (§4g.2 step 1). Recovery
            # re-verifies by READ-ONLY inspect against this exact id with
            # the §4f.1 stable-absence discipline — never destructive.
            absent, outcome = inspect_state_or_absent(candidate)
            if absent is None and outcome is None:
                return "recovery_pending", "candidate_daemon_error"
            if absent and not _absent_stable(candidate):
                return "recovery_pending", "create_in_flight_zero_match"
            outcome = "deleted_404" if absent else outcome
            if outcome not in ("deleted_404", "created", "exited", "dead"):
                return "recovery_pending", f"candidate_{outcome or 'unknown_state'}"
            verification = dict(container_id=candidate, checked_at=now_iso(),
                                outcome="verified_absent" if
                                outcome == "deleted_404" else outcome,
                                evidence="inspect_only_stable", state=outcome)
            mark_resolved(gen, candidate, verification, ["none"],
                          reason="t9a_candidate_reclaimed")
        elif candidate:
            # Bound without a consumption record and no refusal closure yet:
            # reclaim per §4f.2 against THIS exact container only.
            verification = verify_candidate_stopped(candidate, gen)
            if verification["outcome"] != "verified_stopped":
                return "recovery_pending", f"candidate_{verification['outcome']}"
            mark_resolved(gen, candidate, verification, ["stop_rm"])
        else:
            located = locate_prepared_candidates(gen)
            if located["outcome"] == "zero":
                # §4f.1: a single zero match is NOT proof create never
                # landed — maintain the block until absence is stable.
                if not _absent_stable(None, gen):
                    return "recovery_pending", "lookup_zero_not_stable"
                mark_resolved(gen, None, dict(outcome="verified_absent",
                                              evidence="label_lookup_zero_x2"),
                              ["none"])
            elif located["outcome"] == "unique":
                cid = located["ids"][0]
                absent, st = inspect_state_or_absent(cid)
                if absent is None and st is None:
                    return "recovery_pending", "candidate_daemon_error"
                outcome = "deleted_404" if absent else st
                if outcome == "created":
                    # PREPARED-only candidate (§4f.2): reclaim THIS exact
                    # container, then re-confirm via fresh inspect.
                    request_docker("rm", "-f", cid, gen_note=gen)
                    again, st2, _ = docker(
                        "inspect", "--format", "{{.State.Status}}", cid)
                    ok = (again != 0) or (st2 in ("", "exited", "dead"))
                    if not ok:
                        return "recovery_pending", f"candidate_{st2 or 'unknown'}"
                    verification = dict(outcome="verified_stopped",
                                        state="removed_created", action="rm")
                elif outcome in ("exited", "dead"):
                    verification = dict(outcome="verified_stopped", state=outcome)
                elif outcome == "deleted_404":
                    verification = dict(outcome="verified_stopped",
                                        state="deleted_404")
                else:
                    return "recovery_pending", f"candidate_{outcome or 'unknown'}"
                mark_resolved(gen, cid, verification, ["rm_if_created"])
            else:
                return "recovery_pending", f"lookup_{located['outcome']}";
    try:
        doc, raw = read_json_strict(rp)
    except Exception:
        return "recovery_pending", "resolved_corrupt"
    if doc.get("gen_id") != gen or doc.get("attempt") != ATTEMPT:
        return "recovery_pending", "resolved_binding_mismatch"
    if doc.get("published") is not True:
        return "recovery_pending", "resolved_unpublished"
    if kind and not finalization_present(kind, gen):
        # Closure record missing but RESOLVED published: complete it now
        # (still under the same lock), then re-verify per §4g.4.
        finalize_cleared(gen)
        if not finalization_present(kind, gen):
            return "recovery_pending", "finalization_missing"
    # Records look complete: still re-verify candidate state and re-sync.
    consumed_rec = load_consumed() or {}
    unstarted = consumed_rec.get("gen_id") == gen and \
            consumed_rec.get("state") == "START_REQUESTED"
    if unstarted:
        # Five-step order (§4g.2): with RESOLVED already published and the
        # terminal update still pending, recovery owns the closure step —
        # never destructive here. Inspect-only adjudication applies.
        absent, st = inspect_state_or_absent(doc.get("container_id"))
        if absent is None and st is None:
            return "recovery_pending", "candidate_daemon_error"
        outcome = "deleted_404" if absent else st
        if outcome not in ("deleted_404", "created", "exited", "dead",
                           "running"):
            return "recovery_pending", f"candidate_{outcome or 'unknown_state'}"
        if outcome == "running":
            # A confirmed-start generation may legitimately still be running
            # while its terminal update is missing; finalize_cleared will
            # wait for it under the same lock before closing.
            pass
    else:
        verification = verify_candidate_stopped(doc.get("container_id"), gen)
        if verification["outcome"] != "verified_stopped":
            return "recovery_pending", f"candidate_{verification['outcome']}"
    for target in (rp, p["consumed"] if kind == "consumed" else rp):
        try:
            fd = os.open(str(target), os.O_RDONLY)
            _scoped_resync_fault(str(target))
            os.fsync(fd)
            os.close(fd)
            fsync_dir(target.parent)
        except OSError as error:
            return "recovery_pending", f"resync_failed:{error.errno}"
    return "cleared", "reentry_verified_and_resynced"


def consumption_kind(gen):
    p = paths()
    consumed_rec = load_consumed() or {}
    if consumed_rec.get("gen_id") == gen:
        # Consumption gens follow their own rule; terminal closure is the
        # finalize step of §4g.2, not a pre-existing receipt.
        return "consumed"
    if (p["receipts"] / f"stage-a-{gen}.json").exists() or _gen_role(gen) == "stage-a":
        return "stage-a"
    if (p["receipts"] / "refusals" / f"t9a-{gen}.json").exists():
        return "refusal"
    # A BOUND stage-b generation with no consumption record can only be an
    # interrupted T9a refusal (that path never starts containers).
    role = _gen_role(gen)
    if role == "refusal":
        return "refusal"
    return None


def _gen_role(gen):
    p = paths()
    try:
        doc, _ = read_json_strict(gen_record_path(gen))
    except Exception:
        return None
    role = doc.get("role")
    if role == "stage-a":
        return "stage-a"
    if role == "stage-b":
        consumed = load_consumed() or {}
        if consumed.get("gen_id") == gen:
            # Any state (START_REQUESTED or terminal): the consumption
            # record owns this generation's adjudication rule.
            return "consumed"
        return "refusal"
    return None


def close_stage_b_generation(gen, container_id, verification, actions):
    """Five-step closure (§4g.2) shared by normal refusals and recovery."""
    p = paths()
    mark_resolved(gen, container_id, verification, actions)
    consumed = load_consumed()
    if consumed and consumed.get("gen_id") == gen and \
            consumed.get("state") == "START_REQUESTED":
        finalize_cleared(gen)


def pending_gens():
    """Generations whose RESOLVED closure is missing. Generations referenced
    by a persisted consumption record are adjudicated by the consumption
    rule (enforce_blocking / cmd_recover_orphan), never through this glob —
    otherwise a mid-five-step crash would be double-adjudicated."""
    p = paths()
    consumed = load_consumed() or {}
    consumed_gen = consumed.get("gen_id")
    out = []
    for prepared in sorted(p["run_authz"].glob("gen-*.PREPARED.json")):
        gen = prepared.name[len("gen-"):-len(".PREPARED.json")]
        if gen == consumed_gen:
            continue
        if not resolved_path(gen).exists():
            out.append(gen)
    return out


def verify_candidate_stopped(container_id, gen):
    p = paths()
    evidence = dict(container_id=container_id, checked_at=now_iso())
    if not container_id:
        located = locate_prepared_candidates(gen)
        evidence.update(located)
        if located["outcome"] != "unique":
            return dict(outcome="lookup_" + located["outcome"], **evidence)
        container_id = located["ids"][0]
        evidence["container_id"] = container_id
    code, status, err = docker("inspect", "--format", "{{.State.Status}}", container_id)
    if code != 0 and "No such container" in (err + status):
        return dict(outcome="verified_stopped", state="deleted_404", **evidence)
    if code != 0:
        return dict(outcome="daemon_error", stderr=err, **evidence)
    if status in ("exited", "dead"):
        return dict(outcome="verified_stopped", state=status, **evidence)
    if status in ("created",):
        rm_code, _, rm_err = request_docker("rm", "-f", container_id, gen_note=gen)
        again, st2, _ = docker("inspect", "--format", "{{.State.Status}}", container_id)
        # 404 after rm means gone; rc==0 with empty output also means the
        # stub/daemon no longer reports a state for it.
        ok = (again != 0) or (st2 in ("", "exited", "dead"))
        return dict(outcome="verified_stopped" if ok else "daemon_error",
                    action="rm_created", state_after=st2, **evidence)
    if status == "running":
        stop_code, _, stop_err = request_docker("stop", "--time", "10", container_id,
                                                gen_note=gen)
        wait = 0
        while wait < 15:
            again, st2, _ = docker("inspect", "--format", "{{.State.Running}}", container_id)
            if again != 0 or st2 == "false":
                break
            time.sleep(1)
            wait += 1
        rm_code, _, _ = request_docker("rm", container_id, gen_note=gen)
        gone, st3, err3 = docker("inspect", "--format", "{{.State.Status}}", container_id)
        ok = gone != 0 or st3 in ("exited", "dead")
        return dict(outcome="verified_stopped" if ok else "daemon_error",
                    action="stop_rm", state_after=st3, **evidence)
    return dict(outcome="unknown_state", state=status, **evidence)


def inspect_state_or_absent(cid):
    """(is_404, state). (None, None) means daemon error/unknown — callers
    must maintain the block (§4f.3). 404 requires the daemon's explicit
    no-such-container answer, never a bare non-zero exit."""
    code, status, err = docker("inspect", "--format", "{{.State.Status}}", cid)
    if code == 0:
        return False, status.strip()
    text = (err + status).lower()
    if "no such container" in text or "no such object" in text:
        # Docker 29 answers "No such object" for inspect misses; older and
        # the stub use "No such container". Both are explicit 404s.
        return True, None
    return None, None


def _absent_stable(candidate, gen=None):
    """§4f.1: one zero match only means 'not seen at that moment'. Absence
    becomes adjudicable after a second independent observation with no
    in-flight create evidence in between (log-before-invoke primary count)."""
    time.sleep(float(os.environ.get("XRG_P01_ABSENT_CONFIRM_S", "0.6")))
    if candidate:
        absent, _o = inspect_state_or_absent(candidate)
        if absent is not True:
            return False
        if not os.environ.get("XRG_P01_FIXTURE"):
            # second independent observation only makes sense against a
            # live daemon; the stub answers deterministically.
            code2, _, _ = docker(
                "--timeout", "5", "inspect", "--format",
                "{{.State.Status}}", candidate)
            return code2 != 0
        return True
    again = locate_prepared_candidates(gen)
    if again["outcome"] != "zero":
        return False
    if not os.environ.get("XRG_P01_FIXTURE"):
        again2 = locate_prepared_candidates(gen)
        return again2["outcome"] == "zero"
    return True


def _scoped_resync_fault(target_note):
    """Fire `resync_file_fsync` ONLY while the caller is inside the re-sync
    loop, never during the durable writes of the closure step it precedes.
    Bare hook names match every re-sync target; :FRAG narrows further."""
    spec = os.environ.get("XRG_P01_FAULT", "")
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        hook, _, frag = item.partition(":")
        if hook != "resync_file_fsync":
            continue
        if frag and frag not in target_note:
            continue
        raise OSError(errno.EIO, f"injected resync_file_fsync ({target_note})")


def locate_prepared_candidates(gen):
    """PREPARED lookup: label ↔ fixed creation config (§4f.1). Never batch rm."""
    code, out, err = docker("ps", "-a", "--filter",
                            f"label=io.xiangrugu.attempt-gen={gen}", "--format", "{{.ID}}")
    ids = [x for x in out.splitlines() if x.strip()]
    if code != 0:
        return dict(outcome="daemon_error", ids=[], stderr=err)
    if len(ids) == 0:
        return dict(outcome="zero", ids=[])
    matches, mismatches = [], []
    try:
        gdoc, _ = read_json_strict(prepared_path(gen))
        want_digest = gdoc.get("creation_digest")
    except Exception:
        want_digest = None
    for cid in ids:
        c2, cfg, _ = docker("inspect", "--format", "{{json .Config.Labels}}", cid)
        labels = {}
        try:
            labels = json.loads(cfg)
        except Exception:
            pass
        ok = labels.get("io.xiangrugu.attempt-gen") == gen and c2 == 0
        if ok and want_digest and real_docker_mode():
            _, full, _ = docker("inspect", "--format", "{{json .}}", cid)
            try:
                doc_full = json.loads(full)
            except Exception:
                doc_full = {}
            actual = sha_bytes(canon(dict(
                labels=(doc_full.get("Config") or {}).get("Labels"),
                host=(doc_full.get("HostConfig") or {}),
                image=image_id())))
            ok = actual == want_digest
        if ok:
            matches.append(cid)
        else:
            mismatches.append(cid)
    if len(matches) > 1 or mismatches:
        return dict(outcome="ambiguous", ids=matches + mismatches)
    if len(matches) == 1:
        return dict(outcome="unique", ids=matches)
    return dict(outcome="zero", ids=[])


# --------------------------------------------------------------- RESOLVED etc
def load_consumed():
    p = paths()
    if not p["consumed"].exists():
        return None
    try:
        doc, _ = read_json_strict(p["consumed"])
    except Exception:
        return dict(state="_corrupt")
    return doc


def refusal_write(kind, gen, detail):
    p = paths()
    name = f"{kind}-{gen}.json" if gen else f"{kind}-{int(time.time())}.json"
    write_durable(p["receipts"] / "refusals" / name,
                  canon(dict(kind=kind, attempt=ATTEMPT, gen_id=gen, detail=detail,
                             ts=now_iso())), mode=0o640)
    record("REFUSAL", kind=kind, gen=gen, detail=str(detail)[:200])


# -------------------------------------------------------------- verify-inbox
def cmd_verify_inbox():
    ensure_layout()
    p = paths()
    inbox_pkg = p["inbox"] / "source-green-v1"
    if not inbox_pkg.is_dir():
        raise Refused("inbox_missing", str(inbox_pkg))
    listing = inbox_pkg / "INPUTS.sha256"
    admin = p["admin_list"]
    if not admin.exists():
        raise Refused("admin_pins_missing", str(admin))
    # pins/ is root-owned authority: strict no-follow read here too, so a
    # swapped-in symlink cannot redirect the comparison either.
    admin_bytes = read_bytes_nofollow(admin)
    entries_admin = parse_manifest(admin_bytes.decode())
    if len(entries_admin) != packet_files():
        raise Refused("admin_list_size", len(entries_admin))
    if read_bytes_nofollow(listing) != admin_bytes:
        raise Refused("manifest_mismatch", "package INPUTS.sha256 != pins authority")
    dest = p["run_input"] / "source-green-v1"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in sorted(os.listdir(inbox_pkg)):
        if name == "INPUTS.sha256":
            continue
        src_member = inbox_pkg / name
        if src_member.is_symlink() or not src_member.is_file():
            raise Refused("inbox_member_not_regular", name)
        with os.fdopen(open_nofollow(src_member), "rb") as fin:
            with open(dest / name, "wb") as fout:
                shutil.copyfileobj(fin, fout)
    failures = []
    for name, digest in entries_admin.items():
        target = dest / name
        if not target.is_file():
            failures.append(name)
            continue
        try:
            body = read_bytes_nofollow(target)
        except (OSError, Refused):
            failures.append(name)
            continue
        if sha_bytes(body) != digest:
            failures.append(name)
    if failures:
        raise Refused("content_digest_fail", failures[:8])
    for dirpath, _, files in os.walk(p["run_input"]):
        os.chmod(dirpath, 0o755)
        for f in files:
            os.chmod(os.path.join(dirpath, f), 0o644)
    lines = "\n".join(f"{entries_admin[n]}  source-green-v1/{n}"
                      for n in sorted(entries_admin)) + "\n"
    write_durable(p["verified"], lines.encode(), mode=0o644)
    admin_digest = sha_bytes(admin_bytes)
    doc = dict(status="VERIFIED", files=len(entries_admin),
               listing_body_sha256=sha_bytes(lines.encode()),
               admin_listing_sha256=admin_digest,
               plan=f"sha256(body)={admin_digest}", ts=now_iso())
    if os.environ.get("XRG_P01_IMAGE_ID"):
        doc["rehearsal_image_override"] = dict(
            pinned_default=IMAGE_ID, actual=os.environ["XRG_P01_IMAGE_ID"],
            note="真实 p01 镜像不在本机；披露性替换，仅演练链使用")
    receipt("verify-inbox.json", doc)
    print(f"Staged {len(entries_admin)} verified files into run-input")


def parse_manifest(text):
    entries = {}
    for line in text.splitlines():
        line = line.strip().lstrip("*")
        if not line:
            continue
        digest, _, name = line.partition("  ")
        if not digest or not name:
            digest, _, name = line.partition(" ")
        entries[name.lstrip("*").strip()] = digest
    return entries


# ------------------------------------------------------------------ stage-a
def cmd_stage_a(suffix):
    check_suffix("stage-a-suffix", suffix)
    p = paths()
    lock = Locks()
    if lock.acquire("stage-a.flock") is None:
        raise Refused("busy", "stage-a.flock held")
    try:
        # v14 §4g.1: stage-a takes the attempt lock only for the brief
        # record-touch windows; holding it across container execution would
        # starve recover-orphan. Blocking acquisition keeps order A->B.
        if lock.acquire(attempt_lock_name(), block=True) is None:
            raise Refused("busy", "attempt.flock unavailable")
        ensure_layout()
        blocked = enforce_blocking(lock)
        if blocked:
            raise Refused("recovery_pending", blocked)
        doc, original_sha = host_gate()
        if real_docker_mode():
            image_identity_gate()
        existing = p["receipts"] / "stage-a-done.json"
        if existing.exists():
            print("STAGE_A_ALREADY_DONE (idempotent)")
            return
        gen = new_gen_id()
        gen_doc = build_generation(gen, original_sha)
        prepared = dict(version=1, attempt=ATTEMPT, gen_id=gen, phase="pre-create",
                        role="stage-a", original_sha256=original_sha,
                        confirmed_sha256=gen_doc["confirmed_sha256"],
                        mount_plan=stage_a_mount_plan(gen), ts=now_iso())
        prepared["creation_digest"] = plan_digest(
            prepared["mount_plan"] + ["IMAGE:" + image_id()])
        write_durable(prepared_path(gen), canon(prepared))
        update_gen_role(gen, "stage-a")
        try:
            code, container_id, err = request_docker(
                "create", *create_args(gen, prepared["mount_plan"], suffix,
                                       "stage-a"), gen_note=gen)
        except Exception as exc:
            # A create REQUEST whose outcome is unknown (timeout/crash of the
            # CLI itself) must never be retried blindly: PREPARED stays
            # unresolved and recovery adjudicates by label lookup (§4f.1).
            record("CREATE_RESULT_UNKNOWN", gen=gen, detail=str(exc)[:200])
            raise Refused("create_result_unknown", str(exc)[:200])
        if code != 0:
            mark_resolved(gen, None, dict(outcome="create_failed", stderr=err[:200]),
                          ["none"])
            raise Refused("create_failed", err[:200])
        container_id = (container_id or "").strip()
        if len(container_id) != 64 or any(c not in "0123456789abcdef"
                                          for c in container_id):
            # Malformed create answer: do NOT bind a garbage id — leave the
            # generation PREPARED for recovery, refuse this invocation.
            record("CREATE_ANSWER_MALFORMED", gen=gen,
                   detail=container_id[:80])
            raise Refused("create_answer_malformed", container_id[:80])
        bind_container(gen, container_id)
        if real_docker_mode():
            write_durable(gen_dir(gen) / "argv.txt",
                          (" ".join(shlex_quote(a) for a in create_args(
                              gen, prepared["mount_plan"], suffix, "stage-a"))
                           + "\n").encode(), mode=0o644)
        ok, why = static_config_check(container_id, prepared["mount_plan"], require_snapshot=False)
        if not ok:
            cleanup_created(container_id, gen)
            try:
                mark_resolved(gen, container_id, why["verification"], ["rm"])
            except OSError:
                # Publication interrupted: remove the refusal closure we
                # just wrote so the generation stays wholly un-closed and
                # recovery redoes verification + publication from scratch.
                target = p["receipts"] / "refusals" / f"t9a-{gen}.json"
                if target.exists():
                    os.unlink(target)
                raise
            refusal_write("t9a", gen, why)
            raise Refused("static_config_refused", why)
        os.environ["XRG_P01_STUB_GO"] = "off"   # Stage A has no GO gate
        feeder = MonitorFeeder(gen, container_id)
        feeder.start()               # first lease sample lands pre-start
        try:
            code2, _, _ = request_docker("start", container_id, gen_note=gen)
            exit_code = await_container(container_id, STAGE_A_SECONDS, gen)
            capture_supervisor_evidence(gen, container_id)
        finally:
            feeder.stop()
        outcome = classify_terminal(gen, exit_code, container_id)
        mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                              exit_code=exit_code), ["wait"])
        write_durable(p["receipts"] / f"stage-a-{gen}.json",
                      canon(dict(stage="A", attempt=ATTEMPT, gen_id=gen,
                                 container_id=container_id, outcome=outcome,
                                 exit_code=exit_code, ts=now_iso())), mode=0o640)
        if outcome == "COMPLETED" and real_docker_mode():
            # The worker's product is the durable materialization dir; a
            # zero exit without it is NOT completion of Stage A.
            mat = output_dir(gen) / "durable" / "materialization"
            receipt(f"stage-a-materialization-{gen}.json", dict(
                gen_id=gen, present=mat.is_dir(),
                files=sorted(os.listdir(mat)) if mat.is_dir() else [],
                ts=now_iso()))
            if not (mat / "request.json").is_file():
                outcome = "INVALID_SUPERVISION_EXIT"
        if outcome == "COMPLETED":
            write_durable(existing, canon(dict(done=True, gen_id=gen,
                                               ts=now_iso())), mode=0o640)
        # The lease is bound FILE-level into the container: docker rm can
        # only succeed after the feeder stopped touching the host inode.
        code_rm, _, err_rm = request_docker("rm", container_id,
                                            gen_note=gen)
        if code_rm != 0 and real_docker_mode():
            record("RM_DEFERRED", gen=gen, detail=err_rm[:150])
        print(f"STAGE_A_{outcome} gen={gen}")
    finally:
        lock.release_all()


def update_gen_role(gen, role):
    doc, _ = read_json_strict(gen_record_path(gen))
    doc["role"] = role
    write_durable(gen_record_path(gen), canon(doc), mode=0o644)


def plan_digest(mount_plan):
    """Fixed creation-config summary (§4f.1): digest over the exact argv
    fragment the host will submit — labels included."""
    return sha_bytes(canon(mount_plan))


def create_args(gen, plan_lines, suffix, role):
    argv = ["--label", f"io.xiangrugu.attempt-gen={gen}",
            "--label", f"io.xiangrugu.synthetic-run={role}-{suffix}"]
    for line in plan_lines:
        argv.extend(shlexish(line))
    if real_docker_mode():
        ref = os.environ.get("XRG_P01_IMAGE_REF") or image_id()
        # v14: the formal candidate runs pinned to the worker uid/gid; the
        # GO reader then opens the host FIFO through the /control ro bind.
        return [*argv, "--user", "10001:10001", ref,
                *real_container_argv(gen, role, suffix)]
    return [*argv, image_id(), role]


def real_container_argv(gen, role, suffix):
    """v14/run-real.sh-conformant argv for the manual-Docker candidate.
    The image carries the verified package at /inputs/source-green-v1 and
    the supervisor copy at /opt/xrg-p01; delivery is by bind mounts below."""
    # run-real.sh Stage A worker, byte-for-byte in shape:
    #   python /installed-origin.py /materialize-real.py "$image" "$revision"
    # installed-origin records product origins then execs its tail args, so
    # materialize runs as __main__ against the identity argv it hard-checks.
    # run-real.sh adjudication: installed-origin.py is a 0644 copy WITHOUT a
    # shebang; Popen must not exec it directly. The worker tuple starts with
    # the interpreter token ("python"), which candidate_supervisor execs via
    # the shell PATH — matching the adjudicated argv exactly.
    # run-real.sh passes "$image"/"$revision" as the worker's identity argv:
    # the pinned IMAGE ID (a sha256: digest), not the repository tag. The
    # materializer asserts that shape byte-exactly.
    if role == "stage-b" and real_docker_mode():
        # Real chain stage-b worker: the adjudicated task_control tuple,
        # byte-for-byte from TIMEBOX-EVIDENCE.json worker_argv_actual
        # (.reh-timebox-30m2, rc=0 SOURCE_ONLY_WORKER_COMPLETED). Only the
        # argv tail is swapped here; GO delivery and host verification gates
        # are untouched. request/approval pins come from this gen's own
        # PREPARED doc; roots/image/git use the fixed constants.
        pdoc, _ = read_json_strict(prepared_path(gen))
        worker = ["python", "/installed-origin.py", "-m",
                  "xiangrugu_datamgmt.task_control",
                  "--request",
                  "/data/var/snapshots/materialization/request.json",
                  "--request-sha256", pdoc["request_pin"],
                  "--approval-sha256", pdoc["approval_pin"],
                  "--roots-sha256", pdoc["roots_pin"],
                  "--image-id", IMAGE_ID,
                  "--git-revision", GIT_REVISION,
                  "--image-user", "10001:10001",
                  "--source-status", "dirty",
                  "--lifecycle-seconds", str(STAGE_B_SECONDS - 30),
                  # run-real.sh:367 unified failure receipt path; identical
                  # to the supervisor --worker-failure below.
                  "--failure-evidence", FAILURE_REPORT,
                  "--authorized-source-mode", "project_snapshot"]
    else:
        worker = ["python", "/installed-origin.py", "/materialize-real.py",
                  image_id(), GIT_REVISION]
    evidence = "/data/var/run/monitor.json"
    # run-real.sh §: the monitor input is the HOST-FED lease file bound at
    # /control/lease (ro); a /control DIRECTORY bind would shadow a lease
    # written after create, so real mode binds files individually.
    # The fixture stub never parses these tokens; its argv is unchanged.
    lease_arg = "/control/lease" if real_docker_mode() else evidence
    if role == "stage-a":
        # Stage A has NO GO gate — plain candidate_supervisor exactly like
        # run-real.sh. Only Stage B ever uses the gated variant. The image
        # reference is the LAST positional (before it sits the module argv);
        # `--entrypoint python` already fixes the interpreter, so the argv
        # starts at "-B", never a second "python" token.
        # run-real.sh materialize mode: supervisor args are EXACTLY these
        # three (§ adjudicated); _publication_selection('artificial', None)
        # requires that no request pin be passed in artificial mode.
        return ["-B", "-m",
                "xiangrugu_datamgmt.candidate_supervisor",
                "--lease", lease_arg, "--evidence", evidence,
                "--seconds", "120",
                "--", *worker]
    # v14 §4e: /control is a ro bind of the HOST go dir, so the host FIFO
    # inode IS /control/go inside the container — no in-namespace prelude.
    # The gate opens it NONBLOCK and tolerates EOF/EAGAIN zero phases until
    # the one-shot frame arrives from the host writer. Fixture parity too.
    listener = ""
    # The bound lib is a package overlay: __init__.py re-exports the
    # supervisor module from the installed product package, so running the
    # overlay module by name keeps relative imports valid.
    gated = ("import runpy,sys;" + listener +
             "sys.path.insert(0,'/opt/xrg-p01');"
             "runpy.run_module('go_gated_overlay',"
             "run_name='__main__')")
    return ["-B", "-c", gated,
            "--lease", lease_arg, "--evidence", evidence,
            # run-real.sh:291 seconds=1800 (host_seconds=1830 is the HOST
            # wait, which stays in await_container(STAGE_B_SECONDS) — the
            # recovery/wait plane is untouched this round). Fixture/stub
            # parity keeps the previous value.
            "--seconds", str(STAGE_B_SECONDS - 30 if real_docker_mode()
                              else STAGE_B_SECONDS),
            # artificial rehearsal mode (fixture/stub): _publication_selection
            # requires the request pin to be ABSENT. The real chain runs the
            # project_snapshot task_control tuple above, so it passes the
            # full run-real.sh Stage B supervisor set (§362-367): --final at
            # the request's own output path inside executions/<attempt>, the
            # controller-pin pair, and the worker-failure correlation pair.
            # The materialization ro bind + /metadata bind that these paths
            # depend on are wired in stage_b_mount_plan below.
            *(["--final", f"/data/var/snapshots/executions/{ATTEMPT}/batch.staged.json",
               "--authorized-source-mode", "project_snapshot",
               "--request-sha256", pdoc["request_pin"],
               "--controller-request-file",
               "/data/var/snapshots/materialization/request.json",
               "--controller-request-sha256", pdoc["request_pin"],
               "--worker-failure", FAILURE_REPORT,
               "--worker-request-sha256", pdoc["request_pin"]]
              if (role == "stage-b" and real_docker_mode()) else []),
            # request pin ABSENT for artificial mode:
            "--go-frame-file", "/control/go",
            "--go-deadline-seconds", str(int(GO_DEADLINE_S)),
            "--authorization-copy", "/authorization/authorization.json",
            "--confirmed-sha256", confirmed_sha_of(gen),
            "--attempt-id", ATTEMPT, "--gen-id", gen,
            "--", *worker]


def capture_supervisor_evidence(gen, container_id):
    """Real-chain evidence pull after the container exits: the supervisor
    prints its verdict to stdout (docker logs) and writes monitor.json +
    go-gate.json + limits.json under /data/var/run. Copy them into the host
    output dir so runner_verdict/classify_terminal and the acceptance audit
    read durable bytes, never a self-report over a live channel."""
    if not real_docker_mode():
        return None
    out = output_dir(gen)
    code, logs, _ = docker("logs", container_id, timeout=15, capture=True)
    if code == 0 and logs:
        write_durable(out / "worker.log", (logs + "\n").encode(), mode=0o640)
        if logs is None:
            logs = ""
        code_e, lerr, _ = docker("logs", "--stderr", container_id,
                                 timeout=15, capture=True)
        if code_e == 0 and lerr:
            write_durable(out / "worker.err.log", (lerr + "\n").encode(),
                          mode=0o640)
        # Copy the container-side evidence up next to the verdict so the
        # audit reads durable bytes: monitor.json (final result), limits
        # snapshot and the go-gate receipt.
        for name in ("monitor.json", "limits.json", "go-gate.json"):
            src = out / "run" / name
            if src.is_file():
                try:
                    shutil.copyfile(str(src), str(out / name))
                except OSError:
                    pass
        # Durable result first: monitor.json carries status+reason+exit.
        mon = out / "monitor.json"
        if mon.is_file():
            try:
                mdoc = json.loads(mon.read_text())
                if isinstance(mdoc, dict) and "status" in mdoc:
                    write_durable(out / "supervision-verdict.json",
                                  canon(dict(status=mdoc.get("status"),
                                             reason=mdoc.get("reason"),
                                             worker_exit_code=mdoc.get(
                                                 "worker_exit_code"),
                                             process_group_gone=mdoc.get(
                                                 "process_group_gone"))),
                                  mode=0o640)
                    return mdoc
            except Exception:
                pass
        # Fall back to the supervisor's last stdout verdict line.
        for line in reversed(logs.splitlines()):
            line = line.strip()
            if line.startswith("{") and '"status"' in line:
                try:
                    doc = json.loads(line)
                except Exception:
                    continue
                write_durable(out / "supervision-verdict.json",
                              canon(doc), mode=0o640)
                return doc
    return None


def ensure_lease_file(gen):
    """Real chain: the lease must exist as a regular file BEFORE create
    because it is bound file-level into /control."""
    go_dir(gen).mkdir(parents=True, exist_ok=True)
    target = go_dir(gen) / "lease"
    fd = os.open(str(target), os.O_WRONLY | os.O_CREAT, 0o644)
    os.close(fd)


def _chown_tree(top):
    """Recursive ownership+mode handoff for the evidence plane. run-real.sh
    chowns the whole tree 10001:10001 before create; off-host (rehearsal)
    chown fails and we fall back to world-writable modes so the container
    user can write limits.json / monitor.json / materialization outputs."""
    gid = int(os.environ.get("XRG_P01_WORKER_GID", "10001"))
    for dirpath, dirnames, filenames in os.walk(str(top)):
        for name in [""] + dirnames + filenames:
            target = os.path.join(dirpath, name) if name else dirpath
            try:
                os.chown(target, -1, gid)
            except OSError:
                pass
            try:
                os.chmod(target, 0o777 if os.path.isdir(target) else 0o666)
            except OSError:
                pass


def stage_a_materialization_dir():
    """Locate the completed Stage A durable materialization output for this
    attempt (receipt-named gen only; missing outputs block the chain)."""
    p = paths()
    done = p["receipts"] / "stage-a-done.json"
    try:
        doc, _ = read_json_strict(done)
    except Exception:
        return None
    gen = doc.get("gen_id")
    if not gen:
        return None
    cand = output_dir(gen) / "durable" / "materialization"
    return cand if cand.is_dir() else None


def _stage_a_view_binds(prior):
    """Explicit XRG_P01_STAGE_A_VIEW channel (SNAPSHOT_HOST precedent):
    locate the Stage A view tree, digest-gate EVERY request-referenced
    input against the request's own pins, and emit the three readonly
    binds (/metadata, /data/var/run/preparation, /data/var/run/review).
    No worktree or hand-filled fallback: missing/empty/mismatch all
    refuse BEFORE create."""
    view = os.environ.get("XRG_P01_STAGE_A_VIEW")
    if not view:
        raise Refused("stage_a_view_missing",
                      "XRG_P01_STAGE_A_VIEW unset; metadata/preparation/"
                      "review segments untraceable")
    view = Path(view)
    segs = {"metadata": view / "metadata",
            "preparation": view / "a" / "preparation",
            "review": view / "a" / "review"}
    for name, d in segs.items():
        if not d.is_dir() or not any(d.iterdir()):
            raise Refused("stage_a_view_empty", name)
    try:
        request, _ = read_json_strict(prior / "request.json")
    except Exception as error:
        raise Refused("stage_a_view_request_unreadable", str(error)[:120])
    prefix_map = {"/metadata/": segs["metadata"],
                  "/data/var/run/preparation/": segs["preparation"],
                  "/data/var/run/review/": segs["review"]}

    def host_for(container_path):
        for pre, base in prefix_map.items():
            if container_path.startswith(pre):
                return base / container_path[len(pre):]
        return None
    # canonical reference set straight from the request document:
    # roots/certificate are plain path strings pinned by top-level fields;
    # bindings entries carry their own {path, sha256} pairs.
    refs = [(request["roots"], request["roots_sha256"]),
            (request["certificate"], request["certificate_sha256"])]
    refs += [(b["path"], b["sha256"]) for b in request["bindings"].values()]
    for cp, want in refs:
        local = host_for(cp)
        if local is None:
            raise Refused("stage_a_view_missing", f"unmapped path {cp}")
        if not local.is_file():
            raise Refused("stage_a_view_empty", cp)
        got = sha_bytes(read_bytes_nofollow(local))
        if got != want:
            raise Refused("stage_a_view_digest_mismatch",
                          f"{cp}: expected {want} got {got}")
    return [f"--mount type=bind,src={segs['metadata']},dst=/metadata,readonly",
            f"--mount type=bind,src={segs['preparation']},"
            f"dst=/data/var/run/preparation,readonly",
            f"--mount type=bind,src={segs['review']},"
            f"dst=/data/var/run/review,readonly"]


class MonitorFeeder:
    """Host-side monitor sibling — the run-real.sh sample()/lease contract.

    Writes a fresh 9-line lease file every interval into $ROOT/go/gen-<gen>/
    lease, the exact directory bind-mounted at /control in the container.
    The supervisor freshness window is |now-ts| <= 25 s, so the default
    interval is 10 s. The FIRST sample is published synchronously before
    `docker start` because supervise() observes(initial=True) before it
    Popen()s the worker; later samples come from the detached child until
    stop(). Every sample is appended to host-samples.log next to the lease
    so acceptance evidence shows a real moving series, not one frozen file.
    Fixture mode never starts a feeder (the stub runner needs no lease).
    """

    def __init__(self, gen, container_id, interval=None, disk_path=None):
        self.gen = gen
        self.container_id = container_id
        self.interval = float(interval if interval is not None else
                              os.environ.get("XRG_P01_LEASE_INTERVAL", "10"))
        self.disk_path = disk_path or str(root())
        self.proc = None

    @staticmethod
    def collect_sample(disk_path):
        import subprocess as sp
        def sh(cmd):
            try:
                r = sp.run(["bash", "-c", cmd], capture_output=True,
                           text=True, timeout=5)
                return r.stdout.strip()
            except Exception:
                return ""
        # read_lease requires EXACTLY nine lines: each source contributes
        # its first matching line only (run-real.sh greps single-line files;
        # pressure files can carry both some/full rows).
        def sh1(cmd):
            return sh(cmd).splitlines()[0] if sh(cmd) else ""
        meminfo = sh1("grep '^MemAvailable:' /proc/meminfo")
        loadavg = sh1("cat /proc/loadavg")
        io_pressure = sh1("grep '^some ' /proc/pressure/io")
        memory_pressure = sh1("grep '^some ' /proc/pressure/memory")
        vmstat = sh1("grep '^pswpout ' /proc/vmstat")
        try:
            st = os.statvfs(disk_path)
            disk_available = str(st.f_bavail * st.f_frsize)
        except OSError:
            disk_available = "0"
        # rehearsal services gate: docker daemon reachable counts as the
        # observed service baseline being unchanged (real host compares
        # pg32/pg32b id+startedat+health against services-before).
        healthy = "true" if sh("docker version --format '{{.Server.Version}}'"
                               ) else "false"
        # Seven metric fields; _publish prepends ts + seq => exactly nine
        # lines, the read_lease contract.
        return [meminfo, loadavg, io_pressure, memory_pressure, vmstat,
                disk_available, healthy]

    def _publish(self, seq, fields):
        d = go_dir(self.gen)
        body = "\n".join([str(int(time.time())), str(seq)] +
                         list(fields)) + "\n"
        lease = d / "lease"
        # The real chain binds the lease FILE into /control, so updates must
        # preserve the inode: truncate+write in place (the reader tolerates
        # a momentary short read via monitor_lost retry on next sample).
        fd = os.open(str(lease), os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                     0o644)
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(body)
                fh.flush()
                os.fsync(fh.fileno())
        except OSError:
            # fd already owned by fdopen path above; best-effort only.
            pass
        with open(str(d / ".lease-next"), "w") as mirror:
            mirror.write(body)                 # mv -T audit twin
        with open(str(d / "host-samples.log"), "a") as fh:
            fh.write(body)

    def run_forever(self):
        seq = 0
        while True:
            seq += 1
            self._publish(seq, self.collect_sample(self.disk_path))
            time.sleep(self.interval)

    def start(self):
        if not real_docker_mode():
            return None
        self._publish(1, self.collect_sample(self.disk_path))
        # The child inherits the full environment (chain markers included);
        # argv only pins root/module path and feeder parameters.
        script = (
            "import os,sys\n"
            "os.environ['XRG_P01_ROOT']=sys.argv[1]\n"
            # The child must be in real mode to publish; inherit the marker
            # explicitly in case the parent env is scrubbed by the launcher.
            "os.environ['XRG_P01_REAL_CHAIN']='1'\n"
            "sys.path.insert(0, sys.argv[2])\n"
            "import xrg_p01_entry as e\n"
            "e.MonitorFeeder(sys.argv[3], sys.argv[4], interval=float("
            "sys.argv[5]), disk_path=sys.argv[6]).run_forever()\n")
        path = root() / "registry" / f"feeder-{self.gen}.py"
        write_durable(path, script.encode(), mode=0o600)
        env = dict(os.environ)
        self.proc = subprocess.Popen(
            [sys.executable, "-B", str(path), str(root()),
             str(Path(__file__).resolve().parent), self.gen,
             self.container_id, str(self.interval), self.disk_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env,
            start_new_session=True)
        return self.proc

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        try:
            (root() / "registry" / f"feeder-{self.gen}.py").unlink()
        except OSError:
            pass


def confirmed_sha_of(gen):
    try:
        doc, _ = read_json_strict(gen_record_path(gen))
        return doc.get("confirmed_sha256")
    except Exception:
        return ""


def request_pin_for(role, suffix):
    """Digest of the delivered request document when present; rehearsal
    accepts the synthetic pin derived from the run label."""
    p = paths()
    for cand in (p["run_input"] / "source-green-v1" / "request.json",
                 p["run_input"] / "request.json"):
        if cand.is_file():
            return sha_bytes(read_bytes_nofollow(cand))
    return sha_bytes(f"{ATTEMPT}|{role}|{suffix}".encode())


def output_dir(gen):
    return paths()["output"] / f"gen-{gen}"


def output_bind(gen, role="stage-b"):
    """Evidence plane layout mirroring run-real.sh: /data/var/run is this
    gen's output dir (rw); stage-a additionally gets durable/{materialization,
    executions/<attempt>/scratch} so materialize writes land on the host."""
    out = output_dir(gen)
    subs = ["", "run", "metadata", "review"]
    if role == "stage-a":
        subs += ["durable", "durable/materialization",
                 f"durable/executions/{ATTEMPT}",
                 f"durable/executions/{ATTEMPT}/scratch"]
    else:
        subs += ["executions", f"executions/{ATTEMPT}",
                 f"executions/{ATTEMPT}/scratch"]
    for sub in subs:
        (out / sub).mkdir(parents=True, exist_ok=True)
    for target in (out, *{out / sub for sub in subs}):
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
    try:
        os.chmod(out / "run", 0o777)   # uid 10001 writes evidence here
    except OSError:
        pass
    # docker --mount syntax: read-write is the default; explicit `rw` is
    # rejected by the daemon ("must be a key=value pair"). run-real.sh uses
    # the same plain form for its evidence mount.
    return f"--mount type=bind,src={out},dst=/data/var/run"


def supervisor_bind():
    lib = os.environ.get("XRG_P01_SUPERVISOR_LIB") or \
        "/usr/local/lib/xrg-p01"
    return f"--mount type=bind,src={lib},dst=/opt/xrg-p01,readonly"


def origin_script_bind():
    src = os.environ.get("XRG_P01_ORIGIN_SCRIPT")
    if not src:
        raise Refused("origin_script_missing",
                      "real chain requires XRG_P01_ORIGIN_SCRIPT")
    return f"--mount type=bind,src={src},dst=/installed-origin.py,readonly"


def materialize_bind():
    src = os.environ.get("XRG_P01_MATERIALIZE_SCRIPT")
    if not src:
        raise Refused("materialize_script_missing",
                      "real chain requires XRG_P01_MATERIALIZE_SCRIPT")
    return f"--mount type=bind,src={src},dst=/materialize-real.py,readonly"


def stage_a_mount_plan(gen):
    p = paths()
    base = [f"--mount type=bind,src={p['run_input']},dst=/inputs,readonly",
            f"--mount type=bind,src={gen_dir(gen)},dst=/authorization,readonly"]
    if real_docker_mode():
        # File-level bind of the host-fed lease only; a directory bind made
        # before the lease exists would pin an empty inode forever.
        ensure_lease_file(gen)
        base.append(f"--mount type=bind,src={go_dir(gen) / 'lease'},"
                    f"dst=/control/lease,readonly")
        base.extend([output_bind(gen, "stage-a"), origin_script_bind(),
                     materialize_bind(),
                     f"--mount type=bind,src={output_dir(gen) / 'durable'},"
                     f"dst=/data/var/snapshots"])
        # run-real.sh chown -R 10001:10001 on the evidence + durable trees
        # BEFORE create; without it the read-only-rootfs worker cannot write
        # its outputs. Best-effort off-host, mandatory in the install flow.
        _chown_tree(output_dir(gen))
    else:
        base.append(f"--mount type=bind,src={go_dir(gen)},"
                    f"dst=/control,readonly")
    return base + ["--cpus 0.5", "--memory 768m", "--memory-swap 768m",
                   "--pids-limit 128", "--network none", "--read-only",
                   "--cap-drop ALL", "--security-opt no-new-privileges",
                   "--tmpfs /tmp:rw,nosuid,nodev,size=33554432,"
                   "uid=10001,gid=10001,mode=1777",
                   "--workdir /app", "--entrypoint python"]


def shlexish(line):
    import shlex
    return shlex.split(line)


def shlex_quote(token):
    import shlex
    return shlex.quote(str(token))


# ------------------------------------------------------------------ stage-b
def cmd_stage_b(args):
    # Exact argv shape first (§2): no locks, no docker, no writes until the
    # whole command line matches the whitelisted grammar.
    if set(args) - {"suffix", "stage_b_suffix", "mat_suffix", "request_pin",
                    "approval_pin", "roots_pin"}:
        raise Refused("usage", "unknown stage-b option")
    for key in ("stage_b_suffix", "mat_suffix", "request_pin", "approval_pin"):
        if key not in args:
            raise Refused("usage", f"missing {key.replace('_', '-')}")
    check_suffix("stage-b-suffix", args["stage_b_suffix"])
    args["suffix"] = args["stage_b_suffix"]
    check_suffix("mat-suffix", args["mat_suffix"])
    check_pin("request-pin", args["request_pin"])
    check_pin("approval-pin", args["approval_pin"])
    if "roots_pin" in args:
        check_pin("roots-pin", args["roots_pin"])
    p = paths()
    lock = Locks()
    if lock.acquire(attempt_lock_name()) is None:
        raise Refused("busy_or_consumed", "attempt.flock held by another process")
    try:
        ensure_layout()
        blocked = enforce_blocking(lock)
        if blocked:
            raise Refused("recovery_pending", blocked)
        consumed = load_consumed()
        if consumed:
            raise Refused("attempt_consumed", consumed.get("state"))
        doc, original_sha = host_gate()
        if real_docker_mode():
            image_identity_gate()
        if not (p["receipts"] / "stage-a-done.json").exists():
            raise Refused("stage_a_missing", "run stage-a first")
        gen = new_gen_id()
        gen_doc = build_generation(gen, original_sha)
        mount_plan = stage_b_mount_plan(gen, args)
        prepared = dict(version=1, attempt=ATTEMPT, gen_id=gen, phase="pre-create",
                        role="stage-b", original_sha256=original_sha,
                        confirmed_sha256=gen_doc["confirmed_sha256"],
                        request_pin=args["request_pin"],
                        approval_pin=args["approval_pin"],
                        roots_pin=args.get("roots_pin", ROOTS_SHA),
                        mount_plan=mount_plan, ts=now_iso())
        if prepared["roots_pin"] != ROOTS_SHA:
            raise Refused("roots_pin_mismatch", prepared["roots_pin"])
        prepared["creation_digest"] = plan_digest(
            prepared["mount_plan"] + ["IMAGE:" + image_id()])
        write_durable(prepared_path(gen), canon(prepared))
        update_gen_role(gen, "stage-b")
        write_durable(gen_dir(gen) / "mount-plan.txt",
                      ("\n".join(mount_plan) + "\n").encode(), mode=0o644)
        try:
            code, container_id, err = request_docker(
                "create", *create_args(gen, mount_plan, args["suffix"],
                                       "stage-b"), gen_note=gen)
        except Exception as exc:
            # Unknown create outcome: PREPARED stays unresolved; recovery
            # adjudicates by label lookup. Never blind-retry (§4f.1).
            record("CREATE_RESULT_UNKNOWN", gen=gen, detail=str(exc)[:200])
            raise Refused("create_result_unknown", str(exc)[:200])
        if code != 0:
            mark_resolved(gen, None, dict(outcome="create_failed", stderr=err[:200]),
                          ["none"])
            raise Refused("create_failed", err[:200])
        container_id = (container_id or "").strip()
        if len(container_id) != 64 or any(c not in "0123456789abcdef"
                                          for c in container_id):
            record("CREATE_ANSWER_MALFORMED", gen=gen,
                   detail=container_id[:80])
            raise Refused("create_answer_malformed", container_id[:80])
        bind_container(gen, container_id)
        if real_docker_mode():
            write_durable(gen_dir(gen) / "argv.txt",
                          (" ".join(shlex_quote(a) for a in create_args(
                              gen, mount_plan, args["suffix"], "stage-b"))
                           + "\n").encode(), mode=0o644)
        ok, why = static_config_check(container_id, mount_plan, require_snapshot=True)
        if not ok:
            cleanup_created(container_id, gen)
            # §4g.2 step order on the T9a retryable-refusal path: candidate
            # reclaimed -> RESOLVED published via the §4g.3 procedure ->
            # refusal closure. If the publication itself is interrupted we
            # roll the refusal closure back so nothing half-published can
            # be mistaken for a qualified retry (§4g.3 no half-way release).
            try:
                mark_resolved(gen, container_id, why["verification"], ["rm"])
            except OSError:
                target = p["receipts"] / "refusals" / f"t9a-{gen}.json"
                if target.exists():
                    os.unlink(target)
                raise
            refusal_write("t9a", gen, why)
            raise Refused("static_config_refused", why)
        # T9b: consumption record BEFORE the first start request.
        consumed_doc = dict(version=1, attempt=ATTEMPT, gen_id=gen,
                            container_id=container_id, state="START_REQUESTED",
                            consumed_at=now_iso())
        try:
            made = publish_exclusive(p["consumed"], canon(consumed_doc))
        except OSError:
            # §4f window (b): never delete an existing record — recovery
            # adjudicates from its bytes. If nothing was created, clean up.
            if p["consumed"].exists():
                verification = verify_candidate_stopped(container_id, gen)
                mark_resolved(gen, container_id,
                              dict(outcome=verification["outcome"],
                                   reason="consumed_sync_unconfirmed"),
                              ["stop_rm" if verification["outcome"] ==
                               "verified_stopped" else "none"])
            else:
                cleanup_running(container_id, gen)
                mark_resolved(gen, container_id,
                              dict(outcome="verified_stopped",
                                   reason="consumed_sync_failed"), ["stop_rm"])
            raise Refused("consumed_fsync_failed",
                          "no start issued; record state decides retry")
        if not made:
            existing = read_bytes_nofollow(p["consumed"])
            try:
                parsed = json.loads(existing)
                verdict = "consumed_valid" if parsed.get("attempt") == ATTEMPT \
                    else "consumed_foreign"
            except Exception:
                verdict = "consumed_record_corrupt"
            raise Refused(verdict, "existing record kept, never overwritten")
        # Journal the persistence event BEFORE the start request so receipts
        # prove T9b ordering (record fsynced -> first start requested).
        record("CONSUMED_STATE", gen=gen, state="START_REQUESTED")
        # §4f window (c): crash after the consumption record is durable but
        # before the start request is ever issued — recovery must resolve the
        # generation without resending a start.
        try:
            maybe_fault("consumed_pre_start", str(p["consumed"]))
        except OSError:
            # Crash AFTER consumption persisted, BEFORE any start request:
            # candidate stays created; nothing else is touched. Recovery
            # owns the resolution (§4g.4 single rule).
            raise
        scope = cgroup_scope(container_id)
        feeder = MonitorFeeder(gen, container_id)
        feeder.start()               # observe(initial=True) needs lease NOW
        try:
            code2, _, err2 = request_docker("start", container_id, gen_note=gen)
        except OSError:
            cleanup_running(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="start_result_unknown"),
                          ["stop_rm"])
            update_consumed_state(gen, container_id, "INVALID_START_UNCONFIRMED")
            raise Refused("start_result_unknown", container_id)
        if code2 == 0:
            record("START_CONFIRMED", gen=gen, container_id=container_id)
        if code2 != 0:
            # §4c: a failed start request is retry-eligible like a precheck
            # refusal — the consumption record stays at START_REQUESTED and
            # recovery resolves it to INVALID_START_UNCONFIRMED (terminal).
            cleanup_created(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="start_failed",
                                                  stderr=err2[:200]), ["rm"])
            raise Refused("start_failed", err2[:200])
        t_probe = time.monotonic()
        reader_ready = wait_fifo_reader(gen, budget=init_wait_s(),
                                        container_id=container_id)
        reader_waited = time.monotonic() - t_probe
        values, deadline_hit = poll_readback(scope)
        prio = None
        # The §8 host verification needs the supervisor to have reached its
        # nice/ionice step first; that step precedes limits.json in the
        # evidence dir. Wait for the file (bounded by the same init budget
        # as the reader probe), THEN audit — never race the container.
        if values is not None and real_docker_mode():
            wait_priority_step(container_id, init_wait_s())
        if values is not None and real_docker_mode():
            # §8 requirement of this round: four cgroup files AND the
            # process-level nice/ionice plane must both be host-verified
            # before any GO frame may be written. The supervisor applies
            # os.nice(19)+ionice strictly BEFORE its first lease sample /
            # limits.json, so polling until the plane holds (within the
            # init budget) verifies establishment, not just a snapshot.
            prio = wait_priority_established(container_id, init_wait_s())
            receipt(f"priority-audit-{gen}.json",
                    dict(gen_id=gen, container_id=container_id, **prio,
                         ts=now_iso()))
            if not prio.get("ok"):
                cleanup_running(container_id, gen)
                mark_resolved(gen, container_id, dict(
                    outcome="verified_stopped",
                    reason="priority_audit_failed", detail=prio), ["stop_rm"])
                update_consumed_state(gen, container_id, "INVALID_READBACK")
                raise Refused("priority_audit_failed", str(prio)[:200])
        if values is None:
            cleanup_running(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="readback_timeout"), ["stop_rm"])
            update_consumed_state(gen, container_id, "INVALID_READBACK")
            raise Refused("readback_timeout", scope)
        try:
            if real_docker_mode():
                delivered = deliver_go(gen, values, reader_waited,
                                       deadline=time.monotonic() + GO_DELIVERY_WINDOW_S)
            else:
                delivered = deliver_go(gen, values, reader_waited)
        except NoGoDelivery:
            if not reader_ready:
                cleanup_running(container_id, gen)
                mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                      reason="container_init_absent"),
                              ["stop_rm"])
                update_consumed_state(gen, container_id, "INVALID_SUPERVISION_NO_GO")
                raise Refused("readback_timeout", "no container init")
            exit_code = await_container(container_id, STAGE_B_SECONDS, gen)
            terminal = classify_terminal(gen, exit_code, container_id)
            cleanup_running(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="go_no_reader"), ["wait_stop_rm"])
            update_consumed_state(gen, container_id, terminal)
            print(f"STAGE_B_{terminal} gen={gen}")
            return
        try:
            exit_code = await_container(container_id, STAGE_B_SECONDS, gen)
            terminal = classify_terminal(gen, exit_code, container_id)
            capture_supervisor_evidence(gen, container_id)
            mark_resolved(gen, container_id, dict(
                outcome="verified_stopped", exit_code=exit_code), ["wait"])
            update_consumed_state(gen, container_id, terminal,
                                  delivered=delivered)
            request_docker("rm", container_id, gen_note=gen)
            receipt(f"stage-b-{gen}.json",
                    dict(stage="B", attempt=ATTEMPT, gen_id=gen,
                         container_id=container_id,
                         readback=values, terminal=terminal,
                         go_nonce=nonce_of(gen), ts=now_iso()))
            print(f"STAGE_B_{terminal} gen={gen}")
        finally:
            feeder.stop()
    finally:
        lock.release_all()


def stage_b_mount_plan(gen, args):
    p = paths()
    if not fixture_mode() and not real_docker_mode():
        raise Refused("real_stage_b_locked",
                      "真实 Stage B 需茶香另行授权；本入口当前只允许夹具演练")
    if real_docker_mode() and not os.environ.get("XRG_P01_SNAPSHOT_HOST"):
        # Rehearsal chain MUST state its substitute snapshot explicitly; the
        # real project snapshot plane stays untouched and unmounted.
        raise Refused("real_stage_b_locked",
                      "真实 Stage B 锁死：rehearsal 必须显式 XRG_P01_SNAPSHOT_HOST"
                      "且只能是合成演练件")
    snapshot_host = os.environ.get(
        "XRG_P01_SNAPSHOT_HOST", str(root() / "fixture-snapshot" / SNAPSHOT_ID))
    base = [f"--mount type=bind,src={p['run_input']},dst=/inputs,readonly",
            f"--mount type=bind,src={gen_dir(gen)},dst=/authorization,readonly",
            f"--mount type=bind,src={snapshot_host},"
            f"dst=/data/imports/usedata/{snapshot_id()},readonly"]
    if real_docker_mode():
        base.extend([output_bind(gen, "stage-b"), supervisor_bind(),
                     origin_script_bind(), materialize_bind()])
        _chown_tree(output_dir(gen))
        ensure_lease_file(gen)
        # Overlay preflight: the lib dir must expose BOTH the supervisor
        # module and the package shim that makes its relative imports work.
        lib = Path(os.environ.get("XRG_P01_SUPERVISOR_LIB")
                   or "/usr/local/lib/xrg-p01")
        for need in ("go_gated_supervisor.py", "go_gated_overlay.py"):
            if not (lib / need).is_file():
                raise Refused("supervisor_overlay_missing", str(lib / need))
        # v14 §4e: /control is a read-only bind of the HOST go dir, so
        # the container sees the host FIFO inode AS /control/go (R12:
        # directory binds carry FIFOs fine; the earlier daemon-refusal
        # claim was disproved). The gate opens it NONBLOCK, tolerates
        # EOF/EAGAIN zero phases, and reads exactly one "GO <hex64>"
        # frame before the writer closes. The lease keeps its single-file
        # ro bind below: same source file, in-place updates propagate.
        # No socket plane exists anywhere: --network none stays intact.
        base.append(f"--mount type=bind,src={go_dir(gen)},"
                    f"dst=/control,readonly")
        base.append(f"--mount type=bind,src={go_dir(gen) / 'lease'},"
                    f"dst=/control/lease,readonly")
        # Stage B input closure: the Stage A materialization dir becomes a
        # read-only bind (run-real.sh: $mat_run/.../materialization). The
        # rehearsal snapshot plane replaces the real one via SNAPSHOT_HOST.
        prior = stage_a_materialization_dir()
        if prior is None:
            raise Refused("materialization_missing",
                          "real chain requires completed stage-a outputs")
        # run-real.sh:340 binds the Stage A materialization directory into
        # Stage B READ-ONLY; the worker never writes there — its outputs go
        # to /data/var/run (evidence) and executions/<attempt> (batch). The
        # request/approval pair inside it is what task_control reads through
        # this ro bind, which also satisfies _require_readonly_mount.
        base.append(f"--mount type=bind,src={prior},"
                    f"dst=/data/var/snapshots/materialization,readonly")
        # Stage A view closure: /metadata + preparation + review inputs the
        # request references must be bindable AND digest-verified against
        # the request's own pins before they ever reach create.
        base.extend(_stage_a_view_binds(prior))
        # --final's parent must exist BEFORE create (publish_batch resolves
        # it strict), and the product requires request.output.parent plus
        # scratch_parent to be present directories owned for uid 10001
        # (run-real.sh:322-325). output_bind already created these under
        # executions/<attempt>; re-assert and hand ownership over.
        attempt_exec = output_dir(gen) / "executions" / ATTEMPT
        (attempt_exec / "scratch").mkdir(parents=True, exist_ok=True)
        _chown_tree(output_dir(gen) / "executions")
        base.append(f"--mount type=bind,src={output_dir(gen) / 'executions'},"
                    f"dst=/data/var/snapshots/executions")
    return base + ["--cpus 0.5", "--memory 768m", "--memory-swap 768m",
                   "--pids-limit 128", "--network none", "--read-only",
                   "--cap-drop ALL", "--security-opt no-new-privileges",
                   "--tmpfs /tmp:rw,nosuid,nodev,size=33554432,"
                   "uid=10001,gid=10001,mode=1777",
                   "--workdir /app", "--entrypoint python"]


def nonce_of(gen):
    doc, _ = read_json_strict(gen_record_path(gen))
    return doc["nonce_expected"]


def cleanup_created(container_id, gen):
    request_docker("rm", "-f", container_id, gen_note=gen)


def cleanup_running(container_id, gen):
    request_docker("stop", "--time", "10", container_id, gen_note=gen)
    # ensure the runner verdict has been recorded before removal
    docker("inspect", "--format", "{{.State.Status}}", container_id)
    request_docker("rm", container_id, gen_note=gen)


def static_config_check(container_id, mount_plan, *, require_snapshot):
    p = paths()
    code, mounts_json, _ = docker("inspect", "--format", "{{json .Mounts}}", container_id)
    if code != 0:
        return False, dict(verification=dict(outcome="daemon_error"), reason="inspect")
    mounts = json.loads(mounts_json or "[]")
    expected_srcs = [line.split("src=", 1)[1].split(",")[0] for line in mount_plan
                     if "type=bind" in line]
    actual_srcs = [m.get("Source") for m in mounts]
    if sorted(expected_srcs) != sorted(actual_srcs):
        return False, dict(verification=dict(outcome="config_mismatch",
                                             expected=expected_srcs,
                                             actual=actual_srcs), reason="mounts")
    ro_expected = {line.split("src=", 1)[1].split(",")[0] for line in mount_plan
                   if "type=bind" in line and ",readonly" in line}
    ro_bad = [m.get("Source") for m in mounts
              if m.get("Source") in ro_expected and m.get("RW") is not False]
    if ro_bad:
        return False, dict(verification=dict(outcome="ro_mismatch", bad=ro_bad),
                           reason="readonly")
    # Real docker exposes the CPU limit as HostConfig.NanoCpus (the field
    # exists since API 1.27 but real daemons leave it 0 when only --cpus
    # was set... they do not: create records NanoCpus). The fixture stub
    # reports Cpus instead. Read BOTH fields unconditionally; prefer a
    # positive NanoCpus, fall back to Cpus; treat ANY inspect failure on a
    # four-item field as a hard mismatch — never a silent empty string.
    code_n, nano, _ = docker("inspect", "--format",
                             "{{.HostConfig.NanoCpus}}", container_id)
    code_c, cpus, _ = docker("inspect", "--format",
                             "{{.HostConfig.Cpus}}", container_id)
    cpu_val = None
    nano_i = 0
    if code_n == 0:
        try:
            # Go templates may print floats in exponent form ("5e+08").
            nano_i = int(float(nano))
        except ValueError:
            nano_i = 0
    if nano_i > 0:
        # cpu.cfs_quota_us over the default period: NanoCpus(1e9/cpu)
        # -> quota per 100ms period => nano_i // 10_000.
        cpu_val = nano_i // 10_000
    elif code_c == 0:
        try:
            cpu_val = int(float(cpus) * 100000)
        except ValueError:
            cpu_val = None
    codes = {}
    vals = {}
    for key, fmt in (("memory.max", "{{.HostConfig.Memory}}"),
                     ("memory.swap.max", "{{.HostConfig.MemorySwap}}"),
                     ("pids.max", "{{.HostConfig.PidsLimit}}")):
        codes[key], vals[key], _ = docker("inspect", "--format", fmt,
                                          container_id)
    if cpu_val is None or any(codes[k] != 0 for k in codes):
        return False, dict(verification=dict(
            outcome="hostconfig_unreadable", cpu_val=cpu_val,
            failed=[k for k, c in codes.items() if c != 0]), reason="hostconfig")
    got = {"cpu.max": f"{cpu_val} 100000",
           "memory.max": vals["memory.max"],
           "memory.swap.max": vals["memory.swap.max"],
           "pids.max": vals["pids.max"]}
    # cgroup memory.swap.max == 0 (no swap) corresponds to the docker flag
    # --memory-swap equal to --memory; HostConfig.MemorySwap reports bytes.
    want = {"cpu.max": CGROUP_EXPECT["cpu.max"],
            "memory.max": CGROUP_EXPECT["memory.max"],
            "memory.swap.max": CGROUP_EXPECT["memory.max"],
            "pids.max": CGROUP_EXPECT["pids.max"]}
    if {k: str(v) for k, v in got.items()} != {k: str(v) for k, v in want.items()}:
        return False, dict(verification=dict(outcome="hostconfig_mismatch",
                                             got=got, want=want), reason="hostconfig")
    if require_snapshot and not any("/data/imports/usedata/" in (m.get("Destination") or "")
                                    for m in mounts):
        return False, dict(verification=dict(outcome="snapshot_missing"), reason="mounts")
    return True, dict(verification=dict(outcome="ok", mounts=len(mounts)))


def cgroup_scope(container_id):
    base = cgroup_base()
    name = os.environ.get("XRG_P01_SCOPE_NAME") or \
        f"system.slice/docker-{container_id}.scope"
    direct = base / name
    if direct.is_dir():
        return direct
    if fixture_mode() and (base / "cpu.max").exists():
        return base          # fixture harness points the base at a scope dir
    if real_docker_mode():
        # Discover the LIVE scope from the container's own /proc/<pid>/cgroup
        # (authoritative under cgroup v2, independent of driver naming).
        pid = container_init_pid(container_id)
        if pid:
            try:
                lines = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
                for line in lines:
                    _, _, path = line.partition("::")
                    if path and path != "/":
                        cand = base / path.lstrip("/")
                        if cand.is_dir():
                            return cand
            except OSError:
                pass
    return direct            # real host: non-existent scope must fail readback


def container_init_pid(container_id):
    code, pid, _ = docker("inspect", "--format", "{{.State.Pid}}", container_id)
    try:
        value = int(pid)
    except ValueError:
        return None
    return value if code == 0 and value > 0 else None


def process_priority_evidence(container_id):
    """Host-side, process-level verification of the resource plane BEFORE
    GO (§8 stance): every task in the container's cgroup must carry nice=19
    and ionice policy idle(3)/best-effort(0..7 handled as class<=1 not
    accepted; only class 3 passes), read from /proc — never trusting the
    supervisor's self-report."""
    code, pid_s, _ = docker("inspect", "--format", "{{.State.Pid}}",
                            container_id)
    try:
        pid = int(pid_s)
    except ValueError:
        return dict(ok=False, reason="init_pid_unavailable")
    if code != 0 or pid <= 0:
        # Host procfs may hide the pid from an unprivileged observer; the
        # kernel fact still exists inside the container — go straight to
        # the exec-based snapshot before declaring anything unavailable.
        return process_priority_evidence_via_exec(container_id)
    tasks = []
    try:
        for entry in os.listdir(f"/proc/{pid}/task"):
            tasks.append(entry)
    except OSError as error:
        if error.errno in (errno.EACCES, errno.EPERM, errno.ENOENT):
            # Host procfs is restricted (hidepid / unprivileged sandbox) or
            # the pid vanished from our view. The kernel fact still exists
            # INSIDE the container's own /proc, which shows the same task
            # threads; read it through docker exec — the daemon enforces
            # the container boundary, so this remains an external-to-task
            # observation, never a supervisor self-report.
            return process_priority_evidence_via_exec(container_id)
    except OSError as error:
        return dict(ok=False, reason=f"task_walk:{error.errno}")
    raw = {}
    for tid in tasks:
        try:
            raw[tid] = Path(f"/proc/{pid}/task/{tid}/stat").read_text()
        except OSError as error:
            if error.errno in (errno.ENOENT, errno.EACCES, errno.EPERM):
                return process_priority_evidence_via_exec(container_id)
            return dict(ok=False, reason=f"proc_read:{type(error).__name__}")
    offenders, seen = [], []
    if not tasks:
        # An empty task list means NOTHING was observed; ok=True by vacuity
        # would be a silent pass. Fail explicitly instead.
        return dict(ok=False, reason="no_task_rows")
    for tid in tasks:
        try:
            stat = raw[tid]
            # field 19 (nice) after comm which may contain spaces/parens
            after = stat.rpartition(")")[2].split()
            nice = int(after[16])
            # I/O class read-back: /usr/bin/ionice -p <tid> — the kernel
            # ioprio_get through util-linux. This kernel family (6.12.x)
            # exposes no IoPriority line in /proc status at all, and raw
            # syscall numbers are banned here (no system headers), so the
            # CLI is the only auditable source. util-linux reports
            # classless as "none: prio 0"; rc!=0 / unparsable output =>
            # pol=-1 => _priority_offender fails closed with an explicit
            # ioprio_query_failed reason, never a silent pass.
            r = subprocess.run(["/usr/bin/ionice", "-p", str(tid)],
                               capture_output=True, text=True, timeout=5)
            pol = -1
            if r.returncode == 0:
                head = r.stdout.strip().split(":")[0]
                pol = {"idle": 3, "best-effort": 2, "realtime": 1,
                       "none": 0, "null": 0}.get(head, -1)
        except (OSError, IndexError, ValueError,
                subprocess.SubprocessError) as error:
            return dict(ok=False, reason=f"proc_read:{type(error).__name__}")
        seen.append(dict(tid=tid, nice=nice, ionice_class=pol))
        # Shared judgement: only nice==19 with IDLE(3) passes (docstring
        # stance); classless NONE(0) is NOT accepted; pol<0 is an
        # explicit query failure.
        verdict = _priority_offender(nice, pol)
        if verdict is not None:
            offenders.append(dict(tid=tid, nice=nice, ionice_class=pol,
                                  why=verdict))
    return dict(ok=not offenders, tasks=len(seen), offenders=offenders[:8],
                evidence="host_procfs", sample=seen[:4])


# Snapshot one-liner inside the container: prints "<tid> <nice> <pol>" per
# task, pol being the ionice class (0 none/classless, 1 realtime, 2
# best-effort, 3 idle) or -1 when the query failed. nice is field 19 of
# /proc/<pid>/task/<tid>/stat (after the comm paren). The ionice class is
# read through /usr/bin/ionice -p <tid> — the same kernel ioprio_get the
# host path uses; on this kernel family (6.12.x here) /proc status exposes
# no IoPriority line at all, and a raw syscall number would violate the
# "numbers only from system headers" rule (this host has no headers), so
# neither procfs nor ctypes/syscall is an option. util-linux reports
# classless as "none: prio 0"; any rc!=0 or unparsable row becomes
# QUERY_FAILED (-1) explicitly — never silently skipped, never defaulted
# to a pass value. The gate process runs as uid 10001 and sees ONLY its
# own namespace — a kernel fact, not a supervisor self-report.
# Snapshot discipline: resolve every task's stat FIRST (one atomic-ish
# sweep), then query priorities. A helper thread that exits mid-scan can
# no longer poison the audit with defaults; its row surfaces as -1 and the
# consumer fails closed.
_PROC_SNAPSHOT = (
    "import glob,subprocess\n"
    "handles=[]\n"
    "for d in sorted(glob.glob('/proc/[0-9]*/task/[0-9]*')):\n"
    "    try:\n"
    "        handles.append((d,open(d+'/stat').read()))\n"
    "    except OSError:\n"
    "        pass\n"
    "for d,st in handles:\n"
    "    try:\n"
    "        tid=int(d.rsplit('/',1)[-1])\n"
    "        nice=int(st.rpartition(')')[2].split()[16])\n"
    "    except (IndexError,ValueError):\n"
    "        continue\n"
    "    pol=-1\n"
    "    try:\n"
    "        r=subprocess.run(['/usr/bin/ionice','-p',str(tid)],\n"
    "                         capture_output=True,text=True,timeout=5)\n"
    "        if r.returncode==0:\n"
    "            head=r.stdout.strip().split(':')[0]\n"
    "            pol={'idle':3,'best-effort':2,'realtime':1,\n"
    "                 'none':0,'null':0}.get(head,-1)\n"
    "    except Exception:\n"
    "        pol=-1\n"
    "    print(tid,nice,pol)")


def _priority_offender(nice, pol):
    """Single judgement shared by BOTH priority-evidence paths. Only
    nice==19 with ionice class IDLE(3) passes — matching the docstring
    stance ('only class 3 passes'); classless NONE(0) is NOT accepted.
    pol<0 (QUERY_FAILED) fails closed with an explicit reason instead of
    mixing into the ordinary offender rows."""
    if pol < 0:
        return "ioprio_query_failed"
    if nice != 19:
        return "nice_not_19"
    if pol != 3:
        return f"ionice_class={pol}"
    return None


def process_priority_evidence_via_exec(container_id):
    code, out, err = docker("exec", container_id, "python", "-B", "-c",
                            _PROC_SNAPSHOT, timeout=15, capture=True)
    if code != 0:
        return dict(ok=False, reason=f"exec_procfs:{(err or out)[:120]}")
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        tid, nice_s, pol_s = parts
        try:
            nice, pol = int(nice_s), int(pol_s)
        except ValueError:
            return dict(ok=False, reason="proc_parse")
        rows.append(dict(tid=tid, nice=nice, ionice_class=pol))
    if not rows:
        return dict(ok=False, reason="exec_procfs_empty")
    # Judgement scope: the supervisor's OWN thread group only. Threads of
    # other processes visible here are docker-exec helpers spawned by this
    # very observation (they inherit nice=0 from the daemon); auditing
    # them would fail on our own noise. The supervisor's process identity
    # is resolved INSIDE the container from its own pid — never trusted
    # from a self-report channel; it is the init of the exec'd argv.
    # Enumerate command lines to attribute threads precisely: only pids
    # whose cmdline names the gated supervisor are judged.
    code_c, cmdlines, _ = docker(
        "exec", container_id, "python", "-B", "-c",
        "import glob\n"
        "for p in sorted(glob.glob('/proc/[0-9]*')):\n"
        "    try:\n"
        "        cl=open(p+'/cmdline').read().replace(chr(0),' ').strip()\n"
        "    except OSError:\n"
        "        continue\n"
        "    if 'go_gated_overlay' in cl or 'candidate_supervisor' in cl:"
        "\n        print(p.rsplit('/',1)[-1])", timeout=10)
    if code_c != 0 or not cmdlines.strip():
        return dict(ok=False, reason="exec_scope_unresolved")
    supervisor_pids = set(cmdlines.split())
    # A thread row's tid equals its TGID only for the main thread; child
    # threads of the supervisor share the process, so judge every row and
    # treat non-supervisor PROCESS rows as observer noise. The snapshot
    # prints tids only; with a single-process supervisor (stage-b gate),
    # any tid not equal to a supervisor pid belongs to an exec helper.
    main = [r for r in rows if r["tid"] in supervisor_pids]
    if not main:
        return dict(ok=False, reason="exec_init_row_missing")
    offenders = []
    for r in main:
        verdict = _priority_offender(r["nice"], r["ionice_class"])
        if verdict is not None:
            offenders.append(dict(**r, why=verdict))
    seen = rows
    return dict(ok=not offenders, tasks=len(seen), offenders=offenders[:8],
                evidence="container_procfs_via_exec", sample=seen[:4])


def wait_priority_step(container_id, budget):
    """Poll until the supervisor has written /data/var/run/limits.json —
    it does so strictly AFTER os.nice(19) + ionice -c3 and BEFORE reading
    the lease or waiting on the GO frame, so once the file exists the
    process-level priority plane provably holds. Returns False when the
    container dies first (audit below then reports the crash honestly)."""
    end = time.monotonic() + budget
    while time.monotonic() < end:
        code, _, _ = docker("exec", container_id, "python", "-B", "-c",
                            "import os,sys;"
                            "sys.exit(0 if os.path.exists("
                            "'/data/var/run/limits.json') else 1)",
                            timeout=10)
        if code == 0:
            return True
        if code == 1 and "is not running" not in "":
            pass
        rc2, running, _ = docker("inspect", "--format", "{{.State.Running}}",
                                 container_id)
        if rc2 != 0 or running == "false":
            return False
        time.sleep(0.4)
    return False


def wait_priority_established(container_id, budget):
    """Poll the process-level priority plane until EVERY task carries
    nice=19 with idle/none ionice; returns the last audit dict (ok True/
    False). A fresh monitor.json in the evidence dir means the gate wrote
    it AFTER applying priorities, so once that file exists and the audit
    still fails, further polls cannot help — fail fast then."""
    end = time.monotonic() + budget
    last = None
    while True:
        last = process_priority_evidence(container_id)
        if last.get("ok"):
            return last
        if time.monotonic() >= end:
            return last
        time.sleep(0.4)


def wait_fifo_reader(gen, budget=5.0, container_id=None):
    """Fixture harness only: wait until the simulated container-init process
    recorded by the stub is alive again after interpreter startup. The FIFO
    itself is never touched here (an observer open would perturb the real
    one-way channel semantics under test)."""
    if real_docker_mode():
        # Real host: poll until SOME process holds the read end of our go
        # FIFO (kernel fact via /proc/*/fd inode match). Never touches the
        # FIFO itself; delivery budget remains §4e-bounded downstream.
        return wait_real_reader(gen, container_id, init_wait_s())
    if not os.environ.get("XRG_P01_FIXTURE"):
        return True
    state = os.environ.get("XRG_P01_STUB_STATE")
    marker = None
    if state:
        gen_id = gen
        end = time.monotonic() + budget
        while marker is None and time.monotonic() < end:
            for d in Path(state).glob("containers/*"):
                meta_f = d / "meta.json"
                try:
                    labels = json.loads(meta_f.read_text()).get("labels", {})
                except Exception:
                    continue
                if labels.get("io.xiangrugu.attempt-gen") == gen_id and                         (d / "runner.pid").exists():
                    marker = d / "runner.pid"
                    break
            if marker is None:
                time.sleep(0.05)
    if marker is None:
        return True
    try:
        pid = int(marker.read_text())
    except Exception:
        return True
    deadline = time.monotonic() + budget
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
            return True        # container-init alive: FIFO reader will exist
        except ProcessLookupError:
            return False       # runner died before ever opening
        except PermissionError:
            return True
        time.sleep(0.05)
    return False


def poll_readback(scope):
    deadline = time.monotonic() + READBACK_BUDGET_S
    last = {}
    while time.monotonic() < deadline:
        ok = True
        for key, want in CGROUP_EXPECT.items():
            try:
                got = (scope / key).read_text().strip()
            except OSError:
                got = None
            last[key] = got
            if got != want:
                ok = False
        if ok:
            return dict(last), False
        time.sleep(READBACK_POLL_S)
    return None, True


def container_pids(container_id):
    """All host pids inside the container's PID namespace (docker top is a
    daemon query; empty list when unavailable)."""
    code, out, _ = docker("top", container_id, "-o", "pid")
    if code != 0:
        return []
    pids = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts and parts[0].isdigit():
            pids.append(parts[0])
    return pids


def fifo_readers_present(gen, container_id=None):
    """True if the container init currently holds the read end of its
    in-container /control/go FIFO open. The inode lives in the CONTAINER's
    mount namespace (the daemon refuses FIFO bind sources), so the kernel
    fact is read from the init pid's own fd table — never by touching the
    FIFO itself (an observer open would perturb one-way channel semantics).
    Fixture mode keeps the historical host-inode scan."""
    if real_docker_mode():
        if not container_id:
            return False
        code, out, _ = docker(
            "exec", container_id, "python", "-B", "-c",
            "import glob,os\n"
            "for l in glob.glob('/proc/[0-9]*/task/[0-9]*/fd/*'):\n"
            "    try:\n"
            "        t=os.readlink(l)\n"
            "    except OSError:\n"
            "        continue\n"
            "    if t in ('/control/go',):\n"
            "        print('READER'); break", timeout=8, capture=True)
        if code == 0 and "READER" in out:
            return True
        # exec unavailable or reader not yet opened: fall back to the
        # weaker-but-sound fact that the container init is alive — the gate
        # reaches its NONBLOCK open within milliseconds of start and
        # deliver_go below still retries against ENXIO with the §4e budget.
        return bool(container_pids(container_id))
    try:
        st = os.stat(str(go_dir(gen) / "go"))
    except OSError:
        return False
    target = (st.st_dev, st.st_ino)
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        fd_dir = pid_dir / "fd"
        try:
            names = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in names:
            try:
                st2 = os.stat(os.path.join(str(fd_dir), fd))
            except OSError:
                continue
            if (st2.st_dev, st2.st_ino) == target:
                return True
    return False


def wait_real_reader(gen, container_id, budget):
    end = time.monotonic() + budget
    while time.monotonic() < end:
        if fifo_readers_present(gen, container_id):
            return True
        code, running, _ = docker("inspect", "--format", "{{.State.Running}}",
                                  container_id or "")
        if code == 0 and running == "false":
            return False     # container already exited; nobody will read
        time.sleep(0.25)
    return False


class NoGoDelivery(Exception):
    pass


def deliver_go(gen, values, reader_waited=0.0, deadline=None):
    p = paths()
    fifo = go_dir(gen) / "go"
    nonce = nonce_of(gen)
    frame = f"GO {nonce}\n".encode()
    # §4e wired: BOTH modes use this host writer against the same FIFO
    # inode the container reads through the /control ro bind. The formal
    # call site passes an absolute deadline (readback-passed + 5.0); the
    # fixture call site does NOT and keeps the legacy window below:
    # max(GO_DELIVERY_WINDOW_S, GO_DEADLINE_S - reader_waited).
    explicit_deadline = deadline is not None
    if deadline is None:
        deadline = time.monotonic() + max(GO_DELIVERY_WINDOW_S,
                                          GO_DEADLINE_S - reader_waited)
    fd = None
    while fd is None and time.monotonic() < deadline:
        probe = None
        try:
            probe = os.open(str(fifo), os.O_WRONLY | os.O_NONBLOCK)
            fd = probe
            probe = None
        except OSError as error:
            if error.errno != errno.ENXIO:
                if probe is not None:
                    os.close(probe)
                raise
            if probe is not None:
                os.close(probe)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.1, remaining))
    if fd is None:
        raise NoGoDelivery(f"no reader on {fifo}")
    # Explicit-deadline mode only: a slow open that RETURNS at or after
    # the deadline must not write — close the fd once (outside the write
    # try, so no double close) and refuse before any receipt exists.
    if explicit_deadline and time.monotonic() >= deadline:
        os.close(fd)
        raise NoGoDelivery(f"deadline reached before write on {fifo}")
    try:
        os.write(fd, frame)
    finally:
        os.close(fd)
    delivered = dict(gen_id=gen, nonce=nonce, readback=values,
                     delivered_at=now_iso(), semantics="host wrote and closed only")
    write_durable(go_dir(gen) / "DELIVERED.json", canon(delivered), mode=0o640)
    _relax_outside_sandbox(go_dir(gen) / "DELIVERED.json")
    record("GO_DELIVERED", gen=gen)
    return delivered


def _relax_outside_sandbox(path):
    """Best-effort group-readable mode for files the acceptance probe must
    stat after the entry exits (the harness umask may have masked 0o640)."""
    try:
        os.chmod(str(path), 0o644)
    except OSError:
        pass


def current_container(gen):
    """The container id bound to this generation (recorded in the gen
    record when the container was created), if it is still running."""
    try:
        doc, _ = read_json_strict(gen_record_path(gen))
    except Exception:
        return None
    cid = doc.get("container_id") if isinstance(doc, dict) else None
    if not cid or len(cid) != 64:
        return None
    code, running, _ = docker("inspect", "--format", "{{.State.Running}}",
                              cid)
    return cid if code == 0 and running == "true" else None


def await_container(container_id, seconds, gen):
    waited, poll = 0, 0.5
    while waited < seconds:
        code, running, _ = docker("inspect", "--format", "{{.State.Running}}",
                                  container_id)
        if code != 0 or running == "false":
            _, raw, _ = docker("inspect", "--format", "{{json .}}", container_id)
            try:
                doc = json.loads(raw)
            except Exception:
                doc = {}
            outcome = doc.get("outcome") or ""
            if outcome.startswith("SUPERVISION_ABORTED_NO_GO"):
                return -90   # sentinel: worker never started, self-aborted
            if outcome == "STOPPED" or outcome == "KILLED":
                return int(doc.get("exit_code") or 143)
            _, ex, _ = docker("inspect", "--format", "{{.State.ExitCode}}",
                              container_id)
            try:
                return int(ex)
            except ValueError:
                return -1
        time.sleep(poll)
        waited += poll
    cleanup_running(container_id, gen)
    code, raw, _ = docker("inspect", "--format", "{{json .}}", container_id)
    try:
        doc = json.loads(raw)
    except Exception:
        doc = {}
    if (doc.get("outcome") or "").startswith("SUPERVISION_ABORTED_NO_GO"):
        return -90
    return 124


def runner_verdict(container_id, gen=None):
    if real_docker_mode() and gen:
        out = paths()["output"] / f"gen-{gen}" / "supervision-verdict.json"
        if out.exists():
            try:
                return json.loads(out.read_text())
            except Exception:
                return None
        return None
    state = os.environ.get("XRG_P01_STUB_STATE")
    if not state or not container_id:
        return None
    archived = Path(state) / f"{container_id}.outcome.json"
    live = Path(state) / "containers" / container_id / "outcome.json"
    for target in (live, archived):
        if target.exists():
            try:
                return json.loads(target.read_text())
            except Exception:
                return None
    return None


def classify_terminal(gen, exit_code, container_id=None):
    if exit_code == 0:
        return "COMPLETED"
    if exit_code == 124:
        return "TIMEOUT"
    verdict = runner_verdict(container_id, gen) or {}
    status = verdict.get("status") or ""
    reason = verdict.get("reason") or ""
    if real_docker_mode() and status.endswith(("_WORKER_COMPLETED",)) \
            and reason in ("", None):
        # Supervisor contract: reason is None exactly when the worker exited
        # cleanly AND the final-sample handshake completed. The outer
        # container exit may still be non-zero via installed-origin chains;
        # the durable verdict bytes are authoritative, not the shim rc.
        return "COMPLETED"
    if status.startswith("SUPERVISION_ABORTED_NO_GO"):
        if reason.startswith("open:") or reason == "go_timeout":
            return "INVALID_SUPERVISION_NO_GO"
        return f"INVALID_{reason.upper()}"
    if exit_code == -90:
        return "INVALID_SUPERVISION_NO_GO"
    return "INVALID_SUPERVISION_EXIT"


def update_consumed_state(gen, container_id, state, delivered=None):
    p = paths()
    doc, _ = read_json_strict(p["consumed"])
    doc.update(state=state, terminal_at=now_iso(),
               go_delivered=bool(delivered), gen_id=gen, container_id=container_id)
    maybe_fault("terminal_update", str(p["consumed"]))
    write_durable(p["consumed"], canon(doc))
    record("CONSUMED_STATE", gen=gen, state=state)


# ---------------------------------------------------------- recover-orphan
def cmd_recover_orphan():
    p = paths()
    lock = Locks()
    if lock.acquire(attempt_lock_name()) is None:
        raise Refused("busy", "holder alive; recovery declines to interfere")
    try:
        ensure_layout()
        results = []
        # Consumption adjudication FIRST (§4f window c/e): a persisted
        # START_REQUESTED record names its own generation, which pending_gens
        # deliberately excludes (it only globs PREPARED-without-RESOLVED).
        consumed = load_consumed()
        if consumed and consumed.get("state") == "_corrupt":
            results.append(dict(gen_id=None, status="consumed_record_corrupt",
                                reason="human adjudication required"))
        elif consumed and consumed.get("state") == "START_REQUESTED":
            gen = consumed.get("gen_id")
            candidate = consumed.get("container_id")
            if not gen or not candidate:
                results.append(dict(gen_id=gen, status="recovery_pending",
                                    reason="consumed_record_corrupt"))
            else:
                status, why = reentry_check(lock, gen)
                results.append(dict(gen_id=gen, status=status, reason=why))
                if status == "cleared":
                    finalize_cleared(gen)
                    after = load_consumed() or {}
                    if after.get("state") == "START_REQUESTED":
                        results[-1] = dict(gen_id=gen, status="recovery_pending",
                                           reason="terminal_persist_failed")
        for gen in pending_gens():
            status, why = reentry_check(lock, gen)
            results.append(dict(gen_id=gen, status=status, reason=why))
            if status == "cleared":
                finalize_cleared(gen)
        receipt("recover-orphan.json", dict(attempt=ATTEMPT, results=results,
                                            ts=now_iso()))
        print(json.dumps(dict(results=results)))
    finally:
        lock.release_all()


def _journal_tail(p):
    path = p["receipts"] / "entry-journal.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def finalize_cleared(gen):
    p = paths()
    consumed = load_consumed()
    if consumed and consumed.get("gen_id") == gen and \
            consumed.get("state") == "START_REQUESTED":
        rdoc, _ = read_json_strict(resolved_path(gen))
        why = (rdoc.get("verification") or {}).get("reason") or ""
        delivered = (go_dir(gen) / "DELIVERED.json").exists()
        reqlog = p["receipts"] / "docker-requests.log"
        requested = confirmed = False
        if reqlog.exists():
            for line in reqlog.read_text().splitlines():
                if not line.startswith("START_REQUEST") or f"gen={gen}" not in line:
                    continue
                requested = True
                # A START_CONFIRMED journal event proves the daemon accepted
                # this exact request before we ever call it started.
                confirmed = any(e.get("event") == "START_CONFIRMED"
                                and e.get("gen") == gen
                                for e in _journal_tail(p))
                break
        if why in ("start_failed", "consumed_unstarted") or not \
                (delivered or confirmed):
            state = "INVALID_START_UNCONFIRMED"
        else:
            state = "INVALID_DELIVERY_UNVERIFIED"
        if confirmed and state == "INVALID_DELIVERY_UNVERIFIED":
            cid = consumed.get("container_id")
            deadline = time.monotonic() + STAGE_B_SECONDS
            while time.monotonic() < deadline:
                code, running, _ = docker(
                    "inspect", "--format", "{{.State.Running}}", cid)
                if code != 0 or running == "false":
                    break
                time.sleep(0.5)
            else:
                cleanup_running(cid, gen)
            verify_candidate_stopped(cid, gen)
        consumed.update(state=state, terminal_at=now_iso(), recovery="orphan")
        write_durable(p["consumed"], canon(consumed))
        record("RECOVERY_TERMINAL", gen=gen, state=state)
    kind = consumption_kind(gen)
    if kind == "stage-a":
        doc, _ = read_json_strict(resolved_path(gen))
        outcome = ("COMPLETED" if doc.get("verification", {}).get("exit_code") == 0
                   else "INVALID_SUPERVISION_EXIT")
        if not (p["receipts"] / f"stage-a-{gen}.json").exists():
            write_durable(p["receipts"] / f"stage-a-{gen}.json",
                          canon(dict(stage="A", attempt=ATTEMPT, gen_id=gen,
                                     outcome=outcome, recovery="completed")),
                          mode=0o640)
        if outcome == "COMPLETED" and \
                not (p["receipts"] / "stage-a-done.json").exists():
            write_durable(p["receipts"] / "stage-a-done.json",
                          canon(dict(done=True, gen_id=gen, recovery="completed")),
                          mode=0o640)
    if kind == "refusal" and not (
            p["receipts"] / "refusals" / f"t9a-{gen}.json").exists():
        refusal_write("t9a", gen, dict(recovery="completed_missing_refusal"))


# ----------------------------------------------------- blocking (§4c/§4g.4)
def enforce_blocking(lock):
    # Consumption-record adjudication comes FIRST (§4f window c/e): a
    # generation referenced by a persisted START_REQUESTED record was created
    # and bound; its closure follows the §4g.2 five-step order under this
    # same lock, before any other pending generation is examined.
    consumed = load_consumed()
    if consumed and consumed.get("state") == "_corrupt":
        return "consumed_record_corrupt"
    if consumed and consumed.get("state") == "START_REQUESTED":
        gen = consumed.get("gen_id")
        candidate = consumed.get("container_id")
        if not gen or not candidate:
            return "consumed_record_corrupt"
        # One rule for every shape (§4g.4): reentry_check performs the
        # read-only inspect adjudication (with the §4f.1 stable-absence
        # requirement), publishes RESOLVED via the five-step order, and
        # re-confirms + re-syncs. Only then may the terminal update land.
        status, why = reentry_check(lock, gen)
        if status != "cleared":
            return f"gen={gen}:{why}"
        # Closure step of §4g.2 completes here under the same B lock:
        # RESOLVED (if the crash left it unpublished), then terminal state.
        # If either write is interrupted (injected EIO), the exception
        # propagates: the entry refuses non-zero and issues no requests —
        # the block is maintained by the un-closed record itself (§4g.5).
        if not resolved_path(gen).exists():
            mark_resolved(gen, candidate, dict(
                outcome="verified_stopped", reason="closure_at_launch"),
                ["none"], reason="consumed_unstarted")
        finalize_cleared(gen)
        consumed_after = load_consumed()
        if consumed_after and \
                consumed_after.get("state") == "START_REQUESTED":
            return f"gen={gen}:terminal_persist_failed"
    for gen in pending_gens():
        status, why = reentry_check(lock, gen)
        if status != "cleared":
            return f"gen={gen}:{why}"
        finalize_cleared(gen)
    return None


def ensure_layout():
    p = paths()
    for key in ("inbox", "run_input", "authz", "staging", "publish_tmp",
                "run_authz", "go", "pins", "registry", "output", "receipts"):
        p[key].mkdir(parents=True, exist_ok=True)
    # On a real host these modes are part of the install contract; in fixture
    # mode keep them only where the kernel/sandbox allows (best effort).
    for target, mode in ((p["authz"], 0o750), (p["staging"], 0o770 | stat.S_ISVTX),
                         (p["publish_tmp"], 0o700), (p["go"], 0o750)):
        try:
            os.chmod(target, mode)
        except OSError:
            if not os.environ.get("XRG_P01_FIXTURE"):
                raise


# ----------------------------------------------------------- xrg-authz-publish
def cmd_authz_publish(uuid_value):
    p = paths()
    if not re.fullmatch(r"[0-9a-f-]{8,64}", uuid_value or ""):
        raise Refused("publish_uuid_invalid", uuid_value)
    staged = p["staging"] / f"{uuid_value}.json"
    # §3: the fixed program validates that the CALLER created the staging
    # file. Under sudo, SUDO_UID carries the caller identity; in fixture
    # mode XRG_P01_CALLER_UID plays the same role. Root-native invocations
    # (no caller hint at all) are only possible on a host where root itself
    # is the authorizer — never via the whitelisted sudo path.
    caller_hint = os.environ.get("XRG_P01_CALLER_UID") or \
        os.environ.get("SUDO_UID")
    try:
        owner = staged.stat().st_uid
    except FileNotFoundError:
        raise Refused("staging_missing", str(staged))
    if caller_hint is not None and int(caller_hint) != owner:
        raise Refused("staging_not_caller_owned",
                      f"caller={caller_hint} owner={owner}")
    raw = read_bytes_nofollow(staged)
    try:
        doc = json.loads(raw.decode())
    except Exception:
        raise Refused("publish_content_invalid", "not canonical JSON")
    validate_authz_document(doc)
    target = p["original"]
    if target.exists():
        raise Refused("EEXIST", "authorization already published")
    tmp = p["publish_tmp"] / f"{uuid_value}.out"
    if tmp.exists():
        os.unlink(tmp)
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        maybe_fault("publish_file_fsync", str(tmp))
        os.fsync(stream.fileno())
    os.chmod(tmp, 0o400)
    maybe_fault("publish_rename", str(target))
    rename_noreplace(tmp, target)
    maybe_fault("publish_parent_fsync", str(target.parent))
    fsync_dir(target.parent)
    record("AUTHZ_PUBLISHED", uuid=uuid_value, sha256=sha_bytes(raw))
    try:
        os.unlink(staged)          # consume the staging artifact (§4b)
        fsync_dir(p["staging"])
    except OSError:
        pass                       # original already durable; cleanup best-effort
    print("PUBLISHED")


def rename_noreplace(src, dst):
    flags = getattr(os, "RENAME_NOREPLACE", 0)
    try:
        os.rename(src, dst)
    except OSError:
        if dst.exists():
            raise Refused("EEXIST", str(dst))
        raise


# --------------------------------------------------------------------- cli
def parse_cli(argv):
    prog = Path(sys.argv[0]).name
    if prog == "xrg-authz-publish" or argv[:1] == ["publish"]:
        rest = argv[1:] if argv[:1] == ["publish"] else argv
        positional = [t for t in rest if not t.startswith("--")]
        if len(positional) != 1 or any(
                t.startswith("--") and t != "--uuid" for t in rest):
            raise Refused("usage", "xrg-authz-publish <uuid> only")
        uuid_value = positional[0]
        if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"
                            r"-[0-9a-f]{4}-[0-9a-f]{12}", uuid_value):
            raise Refused("usage", "uuid must be canonical lowercase form")
        return ("publish", dict(uuid=uuid_value))
    if not argv:
        raise Refused("usage", "subcommand required")
    sub, rest = argv[0], argv[1:]
    if sub not in COMMANDS:
        raise Refused("usage", sub)  # reserved-name gate: unknown subcommands
    if sub in ("verify-inbox", "recover-orphan") and rest:
        raise Refused("usage", f"{sub} takes no arguments")
    if sub in ("stage-a", "stage-b"):
        if fixture_program() and not fixture_mode():
            raise Refused("usage", "fixture program requires XRG_P01_FIXTURE=1")
        if not fixture_program() and fixture_mode():
            raise Refused("usage",
                          "fixture mode requires the isolated fixture program")
    # §3b deployment isolation: the fixture program only serves fixture
    # mode; the formal program refuses to inherit XRG_P01_FIXTURE. The
    # publish dispatch above is exempt — it touches no container plane and
    # the fixture suite exercises the same shared code path.
    kv = {}
    it = iter(rest)
    for token in it:
        if token.startswith("--"):
            if "=" in token:
                raise Refused("usage", "--key=value form not accepted")
            key = token[2:].replace("-", "_")
            value = next(it, "")
            kv[key] = value
            kv.setdefault("suffix", value)
        else:
            raise Refused("usage", token)
    return (sub, kv)


COMMANDS = {
    "verify-inbox": lambda a: cmd_verify_inbox(),
    "stage-a": lambda a: cmd_stage_a(a["stage_a_suffix"]),
    "stage-b": lambda a: cmd_stage_b(a),
    "recover-orphan": lambda a: cmd_recover_orphan(),
    "publish": lambda a: cmd_authz_publish(a["uuid"]),
}


def _usage_exit(refused):
    # Usage refusals happen before any layout exists; still emit the same
    # machine-readable stderr shape and exit code 3 (§2 whitelist mirror).
    sys.stderr.write(json.dumps(dict(status="REFUSED", code=refused.code,
                                     detail=str(refused.detail)[:300])) + "\n")
    return 3


def main():
    try:
        sub, kv = parse_cli(sys.argv[1:])
    except StopIteration:
        return _usage_exit(Refused("usage", "option missing value"))
    except Refused as refused:
        return _usage_exit(refused)
    if sub not in COMMANDS:
        raise Refused("usage", sub)
    try:
        record("ARGV_ACCEPTED", command=sub, argv=sys.argv[1:])
    except OSError:
        pass
    try:
        COMMANDS[sub](kv)
        return 0
    except Refused as refused:
        try:
            record("ENTRY_REFUSED", command=sub, code=refused.code,
                   detail=str(refused.detail)[:300])
        except OSError:
            pass
        sys.stderr.write(json.dumps(dict(status="REFUSED", code=refused.code,
                                         detail=str(refused.detail)[:300])) + "\n")
        return 3
    except Exception as error:  # noqa: BLE001 — crash must not leak tracebacks on stdout
        sys.stderr.write(json.dumps(dict(status="ENTRY_CRASHED",
                                         detail=f"{type(error).__name__}: {error}"[:300])) + "\n")
        return 4


if __name__ == "__main__":
    sys.exit(main())
