#!/usr/bin/env bash
# Fixture docker stub for p01 entry acceptance (host 38 local suite ONLY).
# Never install on 32. State lives under $XRG_P01_STUB_STATE. create/start/
# stop/rm/inspect/ps simulate container lifecycle; `start` spawns the runner
# script named by XRG_P01_STUB_RUNNER so tests control the worker side.
set -u
export XRG_P01_STUB_STATE="${XRG_P01_STUB_STATE:?stub needs state dir}"
mkdir -p "$XRG_P01_STUB_STATE/containers" "$XRG_P01_STUB_STATE/log"
exec python3 - "$@" <<'PY'
import json, os, subprocess, sys, time, hashlib, pathlib
state = pathlib.Path(os.environ["XRG_P01_STUB_STATE"])
cont = state / "containers"; cont.mkdir(parents=True, exist_ok=True)
argv = sys.argv[1:]
log = open(state / "log" / "calls.log", "a") if (state / "log").mkdir(exist_ok=True) or True else None
def out(s=""): print(s)
if not argv: sys.exit(0)
sub = argv[0]; rest = argv[1:]
def cid_dir(cid): return cont / cid


def read_meta(d):
    return json.loads((d / "meta.json").read_text())


def write_meta(d, m):
    json.dump(m, open(d / "meta.json", "w"))


def runner_alive(d):
    pidfile = d / "runner.pid"
    if not pidfile.exists():
        return False
    try:
        os.kill(int(pidfile.read_text()), 0)
        return True
    except (ProcessLookupError, ValueError):
        return False


def verdict_of(d):
    v = d / "outcome.json"
    if v.exists():
        try:
            return json.loads(v.read_text())
        except Exception:
            pass
    return None


def settle(d, timeout=8):
    """Wait for the runner to finish; its exit code is authoritative."""
    end = time.time() + timeout
    while runner_alive(d) and time.time() < end:
        time.sleep(0.05)
    m = read_meta(d)
    if m["status"] != "running":
        return m
    v = verdict_of(d)
    if v is not None:
        m.update(status="exited", exit_code=v.get("exit_code"),
                 outcome=v.get("status"), reason=v.get("reason", ""))
        write_meta(d, m)
    return m


def signal_runner(d, sig):
    pidfile = d / "runner.pid"
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text()), sig)
        except (ProcessLookupError, ValueError):
            pass
if sub == "create":
    labels, mounts, opts = {}, [], {}
    VALUE_FLAGS = {"--cpus", "--memory", "--memory-swap", "--pids-limit",
                   "--network", "--security-opt", "--entrypoint", "--workdir",
                   "--tmpfs", "--user", "--stop-timeout"}
    BOOL_FLAGS = {"--read-only", "--init", "--privileged"}
    it = iter(rest)
    positional = []
    while True:
        try: token = next(it)
        except StopIteration: break
        if "=" in token and token.startswith("--"):
            head, _, value = token.partition("=")
            if head == "--label":
                k, v = value.split("=", 1); labels[k] = v
            elif head == "--mount":
                mounts.append(value)
            elif head in ("--cpus", "--memory", "--memory-swap", "--pids-limit"):
                opts[head[2:]] = value
            continue
        if token == "--label":
            k, v = next(it).split("=", 1); labels[k] = v
        elif token == "--mount":
            mounts.append(next(it))
        elif token in VALUE_FLAGS:
            value = next(it, "")
            if token in ("--cpus", "--memory", "--memory-swap", "--pids-limit"):
                opts[token[2:]] = value
        elif token in BOOL_FLAGS:
            pass
        elif token.startswith("--"):
            pass                 # unknown boolean-ish flag
        else: positional.append(token)
    image = positional[0] if positional else "img"
    cid = hashlib.sha256(f"{time.time_ns()}{len(list(cont.iterdir()))}".encode()).hexdigest()[:64]
    d = cid_dir(cid); d.mkdir()
    (d / "meta.json").write_text(json.dumps(dict(
        id=cid, labels=labels, mounts=mounts, opts=opts, image=image,
        cmd=positional[1:], status="created", exit_code=None)))
    out(cid)
elif sub == "start":
    cid = rest[-1]
    d = cid_dir(cid)
    meta = read_meta(d)
    if os.environ.get("XRG_P01_STUB_START_FAIL"):
        sys.stderr.write("Error: injected start failure\n"); sys.exit(1)
    env = dict(os.environ)
    runner = env.get("XRG_P01_STUB_RUNNER")
    proc_log = open(d / "proc.log", "w")
    if runner:
        run_label = meta["labels"].get("io.xiangrugu.synthetic-run", "")
        env["XRG_P01_STUB_GO"] = "off" if run_label.startswith("stage-a") else "on"
        # Detached supervisor: Popen returns immediately, the container-init
        # keeps running in its own session and writes outcome.json when done.
        subprocess.Popen(["setsid", "-f", "bash", runner, str(d)],
                         stdout=proc_log, stderr=proc_log, env=env,
                         close_fds=True)
        end = time.time() + 5
        pidfile = d / "runner.pid"
        while time.time() < end and not pidfile.exists():
            time.sleep(0.02)
    write_meta(d, {**meta, "status": "running", "started_at": time.time()})
    out(cid)
