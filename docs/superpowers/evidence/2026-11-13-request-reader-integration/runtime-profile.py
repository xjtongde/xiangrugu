"""Measure the installed pipeline only on the fixed artificial p01 fixture."""
import json
import sys
from functools import wraps
from pathlib import Path
from time import monotonic_ns

from xiangrugu_datamgmt import request_reader, sqlite_expectations, sqlite_values, task_control, value_sort
from xiangrugu_datamgmt.snapshots import write_json_exclusive


root = Path('/data/var/run/project')
allowed = {'--request', '--request-sha256', '--approval-sha256', '--roots-sha256',
           '--image-id', '--git-revision', '--image-user', '--source-status',
           '--lifecycle-seconds', '--failure-evidence', '--authorized-source-mode'}
args = sys.argv[1:]
flags = args[::2]
if len(args) != 2 * len(allowed) or set(flags) != allowed:
    raise ValueError('profile_fixture_arguments')
options = dict(zip(flags, args[1::2], strict=True))
receipt = json.loads((root / 'fixture-receipt.json').read_text())
golden = json.loads((root / 'project-golden.json').read_text())
if (options['--request'] != str(root / 'executions/large-p01/request.json')
        or options['--authorized-source-mode'] != 'project_snapshot'
        or receipt.get('test_fixture_only') is not True
        or receipt.get('real_source_read') is not False
        or receipt.get('scenario') != 'reader-multi-merge'
        or golden['objects'][0]['expected_count'] != 465284):
    raise ValueError('profile_fixture_only')

started = monotonic_ns()
output = Path('/data/var/run')
phases = []


def enter(name):
    if phases and phases[-1]['name'] == name:
        return
    now = monotonic_ns() - started
    if phases:
        phases[-1]['elapsed_ns'] = now - phases[-1]['start_ns']
    phases.append(dict(name=name, start_ns=now, measurements={}))
    with (output / 'phase-events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(name=name, start_ns=now)) + '\n')


def measure(function, name):
    @wraps(function)
    def call(*args, **kwargs):
        measurements = phases[-1]['measurements']
        if name not in measurements:
            measurements[name] = dict(calls=0, elapsed_ns=0)
        counter = measurements[name]
        before = monotonic_ns()
        try:
            return function(*args, **kwargs)
        finally:
            counter['calls'] += 1
            counter['elapsed_ns'] += monotonic_ns() - before
    return call


def mark(function, name):
    @wraps(function)
    def call(*args, **kwargs):
        enter(name)
        return function(*args, **kwargs)
    return call


execute = task_control.execute_readonly_batch


def execute_with_phases(*args, progress=None, **kwargs):
    def boundary(stage, **details):
        enter(stage)
        if progress is not None:
            progress(stage, **details)
    return execute(*args, progress=boundary, **kwargs)


enter('controller_preflight')
task_control.execute_readonly_batch = execute_with_phases
task_control.read_request = measure(task_control.read_request, 'request_read')
request_reader.read_metadata = measure(request_reader.read_metadata, 'request_reader_fallback')
task_control._require_readonly_mount = measure(task_control._require_readonly_mount, 'request_mount_check')
sqlite_values._ValueRows.__next__ = measure(sqlite_values._ValueRows.__next__, 'sqlite_next_inclusive')
sqlite_expectations.sort_rows = mark(sqlite_expectations.sort_rows, 'read_encode_bucket')
read = value_sort.SortWorkspace.read


@wraps(read)
def read_with_phase(self, file, schema, *, ordered):
    if not ordered:
        enter('chunk_sort')
    return read(self, file, schema, ordered=ordered)


value_sort.SortWorkspace.read = read_with_phase
value_sort._merge = mark(value_sort._merge, 'merge')
value_sort.SortedRows.iter_frames = mark(value_sort.SortedRows.iter_frames, 'final_stream_digest')
code = None
try:
    code = task_control.main()
finally:
    elapsed = monotonic_ns() - started
    phases[-1]['elapsed_ns'] = elapsed - phases[-1]['start_ns']
    write_json_exclusive(output / 'profile.json', dict(
        version=1, test_fixture_only=True, real_source_read=False,
        instrumentation='in_process_timing_wrappers', request_reader='installed', elapsed_ns=elapsed,
        sqlite_next_contains_request_checks=True, checks_skipped=0,
        worker_exit_code=code, phases=phases))
raise SystemExit(code)
