"""Private project protocol fixtures never accept an external data source."""
import json
from pathlib import Path
import runpy

import pytest

from test_artificial_partition_fixture import candidate_root


def builder():
    return runpy.run_path(str(Path(__file__).parents[1]/'fixtures/partition/prepare_project_protocol.py'))['build']


@pytest.mark.parametrize('scenario',['coverage','wide-fit','wide-over'])
def test_project_protocol_fixed_owned_data(candidate_root,scenario):
    import sqlite3
    root=candidate_root
    result=builder()(root,image='sha256:'+'2'*64,revision='a'*40,scenario=scenario)
    receipt=json.loads(result['receipt'].read_text())
    assert receipt['test_fixture_only'] is True and receipt['real_source_read'] is False and receipt['new_real_expectations']==0
    paths=json.loads(result['requests'].read_text())
    assert len(paths)==(10 if scenario=='coverage' else 1)
    first=json.loads(Path(paths[0]).read_text());scope=json.loads(Path(first['scope_file']).read_text())
    parent=json.loads(Path(first['bindings']['parent_scope']['path']).read_text())
    assert len(parent['objects'])==10 and sum(len(o['columns']) for o in parent['objects'])==235
    assert all(parent[k] is False for k in ('source_read_authorized','postgresql_authorized','contract_frozen','ready_for_import'))
    assert first['source_mode']=='project_snapshot' and len(scope['objects'])==1
    assert scope['source_read_authorized'] is True and scope['synthetic_data_authorized'] is False
    assert scope['postgresql_authorized'] is False and scope['ready_for_import'] is False
    if scenario!='coverage':
        golden=json.loads(result['golden'].read_text())
        assert golden['row_frame_bytes']==65573 and golden['rows_per_table']==(4093 if scenario=='wide-fit' else 4094)
        assert golden['objects'][0]['canonical_stream_bytes']==(268390370 if scenario=='wide-fit' else 268455943)
        budget=json.loads(Path(first['budget_file']).read_text())['objects'][0]
        assert budget['read_limits']['max_rows']==4094 and budget['read_limits']['max_cells']==32752
        assert budget['sort_limits']['max_rows']==4094 and budget['sort_limits']['max_stream_bytes']==2**28
        with sqlite3.connect(f'file:{result["sqlite"]}?mode=ro',uri=True) as connection:
            name=scope['objects'][0]['source_object_name']
            count,size=connection.execute(f'SELECT count(*), min(length(CAST(c_001 AS BLOB))) FROM "{name}"').fetchone()
            assert count==golden['rows_per_table'] and size==65536


@pytest.mark.parametrize('scenario',['unknown',True,None])
def test_bad_scenario_rejected_before_creation(tmp_path,scenario):
    with pytest.raises(ValueError):builder()(tmp_path,image='sha256:'+'2'*64,revision='a'*40,scenario=scenario)
    assert list(tmp_path.iterdir())==[]


def test_outside_root_rejected_before_seed():
    with pytest.raises(ValueError):builder()(Path('/not-owned-project-fixture'),image='sha256:'+'2'*64,revision='a'*40,scenario='coverage')


def test_link_root_rejected(candidate_root):
    target=candidate_root/'target';target.mkdir();alias=candidate_root/'alias';alias.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError):builder()(alias,image='sha256:'+'2'*64,revision='a'*40,scenario='coverage')
    assert list(target.iterdir())==[]


def test_existing_project_fixture_preserved(candidate_root):
    (candidate_root/'fixture').mkdir();keep=candidate_root/'fixture'/'keep';keep.write_text('keep')
    with pytest.raises(FileExistsError):builder()(candidate_root,image='sha256:'+'2'*64,revision='a'*40,scenario='coverage')
    assert keep.read_text()=='keep'
