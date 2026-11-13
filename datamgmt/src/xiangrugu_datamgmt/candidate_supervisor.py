"""Container-local lease watchdog for one artificial worker process group."""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .batch_execution import publish_batch, read_metadata, _publication_selection
from .readonly_batch import _require_readonly_mount, _hash
from .resource_watch import ResourceWatch, parse_host_metrics
from .snapshots import write_json_exclusive
from .task_failure import read_worker_failure
from .unordered_values import valid_digest


def read_lease(path):
    try:
        lines = read_metadata(path).decode("ascii").splitlines()
        if len(lines) != 9:
            raise ValueError("monitor_invalid")
        timestamp, seq = float(lines[0]), int(lines[1])
        if not math.isfinite(timestamp) or abs(time.time()-timestamp) > 25 or seq <= 0:
            raise ValueError("monitor_lost")
        if lines[8] not in ("true", "false"):
            raise ValueError("monitor_invalid")
        metrics = parse_host_metrics(meminfo=lines[2], loadavg=lines[3], io_pressure=lines[4],
            memory_pressure=lines[5], vmstat=lines[6], disk_available=int(lines[7]),
            services_healthy=lines[8] == "true")
        return seq, metrics
    except (OSError, UnicodeError, ValueError, OverflowError):
        raise ValueError("monitor_lost") from None


def check_limits(root=Path("/sys/fs/cgroup")):
    try:
        values = {name: (root/name).read_text().strip() for name in
                  ("cpu.max", "memory.max", "memory.swap.max", "pids.max")}
        quota, period = map(int, values["cpu.max"].split())
        if (quota <= 0 or period <= 0 or quota / period > 0.5
                or not 0 < int(values["memory.max"]) <= 805306368
                or values["memory.swap.max"] != "0" or not 0 < int(values["pids.max"]) <= 128):
            raise ValueError("limits_invalid")
        return values
    except (OSError, ValueError):
        raise ValueError("limits_invalid") from None


def _group_exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def _reap_group(pgid):
    while True:
        try:
            pid, _ = os.waitpid(-pgid, os.WNOHANG)
            if pid == 0:
                return
        except ChildProcessError:
            return


def _stop_group(worker):
    for sig, seconds in ((signal.SIGTERM, 1), (signal.SIGKILL, 2)):
        try:
            os.killpg(worker.pid, sig)
        except ProcessLookupError:
            pass
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            worker.poll()
            _reap_group(worker.pid)
            if not _group_exists(worker.pid):
                return True
            time.sleep(0.02)
    return False


def _diagnostic_preflight(worker_failure, worker_request_sha256, *, lease, evidence, final,
                          authorized_source_mode, expected_request_sha256):
    """Reject paths and aliases before CLI evidence writes or worker launch."""
    if worker_failure is None:
        if worker_request_sha256 is not None:
            raise ValueError('worker_diagnostic_parameters')
        return None
    path = Path(worker_failure)
    reserved = [Path(lease), Path(evidence)] + [Path(evidence).with_name(name) for name in
                 ('limits.json', 'publication-failure.json', 'final-sample-request.json')]
    if final is not None:
        reserved.extend((Path(final), Path(final).with_name('.' + Path(final).name + '.incomplete')))
    if (not valid_digest(worker_request_sha256) or not path.is_absolute()
            or path.parent.resolve(strict=True) != path.parent or path in reserved
            or (authorized_source_mode == 'project_snapshot'
                and worker_request_sha256 != expected_request_sha256)):
        raise ValueError('worker_diagnostic_parameters')
    if path.exists() or path.is_symlink():
        raise ValueError('worker_diagnostic_exists')
    return path