elif sub == "stop":
    cid = rest[-1]
    d = cid_dir(cid)
    meta = settle(d)
    if meta["status"] == "running":
        signal_runner(d, 15)
        meta = settle(d)
    if meta["status"] == "running":
        meta.update(status="exited", exit_code=143, outcome="STOPPED")
        write_meta(d, meta)
    out(cid)
elif sub == "kill":
    cid = rest[-1]
    d = cid_dir(cid)
    signal_runner(d, 9)
    meta = settle(d, 5)
    if meta["status"] == "running":
        meta.update(status="exited", exit_code=137, outcome="KILLED")
        write_meta(d, meta)
    out(cid)
elif sub == "rm":
    force = "-f" in rest
    cid = rest[-1]
    d = cid_dir(cid)
    if not d.exists():
        sys.stderr.write(f"Error: No such container: {cid}\n"); sys.exit(1)
    meta = read_meta(d)
    if meta["status"] == "running":
        meta = settle(d)
    if meta["status"] == "running" and force:
        signal_runner(d, 9)
        meta = settle(d, 5)
        if meta["status"] == "running":
            meta.update(status="exited", exit_code=137, outcome="KILLED")
            write_meta(d, meta)
    if meta["status"] == "running" and not force:
        sys.stderr.write("you cannot remove a running container\n"); sys.exit(1)
    v = d / "outcome.json"
    if v.exists():
        (state / f"{cid}.outcome.json").write_text(v.read_text())
    import shutil
    shutil.rmtree(d)
    out(cid)
elif sub == "inspect":
    # inspect is read-only: settle the runner verdict without signalling it.
    target0 = [a for a in rest if not a.startswith("--") and not a.startswith("{{")]
    if target0 and cid_dir(target0[-1]).exists():
        m0 = read_meta(cid_dir(target0[-1]))
        if m0["status"] == "running" and not runner_alive(cid_dir(target0[-1])):
            v = verdict_of(cid_dir(target0[-1]))
            if v is not None:
                m0.update(status="exited", exit_code=v.get("exit_code"),
                          outcome=v.get("status"), reason=v.get("reason", ""))
                write_meta(cid_dir(target0[-1]), m0)
    fmt = ""
    args = [a for a in rest if not a.startswith("--")]
    for i, a in enumerate(rest):
        if a == "--format": fmt = rest[i+1]
    target = args[-1] if args else ""
    d = cid_dir(target)
    if not d.exists():
        sys.stderr.write(f"Error: No such object: {target}\n"); sys.exit(1)
    meta = json.loads((d / "meta.json").read_text())
    st = meta["status"]
    def to_bytes(value):
        v = str(value)
        mult = {"k": 1024, "m": 1024**2, "g": 1024**3}
        if v and v[-1] in mult: return int(float(v[:-1]) * mult[v[-1]])
        return int(float(v)) if v else 0
    mem_b = to_bytes(meta["opts"].get("memory", "805306368"))
    swap_b = to_bytes(meta["opts"].get("memory-swap", "805306368"))
    mapping = {
        "{{.State.Status}}": st,
        "{{.State.Running}}": "true" if st == "running" else "false",
        "{{.State.ExitCode}}": str(meta.get("exit_code") if meta.get("exit_code") is not None else 0),
        "{{json .}}": json.dumps(meta),
        "{{json .Config.Labels}}": json.dumps(meta["labels"]),
        "{{json .Mounts}}": json.dumps(([
            dict(Type="bind", Source="/injected/foreign/path",
                 Destination="/foreign", RW=False)] if
            os.environ.get("XRG_P01_STUB_BAD_MOUNTS") else []) + [
            dict(Type="bind", Source=m.split("src=",1)[1].split(",")[0],
                 Destination=m.split("dst=",1)[1].split(",")[0],
                 RW=("readonly" not in m)) for m in meta["mounts"]]),
        "{{.HostConfig.Cpus}}": str(meta["opts"].get("cpus", "0.5")),
        "{{.HostConfig.Memory}}": str(mem_b),
        "{{.HostConfig.MemorySwap}}": str(swap_b),
        "{{.HostConfig.PidsLimit}}": str(meta["opts"].get("pids-limit", "128")),
        "{{.Id}}": meta["id"],
    }
    if fmt in mapping: out(mapping[fmt])
    elif fmt == "": out(json.dumps(meta))
    else: out(fmt)
elif sub == "ps":
    filt = [a for a in rest if a.startswith("--filter")]
    label = None
    for f in filt:
        _, _, kv = f.partition("=")
        if kv.startswith("label=io.xiangrugu.attempt-gen="):
            label = kv.split("=",1)[1]
    ids = []
    for d in sorted(cont.iterdir()):
        meta = json.loads((d / "meta.json").read_text())
        if label is None or meta["labels"].get("io.xiangrugu.attempt-gen") == label:
            ids.append(meta["id"])
    out("\n".join(ids))
else:
    sys.exit(127)
PY
