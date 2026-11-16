#!/usr/bin/env python3
"""Item-1 real-Docker chain probe (host 38 sandbox, rehearsal image only).

Drives the FORMAL program through real_docker_mode against the real docker
CLI: stage-a materialize run + stage-b gated run with live cgroup readback
and process-level nice/ionice verification before GO. Everything it touches
is a synthetic rehearsal plane; the real snapshot plane and production mode
stay locked. Exit 0 = full chain green; receipts land under .suite/.
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
BASE = HERE / ".suite" / "real-chain-probe"
OUTER = BASE.parent
if BASE.exists():
    shutil.rmtree(BASE)
ROOT = BASE / "runtime-root"
SNAP = ROOT / "rehearsal-snapshot"
for d in (ROOT / "inbox" / "source-green-v1", ROOT / "pins", SNAP):
    d.mkdir(parents=True)
entries = {}
for i in range(48):
    f = ROOT / "inbox" / "source-green-v1" / f"file-{i:02}.dat"
    body = f"probe payload {i}\n".encode()
    f.write_bytes(body)
    entries[f.name] = hashlib.sha256(body).hexdigest()
manifest = "".join(f"{entries[n]}  {n}\n" for n in sorted(entries))
(ROOT / "inbox" / "source-green-v1" / "INPUTS.sha256").write_text(manifest)
(ROOT / "pins" / "INPUTS.admin.sha256").write_text(manifest)
SNAP.joinpath("leaf.txt").write_text("rehearsal bytes only\n")

MAT = r'''
import json, sys, time
from pathlib import Path
image_id, git_rev = sys.argv[1], sys.argv[2]
assert image_id.startswith("sha256:") and len(git_rev) == 40, "identity_shape"
auth = json.loads(Path("/authorization/authorization.json").read_text())
assert auth["status"] == "AUTHORIZED_REAL_P01_SINGLE_ATTEMPT", "authz_gate"
out = Path("/data/var/snapshots/materialization")
out.mkdir(parents=True, exist_ok=True)
doc = {"status": "REHEARSAL_MATERIALIZED", "image_id": image_id,
       "git_revision": git_rev,
       "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
(out / "request.json").write_text(json.dumps(doc, sort_keys=True) + "\n")
print("MATERIALIZE_REAL_REQUEST_OK", json.dumps(doc, sort_keys=True))
'''
MATF = BASE / "materialize-rehearsal.py"
MATF.write_text(MAT)
ORIG = BASE / "installed-origin-rehearsal.py"
ORIG.write_text('''import os, sys
# rehearsal installed-origin twin: records origins then execs its tail args
sys.stderr.write("INSTALLED_ORIGIN_REHEARSAL\\n")
os.execv(sys.executable, [sys.executable] + sys.argv[1:])
''')

IMAGE = "xiangrugu-rehearsal:p01-local"
code = subprocess.run(["docker", "images", "--no-trunc", "--format",
                       "{{.ID}}", IMAGE], capture_output=True, text=True)
if code.returncode != 0 or not code.stdout.strip():
    print("SKIP: rehearsal image absent:", code.stderr.strip()[:120])
    sys.exit(7)
image_id = code.stdout.strip()

env = dict(os.environ)
env.update(XRG_P01_ROOT=str(ROOT), XRG_P01_DOCKER="docker",
           XRG_P01_REAL_CHAIN="1", XRG_P01_IMAGE_ID=image_id,
           XRG_P01_IMAGE_REF="xiangrugu-rehearsal:p01-local",
           XRG_P01_SNAPSHOT_HOST=str(SNAP),
           XRG_P01_MATERIALIZE_SCRIPT=str(MATF),
           XRG_P01_ORIGIN_SCRIPT=str(ORIG),
           XRG_P01_SUPERVISOR_LIB=str(HERE),
           PYTHONPATH=str(HERE))
env.pop("XRG_P01_FIXTURE", None)

def run(args, timeout=240):
    return subprocess.run([sys.executable, "xrg_p01_entry.py", *args],
                          capture_output=True, text=True, env=env,
                          timeout=timeout)

results = []
r = run(["verify-inbox"])
results.append(("verify-inbox", r.returncode == 0, r.stdout[-100:] + r.stderr[-100:]))
staging = ROOT / "authz" / ".staging"; staging.mkdir(parents=True, exist_ok=True)
u = "aaaaaaaa-bbbb-cccc-dddd-0000000000f1"
doc = {"attempt_id": "real-p01-20261113-a", "granted_by": "茶香-probe",
       "one_attempt_only": True,
       "status": "AUTHORIZED_REAL_P01_SINGLE_ATTEMPT",
       "task_card_sha256": "41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69",
       "version": 1}
fd = os.open(str(staging / f"{u}.json"), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.write(fd, (json.dumps(doc, sort_keys=True) + "\n").encode()); os.close(fd)
r = run(["publish", "--uuid", u])
results.append(("publish", r.returncode == 0 and "PUBLISHED" in r.stdout, r.stdout[-80:] + r.stderr[-80:]))
r = run(["stage-a", "--stage-a-suffix", "pra"])
sa_ok = r.returncode == 0 and "STAGE_A_COMPLETED" in r.stdout
results.append(("stage-a", sa_ok, (r.stdout or "").strip().splitlines()[-1:] and r.stdout.strip().splitlines()[-1][-160:] or r.stderr[-200:]))
gen_a = ""
try:
    done = json.loads((ROOT / "receipts" / "stage-a-done.json").read_text())
    gen_a = done.get("gen_id", "")
except Exception:
    pass
argv_a = ROOT / "run-authz" / f"gen-{gen_a}" / "argv.txt"
results.append(("stage-a argv receipt", sa_ok and argv_a.exists(), str(argv_a)))
mat_req = ROOT / "output" / f"gen-{gen_a}" / "durable" / "materialization" / "request.json"
results.append(("stage-a materialization durable", sa_ok and mat_req.exists(), str(mat_req)))

rb = run(["stage-b", "--stage-b-suffix", "prb", "--mat-suffix", "pra",
          "--request-pin", "a" * 64, "--approval-pin", "b" * 64])
sb_line = (rb.stdout or "").strip().splitlines()
results.append(("stage-b", rb.returncode == 0 and any("STAGE_B_COMPLETED" in l for l in sb_line),
                (sb_line[-1][-160:] if sb_line else rb.stderr[-300:])))
gen_b = ""
for l in sb_line:
    if "gen=" in l:
        gen_b = l.split("gen=")[-1].strip()
prio = ROOT / "receipts" / f"priority-audit-{gen_b}.json"
if prio.exists():
    pdoc = json.loads(prio.read_text())
    results.append(("pre-GO priority audit ok", pdoc.get("ok") is True,
                    f"tasks={pdoc.get('tasks')} sample={pdoc.get('sample')}"))
else:
    results.append(("pre-GO priority audit ok", False, "receipt missing"))
verdict = ROOT / "output" / f"gen-{gen_b}" / "supervision-verdict.json"
results.append(("stage-b supervisor verdict", verdict.exists(),
                verdict.read_text()[:120] if verdict.exists() else str(verdict)))
lease = ROOT / "go" / f"gen-{gen_b}" / "lease"
samples = ROOT / "go" / f"gen-{gen_b}" / "host-samples.log"
results.append(("monitor lease fed", lease.exists() and samples.exists() and
                len(samples.read_text().splitlines()) >= 18,   # >=3 min @10s
                f"lease_exists={lease.exists()}"))
argv_b = ROOT / "run-authz" / f"gen-{gen_b}" / "argv.txt"
results.append(("stage-b argv receipt", argv_b.exists(), str(argv_b)))

summary = []
allok = True
for name, ok, detail in results:
    print(("PASS" if ok else "FAIL"), name, "::", str(detail)[:180])
    allok = allok and ok
    summary.append(dict(case=name, result="PASS" if ok else "FAIL",
                        detail=str(detail)[:300]))
(BASE / "PROBE-SUMMARY.json").write_text(json.dumps(summary, indent=1) + "\n")
print("ALL GREEN" if allok else "NOT GREEN")
sys.exit(0 if allok else 1)