def supervise(argv, *, lease, evidence, max_seconds=300, lease_seconds=25,
              poll_seconds=0.2, cancelled=lambda: False, final=None, require_final_sample=False,
              authorized_source_mode='artificial', expected_request_sha256=None,
              worker_failure=None, worker_request_sha256=None, controller_request_file=None,
              controller_request_sha256=None):
    """Fresh initial/final monitor checks; always reap on errors and signals.

    PR_SET_CHILD_SUBREAPER reaps orphaned worker descendants. Workers must
    remain in their process group; Docker's PID namespace is the outer boundary.
    Raw worker output goes to caller-controlled files, never into exceptions.
    """
    if (type(argv) is not list or not argv or any(type(a) is not str for a in argv)
            or any(not math.isfinite(v) or v <= 0 for v in (max_seconds, lease_seconds, poll_seconds))):
        raise ValueError("worker_parameters")
    _publication_selection(authorized_source_mode, expected_request_sha256)
    def check_controller_request():
        if controller_request_file is not None or controller_request_sha256 is not None:
            if (final is None or controller_request_file is None or not _hash(controller_request_sha256)
                    or (authorized_source_mode=='project_snapshot' and controller_request_sha256!=expected_request_sha256)):
                raise ValueError('controller_pin')
            if hashlib.sha256(read_metadata(Path(controller_request_file))).hexdigest() != controller_request_sha256:
                raise ValueError('controller_request_changed')
            _require_readonly_mount(Path(controller_request_file))
    check_controller_request()
    worker_failure = _diagnostic_preflight(worker_failure, worker_request_sha256,
        lease=lease, evidence=evidence, final=final, authorized_source_mode=authorized_source_mode,
        expected_request_sha256=expected_request_sha256)
    # Linux only, same supported platform as the project container.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise ValueError("subreaper_failed")
    watch = ResourceWatch()
    samples, worker, reason, last_seq, last_metrics = [], None, None, None, None
    final_sample_after_sequence,final_sample_sequence=None,None
    start = last_fresh = time.monotonic()
    def observe(initial=False):
        nonlocal last_seq, last_fresh, last_metrics
        seq, metrics = read_lease(lease)
        if last_seq is not None and seq < last_seq:
            raise ValueError("monitor_invalid")
        if seq == last_seq and metrics != last_metrics:
            raise ValueError("monitor_invalid")
        if seq != last_seq:
            reason = watch.preflight(metrics) if initial else watch.observe(metrics)
            samples.append(dict(sequence=seq, elapsed_seconds=time.monotonic()-start, **metrics))
            last_seq, last_fresh = seq, time.monotonic()
            last_metrics = metrics
            if reason:
                raise ValueError(reason)
        if time.monotonic()-last_fresh >= lease_seconds:
            raise ValueError("monitor_lost")
        if cancelled():
            raise ValueError("cancelled")
        if time.monotonic()-start >= max_seconds:
            raise ValueError("timeout")
        return False
    gone = True
    known = {"monitor_lost", "monitor_invalid", "memory_headroom", "disk_headroom", "load_headroom",
        "pressure_headroom", "service_unhealthy", "disk_floor", "memory_pressure", "load_pressure",
        "io_pressure", "memory_stall", "swap_pressure", "cancelled", "timeout", "worker_exit", "orphaned_worker"}
    try:
        observe(initial=True)
        worker = subprocess.Popen(argv, start_new_session=True)
        while True:
            observe()
            if worker.poll() is not None:
                if worker.returncode != 0:
                    raise ValueError("worker_exit")
                if _group_exists(worker.pid):
                    raise ValueError("orphaned_worker")
                observe()
                if require_final_sample:
                    completed_sequence = last_seq
                    final_sample_after_sequence=completed_sequence
                    write_json_exclusive(Path(evidence).with_name("final-sample-request.json"),
                                         dict(after_sequence=completed_sequence))
                    # A recent pre-completion sample cannot approve publication.
                    # The same lease/time/cancel gates bound this acknowledgement.
                    while last_seq <= completed_sequence:
                        observe()
                        if last_seq <= completed_sequence:
                            time.sleep(poll_seconds)
                    final_sample_sequence=last_seq
                break
            time.sleep(poll_seconds)
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) and str(error) in known else "supervisor_error"
    finally:
        if worker is not None:
            gone = _stop_group(worker)
    if not gone:
        reason = "cancel_unconfirmed"
    failure, failure_sha256, failure_state = read_worker_failure(
        worker_failure, worker_request_sha256, authorized_source_mode)
    if reason is None and failure_state in ('valid', 'invalid'):
        reason = 'worker_diagnostic_inconsistent'
    cgroup_stats = {name: (Path("/sys/fs/cgroup")/name).read_text().strip() for name in
        ("memory.peak", "memory.current", "memory.swap.current", "cpu.stat", "io.stat", "pids.current")}
    status_prefix = 'SOURCE_ONLY' if authorized_source_mode == 'project_snapshot' else 'SYNTHETIC'
    result = dict(version=1, status=status_prefix + ('_WORKER_STOPPED' if reason else '_WORKER_COMPLETED'),
        max_seconds=max_seconds,
        reason=reason, worker_exit_code=None if worker is None else worker.returncode,
        process_group_gone=gone, samples=samples, elapsed_seconds=time.monotonic()-start,
        ready_for_import=False, synthetic_only=authorized_source_mode == 'artificial',
        source_mode=authorized_source_mode, cgroup_stats=cgroup_stats,
        final_sample_after_sequence=final_sample_after_sequence,final_sample_sequence=final_sample_sequence,
        worker_failure=failure, worker_failure_sha256=failure_sha256,
        worker_failure_state=failure_state)
    # Monitor evidence must fsync before a final batch result can appear.
    write_json_exclusive(Path(evidence), result)
    if reason is None and final is not None:
        try:
            publication_guard = observe
            if controller_request_file is not None:
                def publication_guard():
                    observe()
                    check_controller_request()
                    observe()
                    return False
                publication_guard()
            publish_batch(Path(final).with_name("." + Path(final).name + ".incomplete"), Path(final),
                          cancelled=publication_guard, authorized_source_mode=authorized_source_mode,
                          expected_request_sha256=expected_request_sha256)
        except Exception as error:
            # Preserve the fsynced pre-publication monitor; append the failed
            # final decision instead of rewriting it or deleting the stage.
            result['reason'] = str(error) if isinstance(error, ValueError) and str(error) in known else 'publication_failed'
            result['status'] = status_prefix + '_WORKER_STOPPED'
            write_json_exclusive(Path(evidence).with_name('publication-failure.json'),
                dict(status=result['status'], reason=result['reason'], ready_for_import=False,
                     max_seconds=max_seconds, elapsed_seconds=time.monotonic()-start))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lease", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--final", type=Path)
    parser.add_argument('--authorized-source-mode', choices=('artificial', 'project_snapshot'), default='artificial')
    parser.add_argument('--request-sha256')
    parser.add_argument('--worker-failure', type=Path)
    parser.add_argument('--worker-request-sha256')
    parser.add_argument('--controller-request-file', type=Path)
    parser.add_argument('--controller-request-sha256')
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        _publication_selection(args.authorized_source_mode, args.request_sha256)
        _diagnostic_preflight(args.worker_failure, args.worker_request_sha256,
            lease=args.lease, evidence=args.evidence, final=args.final,
            authorized_source_mode=args.authorized_source_mode, expected_request_sha256=args.request_sha256)
        limits = check_limits()
        os.nice(19)
        io_priority = subprocess.run(["ionice", "-c", "3", "-p", str(os.getpid())],
            capture_output=True, timeout=2, check=False)
        if io_priority.returncode != 0:
            raise ValueError("priority_failed")
        limits["worker_nice"] = os.getpriority(os.PRIO_PROCESS, 0)
        limits["worker_ionice"] = subprocess.run(["ionice", "-p", str(os.getpid())],
            capture_output=True, text=True, timeout=2, check=True).stdout.strip()
        write_json_exclusive(args.evidence.with_name("limits.json"), limits)
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        result = supervise(argv, lease=args.lease, evidence=args.evidence,
            max_seconds=args.seconds, cancelled=lambda: stopped, final=args.final, require_final_sample=True,
            authorized_source_mode=args.authorized_source_mode, expected_request_sha256=args.request_sha256,
            worker_failure=args.worker_failure, worker_request_sha256=args.worker_request_sha256,
            controller_request_file=args.controller_request_file,
            controller_request_sha256=args.controller_request_sha256)
        print(json.dumps({k: result[k] for k in ("status", "reason", "process_group_gone")}))
        return 0 if result["reason"] is None else 1
    except Exception:
        print(json.dumps(dict(status="SUPERVISION_FAILED", ready_for_import=False)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
