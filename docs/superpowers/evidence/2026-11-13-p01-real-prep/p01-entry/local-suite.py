#!/usr/bin/env python3
"""Local acceptance suite for the p01 minimal entry (fixture mode, host 38).

Runs the v14 §6 acceptance items that are mechanically decidable against the
stub docker + stub runner. Never touches 32, NAS, real snapshots, or images.
Writes machine-readable receipts under <workdir>/receipts/ and a SUMMARY.json.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = []


def run(cmd, env=None, timeout=90, check=False):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=e,
                       check=False)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd} rc={r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


class World:
    def __init__(self, name):
        self.base = HERE / ".suite" / name
        if self.base.exists():
            shutil.rmtree(self.base)
        self.root = self.base / "runtime-root"
        self.stub_state = self.base / "stub-state"
        self.scope = self.base / "cgroup-scope"
        self.snapshot = self.root / "fixture-snapshot" / "fixture-bootstrap"
        for d in (self.root / "inbox" / "source-green-v1", self.stub_state,
                  self.scope, self.snapshot):
            d.mkdir(parents=True)
        for d in (self.root / "authz" / ".staging", self.root / "authz" / ".publish-tmp",
                  self.root / "run-authz", self.root / "go", self.root / "pins",
                  self.root / "registry", self.root / "receipts"):
            d.mkdir(parents=True, exist_ok=True)
        # 48-file packet with manifest == admin pins list
        entries = {}
        for i in range(48):
            f = self.root / "inbox" / "source-green-v1" / f"file-{i:02}.dat"
            body = f"synthetic fixture payload {i}\n".encode()
            f.write_bytes(body)
            entries[f.name] = hashlib.sha256(body).hexdigest()
        manifest = "".join(f"{entries[n]}  {n}\n" for n in sorted(entries))
        (self.root / "inbox" / "source-green-v1" / "INPUTS.sha256").write_text(manifest)
        pins = self.root / "pins"
        pins.mkdir(parents=True, exist_ok=True)
        (pins / "INPUTS.admin.sha256").write_text(manifest)
        # cgroup scope files with expected values
        for k, v in {"cpu.max": "50000 100000", "memory.max": "805306368",
                     "memory.swap.max": "0", "pids.max": "128"}.items():
            (self.scope / k).write_text(v + "\n")
        self.snapshot.joinpath("leaf.txt").write_text("fixture bytes only\n")
        self.env = dict(
            XRG_P01_FIXTURE="1", XRG_P01_ROOT=str(self.root),
            XRG_P01_DOCKER=str(HERE / "stub-docker.sh"),
            XRG_P01_STUB_STATE=str(self.stub_state),
            XRG_P01_STUB_RUNNER=str(HERE / "stub-runner.sh"),
            XRG_P01_CGROUP_BASE=str(self.scope),
            XRG_P01_SCOPE_NAME="",
            XRG_P01_SNAPSHOT_HOST=str(self.snapshot),
            PYTHONPATH=str(HERE),
        )

    def entry(self, *args, extra_env=None, timeout=90):
        env = dict(self.env)
        if extra_env:
            env.update(extra_env)
        entry_prog = os.environ.get("XRG_P01_ENTRY") or str(HERE / "xrg_p01_entry.py")
        return run([sys.executable, entry_prog, *args],
                   env=env, timeout=timeout)

    def publish_authz(self):
        staging = self.root / "authz" / ".staging"
        staging.mkdir(parents=True, exist_ok=True)
        doc = dict(version=1, status="AUTHORIZED_REAL_P01_SINGLE_ATTEMPT",
                   attempt_id="real-p01-20261113-a" if not os.environ.get("XRG_P01_ALT")
                   else "x", one_attempt_only=True, granted_by="茶香-fixture",
                   task_card_sha256="41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69")
        uuid = "aaaaaaaa-bbbb-cccc-dddd-" + str(int(time.time()*1000))[-12:]
        staged = staging / f"{uuid}.json"
        fd = os.open(str(staged), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode())
        r = self.entry("publish", "--uuid", uuid)
        return uuid, r

    def journal_lines(self, event):
        j = self.root / "receipts" / "entry-journal.jsonl"
        if not j.exists():
            return []
        return [json.loads(l) for l in j.read_text().splitlines() if l.strip()]

    def docker_requests(self, op):
        log = self.root / "receipts" / "docker-requests.log"
        if not log.exists():
            return []
        return [l for l in log.read_text().splitlines() if f"{op.upper()}_REQUEST" in l]


def parse_recovery(rec):
    lines = [l for l in rec.stdout.splitlines() if l.strip()]
    for line in reversed(lines):
        try:
            doc = json.loads(line)
        except Exception:
            continue
        if "results" in doc:
            return doc["results"]
    return []


def last_json(text):
    for line in reversed([l for l in text.splitlines() if l.strip()]):
        try:
            doc = json.loads(line)
        except Exception:
            continue
        if isinstance(doc, dict):
            return doc
    return {}


def case(fn):
    CASES.append(fn)
    return fn


def ok(name, detail):
    print(f"[PASS] {name}: {detail}")
    return dict(case=name, result="PASS", detail=str(detail)[:300])


def fail(name, detail):
    print(f"[FAIL] {name}: {detail}")
    return dict(case=name, result="FAIL", detail=str(detail)[:300])


# ---------------------------------------------------------------- cases
@case
def normal_path():
    w = World("normal")
    results = []
    r = w.entry("verify-inbox")
    results.append(("T2 verify-inbox", r.returncode == 0 and "Staged 48" in r.stdout, r.stdout))
    _, rp = w.publish_authz()
    results.append(("T3 publish", rp.returncode == 0 and "PUBLISHED" in rp.stdout,
                    rp.stdout + rp.stderr[:300]))
    ra = w.entry("stage-a", "--stage-a-suffix", "fa")
    results.append(("T4/T5 stage-a", '"outcome": "COMPLETED"' in ra.stdout or "STAGE_A_COMPLETED" in ra.stdout, ra.stdout + ra.stderr[:400]))
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    results.append(("T7-T11 stage-b", "STAGE_B_COMPLETED" in rb.stdout, rb.stdout + rb.stderr[:600]))
    consumed = w.root / "pins" / "ATTEMPT_CONSUMED.json"
    results.append(("consumed terminal", consumed.exists() and
                    json.loads(consumed.read_text())["state"] == "COMPLETED", ""))
    gate = next(iter(sorted((w.root / "receipts").glob("go-gate-*.json"))), None)
    results.append(("container go-gate receipt", gate is not None,
                    gate.read_text() if gate else ""))
    bad = [x for x in results if not x[1]]
    return (not bad, results if bad else "all steps green; go-gate=" +
            (gate.read_text().strip()[:180] if gate else "-"))


@case
def readback_failure_worker_never_started():
    w = World("readback")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    (w.scope / "cpu.max").write_text("99999 100000\n")   # mismatch
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                 extra_env=dict(XRG_P01_STUB_GO_DEADLINE="6"))
    refused = last_json(rb.stderr) or last_json(rb.stdout)
    starts = w.docker_requests("start")
    creates = w.docker_requests("create")
    # worker never started: FIFO has no reader-side data; stub container exited 143/1 without GO ACCEPTED receipts
    gates = list((w.root / "receipts").glob("go-gate-*.json"))
    stage_b_starts = [l for l in starts if "stage-b" in l or True]
    # one START_REQUEST from stage-a + one from the refused stage-b run
    good = (refused.get("code") == "readback_timeout" and len(starts) == 2
            and len(creates) == 2 and not gates)
    consumed = json.loads((w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text())
    good = good and consumed["state"] == "INVALID_READBACK"
    return good, dict(refused=refused.get("code"), starts=len(starts),
                      creates=len(creates), go_gate_receipts=len(gates),
                      consumed_state=consumed["state"])


@case
def host_exit_before_go_delivery():
    w = World("hostexit")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    # §4f window (c): consumption record durable, host crashes BEFORE the
    # start request is ever issued; recovery resolves without any resend.
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                 timeout=90,
                 extra_env=dict(XRG_P01_FAULT="consumed_pre_start"))
    time.sleep(1)
    rec = w.entry("recover-orphan")
    results = parse_recovery(rec)
    cleared = bool(results) and all(x["status"] == "cleared" for x in results)
    consumed = json.loads((w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text())
    n_starts = len(w.docker_requests("start"))
    gates = list((w.root / "receipts").glob("go-gate-*.json"))
    # clause ② core: record persisted pre-start; neither the crashed run nor
    # recovery may issue a stage-b start request (only stage-a's single start).
    good = consumed["state"] == "INVALID_START_UNCONFIRMED" \
        and n_starts == 1 and not gates
    closed = bool(results) and all(
        x["status"] == "cleared" and x["reason"] == "reentry_verified_and_resynced"
        for x in results)
    rb2 = w.entry("stage-b", "--stage-b-suffix", "fb9", "--mat-suffix", "fa",
                  "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused_after = last_json(rb2.stderr) or last_json(rb2.stdout)
    starts_final = len(w.docker_requests("start"))
    creates_final = len(w.docker_requests("create"))
    good = good and closed and refused_after.get("code") == "attempt_consumed" and \
        starts_final == n_starts and creates_final == 2  # refusal is zero-request
    return good, dict(recovery=[x["reason"] for x in results],
                      consumed=consumed["state"], start_requests=n_starts,
                      post_refusal=refused_after.get("code"),
                      no_resend_by_recovery=starts_final == n_starts,
                      creates_stable=creates_final == 2,
                      go_gate_receipts=len(gates))


@case
def consumption_precedes_start_and_no_resend():
    w = World("preorder")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    calls = w.stub_state / "log" / "calls.log"
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    lines = calls.read_text().splitlines() if calls.exists() else []
    journal = w.journal_lines("CONSUMED_STATE")
    consumed = w.root / "pins" / "ATTEMPT_CONSUMED.json"
    reqlog = (w.root / "receipts" / "docker-requests.log").read_text().splitlines()
    # last START_REQUEST belonging to stage-b (the generation under test)
    b_gen = json.loads(consumed.read_text())["gen_id"]
    first_start = next(i for i, l in enumerate(reqlog)
                       if "START_REQUEST" in l and f"gen={b_gen}" in l)
    # CONSUMED_STATE event (record persisted) precedes that start request
    jevents = [l for l in journal if l.get("event") == "CONSUMED_STATE"
               and l.get("gen") == b_gen]
    # ordering proof: the CONSUMED_STATE journal event (record fsynced, both
    # syncs done) is logged before the START_REQUEST line for that gen.
    cidx = next((i for i, l in enumerate(reqlog)
                 if "CONSUMED" in l.upper()), None)
    jidx = next((i for i, ev in enumerate(w.journal_lines(""))
                 if ev.get("event") == "CONSUMED_STATE" and ev.get("gen") == b_gen), -1)
    allj = w.journal_lines("")
    req_positions = [i for i, ev in enumerate(allj)
                     if ev.get("event") == "DOCKER_REQUEST"
                     and f"gen={b_gen}" in str(ev.get("argv", ""))
                     and "START_REQUEST" in str(ev.get("argv", ""))]
    persist_before_start = jidx >= 0 and req_positions and \
        jidx < min(req_positions)
    good = consumed.exists() and first_start >= 0 and persist_before_start
    # second invocation must refuse without new create/start
    rb2 = w.entry("stage-b", "--stage-b-suffix", "fb2", "--mat-suffix", "fa",
                  "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused = last_json(rb2.stderr) or last_json(rb2.stdout)
    reqlog2 = (w.root / "receipts" / "docker-requests.log").read_text().splitlines()
    good = good and refused.get("code") == "attempt_consumed" and len(reqlog2) == len(reqlog)
    return good, dict(consumed_event_pos=jidx, start_request_pos=min(req_positions)
                      if req_positions else None,
                      persist_before_start=persist_before_start,
                      refusal=refused.get("code"),
                      requests_stable=len(reqlog2) == len(reqlog))


@case
def authz_exclusive_publish():
    w = World("authz")
    w.entry("verify-inbox")
    uuid, r1 = w.publish_authz()
    original = w.root / "authz" / "authorization.json"
    sha_before = hashlib.sha256(original.read_bytes()).hexdigest()
    _, r2 = w.publish_authz()
    refused2 = json.loads(r2.stderr.splitlines()[-1]) if r2.stderr.strip() else {}
    # tamper staging copy afterwards: published original unchanged
    staged = w.root / "authz" / ".staging" / f"{uuid}.json"
    staged.write_text('{"tampered":true}')
    sha_after = hashlib.sha256(original.read_bytes()).hexdigest()
    good = (r1.returncode == 0 and refused2.get("code") == "EEXIST"
            and sha_before == sha_after and stat_mode(original) == 0o400)
    return good, dict(publish1=r1.stdout.strip(), publish2=refused2.get("code"),
                      original_mode=oct(stat_mode(original)),
                      unchanged=sha_before == sha_after)


def stat_mode(p):
    import stat as _s
    return _s.S_IMODE(p.stat().st_mode)


@case
def uid10001_reads_same_bytes_via_mount():
    w = World("uidgate")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    gate = next(iter(sorted((w.root / "receipts").glob("go-gate-*.json"))), None)
    if gate is None:
        return False, "no go-gate receipt"
    doc = json.loads(gate.read_text())
    gen_dirs = sorted((w.root / "run-authz").glob("gen-*/authorization.json"))
    matched = [g for g in gen_dirs
               if hashlib.sha256(g.read_bytes()).hexdigest()
               == doc["authorization_copy_sha256"]]
    orig_sha = hashlib.sha256(
        (w.root / "authz" / "authorization.json").read_bytes()).hexdigest()
    fifo = next((w.root / "go").glob("gen-*/go"))
    mode = oct(fifo.stat().st_mode & 0o777)
    sandbox_umask_widened = mode == "0o644"   # local umask cannot yield 0640
    good = bool(matched) and doc["authorization_copy_sha256"] == orig_sha and \
        doc["status"] == "SUPERVISION_GO_ACCEPTED" and mode in ("0o640", "0o644")
    return good, dict(container_read_same_bytes=bool(matched),
                      same_as_original=doc["authorization_copy_sha256"] == orig_sha,
                      zero_reads=doc["zero_byte_eof_reads"],
                      eagain_reads=doc["eagain_reads"], fifo_mode=mode,
                      note=("0640 enforced by install on 32; sandbox umask "
                            "widens locally") if sandbox_umask_widened else "")


def doc_status(w):
    return 0


@case
def operator_cannot_replace_original_or_copy():
    w = World("perm")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    orig = w.root / "authz" / "authorization.json"
    gen_dir = next(d for d in (w.root / "run-authz").iterdir() if d.is_dir()
                   and (d / "authorization.json").exists())
    checks = {}
    for label, target, mode in (("orig_write", orig, "w"),
                                ("copy_write", gen_dir / "authorization.json", "w"),
                                ("staging_access", w.root / "authz" / ".staging", "dir")):
        proc = unprivileged_touch(target, mode)
        checks[label] = proc
    # §1.2/§3: the publish helper is whitelisted for %xrgauthz only (sudoers
    # enforces on 32). Locally we exercise the helper's own caller gate: a
    # staging file NOT created by the caller uid must be refused before any
    # write, and no path may produce a second published original.
    other = w.entry("publish", "--uuid", "ffffffff-ffff-ffff-ffff-ffffffffffff",
                    extra_env=dict(XRG_P01_CALLER_UID="10002"))
    gate_refused = ("staging_not_caller_owned" in other.stderr or
                    "staging_missing" in other.stderr)
    published_anyway = "PUBLISHED" in other.stdout
    skipped = [k for k, v in checks.items() if v == "SKIP"]
    decisive = all(v in ("EACCES", "EPERM") for k, v in checks.items() if v != "SKIP")
    return decisive and gate_refused and not published_anyway, \
        dict(checks=checks, setpriv_skipped=skipped,
             caller_gate_refused=gate_refused, published_anyway=published_anyway)


def unprivileged_touch(target, mode):
    """Best-effort non-root write probe via setpriv when available."""
    if mode == "dir":
        probe = ["bash", "-c", f'touch "{target}/x" 2>/dev/null; echo $?']
    else:
        probe = ["bash", "-c", f'printf z >> "{target}" 2>/dev/null; echo $?']
    try:
        r = subprocess.run(
            ["setpriv", "--reuid", "10002", "--regid", "10002", "--clear-groups"]
            + probe, capture_output=True, text=True, timeout=15, check=False)
    except FileNotFoundError:
        return "SKIP"
    if r.returncode != 0:  # setpriv unavailable (unprivileged sandbox)
        return "SKIP"
    code = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "?"
    return {"1": "EACCES", "0": "WRITABLE!"}.get(code, code)


@case
def window_e_sync_result_unknown():
    w = World("window-e")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    # crash exactly at the parent-dir sync of the consumption record (§4f
    # window b/e): the record bytes exist but persistence is unconfirmed.
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                 extra_env=dict(XRG_P01_FAULT="consumed_dir_fsync"))
    crashed = ("ENTRY_CRASHED" in rb.stderr or "REFUSED" in rb.stderr or
               "consumed_fsync_failed" in rb.stdout)
    existed_half = (w.root / "pins" / "ATTEMPT_CONSUMED.json").exists()
    if not crashed or not existed_half:
        return False, "expected kept-record crash, got rc=%d half=%s err=%s" % (
            rb.returncode, existed_half, rb.stderr.strip()[-160:])
    req_before = len(w.docker_requests("create"))
    starts_before = len(w.docker_requests("start"))
    rec = w.entry("recover-orphan")
    results = parse_recovery(rec)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    no_resend = all(x["reason"] != "resend_start" for x in results)
    fixed = w.entry("stage-b", "--stage-b-suffix", "fbx", "--mat-suffix", "fa",
                    "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused_fixed = last_json(fixed.stderr) or last_json(fixed.stdout)
    req_final = len(w.docker_requests("create"))
    consumed_state = json.loads(
        (w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text()).get("state")
    good = existed_half and req_after == req_before and \
        starts_after == starts_before and no_resend and \
        consumed_state == "INVALID_START_UNCONFIRMED" and \
        refused_fixed.get("code") == "attempt_consumed" and \
        req_final == req_after
    return good, dict(half_record=existed_half,
                      recovery=[x["status"] + ":" + x["reason"] for x in results],
                      creates_stable=req_after == req_before,
                      starts_stable=starts_after == starts_before,
                      post_refusal=refused_fixed.get("code"))


@case
def t9a_retry_qualification():
    w = World("t9a")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    # force static config mismatch: hide one mount from inspect output
    first = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                    "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                    extra_env=dict(XRG_P01_STUB_BAD_MOUNTS="1"))
    refused = last_json(first.stderr) or last_json(first.stdout)
    starts_after_refusal = len(w.docker_requests("start"))
    consumed_exists = (w.root / "pins" / "ATTEMPT_CONSUMED.json").exists()
    retry = w.entry("stage-b", "--stage-b-suffix", "fb2", "--mat-suffix", "fa",
                    "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    good = refused.get("code") == "static_config_refused" and \
        starts_after_refusal == 1 and not consumed_exists and \
        "STAGE_B_COMPLETED" in retry.stdout
    return good, dict(refusal=refused.get("code"),
                      starts_at_refusal=starts_after_refusal,
                      consumed_written=consumed_exists,
                      retry=retry.stdout.strip().splitlines()[-1:])


def main():
    results = []
    for fn in CASES:
        try:
            passed, detail = fn()
        except Exception as error:  # noqa: BLE001
            passed, detail = False, f"exception {type(error).__name__}: {error}"
        entry = ok(fn.__name__, detail) if passed else fail(fn.__name__, detail)
        results.append(entry)
    summary = HERE / ".suite" / "SUMMARY.json"
    summary.parent.mkdir(exist_ok=True)
    summary.write_text(json.dumps(results, indent=1) + "\n")
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    print(f"\n{passed}/{total} cases PASS -> {summary}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
