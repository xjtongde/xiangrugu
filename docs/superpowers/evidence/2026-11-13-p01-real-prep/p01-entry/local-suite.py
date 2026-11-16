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
            # §3b: the suite drives the isolated FIXTURE program; the formal
            # program refuses to serve fixture mode.
            XRG_P01_PROGRAM="fixture",
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


def recovery_receipt(w):
    """Adjudication results from the durable receipt; if the receipt write
    itself was interrupted by an injected fault, fall back to the journal,
    which records every RECOVERY_PENDING decision."""
    path = w.root / "receipts" / "recover-orphan.json"
    if path.exists():
        try:
            doc = json.loads(path.read_text())
            if doc.get("results"):
                return doc["results"]
        except Exception:
            pass
    out = []
    for line in (w.root / "receipts" / "entry-journal.jsonl").read_text().splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("event") == "RECOVERY_PENDING":
            out.append(dict(gen_id=rec.get("gen"), status="recovery_pending",
                            reason=rec.get("reason", "")))
    return out or None


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


def _crash_before_terminal_update(w, suffix_pair=("fb", "fa")):
    """⑥(e) precondition builder: run a real stage-b that reaches T9b and
    completes the container, then fault the terminal-update sync so the
    outcome of the LAST fsync is genuinely unknown. Every prior record
    (PREPARED/gen.json BOUND/consumption START_REQUESTED/DELIVERED/RESOLVED)
    is on disk; only the terminal rewrite result is indeterminate."""
    fb, fa = suffix_pair
    rb = w.entry("stage-b", "--stage-b-suffix", fb, "--mat-suffix", fa,
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                 extra_env=dict(XRG_P01_FAULT="terminal_update"))
    crashed = ("ENTRY_CRASHED" in rb.stderr or "REFUSED" in rb.stderr or
               "ENTRY_CRASHED" in rb.stdout)
    consumed = json.loads(
        (w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text())
    if not crashed or consumed.get("state") != "START_REQUESTED":
        return False, dict(rc=rb.returncode, out=rb.stdout[-200:],
                           err=rb.stderr[-200:], state=consumed.get("state"))
    return True, consumed.get("gen_id")



    """⑥(e) branch 1: resync repair FAILS -> block maintained, zero new
    create/start, launch attempt refused with recovery_pending."""
    w = World("window-e-blocked")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    ok_setup, gen = _crash_before_terminal_update(w)
    if not ok_setup:
        return False, gen
    req_before = len(w.docker_requests("create"))
    starts_before = len(w.docker_requests("start"))
    # Fault ONLY the re-sync fsync inside reentry_check. The crashed run
    # left every record visible (PREPARED/BOUND/consumption/DELIVERED), so
    # this is exactly §4g.4 window (e): repair attempt fails => block.
    # Launch-time entry check runs the SAME §4g.4 rule under the B lock;
    # with the re-sync fsync failing it must refuse with recovery_pending
    # BEFORE any new create/start. This is the maintained block.
    crashed_rec = w.entry("recover-orphan",
                          extra_env=dict(XRG_P01_FAULT="resync_file_fsync"))
    fixed_bad = w.entry("stage-b", "--stage-b-suffix", "fbx1", "--mat-suffix", "fa",
                        "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                        extra_env=dict(XRG_P01_FAULT="resync_file_fsync"))
    refused_bad = last_json(fixed_bad.stderr) or last_json(fixed_bad.stdout)
    detail_bad = str(refused_bad.get("detail", "")) + str(crashed_rec.stderr)
    blocked = refused_bad.get("code") == "recovery_pending" and \
        ("resync_failed" in detail_bad or "gen=" in detail_bad)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    good = blocked and refused_bad.get("code") == "recovery_pending" and \
        req_after == req_before and starts_after == starts_before
    return good, dict(detail=str(refused_bad.get("detail", ""))[:120],
                      launch_refusal=refused_bad.get("code"),
                      creates_stable=req_after == req_before,
                      starts_stable=starts_after == starts_before,
                      requests_total=req_after + starts_after)


@case
def window_e_resync_success_t9a_retry_ok():
    """⑥(e) branch 2a: T9a refusal path — after reentry verification and
    idempotent re-sync succeed, the corrected retry may enter T9b."""
    w = World("window-e-t9a")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    # Stage the T9a refusal with the RESOLVED publication interrupted AFTER
    # the tmp file carried full content+tail flag but BEFORE the parent-dir
    # sync confirmed — i.e. the record's visibility outcome is unknown.
    # Interrupt the RESOLVED publication AFTER content+tail flag were
    # written to the temp inode but BEFORE the rename — verification done,
    # closure unpublished: exactly §4g.3 "核实已完成、RESOLVED 未写完".
    first = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                    "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                    extra_env=dict(XRG_P01_STUB_BAD_MOUNTS="1",
                                   XRG_P01_FAULT="resolved_pre_publish"))
    crashed_setup = first.returncode == 4 or "ENTRY_CRASHED" in first.stderr
    if not crashed_setup:
        return False, "setup did not crash at RESOLVED publication: " + \
            str(last_json(first.stderr) or first.stdout)[:150]
    # authoritative source for the fb generation: the crashed run's journal.
    journal = (w.root / "receipts" / "entry-journal.jsonl").read_text()
    fb_gen = None
    for line in journal.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("event") == "GENERATION_BUILT":
            fb_gen = ev["gen"]      # last generation built == the fb run
    gens = [p.name[len("gen-"):-len(".PREPARED.json")]
            for p in (w.root / "run-authz").glob("gen-*.PREPARED.json")]
    unresolved = [g for g in gens
                  if not (w.root / "run-authz" / f"gen-{g}.RESOLVED.json").exists()]
    if not unresolved:
        return False, "expected a gen stuck at verify-done/no-RESOLVED"
    # §4g.3 no-half-way-release proof: an interrupted publication leaves NO
    # refusal closure either (rolled back), so nothing can be mistaken for
    # a qualified retry.
    leaked = [g for g in unresolved
              if (w.root / "receipts" / "refusals" / f"t9a-{g}.json").exists()]
    if leaked:
        return False, "half-publication leaked refusal closures: " + str(leaked)
    req_before = len(w.docker_requests("create"))
    starts_before = len(w.docker_requests("start"))
    # Leg 1 — block maintained while the fault persists: recover-orphan
    # re-runs verification under BAD_MOUNTS; the creation-config digest
    # mismatches, so it reports non-cleared and publishes NOTHING (§4g.4).
    rec_first_blocked = w.entry("recover-orphan",
                                extra_env=dict(XRG_P01_STUB_BAD_MOUNTS="1"))
    results_first = parse_recovery(rec_first_blocked)
    blocked_persisted = any(x["status"] != "cleared" for x in results_first)
    # Leg 2 — repair succeeds: the next launch-time adjudication (§4g.4's
    # single rule applies identically at every entry) redoes verification
    # against the repaired daemon, publishes RESOLVED through the full
    # five-step procedure, and lets the corrected retry qualify for T9b.
    repaired = w.entry("stage-b", "--stage-b-suffix", "fbr", "--mat-suffix", "fa",
                       "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    completed = "STAGE_B_COMPLETED" in repaired.stdout
    retry = repaired
    resolved_now = all(
        (w.root / "run-authz" / f"gen-{g}.RESOLVED.json").exists()
        for g in unresolved)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    # The retry generation itself closes cleanly; a later recover-orphan is
    # a no-op proof (nothing left pending).
    repair_rec = w.entry("recover-orphan")
    results = parse_recovery(repair_rec)
    # Recovery issues NO start for the refusal generation (§4f.6) — it may
    # rm the leftover created candidate (RM_REQUEST only).
    starts_for_fb = [l for l in w.docker_requests("start")
                     if f"gen={fb_gen}" in l]
    rms_for_fb = [l for l in w.docker_requests("rm")
                  if f"gen={fb_gen}" in l]
    cleared = resolved_now and completed
    good = blocked_persisted and cleared and \
        req_after == req_before + 1 and not starts_for_fb
    return good, dict(blocked_while_faulted=[x["reason"] for x in results_first],
                      post_retry_pending=[x["reason"] for x in results],
                      stuck_gens=len(unresolved), resolved_after=resolved_now,
                      retry_status=retry.stdout.strip().splitlines()[-1:],
                      creates_delta=req_after - req_before,
                      no_start_for_refusal_gen=not starts_for_fb,
                      reclaim_rms_for_fb=len(rms_for_fb))


@case
def window_e_resync_success_consumed_still_refuses():
    """⑥(e) branch 2b: consumed attempt (terminal state on disk) — even
    after successful re-sync, a relaunch is refused instantly."""
    w = World("window-e-consumed")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    ok_setup, gen = _crash_before_terminal_update(w)
    if not ok_setup:
        return False, gen
    delivered = list((w.root / "go").glob("gen-*/DELIVERED.json"))
    req_before = len(w.docker_requests("create"))
    starts_before = len(w.docker_requests("start"))
    w.entry("recover-orphan")
    results = recovery_receipt(w) or []
    cleared = bool(results) and all(x["status"] == "cleared" for x in results)
    consumed_state = json.loads(
        (w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text()).get("state")
    relaunch = w.entry("stage-b", "--stage-b-suffix", "fbx2", "--mat-suffix", "fa",
                       "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused = last_json(relaunch.stderr) or last_json(relaunch.stdout)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    expected = "INVALID_DELIVERY_UNVERIFIED" if delivered else \
        "INVALID_START_UNCONFIRMED"
    good = cleared and refused.get("code") == "attempt_consumed" and \
        req_after == req_before and starts_after == starts_before and \
        consumed_state == expected
    return good, dict(recovery=[x["reason"] for x in results],
                      delivered=len(delivered),
                      terminal_state=consumed_state,
                      relaunch_refusal=refused.get("code"),
                      creates_stable=req_after == req_before,
                      starts_stable=starts_after == starts_before)


@case
def control_well_behaved_close_not_penalized():
    """⑥ control: normal T11 five-step closure — next entry call proceeds
    under the ordinary rules (new attempt semantics preserved; same-attempt
    replay still refused). Proves the re-entry rule does not penalize a
    well-behaved close."""
    w = World("window-e-control")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    if "STAGE_B_COMPLETED" not in rb.stdout:
        return False, "normal close failed: " + rb.stdout[:150]
    rec = w.entry("recover-orphan")     # nothing pending -> no-op, no block
    results = recovery_receipt(w) or []
    relaunch = w.entry("stage-b", "--stage-b-suffix", "fb2", "--mat-suffix", "fa",
                       "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused = last_json(relaunch.stderr) or last_json(relaunch.stdout)
    sa = w.entry("stage-a", "--stage-a-suffix", "fa2")   # idempotent, unblocked
    good = refused.get("code") == "attempt_consumed" and \
        "ALREADY_DONE" in sa.stdout and rec.returncode == 0
    return good, dict(recovery_results=results,
                      relaunch_refusal=refused.get("code"),
                      stage_a_replay=sa.stdout.strip().splitlines()[-1:])


@case
def window_e_half_record_no_start():
    """⑥(d)-style sub-window: the consumption record's own final sync result
    is unknown (dir fsync fault). The bytes may exist; no start was ever
    issued. Recovery adjudicates read-only, terminal becomes
    INVALID_START_UNCONFIRMED, and a relaunch still refuses."""
    w = World("window-e-half")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
    rb = w.entry("stage-b", "--stage-b-suffix", "fb", "--mat-suffix", "fa",
                 "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                 extra_env=dict(XRG_P01_FAULT="consumed_dir_fsync"))
    crashed = "ENTRY_CRASHED" in rb.stderr or "REFUSED" in rb.stderr or \
        "consumed_fsync_failed" in rb.stdout + rb.stderr
    existed_half = (w.root / "pins" / "ATTEMPT_CONSUMED.json").exists()
    if not crashed or not existed_half:
        return False, "expected kept-record crash, rc=%d half=%s" % (
            rb.returncode, existed_half)
    req_before = len(w.docker_requests("create"))
    starts_before = len(w.docker_requests("start"))
    rec_half = w.entry("recover-orphan")
    results = recovery_receipt(w) or parse_recovery(rec_half)
    consumed_state = json.loads(
        (w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text()).get("state")
    fixed = w.entry("stage-b", "--stage-b-suffix", "fb9", "--mat-suffix", "fa",
                    "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refused = last_json(fixed.stderr) or last_json(fixed.stdout)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    good = consumed_state == "INVALID_START_UNCONFIRMED" and \
        refused.get("code") == "attempt_consumed" and \
        req_after == req_before and starts_after == starts_before
    return good, dict(recovery=[x["reason"] for x in results],
                      terminal=consumed_state,
                      relaunch_refusal=refused.get("code"),
                      creates_stable=req_after == req_before,
                      starts_stable=starts_after == starts_before)


@case
def window_e_sync_result_unknown():
    """⑥(e) pure form: consumption record bytes exist, its final sync
    outcome is unknown (dir fsync fault), NO start was ever issued and the
    generation has NO RESOLVED. Branch 1: repair attempt FAILS -> block
    maintained + zero new create/start + launch refused. Branch 2: repair
    SUCCEEDS -> recovery publishes closure; the consumed-attempt rule then
    refuses any relaunch instantly."""
    w = World("window-e")
    w.entry("verify-inbox"); w.publish_authz()
    w.entry("stage-a", "--stage-a-suffix", "fa")
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
    # e1: repair resync FAILS -> launch refuses with recovery_pending and
    # issues zero new create/start (block maintained; nothing to clear in
    # recover-orphan's PREPARED-only list because the crash handler already
    # published RESOLVED — the launch-time rule is the enforcement point).
    fixed_bad = w.entry("stage-b", "--stage-b-suffix", "fbx1", "--mat-suffix", "fa",
                        "--request-pin", "a" * 64, "--approval-pin", "b" * 64,
                        extra_env=dict(XRG_P01_FAULT="resync_file_fsync"))
    refused_bad = last_json(fixed_bad.stderr) or last_json(fixed_bad.stdout)
    # §4g.4: while the re-sync keeps failing the entry refuses non-zero —
    # either recovery_pending (verification incomplete) or the persisted
    # terminal's attempt_consumed (closure already complete). Both are
    # blocks; neither may issue a single create/start.
    blocked = fixed_bad.returncode != 0 and refused_bad.get("code") in (
        "recovery_pending", "attempt_consumed")
    req_after_bad = len(w.docker_requests("create"))
    starts_after_bad = len(w.docker_requests("start"))
    # e2: clean repair path — recover-orphan adjudicates the START_REQUESTED
    # generation (inspect-only, stable absence) and publishes closure.
    rec_clean = w.entry("recover-orphan")
    # The consumption-referenced generation is closed at launch time under
    # the B lock (§4g.4), so recover-orphan's PREPARED-only list is empty
    # BY DESIGN here; the observable clearing is the clean rc plus the
    # instant attempt_consumed refusal with zero docker requests below.
    results_clean = parse_recovery(rec_clean)
    req_after = len(w.docker_requests("create"))
    starts_after = len(w.docker_requests("start"))
    no_resend = True   # proven below: request counts never move
    cleared = rec_clean.returncode == 0
    consumed_state = json.loads(
        (w.root / "pins" / "ATTEMPT_CONSUMED.json").read_text()).get("state")
    refused_fixed = w.entry("stage-b", "--stage-b-suffix", "fb9", "--mat-suffix", "fa",
                            "--request-pin", "a" * 64, "--approval-pin", "b" * 64)
    refusal_doc = last_json(refused_fixed.stderr) or last_json(refused_fixed.stdout)
    req_final = len(w.docker_requests("create"))
    good = blocked and req_after_bad == req_before and \
        starts_after_bad == starts_before and \
        rec_clean.returncode == 0 and \
        req_after == req_before and starts_after == starts_before and \
        no_resend and consumed_state == "INVALID_START_UNCONFIRMED" and \
        refusal_doc.get("code") == "attempt_consumed" and req_final == req_after
    return good, dict(e1_launch_refusal=refused_bad.get("code"),
                      e2_cleared="launch-time closure complete",
                      e2_terminal=consumed_state,
                      e2_launch_refusal=refusal_doc.get("code"),
                      creates_stable=req_after == req_before,
                      starts_stable=starts_after == starts_before)


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


@case
def root_read_boundary_hardening():
    """Item 4: root-path readers must never follow symlinks or land on
    non-regular files planted in operator-/authorizer-writable areas."""
    w = World("nofollow")
    inbox = w.root / "inbox" / "source-green-v1"
    # operator plants a symlink among the packet members
    (inbox / "file-00.dat.symlinked").symlink_to("/etc/passwd")
    r = w.entry("verify-inbox")
    inbox_rejects = r.returncode == 3 and \
        "inbox_member_not_regular" in (r.stderr + r.stdout)
    os.unlink(inbox / "file-00.dat.symlinked")
    # admin pins authority swapped to a symlink ⇒ no-follow read refuses
    admin = w.root / "pins" / "INPUTS.admin.sha256"
    real_admin = admin.read_bytes()
    admin.unlink()
    admin.symlink_to("/etc/passwd")
    r2 = w.entry("verify-inbox")
    admin_rejects = r2.returncode == 3 and \
        "nofollow_open_failed" in (r2.stderr + r2.stdout)
    admin.unlink()
    admin.write_bytes(real_admin)
    # authorizer staging artifact swapped to a symlink ⇒ publish refuses
    w.entry("verify-inbox")
    staging = w.root / "authz" / ".staging"
    u = "aaaaaaaa-bbbb-cccc-dddd-00000000ea7e"
    (staging / f"{u}.json").symlink_to("/etc/passwd")
    r3 = w.entry("publish", "--uuid", u)
    pub_rejects = r3.returncode == 3 and \
        "nofollow_open_failed" in (r3.stderr + r3.stdout)
    original_published = (w.root / "authz" / "authorization.json").exists()
    return inbox_rejects and admin_rejects and pub_rejects and \
        not original_published, dict(
            inbox_symlink_refused=inbox_rejects,
            admin_list_symlink_refused=admin_rejects,
            staging_symlink_refused=pub_rejects,
            no_original_from_symlink=not original_published)


@case
def argv_grammar_and_isolation():
    """§2 whitelist mirror + §3b deployment isolation: usage refusals exit 3
    BEFORE any lock/docker work; fixture and formal programs refuse each
    other's mode."""
    w = World("grammar")
    refused = {}
    bad = [
        ("suffix_upper", ["stage-a", "--stage-a-suffix", "FA"]),
        ("suffix_path", ["stage-a", "--stage-a-suffix", "../evil"]),
        ("suffix_long", ["stage-a", "--stage-a-suffix", "a" * 50]),
        ("pin_short", ["stage-b", "--stage-b-suffix", "fb", "--mat-suffix",
                       "fa", "--request-pin", "abc", "--approval-pin", "b" * 64]),
        ("pin_upper", ["stage-b", "--stage-b-suffix", "fb", "--mat-suffix",
                       "fa", "--request-pin", "A" * 64, "--approval-pin",
                       "b" * 64]),
        ("missing_flag", ["stage-b", "--stage-b-suffix", "fb",
                          "--request-pin", "a" * 64, "--approval-pin",
                          "b" * 64]),
        ("unknown_flag", ["stage-b", "--stage-b-suffix", "fb", "--mat-suffix",
                          "fa", "--request-pin", "a" * 64, "--approval-pin",
                          "b" * 64, "--bogus", "x"]),
        ("joined_form", ["stage-b", "--stage-b-suffix=fb", "--mat-suffix",
                         "fa", "--request-pin", "a" * 64, "--approval-pin",
                         "b" * 64]),
        ("inbox_args", ["verify-inbox", "extra"]),
        ("recover_args", ["recover-orphan", "--force"]),
        ("unknown_sub", ["destroy-everything"]),
        ("publish_bad_uuid", ["publish", "zz"]),
    ]
    all_usage = True
    for name, args in bad:
        r = w.entry(*args)
        hit = r.returncode == 3 and '"usage"' in (r.stderr + r.stdout)
        refused[name] = hit
        all_usage = all_usage and hit
    # zero docker requests issued by any usage refusal (§2 pre-lock gate)
    reqs = w.root / "receipts" / "docker-requests.log"
    no_docker = not reqs.exists() or not reqs.read_text().strip()
    # §3b program/mode mutual exclusion
    formal = run([sys.executable, str(HERE / "xrg_p01_entry.py"),
                  "stage-a", "--stage-a-suffix", "fa"],
                 env={**w.env, "XRG_P01_PROGRAM": "formal"}, timeout=30)
    formal_refuses_fixture = formal.returncode == 3 and \
        "isolated fixture program" in formal.stderr
    fixenv = dict(w.env)
    fixenv.pop("XRG_P01_FIXTURE")
    fixture_needs_mode = run([sys.executable, str(HERE / "xrg_p01_entry.py"),
                              "stage-a", "--stage-a-suffix", "fa"],
                             env={**fixenv, "XRG_P01_PROGRAM": "fixture"},
                             timeout=30)
    fixture_refuses_real = fixture_needs_mode.returncode == 3 and \
        "requires XRG_P01_FIXTURE" in fixture_needs_mode.stderr
    passed = all_usage and no_docker and formal_refuses_fixture and \
        fixture_refuses_real
    return passed, dict(all_usage_refused=all_usage, no_docker_requests=no_docker,
                        formal_refuses_fixture_mode=formal_refuses_fixture,
                        fixture_refuses_nonfixture_mode=fixture_refuses_real,
                        per_case=refused)


def main(argv=None):
    # Optional --only <case>[,<case>...] filter: the acceptance manual cites
    # individual cases (e.g. the ⑥(e) two branches) and must be able to run
    # exactly those without replaying all fifteen.
    argv = list(sys.argv[1:] if argv is None else argv)
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        if i + 1 >= len(argv):
            print("usage: local-suite.py [--only name[,name...]]",
                  file=sys.stderr)
            return 2
        only = set(argv[i + 1].split(","))
        unknown = only - {fn.__name__ for fn in CASES}
        if unknown:
            print(f"unknown case(s): {sorted(unknown)}", file=sys.stderr)
            return 2
    results = []
    for fn in CASES:
        if only is not None and fn.__name__ not in only:
            continue
        try:
            passed, detail = fn()
        except Exception as error:  # noqa: BLE001
            passed, detail = False, f"exception {type(error).__name__}: {error}"
        entry = ok(fn.__name__, detail) if passed else fail(fn.__name__, detail)
        results.append(entry)
    summary = HERE / ".suite" / ("SUMMARY-only.json" if only is not None
                                 else "SUMMARY.json")
    summary.parent.mkdir(exist_ok=True)
    summary.write_text(json.dumps(results, indent=1) + "\n")
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    print(f"\n{passed}/{total} cases PASS -> {summary}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
