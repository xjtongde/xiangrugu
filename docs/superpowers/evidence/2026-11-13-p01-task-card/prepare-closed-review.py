"""Prepare one closed real-scope metadata review and task card; no snapshot is mounted.

Adapted from 2026-11-09-p01-read-review/prepare-closed-review.py for the verified
2026-11-13 request-reader runtime. Runs inside the candidate container as
10001:10001 with /metadata (repository metadata only) and a fresh writable
/data/var/run. Never reads source bytes, never connects to PostgreSQL, never
materializes an executable request or approval.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

from xiangrugu_datamgmt.project_partition import prepare_project_partition_review, GENERATED
from xiangrugu_datamgmt.task_partition import prepare_partition_task
from xiangrugu_datamgmt.snapshots import write_json_exclusive

IMAGE = 'sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a'
REVISION = '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
ATTEMPT = 'real-p01-20261113-a'
PARENT_SHA = 'edf31997132133987b7505ce1a90563e7b7a21335b94bcd91dfdf10d8046692e'
ROOTS_SHA = '6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c'
CERT_SHA = '58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a'
RUNTIME_VERIFICATION_SHA = '8c121fd05e47db385b170d379436492ffd79e96ef99c1adae4b5ea0951f7f3da'
MANIFEST_SHA = '03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699'
MEMBER = dict(kind='file', path='harvard/cbdb/cbdb_20260919.sqlite3', size=586485760,
    sha256='bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400')
COLUMNS = ['c_posting_id', 'c_personid', 'c_office_id', 'c_addr_id',
    'c_created_by', 'c_created_date', 'c_modified_by', 'c_modified_date']
OBJECT_ID = '1650019ee3e5efb5dceeac27e7871317eb61551cfb3e7754be6be36c63bc52ac'
SCHEMA_HASH = 'a942064328b43402fcb811a15f8adf24cfbcba2e94b10db203f7b1fa68e0bb08'
# Sum of the 189 member file sizes plus two extra reads of the SQLite member
# (before/after batch digests): 2508987728 + 2*586485760 = 3681959248.
DIGEST_BUDGET = 3681959248


def pin(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


image, revision = sys.argv[1:]
assert image == IMAGE
assert revision == REVISION
assert (os.getuid(), os.getgid()) == (10001, 10001)
repo = Path('/metadata')
output = Path('/data/var/run')
review_relative = 'datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
parent = repo / review_relative
roots = repo / 'datamgmt/config/roots.yaml'
certificate = repo / 'selected-certificate.json'
runtime_verification = repo / 'runtime-verification.json'
assert pin(parent)['sha256'] == PARENT_SHA
assert pin(roots)['sha256'] == ROOTS_SHA
assert pin(certificate)['sha256'] == CERT_SHA
assert pin(runtime_verification)['sha256'] == RUNTIME_VERIFICATION_SHA
verified = json.loads(runtime_verification.read_text())
assert verified['status'] == 'INSTALLED_REQUEST_READER_ARTIFICIAL_VERIFIED'
assert verified['complete'] is True and verified['real_source_read'] is False
assert verified['fixture_rows'] == 465284 and verified['coverage_complete_tables'] == 68
actual = dict(image_id=image, git_revision=revision, user='10001:10001', source_status='dirty')
marker = prepare_partition_task(repository_root=repo, review_file=review_relative,
    expected_review_sha256=pin(parent)['sha256'], expected_roots_sha256=pin(roots)['sha256'],
    expected_image_id=image, actual_image=actual, output_dir=output/'preparation', partition_id='large-p01')
files = {role: pin(marker.parent/name) for role, name in GENERATED.items()}
files.update(preparation=pin(marker), parent_review=pin(parent), roots=pin(roots), certificate=pin(certificate))
cert = json.loads(certificate.read_text())
assert cert['snapshot_id'] == '2026-10-07-bootstrap' and cert['status'] == 'VERIFIED'
assert cert['manifest_sha256'] == MANIFEST_SHA
members = cert['members']
member_files = [m for m in members if m['kind'] == 'file']
member_dirs = [m for m in members if m['kind'] == 'directory']
assert (len(members), len(member_files), len(member_dirs)) == (232, 189, 43)
assert sum(m['size'] for m in member_files) + 2*MEMBER['size'] == DIGEST_BUDGET
selection = dict(version=1, status='SELECTED_PROJECT_PARTITION_REVIEW_METADATA',
    source_mode='project_snapshot', partition_id='large-p01', attempt_id=ATTEMPT,
    files=files, expected_manifest_sha256=cert['manifest_sha256'])
selection_file = output/'review.selection.json'
write_json_exclusive(selection_file, selection)
closed = prepare_project_partition_review(selection_file=selection_file,
    expected_selection_sha256=pin(selection_file)['sha256'], actual_image=actual, output_dir=output/'review')
record = json.loads(closed.read_text())
assert record['status'] == 'DRAFT_PROJECT_PARTITION_REVIEW_NOT_EXECUTABLE'
assert record['missing'] == []
for key in ('source_read_authorized', 'postgresql_authorized', 'contract_frozen', 'ready_for_import'):
    assert record[key] is False
assert not (closed.parent/'approval.json').exists()
write_json_exclusive(output/'metadata-only-receipt.json', dict(metadata_only=True,
    real_source_read=False, source_bytes_read=False, new_real_expectations=0, task8_complete=False,
    partition_id='large-p01', source_object_name='POSTED_TO_ADDR_DATA', columns=8,
    review=pin(closed), selection=pin(selection_file), actual_image=actual,
    postgresql_authorized=False, ready_for_import=False, contract_frozen=False))

# Assemble the closed-permission task card from the generated documents. Every
# digest is read back from the exclusive-write outputs; fixed facts are asserted
# against the pinned parent scope, never hand-copied from narrative logs.
descriptor = json.loads((closed.parent/'descriptor.review.json').read_text())
scope = json.loads((marker.parent/'scope.draft.json').read_text())
budget = json.loads((marker.parent/'budget.draft.json').read_text())
obj = scope['objects'][0]
assert len(scope['objects']) == 1 and len(budget['objects']) == 1
assert obj['source_object_name'] == 'POSTED_TO_ADDR_DATA'
assert obj['source_object_id'] == OBJECT_ID
assert obj['source_columns'] == COLUMNS
# The draft scope carries only identity/columns; schema hash and the unset
# expectations are asserted against the pinned original scope review.
parent_packet = json.loads(parent.read_text())
original_review = json.loads((repo / parent_packet['bindings']['original_scope_review']['path']).read_text())
assert hashlib.sha256((repo / parent_packet['bindings']['original_scope_review']['path']).read_bytes()).hexdigest() == parent_packet['bindings']['original_scope_review']['sha256']
original_obj = original_review['objects'][0]
assert original_obj['source_object_id'] == OBJECT_ID
assert original_obj['schema_hash'] == SCHEMA_HASH
assert original_obj['expected_count'] is None and original_obj['expected_sha256'] is None
assert original_obj['source_columns'] == COLUMNS
assert scope['source'] == MEMBER and scope['snapshot_id'] == '2026-10-07-bootstrap'
assert scope['rule_id'] == 'm007906'
assert descriptor['attempt_id'] == ATTEMPT and descriptor['partition_id'] == 'large-p01'
assert descriptor['image'] == actual and descriptor['manifest_sha256'] == MANIFEST_SHA
limits = budget['objects'][0]
assert budget['group'] == 'large' and budget['max_seconds'] == 1800
sort_limits = limits['sort_limits']
assert sort_limits['workers'] == 1 and sort_limits['chunk_bytes'] == 2097152
assert sort_limits['chunk_rows'] == 4096 and sort_limits['merge_fan_in'] == 16
assert sort_limits['max_temp_files'] == 1024 and sort_limits['max_temp_bytes'] == 1073741824
assert sort_limits['max_stream_bytes'] == 268435456 and sort_limits['max_seconds'] == 1800
card = dict(version=1, status='CLOSED_REAL_PARTITION_TASK_CARD_NOT_EXECUTABLE', as_of='2026-11-13',
    partition_id='large-p01', attempt_id=ATTEMPT, one_attempt_only=True,
    auto_retry=False, auto_next_partition=False,
    source_read_authorized=False, postgresql_authorized=False, contract_frozen=False, ready_for_import=False,
    expected_count=None, expected_sha256=None,
    source_object=dict(source_object_id=OBJECT_ID, source_object_name='POSTED_TO_ADDR_DATA',
        source_columns=COLUMNS, columns=obj['columns'], schema_hash=SCHEMA_HASH, rule_id='m007906'),
    snapshot=dict(snapshot_id='2026-10-07-bootstrap', member=MEMBER, members_total=232,
        files=189, directories=43, manifest_sha256=MANIFEST_SHA, certificate_sha256=CERT_SHA,
        logical_digest_budget_bytes=DIGEST_BUDGET,
        logical_digest_budget_derivation='sum(189 member file sizes)=2508987728 plus 2*586485760 for the before/after SQLite batch digests'),
    runtime=dict(image_id=IMAGE, image_tag='xiangrugu:runtime-request-reader-20261113-a',
        git_revision=REVISION, user='10001:10001', source_status='dirty',
        verified_artificial_batch=dict(rows=465284, fields=3722272,
            supervisor_elapsed_seconds=verified['supervisor_elapsed_seconds'], complete=True),
        verified_by=dict(path='docs/superpowers/evidence/2026-11-13-request-reader-integration/verification.json',
            sha256=RUNTIME_VERIFICATION_SHA)),
    read_scope=dict(business_values='POSTED_TO_ADDR_DATA original 8 columns only',
        full_snapshot_digest_recheck=True, sqlite_digest_before_after=True,
        other_table_values_forbidden=True, nas_forbidden=True, postgresql_forbidden=True,
        freeze_import_publish_forbidden=True),
    resources=dict(cpus=0.5, memory_bytes=805306368, memory_swap_equals_memory=True,
        cgroup_swap_zero=True, workers=1, single_task_serial=True, nice=19, ionice='idle',
        pids_limit=128, network='none', readonly_rootfs=True, readonly_source=True,
        cap_drop='ALL', no_new_privileges=True,
        canonical_stream_bytes=sort_limits['max_stream_bytes'], app_temp_bytes=sort_limits['max_temp_bytes'],
        chunk_bytes=sort_limits['chunk_bytes'], chunk_rows=sort_limits['chunk_rows'],
        merge_fan_in=sort_limits['merge_fan_in'], max_temp_files=sort_limits['max_temp_files'],
        filesystem_hard_quota=False, hard_io_bandwidth_isolation=False),
    deadlines=dict(candidate_seconds=1800, host_seconds=1830, transport_seconds=1880,
        real_mode_activated=False),
    stop_conditions=['candidate_deadline_1800s_timeout', 'host_deadline_1830s', 'transport_deadline_1880s',
        'operator_cancel', 'request_bytes_changed', 'readonly_mount_lost',
        'controller_heartbeat_invalid', 'controller_eof_or_idle_15s', 'lease_lost_or_invalid_25s',
        'service_unhealthy_or_state_changed', 'memory_headroom', 'disk_headroom_or_floor',
        'load_headroom_or_pressure', 'io_pressure', 'memory_pressure_or_stall', 'swap_pressure',
        'worker_exit_or_orphaned', 'cgroup_limits_invalid_before_start'],
    authorization=dict(required=True, authorization_file=None, authorization_sha256=None,
        historical_p01_authorizations_consumed=True,
        protocol='authorization.json must bind this card SHA-256 and attempt_id before materialize_project_partition_request; no executable request or approval exists in the closed state'),
    bindings=dict(parent_review=pin(parent), roots=pin(roots), certificate=pin(certificate),
        closed_review=pin(closed), selection=pin(selection_file), preparation=pin(marker),
        metadata_only_receipt=pin(output/'metadata-only-receipt.json'),
        runtime_verification=pin(runtime_verification)),
    success_criteria='Only a complete batch plus independent verification may add this table source-side expectations (coverage at most 69/78).',
    failure_policy='Preserve evidence, stop, reclaim exact candidates; no auto retry, no next partition, no budget raise, no raw value output.',
    coverage=dict(complete_tables=68, total_tables=78, task8_complete=False),
    risk_note='Real p01 attempts b (2026-11-08) and c (2026-11-09) both timed out at 1800s without a complete batch. The 2026-11-13 artificial 465284-row batch completed in 1338.41s, but real throughput is unproven; the artificial sample differs in scale and value distribution and measurement overhead is uncalibrated. Do not raise budgets on timeout.')
card_file = output/'task-card.closed.json'
write_json_exclusive(card_file, card)
card_sha = pin(card_file)['sha256']
write_json_exclusive(output/'card-receipt.json', dict(status='CLOSED_TASK_CARD_GENERATED',
    task_card=pin(card_file), task_card_sha256=card_sha, attempt_id=ATTEMPT, partition_id='large-p01',
    source_read_authorized=False, postgresql_authorized=False, contract_frozen=False, ready_for_import=False,
    expected_count=None, expected_sha256=None, closed_review=pin(closed), selection=pin(selection_file),
    actual_image=actual, real_execution_ready=False, source_bytes_read=False))
print(json.dumps(dict(status='CLOSED_REAL_PARTITION_REVIEW_AND_CARD_PREPARED',
    task_card_sha256=card_sha, source_bytes_read=False)))
