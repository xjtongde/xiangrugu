"""Fixed artificial generator must keep the real execution gate closed."""
from pathlib import Path
import json
import runpy

import pytest


def builder():
    return runpy.run_path(str(Path(__file__).parents[1]/'fixtures/partition/prepare_artificial_partitions.py'))['build']


@pytest.fixture
def candidate_root(tmp_path):
    if Path('/data/var/run') not in tmp_path.parents:
        pytest.skip('requires bounded candidate /data/var/run basetemp')
    root=tmp_path/'artificial';root.mkdir()
    return root


def test_unbounded_output_rejected_before_data_creation(monkeypatch):
    build=builder()
    def forbidden_seed(*args, **kwargs):
        pytest.fail('unbounded output reached artificial data creation')
    monkeypatch.setitem(build.__globals__, 'seed', forbidden_seed)
    with pytest.raises(ValueError, match='artificial_output'):
        build(Path('/not-authorized-artificial-output'), image='sha256:'+'2'*64, revision='a'*40)


def test_fixed_parent_and_ten_requests(candidate_root):
    root=candidate_root
    requests=builder()(root,image='sha256:'+'2'*64,revision='a'*40)
    assert len(requests)==10
    for i,path in enumerate(requests):
        req=json.loads(path.read_text());scope=json.loads((root/'fixture'/Path(req['scope_file']).name).read_text())
        assert req['source_mode']=='artificial' and len(scope['objects'])==1
        assert scope['source_read_authorized'] is False and scope['synthetic_data_authorized'] is True
        assert scope['objects'][0]['source_object_name']==f'artificial_large_{i:02d}'
        assert set(req['bindings'])=={'descriptor','parent_scope','parent_budget','partition_selection'}
    assert not (root/'fixture/authority-never-read').exists()


def test_existing_fixture_never_overwritten(candidate_root):
    root=candidate_root;(root/'fixture').mkdir();p=root/'fixture/keep';p.write_text('keep')
    with pytest.raises(FileExistsError):builder()(root,image='sha256:'+'2'*64,revision='a'*40)
    assert p.read_text()=='keep'
