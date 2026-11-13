"""Fail-closed host pressure decisions and bounded exact-candidate cancellation.

No background watcher, Docker socket, database access or host changes on import.
The host orchestration layer must supply fresh samples every ten seconds and
call cancellation on monitoring loss; this module alone is not full Task 8.
"""
import math
import re
import subprocess


def _valid(metrics):
    if type(metrics) is not dict:
        return False
    integer_keys = ("available_memory", "disk_available", "swap_out_pages")
    float_keys = ("load_1min", "io_some_avg10", "memory_some_avg10")
    if any(type(metrics.get(key)) is not int or metrics[key] < 0 for key in integer_keys):
        return False
    try:
        finite = all(type(metrics.get(key)) in (int, float) and math.isfinite(metrics[key])
                     and metrics[key] >= 0 for key in float_keys)
    except (ValueError, OverflowError):
        finite = False
    if not finite:
        return False
    return (type(metrics.get("services_healthy")) is bool
            and metrics["io_some_avg10"] <= 100 and metrics["memory_some_avg10"] <= 100)


def parse_host_metrics(*, meminfo, loadavg, io_pressure, memory_pressure, vmstat,
                       disk_available, services_healthy):
    """Parse required Linux fields; missing, duplicate or malformed fields fail."""
    def field(raw, pattern, name):
        if type(raw) is not str or len(raw) > 65536:
            raise ValueError("monitor_invalid")
        matches = re.findall(pattern, raw, re.M)
        occurrences = (len(re.findall(r"^" + re.escape(name) + r"(?=[:\s]|$)", raw, re.M))
                       if name else len(raw.strip().splitlines()))
        if len(matches) != 1 or occurrences != 1:
            raise ValueError("monitor_invalid")
        return matches[0]
    try:
        available = int(field(meminfo, r"^MemAvailable:\s+(\d+) kB\s*$", "MemAvailable"))*1024
        load = float(field(loadavg, r"^([\d.]+)\s+[\d.]+\s+[\d.]+\s+\d+/\d+\s+\d+\s*$", None))
        io = float(field(io_pressure, r"^some avg10=([\d.]+) avg60=[\d.]+ avg300=[\d.]+ total=\d+\s*$", "some"))
        memory = float(field(memory_pressure, r"^some avg10=([\d.]+) avg60=[\d.]+ avg300=[\d.]+ total=\d+\s*$", "some"))
        swap = int(field(vmstat, r"^pswpout (\d+)\s*$", "pswpout"))
        result = dict(available_memory=available, disk_available=disk_available,
            load_1min=load, io_some_avg10=io, memory_some_avg10=memory,
            swap_out_pages=swap, services_healthy=services_healthy)
        if not _valid(result):
            raise ValueError("monitor_invalid")
        return result
    except (TypeError, ValueError):
        raise ValueError("monitor_invalid") from None


class ResourceWatch:
    """Conservative fixed starting thresholds; stop is latched for this run."""
    def __init__(self):
        self._streaks = {}
        self._swap = None
        self.reason = None

    def preflight(self, metrics):
        if self.reason is not None:
            return self.reason
        if not _valid(metrics):
            return "monitor_invalid"
        if not metrics["services_healthy"]:
            return "service_unhealthy"
        if metrics["available_memory"] < 2*1024**3:
            return "memory_headroom"
        if metrics["disk_available"] < 16*1024**3:
            return "disk_headroom"
        if metrics["load_1min"] >= 2:
            return "load_headroom"
        if metrics["io_some_avg10"] >= 10 or metrics["memory_some_avg10"] >= 1:
            return "pressure_headroom"
        self._swap = metrics["swap_out_pages"]
        return None

    def observe(self, metrics):
        if self.reason is not None:
            return self.reason
        if not _valid(metrics) or (self._swap is not None and metrics["swap_out_pages"] < self._swap):
            self.reason = "monitor_invalid"
        elif not metrics["services_healthy"]:
            self.reason = "service_unhealthy"
        elif metrics["disk_available"] < 8*1024**3:
            self.reason = "disk_floor"
        else:
            conditions = dict(memory_pressure=metrics["available_memory"] < 1536*1024**2,
                load_pressure=metrics["load_1min"] >= 3,
                io_pressure=metrics["io_some_avg10"] >= 10,
                memory_stall=metrics["memory_some_avg10"] >= 1,
                swap_pressure=self._swap is not None and metrics["swap_out_pages"] > self._swap)
            self._swap = metrics["swap_out_pages"]
            for key, breached in conditions.items():
                self._streaks[key] = self._streaks.get(key, 0) + 1 if breached else 0
                if self._streaks[key] >= 2:
                    self.reason = key
                    break
        return self.reason


def _execute(argv, timeout):
    try:
        result = subprocess.run(argv, timeout=timeout, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout[:4096].strip()
    except (OSError, subprocess.SubprocessError):
        return -1, ""


def cancel_candidate(name, *, execute=_execute):
    """Stop only an evidence candidate, never a service. Confirm stopped/absent.

    A Docker inspect error is not proof of absence (daemon may be unavailable).
    Stopped containers can be retained for evidence; no delete/prune command.
    """
    if (type(name) is not str or re.fullmatch(r"xiangrugu-evidence-[a-z0-9][a-z0-9-]{0,63}", name) is None):
        raise ValueError("unsafe_cancel_target")
    try:
        execute(["docker", "stop", "--time", "10", name], 15)
        code, state = execute(["docker", "inspect", "--format", "{{.State.Running}}", name], 5)
        if code == 0 and state == "false":
            return
        execute(["docker", "kill", name], 5)
        code, state = execute(["docker", "inspect", "--format", "{{.State.Running}}", name], 5)
        if code != 0 or state != "false":
            raise ValueError("cancel_unconfirmed")
    except Exception:
        raise ValueError("cancel_unconfirmed") from None
