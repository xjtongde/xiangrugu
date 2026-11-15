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
STAGE_A_SECONDS, STAGE_B_SECONDS = 300, 1830
PACKET_FILES = 48
DOCKER_TIMEOUT = 10


def root() -> Path:
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


def read_json_strict(path: Path):
    data = path.read_bytes()
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
    if doc["attempt_id"] != ATTEMPT or doc["task_card_sha256"] != CARD_SHA:
        raise Refused("authz_binding", "attempt/card mismatch")
    if doc["one_attempt_only"] is not True or not isinstance(doc["granted_by"], str) \
            or not doc["granted_by"].strip():
        raise Refused("authz_fields", "one_attempt_only/granted_by")


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
    if not fifo.exists():
        os.mkfifo(str(fifo))
        try:
            os.chmod(fifo, 0o640)
        except OSError:
            pass
    gid = int(os.environ.get("XRG_P01_WORKER_GID", "10001"))
    dgid = int(os.environ.get("XRG_P01_GO_DIR_GID", "10001"))
    # Ownership/mode hardening is best-effort under the local sandbox and
    # mandatory on the real host (install script enforces it there).
    for target, owner, mode in ((gopath, (0, dgid), 0o710), (fifo, (0, gid), 0o640),
                                (gd, (0, 0), 0o755)):
        try:
            os.chown(target, *owner)
            os.chmod(target, mode)
        except OSError:
            if not os.environ.get("XRG_P01_FIXTURE"):
                raise
    src = p["original"].read_bytes()
    if sha_bytes(src) != original_sha:
        raise Refused("authz_race", "original changed mid-generation")
    copy = gd / "authorization.json"
    write_durable(copy, src, mode=0o644)
    confirmed = sha_bytes(copy.read_bytes())
    gen_doc = dict(version=1, attempt=ATTEMPT, gen_id=gen, state="GENERATED",
                   original_sha256=original_sha, confirmed_sha256=confirmed,
                   nonce_expected=compute_nonce(confirmed, gen, ATTEMPT),
                   created_at=now_iso())
    write_durable(gen_record_path(gen), canon(gen_doc), mode=0o644)
    record("GENERATION_BUILT", gen=gen, confirmed=confirmed)
    return gen_doc


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
            # record means the host never confirmed a start for this
            # generation. Recovery verifies by READ-ONLY inspect only — it
            # NEVER stops/removes containers outside the confirmed-start
            # path; that stays human-visible.
            code, status, err = docker(
                "inspect", "--format", "{{.State.Status}}", candidate)
            outcome = ("deleted_404" if code != 0 else status.strip())
            if outcome not in ("deleted_404", "created", "exited", "dead"):
                return "recovery_pending", f"candidate_{outcome or 'unknown_state'}"
            verification = dict(container_id=candidate, checked_at=now_iso(),
                                outcome="verified_absent" if
                                outcome == "deleted_404" else outcome,
                                evidence="inspect_only", state=outcome)
            mark_resolved(gen, candidate, verification, ["none"],
                          reason="consumed_unstarted")
        elif candidate:
            verification = verify_candidate_stopped(candidate, gen)
            if verification["outcome"] != "verified_stopped":
                return "recovery_pending", f"candidate_{verification['outcome']}"
            mark_resolved(gen, candidate, verification, ["stop_rm"])
        else:
            located = locate_prepared_candidates(gen)
            if located["outcome"] == "zero":
                mark_resolved(gen, None, dict(outcome="verified_absent",
                                              evidence="label_lookup_zero"),
                              ["none"])
            elif located["outcome"] == "unique":
                verification = verify_candidate_stopped(located["ids"][0], gen)
                if verification["outcome"] != "verified_stopped":
                    return "recovery_pending", \
                        f"candidate_{verification['outcome']}"
                mark_resolved(gen, located["ids"][0], verification, ["stop_rm"])
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
    if consumed_rec.get("gen_id") == gen and \
            consumed_rec.get("state") == "START_REQUESTED":
        # Inspect-only re-verification (never destructive for unstarted gens).
        code, status, _err = docker("inspect", "--format", "{{.State.Status}}",
                                    doc.get("container_id"))
        outcome = ("deleted_404" if code != 0 else status.strip())
        if outcome not in ("deleted_404", "created", "exited", "dead"):
            return "recovery_pending", f"candidate_{outcome or 'unknown_state'}"
    else:
        verification = verify_candidate_stopped(doc.get("container_id"), gen)
        if verification["outcome"] != "verified_stopped":
            return "recovery_pending", f"candidate_{verification['outcome']}"
    for target in (rp, p["consumed"] if kind == "consumed" else rp):
        try:
            fd = os.open(str(target), os.O_RDONLY)
            os.fsync(fd)
            os.close(fd)
            fsync_dir(target.parent)
        except OSError as error:
            return "recovery_pending", f"resync_failed:{error.errno}"
    return "cleared", "reentry_verified_and_resynced"


