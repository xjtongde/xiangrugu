"""Bounded larger owned data must exercise more than one chunk per hash bucket."""
import json
from pathlib import Path
import runpy
import sqlite3

from test_artificial_partition_fixture import candidate_root


def test_fixed_reader_merge_fixture(candidate_root):
    build = runpy.run_path(str(Path(__file__).parents[1] /
                              'fixtures/partition/prepare_project_protocol.py'))['build']
    result = build(candidate_root, image='sha256:' + '2'*64,
                   revision='a'*40, scenario='reader-multi-merge')
    receipt = json.loads(result['receipt'].read_text())
    assert receipt['test_fixture_only'] is True and receipt['real_source_read'] is False
    assert receipt['new_real_expectations'] == 0
    paths = json.loads(result['requests'].read_text())
    assert len(paths) == 1
    request = json.loads(Path(paths[0]).read_text())
    scope = json.loads(Path(request['scope_file']).read_text())
    parent = json.loads(Path(request['bindings']['parent_scope']['path']).read_text())
    assert len(parent['objects']) == 10 and sum(len(o['columns']) for o in parent['objects']) == 235
    assert len(scope['objects']) == 1 and len(scope['objects'][0]['columns']) == 8
    golden = json.loads(result['golden'].read_text())
    assert golden['rows_per_table'] == 80000 and golden['row_frame_bytes'] is None
    assert golden['objects'][0]['expected_count'] == 80000
    assert golden['objects'][0]['field_count'] == 640000
    assert len(golden['objects'][0]['expected_sha256']) == 64
    budget = json.loads(Path(request['budget_file']).read_text())['objects'][0]
    assert budget['sort_limits']['chunk_rows'] == 4096
    assert budget['sort_limits']['merge_fan_in'] == 16
    with sqlite3.connect(f'file:{result["sqlite"]}?mode=ro', uri=True) as connection:
        assert connection.execute('SELECT count(*) FROM artificial_large_00').fetchone()[0] == 80000
        assert connection.execute('SELECT count(*) FROM artificial_large_01').fetchone()[0] == 1000
