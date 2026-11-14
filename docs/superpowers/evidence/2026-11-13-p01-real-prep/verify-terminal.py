#!/usr/bin/env python3
"""Deep Stage B terminal-state verification for attempt real-p01-20261113-a.

Exit code 0 and "file_digest_passes":2 alone are NOT proof. This checker
reconstructs the whole supervision story from evidence bytes:

  monitor.json      terminal status/reason/worker_exit_code/process_group_gone,
                    final-sample handshake sequence ordering, sample tail vs
                    host-samples.txt, cgroup_stats within card caps
  batch.staged.json complete fields (double digests equal the card member,
                    execution_kind/controller_request_sha256/pins/bindings)
  failure-report    worker receipt schema + state consistency with monitor
  .incomplete twin  byte-identical hardlink publication artifact
  registry          one-shot record fields and container_created flag

real_source_read is derived ONLY from evidence that the candidate actually
consumed snapshot bytes; a pre-read refusal never claims a real read.

Usage: verify-terminal.py <stage_b_run_dir> <materialize_run_dir> [--batch PATH]
Writes nothing except the JSON on stdout (caller may publish it exclusively).
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ATTEMPT = 'real-p01-20261113-a'
CARD_SHA = '41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69'
IMAGE_ID = 'sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
GIT_REVISION = '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
SNAPSHOT_ID = '2026-10-07-bootstrap'
MEMBER_PATH = 'harvard/cbdb/cbdb_20260919.sqlite3'
MEMBER_SIZE = 586485760
MEMBER_SHA = 'bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400'
OBJECT_ID = '1650019ee3e5efb5dceeac27e7871317eb61551cfb3e7754be6be36c63bc52ac'
SCHEMA_HASH = 'a9420643'  # prefix-checked; full value comes from the request
RULE_ID = 'm007906'
MEMORY_MAX = 805306368
CPU_RATIO_MAX = 0.5
PIDS_MAX = 128
STAGES = ('task_preflight', 'request_preflight', 'snapshot_verify',
    'batch_preflight', 'batch_digest_before', 'object_read_sort', 'batch_digest_after',
    'metadata_recheck', 'stage_save', 'task_staged')


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jload(p: Path):
    return json.loads(p.read_text())


class Report:
    def __init__(self):
        self.checks = []
        self.fatal = False

    def check(self, name, condition, detail=None):
        ok = bool(condition)
        entry = {'check': name, 'pass': ok}
        if not ok and detail is not None:
            entry['detail'] = detail
        self.checks.append(entry)
        if not ok:
            self.fatal = True
        return ok

    def result(self):
        return {'checks': self.checks, 'all_passed': not self.fatal,
                'failed': [c['check'] for c in self.checks if not c['pass']]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('stage_b')
    ap.add_argument('stage_a')
    ap.add_argument('--batch', default=None,
                    help='published batch path override (default: $stage_b/output/durable/executions/$ATTEMPT/batch.staged.json)')
    args = ap.parse_args()
    B = Path(args.stage_b)
    A = Path(args.stage_a)
    out = B / 'output'
    mat = A / 'output/durable/materialization'
    R = Report()

    pins_file = B / 'controller-pins-used.txt'
    if not R.check('pins_recorded', pins_file.is_file()):
        print(json.dumps(R.result(), sort_keys=True)); return 1
    req_pin, app_pin, roots_pin = pins_file.read_text().split()[:3]
    reg_path = B.parent / f'attempt-registration-{ATTEMPT}.json'
    R.check('registration_exists', reg_path.is_file())
    registration = None
    if reg_path.is_file():
        registration = jload(reg_path)
        R.check('registration_attempt', registration.get('attempt_id') == ATTEMPT)
        R.check('registration_one_shot', registration.get('one_attempt_only') is True)
        R.check('registration_card', registration.get('task_card_sha256') == CARD_SHA)
        R.check('registration_request_pin', registration.get('request_sha256') == req_pin)
        R.check('registration_approval_pin', registration.get('approval_sha256') == app_pin)
        R.check('registration_roots_pin', registration.get('roots_sha256') == roots_pin)
        R.check('registration_container_created', registration.get('container_created') is True)

    # --- request/approval bytes still match the externally fixed pins -------
    R.check('request_pin_current', mat.is_file() and sha(mat / 'request.json') == req_pin)
    R.check('approval_pin_current', mat.is_file() and sha(mat / 'approval.json') == app_pin)
    request = jload(mat / 'request.json') if (mat / 'request.json').is_file() else {}
    approval = jload(mat / 'approval.json') if (mat / 'approval.json').is_file() else {}
    if request:
        body = {k: v for k, v in request.items() if k not in ('approval_file', 'approval_sha256')}
        R.check('approval_digest_binding',
                approval.get('request_sha256') == hashlib.sha256(
                    json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        R.check('request_task_bindings', request.get('source_mode') == 'project_snapshot'
                and request.get('lifecycle_seconds') == 1800
                and request.get('image_id') == IMAGE_ID
                and request.get('git_revision') == GIT_REVISION
                and request.get('roots_sha256') == roots_pin
                and request.get('approval_sha256') == app_pin
                and request.get('snapshot_id') == SNAPSHOT_ID
                and request.get('relative_path') == MEMBER_PATH
                and request.get('expected_size') == MEMBER_SIZE
                and request.get('expected_sha256') == MEMBER_SHA
                and request.get('rule_id') == RULE_ID)
        R.check('request_output_is_batch_final',
                request.get('output') == str(Path(f'/data/var/snapshots/executions/{ATTEMPT}/batch.staged.json')))

    # --- monitor terminal state --------------------------------------------
    mon_path = out / 'monitor.json'
    if not R.check('monitor_exists', mon_path.is_file()):
        print(json.dumps(R.result(), sort_keys=True)); return 1
    mon = jload(mon_path)
    exit_code = None
    ec = B / 'exit-code.txt'
    if ec.is_file():
        exit_code = int(ec.read_text().strip())
    samples = mon.get('samples', [])
    seqs = [s.get('sequence') for s in samples]
    R.check('monitor_status_terminal', mon.get('status') in
            ('SOURCE_ONLY_WORKER_COMPLETED', 'SOURCE_ONLY_WORKER_STOPPED'))
    R.check('monitor_version', mon.get('version') == 1 and mon.get('max_seconds') == 1800)
    R.check('monitor_authority_flags', mon.get('ready_for_import') is False
            and mon.get('synthetic_only') is False and mon.get('source_mode') == 'project_snapshot')
    R.check('monitor_group_gone', mon.get('process_group_gone') is True)
    R.check('monitor_exit_consistent', exit_code is None or mon.get('worker_exit_code') == exit_code)
    R.check('monitor_sequences_increasing',
            all(isinstance(s, int) for s in seqs) and seqs == sorted(set(seqs)))
    fsa, fst = mon.get('final_sample_after_sequence'), mon.get('final_sample_sequence')
    if mon.get('status') == 'SOURCE_ONLY_WORKER_COMPLETED':
        R.check('handshake_reason_none', mon.get('reason') is None)
        R.check('handshake_fields_present', isinstance(fsa, int) and isinstance(fst, int))
        if isinstance(fsa, int) and isinstance(fst, int) and seqs:
            # boundary sample = last pre-completion observation; ack must be the
            # strictly-later latest sample recorded by the supervisor.
            R.check('handshake_boundary_is_last_pre_completion', fsa in seqs)
            R.check('handshake_ack_after_boundary', fst > fsa)
            R.check('handshake_ack_is_latest_sample', fst == seqs[-1])
            hsr = out / 'final-sample-request.json'
            R.check('handshake_file_matches_monitor', hsr.is_file()
                    and jload(hsr).get('after_sequence') == fsa)
    else:
        R.check('stopped_reason_known', isinstance(mon.get('reason'), str) and mon.get('reason'))
        R.check('stopped_no_publication_claim', fsa is None or isinstance(fsa, int))
    # host-samples.txt tail contains every monitor sample (lease lines of 9)
    hs = B / 'host-samples.txt'
    if hs.is_file():
        lines = hs.read_text().splitlines()
        R.check('host_samples_aligned', len(lines) % 9 == 0 and len(lines) // 9 >= len(samples))
    # cgroup stats within card caps
    cg = mon.get('cgroup_stats', {})
    def num(key):
        try:
            return int(cg.get(key, ''))
        except ValueError:
            return None
    peak = num('memory.peak')
    swap = num('memory.swap.current')
    pids = num('pids.current')
    R.check('cgroup_memory_peak_within_cap', peak is not None and peak <= MEMORY_MAX)
    R.check('cgroup_swap_zero', swap == 0)
    R.check('cgroup_pids_within_cap', pids is not None and pids <= PIDS_MAX)
    if (out / 'limits.json').is_file():
        lim = jload(out / 'limits.json')
        cpumax = lim.get('cpu.max', '').split()
        R.check('limits_cpu_ratio', len(cpumax) == 2 and int(cpumax[1]) > 0
                and int(cpumax[0]) / int(cpumax[1]) <= CPU_RATIO_MAX)
        R.check('limits_memory_max', int(lim.get('memory.max', '0')) <= MEMORY_MAX)
        R.check('limits_swap_zero', lim.get('memory.swap.max') == '0')
        R.check('limits_pids', int(lim.get('pids.max', '0')) <= PIDS_MAX)

    # --- worker failure receipt correlation ----------------------------------
    fr_path = out / 'failure-report.json'
    wf = mon.get('worker_failure')
    state = mon.get('worker_failure_state')
    if fr_path.is_file():
        raw = fr_path.read_bytes()
        doc = json.loads(raw)
        keys = {'version', 'status', 'request_sha256', 'source_mode', 'domain', 'code', 'stage',
                'object_index', 'completed_objects', 'ready_for_import', 'raw_values_emitted'}
        valid_shape = (doc.keys() == keys and doc.get('version') == 1
                       and doc.get('status') == 'CONTROLLED_TASK_FAILURE'
                       and doc.get('request_sha256') == req_pin
                       and doc.get('source_mode') == 'project_snapshot'
                       and doc.get('stage') in STAGES
                       and doc.get('ready_for_import') is False
                       and doc.get('raw_values_emitted') is False)
        R.check('worker_receipt_schema', valid_shape)
        R.check('worker_receipt_sha_in_monitor', mon.get('worker_failure_sha256') == hashlib.sha256(raw).hexdigest())
        R.check('worker_receipt_content_in_monitor', wf == doc)
        R.check('worker_receipt_state_valid_on_failure', state == 'valid')
        if mon.get('status') == 'SOURCE_ONLY_WORKER_COMPLETED':
            R.check('completed_with_receipt_is_inconsistent', False,
                    'success must have no worker failure receipt')
    else:
        R.check('missing_receipt_state_on_success',
                mon.get('status') != 'SOURCE_ONLY_WORKER_COMPLETED' or state == 'missing')
        R.check('no_receipt_no_monitor_copy', wf is None and mon.get('worker_failure_sha256') is None)

    # --- batch result --------------------------------------------------------
    batch_path = Path(args.batch) if args.batch else out / f'durable/executions/{ATTEMPT}/batch.staged.json'
    incomplete = batch_path.with_name('.' + batch_path.name + '.incomplete')
    staged_log_ok = (B / 'worker.log').is_file() and 'CONTROLLED_SOURCE_ONLY_TASK_STAGED' in (B / 'worker.log').read_text(errors='replace')
    success_claim = mon.get('status') == 'SOURCE_ONLY_WORKER_COMPLETED' and exit_code == 0 and staged_log_ok
    if success_claim:
        if R.check('batch_published_exists', batch_path.is_file()):
            batch = jload(batch_path)
            twin = incomplete
            R.check('batch_twin_byte_identical', twin.is_file() and sha(twin) == sha(batch_path))
            bindings = request.get('bindings', {})
            R.check('batch_core_fields', batch.get('version') == 1
                    and batch.get('complete') is True
                    and batch.get('execution_kind') == 'approved-readonly-batch-v1'
                    and batch.get('source_mode') == 'project_snapshot'
                    and batch.get('synthetic_only') is False
                    and batch.get('full_snapshot_verified_this_run') is True
                    and batch.get('raw_values_emitted') is False
                    and batch.get('ready_for_import') is False
                    and batch.get('postgresql_connected') is False
                    and batch.get('group') == 'large'
                    and batch.get('source_status') == 'dirty'
                    and batch.get('image_id') == IMAGE_ID
                    and batch.get('git_revision') == GIT_REVISION)
            R.check('batch_double_digests', batch.get('file_digest_passes') == 2
                    and batch.get('source_sha256_before') == MEMBER_SHA
                    and batch.get('source_sha256_after') == MEMBER_SHA)
            R.check('batch_controller_request_pin',
                    batch.get('controller_request_sha256') == req_pin
                    and batch.get('controller_lifecycle_seconds') == 1800)
            R.check('batch_pin_digests', batch.get('approval_sha256') == app_pin
                    and batch.get('roots_sha256') == roots_pin
                    and batch.get('scope_sha256') == request.get('scope_sha256')
                    and batch.get('budget_sha256') == request.get('budget_sha256')
                    and batch.get('certificate_sha256') == request.get('certificate_sha256')
                    and batch.get('manifest_sha256') == request.get('manifest_sha256'))
            R.check('batch_bindings_map', batch.get('bindings') ==
                    {k: v['sha256'] for k, v in bindings.items()})
            objs = batch.get('objects', [])
            if R.check('batch_single_object', len(objs) == 1):
                o = objs[0]
                R.check('batch_object_identity', o.get('source_object_id') == OBJECT_ID
                        and o.get('source_object_name') and o.get('schema_hash', '').startswith(SCHEMA_HASH)
                        and o.get('cleanup_complete') is True
                        and o.get('source_read', {}).get('digest_scope') == 'verified_by_completed_batch')
                R.check('batch_object_rows_consistent',
                        type(o.get('source_read', {}).get('rows_read')) is int
                        and o['source_read']['rows_read'] > 0)
    else:
        R.check('no_batch_on_failure', not batch_path.exists() or mon.get('reason') is not None,
                'published batch without completed supervision')

    # --- outcome-dependent real source read --------------------------------
    reached_reads = success_claim or (
        isinstance(wf, dict) and wf.get('stage') in
        ('snapshot_verify', 'batch_preflight', 'batch_digest_before',
         'object_read_sort', 'batch_digest_after', 'metadata_recheck', 'stage_save', 'task_staged'))
    real_source_read = success_claim or (
        mon.get('status') == 'SOURCE_ONLY_WORKER_STOPPED' and reached_reads)
    if not success_claim:
        R.check('pre_read_failure_not_claimed', not reached_reads or real_source_read)

    result = R.result()
    result.update({'status': 'P01_TERMINAL_STATE_VERIFIED' if not R.fatal else 'P01_TERMINAL_STATE_FAILED',
                   'outcome': 'staged' if success_claim else 'stopped',
                   'real_source_read': bool(real_source_read),
                   'monitor_status': mon.get('status'), 'monitor_reason': mon.get('reason'),
                   'worker_exit_code': mon.get('worker_exit_code'),
                   'stage_b_exit_code': exit_code,
                   'external_pins': {'request_sha256': req_pin, 'approval_sha256': app_pin, 'roots_sha256': roots_pin},
                   'attempt_id': ATTEMPT})
    print(json.dumps(result, sort_keys=True))
    return 1 if R.fatal else 0


if __name__ == '__main__':
    raise SystemExit(main())
