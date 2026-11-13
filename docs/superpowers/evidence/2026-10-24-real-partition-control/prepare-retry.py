"""Append a fixed owned cancel/retry selection; never rewrite old attempts."""
import argparse
import hashlib
import json
from pathlib import Path

from xiangrugu_datamgmt.project_partition import prepare_project_partition_review,materialize_project_partition_request
from xiangrugu_datamgmt.snapshots import write_json_exclusive

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image',required=True);parser.add_argument('--revision',required=True)
parser.add_argument('--attempt-choice',required=True,choices=('cancel','retry'))
args=parser.parse_args();root=Path('/data/var/run/project')
def pin(path):return hashlib.sha256(path.read_bytes()).hexdigest()
selection=json.loads((root/'reviews/large-p01-selection.json').read_text())
name='large-p01-'+args.attempt_choice
selection['attempt_id']='owned-coverage-'+name
path=root/'reviews'/(name+'-selection.json');write_json_exclusive(path,selection)
image=dict(image_id=args.image,git_revision=args.revision,user='10001:10001',source_status='dirty')
review=prepare_project_partition_review(selection_file=path,expected_selection_sha256=pin(path),actual_image=image,
    output_dir=root/'reviews'/name)
request=materialize_project_partition_request(review_file=review,expected_review_sha256=pin(review),actual_image=image,
    output_dir=root/'executions'/name,result_file=root/'results/batch.json',scratch_parent=root/'results/disk-scratch')
write_json_exclusive(Path('/data/var/run/attempt-receipt.json'),dict(test_fixture_only=True,real_source_read=False,
    new_real_expectations=0,attempt_id=selection['attempt_id'],request_sha256=pin(request)))
print(json.dumps(dict(request=str(request),test_fixture_only=True,real_source_read=False)))
