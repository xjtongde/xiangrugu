#!/usr/bin/env bash
# Fixture container-init simulator. $1 = stub container dir. Mirrors the v14
# T10 GO gate: NONBLOCK open of the gen FIFO, two-phase read (zero-byte phase
# tolerates EOF(0) and EAGAIN until deadline; frame phase validates exactly
# one `GO <hex64>` at EOF), nonce recomputed from same-generation confirmed
# bytes, then writes exit code + go-gate receipt.
set -u
d="$1"
gen="$(python3 -c "import json;print(json.load(open('$d/meta.json'))['labels'].get('io.xiangrugu.attempt-gen',''))")"
exec python3 - "$d" "$gen" <<'PY'
import hashlib, json, os, sys, time
d, gen_id = sys.argv[1], sys.argv[2]
def verdict(code, status, reason=""):
    json.dump(dict(exit_code=code, status=status, reason=reason,
                   finished_at=time.time()), open(f"{d}/outcome.json", "w"))


if os.environ.get("XRG_P01_STUB_GO", "on") == "off":
    # Stage A container-init: no GO gate at all; exits 0 immediately.
    verdict(0, "MATERIALIZE_REAL_REQUEST_OK")
    raise SystemExit(0)
root = os.environ["XRG_P01_ROOT"]
open(f"{d}/runner.pid", "w").write(str(os.getpid()))
deadline = time.time() + int(os.environ.get("XRG_P01_STUB_GO_DEADLINE", "45"))
fifo = f"{root}/go/gen-{gen_id}/go"
genjson = f"{root}/run-authz/gen-{gen_id}/gen.json"


def finish(code, status, reason=""):
    verdict(code, status, reason)
    print(json.dumps(dict(status=status, reason=reason, ready_for_import=False)))
    raise SystemExit(code)


try:
    doc = json.load(open(genjson))
except Exception:
    finish(1, "SUPERVISION_FAILED", "gen_record")
confirmed, attempt = doc["confirmed_sha256"], doc["attempt"]
expected = hashlib.sha256((confirmed + gen_id + attempt).encode()).hexdigest()
buffer, zero_reads, again_reads = b"", 0, 0
fd = None
open_deadline = time.time() + min(10, max(1, deadline - time.time()))
while fd is None:
    try:
        fd = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        if exc.errno != 2:      # ENOENT: generation dir not ready yet
            finish(1, "SUPERVISION_ABORTED_NO_GO", f"open:{exc.errno}")
        if time.time() >= open_deadline:
            finish(1, "SUPERVISION_ABORTED_NO_GO", "open_timeout")
        time.sleep(0.05)
try:
    while time.time() < deadline:
        try:
            chunk = os.read(fd, 4096)
        except BlockingIOError:
            again_reads += 1
            chunk = None
        if chunk is not None:
            if chunk == b"":
                if not buffer:
                    zero_reads += 1
                else:
                    lines = buffer.split(b"\n")
                    if len(lines) != 2 or lines[1] != b"" or not lines[0].startswith(b"GO "):
                        finish(1, "SUPERVISION_ABORTED_NO_GO", "frame_malformed")
                    nonce = lines[0][3:].decode("ascii", "replace")
                    if nonce != expected:
                        finish(1, "SUPERVISION_ABORTED_NO_GO", "nonce_mismatch")
                    copy_path = f"{root}/run-authz/gen-{gen_id}/authorization.json"
                    actual = hashlib.sha256(open(copy_path, "rb").read()).hexdigest()
                    if actual != confirmed:
                        finish(1, "SUPERVISION_ABORTED_NO_GO", "copy_mismatch")
                    rdir = f"{root}/receipts"; os.makedirs(rdir, exist_ok=True)
                    receipt = dict(status="SUPERVISION_GO_ACCEPTED", nonce=nonce,
                                   zero_byte_eof_reads=zero_reads,
                                   eagain_reads=again_reads,
                                   authorization_copy_sha256=actual,
                                   accepted_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
                    with open(f"{rdir}/go-gate-{gen_id}.json", "w") as fh:
                        fh.write(json.dumps(receipt, sort_keys=True) + "\n")
                    finish(0, "SUPERVISION_COMPLETED_WITH_GO")
                continue
            buffer += chunk
        time.sleep(0.05)
    finish(1, "SUPERVISION_ABORTED_NO_GO", "go_timeout")
finally:
    os.close(fd)
PY
