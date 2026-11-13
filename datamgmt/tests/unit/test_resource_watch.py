"""Synthetic host observations; never stop an actual host container."""
import importlib

import pytest


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.resource_watch")
    assert spec is not None, "Resource decision and exact-target cancellation are missing"
    return importlib.import_module(spec.name)


def good(**kwargs):
    return dict(available_memory=5*1024**3, disk_available=100*1024**3,
        load_1min=0.2, io_some_avg10=0.0, memory_some_avg10=0.0,
        swap_out_pages=0, services_healthy=True, **kwargs)


def sample(**overrides):
    result = good()
    result.update(overrides)
    return result


def test_metrics_parse_real_kernel_shapes_without_optional_iostat():
    module = api()
    result = module.parse_host_metrics(
        meminfo="MemTotal: 8000000 kB\nMemAvailable: 5242880 kB\n",
        loadavg="0.20 0.30 0.40 1/123 456\n",
        io_pressure="some avg10=0.50 avg60=1.00 avg300=0.20 total=100\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
        memory_pressure="some avg10=0.00 avg60=0.00 avg300=0.00 total=0\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
        vmstat="pgpgin 123\npswpout 17\n", disk_available=100*1024**3, services_healthy=True)
    assert result["available_memory"] == 5368709120
    assert result["swap_out_pages"] == 17 and result["io_some_avg10"] == 0.5
    assert module.ResourceWatch().preflight(result) is None


@pytest.mark.parametrize("overrides", [dict(available_memory=1024**3),
    dict(disk_available=8*1024**3), dict(load_1min=2), dict(services_healthy=False)])
def test_preflight_rejects_inadequate_headroom(overrides):
    assert api().ResourceWatch().preflight(sample(**overrides)) is not None


@pytest.mark.parametrize("overrides", [dict(available_memory=1024**3), dict(load_1min=3),
    dict(io_some_avg10=10), dict(memory_some_avg10=1)])
def test_sustained_pressure_stops_on_second_sample_not_single_spike(overrides):
    watch = api().ResourceWatch()
    assert watch.observe(sample(**overrides)) is None
    assert watch.observe(sample()) is None
    assert watch.observe(sample(**overrides)) is None
    assert watch.observe(sample(**overrides)) is not None


def test_different_pressure_reasons_do_not_share_streak():
    watch = api().ResourceWatch()
    assert watch.observe(sample(io_some_avg10=20)) is None
    assert watch.observe(sample(load_1min=4)) is None
    assert watch.observe(sample(load_1min=4)) == "load_pressure"


def test_swap_uses_positive_deltas_not_historical_counter():
    watch = api().ResourceWatch()
    assert watch.observe(sample(swap_out_pages=100)) is None
    assert watch.observe(sample(swap_out_pages=100)) is None
    assert watch.observe(sample(swap_out_pages=101)) is None
    assert watch.observe(sample(swap_out_pages=102)) == "swap_pressure"


@pytest.mark.parametrize("metrics", [None, {}, sample(load_1min=float("nan")),
    sample(available_memory=True), sample(disk_available=-1), sample(services_healthy="yes")])
def test_missing_or_invalid_monitoring_stops_immediately(metrics):
    assert api().ResourceWatch().observe(metrics) == "monitor_invalid"


def test_disk_floor_and_unhealthy_services_stop_immediately():
    assert api().ResourceWatch().observe(sample(disk_available=7*1024**3)) == "disk_floor"
    assert api().ResourceWatch().observe(sample(services_healthy=False)) == "service_unhealthy"


def test_stop_is_latched_and_cannot_resume_when_pressure_disappears():
    watch = api().ResourceWatch()
    assert watch.observe(None) == "monitor_invalid"
    assert watch.observe(sample()) == "monitor_invalid"


def test_exact_container_stop_kill_and_absence_check_with_argument_arrays():
    module = api()
    commands = []
    # Deliberately fake only external Docker; the policy and sequence run for real.
    def execute(argv, timeout):
        commands.append((argv, timeout))
        if argv[1] == "inspect":
            return (0, "true") if len(commands) < 4 else (0, "false")
        return 0, ""
    module.cancel_candidate("xiangrugu-evidence-fixture", execute=execute)
    assert commands == [
        (["docker", "stop", "--time", "10", "xiangrugu-evidence-fixture"], 15),
        (["docker", "inspect", "--format", "{{.State.Running}}", "xiangrugu-evidence-fixture"], 5),
        (["docker", "kill", "xiangrugu-evidence-fixture"], 5),
        (["docker", "inspect", "--format", "{{.State.Running}}", "xiangrugu-evidence-fixture"], 5)]


@pytest.mark.parametrize("name", ["pg32", "pg32b", "xiangrugu-dev", "", "x; reboot", "xiangrugu-evidence-"])
def test_cancellation_refuses_unrelated_targets_before_command(name):
    module = api()
    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe target invoked Docker")
    with pytest.raises(ValueError):
        module.cancel_candidate(name, execute=forbidden)


def test_failed_final_stop_confirmation_is_not_reported_as_success():
    with pytest.raises(ValueError, match="cancel_unconfirmed"):
        api().cancel_candidate("xiangrugu-evidence-fixture", execute=lambda argv, timeout: (0, "true"))


def test_preflight_cannot_clear_a_latched_stop():
    watch = api().ResourceWatch()
    assert watch.observe(None) == "monitor_invalid"
    assert watch.preflight(sample()) == "monitor_invalid"


def test_oversized_numeric_monitor_data_fails_closed_not_overflow():
    assert api().ResourceWatch().observe(sample(load_1min=10**1000)) == "monitor_invalid"


@pytest.mark.parametrize("replacement", ["", "MemAvailable: invalid kB\n",
    "MemAvailable: 1 kB\nMemAvailable: 2 kB\n"])
def test_missing_bad_or_duplicate_kernel_fields_rejected(replacement):
    with pytest.raises(ValueError, match="monitor_invalid"):
        api().parse_host_metrics(meminfo=replacement, loadavg="0.2 0.3 0.4 1/2 3\n",
            io_pressure="some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
            memory_pressure="some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
            vmstat="pswpout 0\n", disk_available=100*1024**3, services_healthy=True)


def test_valid_plus_malformed_duplicate_field_is_rejected():
    with pytest.raises(ValueError, match="monitor_invalid"):
        api().parse_host_metrics(meminfo="MemAvailable: 5242880 kB\n",
            loadavg="0.2 0.3 0.4 1/2 3\n",
            io_pressure="some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
            memory_pressure="some avg10=0.00 avg60=0.00 avg300=0.00 total=0\n",
            vmstat="pswpout 17\npswpout invalid\n", disk_available=100*1024**3, services_healthy=True)
