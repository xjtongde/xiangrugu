"""Prepare one closed real-scope metadata review; no snapshot is mounted."""
import hashlib
import json
import os
from pathlib import Path
import sys

from xiangrugu_datamgmt.project_partition import prepare_project_partition_review, GENERATED
from xiangrugu_datamgmt.task_partition import prepare_partition_task
from xiangrugu_datamgmt.snapshots import write_json_exclusive


def pin(path):
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


image, revision = sys.argv[1:]
assert image == 'sha256:55b3f27687ea32e397d49a6fdfa010a6a862c4b6c99c471d4ef68c3fe2030696'
assert revision == '8fbc8c97fcf1d818caddf6ab556fa82d986643ed'
assert (os.getuid(), os.getgid()) == (10001, 10001)
repo = Path('/metadata')
output = Path('/data/var/run')
review_relative = 'datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-project-partition-readiness.closed.json'
parent = repo / review_relative
roots = repo / 'datamgmt/config/roots.yaml'
certificate = repo / 'selected-certificate.json'
assert pin(parent)['sha256'] == 'edf31997132133987b7505ce1a90563e7b7a21335b94bcd91dfdf10d8046692e'
assert pin(roots)['sha256'] == '6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c'
assert pin(certificate)['sha256'] == '58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a'
actual = dict(image_id=image, git_revision=revision, user='10001:10001', source_status='dirty')
marker = prepare_partition_task(repository_root=repo, review_file=review_relative,
    expected_review_sha256=pin(parent)['sha256'], expected_roots_sha256=pin(roots)['sha256'],
    expected_image_id=image, actual_image=actual, output_dir=output/'preparation', partition_id='large-p01')
files = {role: pin(marker.parent/name) for role, name in GENERATED.items()}
files.update(preparation=pin(marker), parent_review=pin(parent), roots=pin(roots), certificate=pin(certificate))
cert = json.loads(certificate.read_text())
selection = dict(version=1, status='SELECTED_PROJECT_PARTITION_REVIEW_METADATA',
    source_mode='project_snapshot', partition_id='large-p01', attempt_id='real-p01-20261109-c',
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
print(json.dumps(dict(status='CLOSED_REAL_PARTITION_REVIEW_PREPARED', source_bytes_read=False)))