def consumption_kind(gen):
    p = paths()
    if (p["receipts"] / f"stage-a-{gen}.json").exists() or _gen_role(gen) == "stage-a":
        return "stage-a"
    if (p["receipts"] / "refusals" / f"t9a-{gen}.json").exists():
        return "refusal"
    if _gen_role(gen) == "consumed":
        return "consumed"
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
        if p["consumed"].exists():
            try:
                c, _ = read_json_strict(p["consumed"])
                if c.get("gen_id") == gen:
                    return "consumed"
            except Exception:
                pass
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
    by a persisted START_REQUESTED consumption record are adjudicated first
    by enforce_blocking, not through this glob."""
    p = paths()
    out = []
    for prepared in sorted(p["run_authz"].glob("gen-*.PREPARED.json")):
        gen = prepared.name[len("gen-"):-len(".PREPARED.json")]
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
    for cid in ids:
        c2, cfg, _ = docker("inspect", "--format", "{{json .Config.Labels}}", cid)
        c3, hc, _ = docker("inspect", "--format", "{{json .HostConfig.Cpus}}", cid)
        labels = {}
        try:
            labels = json.loads(cfg)
        except Exception:
            pass
        if labels.get("io.xiangrugu.attempt-gen") == gen and c2 == 0:
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
    entries_admin = parse_manifest(admin.read_text())
    if len(entries_admin) != PACKET_FILES:
        raise Refused("admin_list_size", len(entries_admin))
    if listing.read_bytes() != admin.read_bytes():
        raise Refused("manifest_mismatch", "package INPUTS.sha256 != pins authority")
    dest = p["run_input"] / "source-green-v1"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in sorted(os.listdir(inbox_pkg)):
        if name == "INPUTS.sha256":
            continue
        shutil.copy2(inbox_pkg / name, dest / name)
    failures = []
    for name, digest in entries_admin.items():
        target = dest / name
        if not target.is_file() or sha_bytes(target.read_bytes()) != digest:
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
    receipt("verify-inbox.json", dict(status="VERIFIED", files=len(entries_admin),
                                      ts=now_iso()))
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
        write_durable(prepared_path(gen), canon(prepared))
        update_gen_role(gen, "stage-a")
        plan_digest = sha_bytes(canon(prepared["mount_plan"]))
        code, container_id, err = request_docker(
            "create", *create_args(gen, prepared["mount_plan"], suffix, "stage-a"),
            gen_note=gen)
        if code != 0:
            mark_resolved(gen, None, dict(outcome="create_failed", stderr=err[:200]),
                          ["none"])
            raise Refused("create_failed", err[:200])
        bind_container(gen, container_id)
        ok, why = static_config_check(container_id, prepared["mount_plan"], require_snapshot=False)
        if not ok:
            cleanup_created(container_id, gen)
            mark_resolved(gen, container_id, why["verification"], ["rm"])
            refusal_write("t9a", gen, why)
            raise Refused("static_config_refused", why)
        os.environ["XRG_P01_STUB_GO"] = "off"   # Stage A has no GO gate
        code2, _, _ = request_docker("start", container_id, gen_note=gen)
        exit_code = await_container(container_id, STAGE_A_SECONDS, gen)
        outcome = classify_terminal(gen, exit_code, container_id)
        mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                              exit_code=exit_code), ["wait"])
        write_durable(p["receipts"] / f"stage-a-{gen}.json",
                      canon(dict(stage="A", attempt=ATTEMPT, gen_id=gen,
                                 container_id=container_id, outcome=outcome,
                                 exit_code=exit_code, ts=now_iso())), mode=0o640)
        if outcome == "COMPLETED":
            write_durable(existing, canon(dict(done=True, gen_id=gen,
                                               ts=now_iso())), mode=0o640)
        request_docker("rm", container_id, gen_note=gen)
        print(f"STAGE_A_{outcome} gen={gen}")
    finally:
        lock.release_all()


def update_gen_role(gen, role):
    doc, _ = read_json_strict(gen_record_path(gen))
    doc["role"] = role
    write_durable(gen_record_path(gen), canon(doc), mode=0o644)


def create_args(gen, plan_lines, suffix, role):
    argv = ["--label", f"io.xiangrugu.attempt-gen={gen}",
            "--label", f"io.xiangrugu.synthetic-run={role}-{suffix}"]
    for line in plan_lines:
        argv.extend(shlexish(line))
    return [*argv, IMAGE_ID, role]


def stage_a_mount_plan(gen):
    p = paths()
    return [f"--mount type=bind,src={p['run_input']},dst=/inputs,readonly",
            f"--mount type=bind,src={gen_dir(gen)},dst=/authorization,readonly",
            f"--mount type=bind,src={go_dir(gen)},dst=/control,readonly",
            "--cpus 0.5", "--memory 768m", "--memory-swap 768m",
            "--pids-limit 128", "--network none", "--read-only",
            "--cap-drop ALL", "--security-opt no-new-privileges",
            "--workdir /app", "--entrypoint python"]


def shlexish(line):
    import shlex
    return shlex.split(line)


# ------------------------------------------------------------------ stage-b
def cmd_stage_b(args):
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
        write_durable(prepared_path(gen), canon(prepared))
        update_gen_role(gen, "stage-b")
        write_durable(gen_dir(gen) / "mount-plan.txt",
                      ("\n".join(mount_plan) + "\n").encode(), mode=0o644)
        code, container_id, err = request_docker(
            "create", *create_args(gen, mount_plan, args["suffix"], "stage-b"),
            gen_note=gen)
        if code != 0:
            mark_resolved(gen, None, dict(outcome="create_failed", stderr=err[:200]),
                          ["none"])
            raise Refused("create_failed", err[:200])
        bind_container(gen, container_id)
        ok, why = static_config_check(container_id, mount_plan, require_snapshot=True)
        if not ok:
            cleanup_created(container_id, gen)
            mark_resolved(gen, container_id, why["verification"], ["rm"])
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
            existing = p["consumed"].read_bytes()
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
        try:
            code2, _, err2 = request_docker("start", container_id, gen_note=gen)
        except OSError:
            cleanup_running(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="start_result_unknown"),
                          ["stop_rm"])
            update_consumed_state(gen, container_id, "INVALID_START_UNCONFIRMED")
            raise Refused("start_result_unknown", container_id)
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
        reader_ready = wait_fifo_reader(gen)
        reader_waited = time.monotonic() - t_probe
        values, deadline_hit = poll_readback(scope)
        if values is None:
            cleanup_running(container_id, gen)
            mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                                  reason="readback_timeout"), ["stop_rm"])
            update_consumed_state(gen, container_id, "INVALID_READBACK")
            raise Refused("readback_timeout", scope)
        try:
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
        exit_code = await_container(container_id, STAGE_B_SECONDS, gen)
        terminal = classify_terminal(gen, exit_code, container_id)
        mark_resolved(gen, container_id, dict(outcome="verified_stopped",
                                              exit_code=exit_code), ["wait"])
        update_consumed_state(gen, container_id, terminal, delivered=delivered)
        request_docker("rm", container_id, gen_note=gen)
        receipt(f"stage-b-{gen}.json", dict(stage="B", attempt=ATTEMPT, gen_id=gen,
                                           container_id=container_id,
                                           readback=values, terminal=terminal,
                                           go_nonce=nonce_of(gen), ts=now_iso()))
        print(f"STAGE_B_{terminal} gen={gen}")
    finally:
        lock.release_all()


def stage_b_mount_plan(gen, args):
    p = paths()
    if not os.environ.get("XRG_P01_FIXTURE"):
        raise Refused("real_stage_b_locked",
                      "真实 Stage B 需茶香另行授权；本入口当前只允许夹具演练")
    snapshot_host = os.environ.get(
        "XRG_P01_SNAPSHOT_HOST", str(root() / "fixture-snapshot" / SNAPSHOT_ID))
    return [f"--mount type=bind,src={p['run_input']},dst=/inputs,readonly",
            f"--mount type=bind,src={gen_dir(gen)},dst=/authorization,readonly",
            f"--mount type=bind,src={go_dir(gen)},dst=/control,readonly",
            f"--mount type=bind,src={snapshot_host},dst=/data/imports/usedata/{SNAPSHOT_ID},readonly",
            "--cpus 0.5", "--memory 768m", "--memory-swap 768m",
            "--pids-limit 128", "--network none", "--read-only",
            "--cap-drop ALL", "--security-opt no-new-privileges",
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
    code, cpus, _ = docker("inspect", "--format", "{{.HostConfig.Cpus}}", container_id)
    code, mem, _ = docker("inspect", "--format", "{{.HostConfig.Memory}}", container_id)
    code, swap, _ = docker("inspect", "--format",
                           "{{.HostConfig.MemorySwap}}", container_id)
    code, pids, _ = docker("inspect", "--format",
                           "{{.HostConfig.PidsLimit}}", container_id)
    got = {"cpu.max": f"{int(float(cpus) * 100000)} 100000",
           "memory.max": mem, "memory.swap.max": swap, "pids.max": pids}
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
    if (base / "cpu.max").exists():
        return base          # fixture harness points the base at a scope dir
    return direct            # real host: non-existent scope must fail readback


def wait_fifo_reader(gen, budget=5.0):
    """Fixture harness only: wait until the simulated container-init process
    recorded by the stub is alive again after interpreter startup. The FIFO
    itself is never touched here (an observer open would perturb the real
    one-way channel semantics under test)."""
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


class NoGoDelivery(Exception):
    pass


def deliver_go(gen, values, reader_waited=0.0):
    p = paths()
    fifo = go_dir(gen) / "go"
    nonce = nonce_of(gen)
    frame = f"GO {nonce}\n".encode()
    # §4e: the delivery window starts when readback passed; the fixture
    # harness may already have spent part of it waiting for the simulated
    # container-init to come up, so the budget covers both.
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
            time.sleep(0.1)
    if fd is None:
        raise NoGoDelivery(f"no reader on {fifo}")
    try:
        os.write(fd, frame)
    finally:
        os.close(fd)
    delivered = dict(gen_id=gen, nonce=nonce, readback=values,
                     delivered_at=now_iso(), semantics="host wrote and closed only")
    write_durable(go_dir(gen) / "DELIVERED.json", canon(delivered), mode=0o640)
    record("GO_DELIVERED", gen=gen)
    return delivered


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


def runner_verdict(container_id):
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
    verdict = runner_verdict(container_id) or {}
    status = verdict.get("status") or ""
    reason = verdict.get("reason") or ""
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
        for gen in pending_gens():
            status, why = reentry_check(lock, gen)
            results.append(dict(gen_id=gen, status=status, reason=why))
            if status == "cleared":
                finalize_cleared(gen)
        consumed = load_consumed()
        if consumed and consumed.get("state") == "_corrupt":
            results.append(dict(gen_id=None, status="consumed_record_corrupt",
                                reason="human adjudication required"))
        receipt("recover-orphan.json", dict(attempt=ATTEMPT, results=results,
                                           ts=now_iso()))
        print(json.dumps(dict(results=results)))
    finally:
        lock.release_all()


def finalize_cleared(gen):
    p = paths()
    consumed = load_consumed()
    if consumed and consumed.get("gen_id") == gen and \
            consumed.get("state") == "START_REQUESTED":
        rdoc, _ = read_json_strict(resolved_path(gen))
        why = (rdoc.get("verification") or {}).get("reason") or ""
        delivered = (go_dir(gen) / "DELIVERED.json").exists()
        reqlog = p["receipts"] / "docker-requests.log"
        started = False
        if reqlog.exists():
            started = any(l.startswith("START_REQUEST") and f"gen={gen}" in l
                          for l in reqlog.read_text().splitlines())
        if why in ("start_failed", "consumed_unstarted") or not (delivered or started):
            state = "INVALID_START_UNCONFIRMED"
        else:
            state = "INVALID_DELIVERY_UNVERIFIED"
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
        # Read-only inspect adjudication (§4f.1 window b/c split). Recovery
        # NEVER stops/removes an unstarted candidate; that stays human-visible.
        code, status, err = docker("inspect", "--format", "{{.State.Status}}",
                                   candidate)
        outcome = ("deleted_404" if code != 0 else status.strip())
        if outcome not in ("deleted_404", "created", "exited", "dead"):
            return f"gen={gen}:candidate_{outcome or 'unknown_state'}"
        verification = dict(container_id=candidate, checked_at=now_iso(),
                            outcome="verified_absent" if outcome == "deleted_404"
                            else outcome, evidence="inspect_only", state=outcome)
        if not resolved_path(gen).exists():
            mark_resolved(gen, candidate, verification, ["none"],
                          reason="consumed_unstarted")
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
    raw = staged.read_bytes()
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
        uuid_value = ""
        it = iter(rest)
        for token in it:
            if token == "--uuid":
                uuid_value = next(it, "")
            elif not token.startswith("--"):
                uuid_value = token
        if not uuid_value:
            raise Refused("usage", "xrg-authz-publish <uuid>")
        return ("publish", dict(uuid=uuid_value))
    if not argv:
        raise Refused("usage", "subcommand required")
    sub, rest = argv[0], argv[1:]
    kv = {}
    it = iter(rest)
    for token in it:
        if token.startswith("--"):
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


def main():
    sub, kv = parse_cli(sys.argv[1:])
    if sub not in COMMANDS:
        raise Refused("usage", sub)
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
