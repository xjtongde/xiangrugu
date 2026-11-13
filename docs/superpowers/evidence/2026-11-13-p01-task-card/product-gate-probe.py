"""Closed-state product gate probe: a project_snapshot request must be refused.

Runs inside the candidate container after the metadata run. Feeds the generated
closed request template (all permissions false, approval null) to the installed
task_control entry point with the DEFAULT artificial source mode, i.e. without
any real-read authorization. The product must raise real_execution_closed
before approval-pin comparison, before any materialize, and before any source
access. The approval pin below is a format-valid placeholder precisely because
refusal must happen earlier; this probe asserts that ordering.
"""
import hashlib
import json
from pathlib import Path
import sys

from xiangrugu_datamgmt.task_control import execute_controlled_batch
from xiangrugu_datamgmt.snapshots import write_json_exclusive

roots_sha, image_id, revision = sys.argv[1:]
assert len(roots_sha) == 64 and image_id.startswith('sha256:')
request_path = Path('/review-input/request.review.json')
raw = request_path.read_bytes()
request_sha = hashlib.sha256(raw).hexdigest()
template = json.loads(raw)
assert template['status'] == 'DRAFT_PROJECT_PARTITION_REQUEST_REVIEW'
assert template['source_mode'] == 'project_snapshot'
for key in ('source_read_authorized', 'postgresql_authorized', 'contract_frozen', 'ready_for_import'):
    assert template[key] is False
assert template['approval_file'] is None and template['approval_sha256'] is None
assert template['output'] is None and template['scratch_parent'] is None
receipt = dict(status='PRODUCT_GATE_PROBE', request_sha256=request_sha,
    authorized_source_mode='artificial', template_closed=True)
try:
    execute_controlled_batch(request_file=request_path, expected_request_sha256=request_sha,
        expected_approval_sha256='0'*64, expected_roots_sha256=roots_sha,
        actual_image=dict(image_id=image_id, git_revision=revision, user='10001:10001',
            source_status='dirty'),
        lifecycle_seconds=1800, authorized_source_mode='artificial')
except ValueError as error:
    receipt['refused'] = True
    receipt['reason'] = str(error)
else:
    receipt['refused'] = False
    receipt['reason'] = None
receipt['batch_created'] = Path('/data/var/run/batch.json').exists()
receipt['executable_request_created'] = Path('/data/var/run/request.json').exists()
receipt['approval_created'] = Path('/data/var/run/approval.json').exists()
receipt['source_bytes_read'] = False
write_json_exclusive(Path('/data/var/run/product-gate-receipt.json'), receipt)
assert receipt['refused'] is True
assert receipt['reason'] == 'real_execution_closed'
assert receipt['batch_created'] is False
assert receipt['executable_request_created'] is False
assert receipt['approval_created'] is False
print(json.dumps(dict(status='PRODUCT_GATE_REFUSED_AS_EXPECTED', reason=receipt['reason'])))
