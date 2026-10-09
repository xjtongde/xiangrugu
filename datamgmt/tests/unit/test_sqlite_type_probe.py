import importlib.util
import hashlib
import json
from pathlib import Path
import pytest

from test_sqlite_structure_probe import args


def probe():
    path = Path(__file__).resolve().parents[3] / "scripts/inspect-sqlite-types.py"
    assert path.is_file(), "missing image type probe"
    spec = importlib.util.spec_from_file_location("sqlite_type_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def type_args(args):
    path = Path(args.roots).parent / "role-decision.json"
    decision = dict(roles_approved=True, profile_read_authorized=True,
        raw_text_or_blob_output_authorized=False, source_identity=dict(path=args.relative_path,
            kind="file", size=args.expected_size, sha256=args.expected_sha256),
        profile_scope={"example": ["x"]}, source_version=args.snapshot_id, rule_id=args.rule_id,
        type_mapping_approved=False, value_contract_approved=False, target_mapping_approved=False,
        ready_for_import=False, contract_frozen=False)
    path.write_text(json.dumps(decision), encoding="utf-8")
    args.roles_file = str(path)
    args.roles_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    return args


def test_type_probe_binds_roles_and_outputs_only_statistics(type_args):
    result = probe().prepare(type_args)
    assert result["profile"]["rows_read"] == 0
    assert len(result["profile"]["tables"]) == 1
    assert result["roles_decision_sha256"] == type_args.roles_sha256
    assert result["source_sqlite_connected"] is True
    assert result["postgresql_connected"] is False
    assert result["ready_for_import"] is False
    assert json.loads(Path(type_args.output).read_text()) == result
    with pytest.raises(FileExistsError):
        probe().prepare(type_args)


@pytest.mark.parametrize("flag,value", [
    ("profile_read_authorized", False), ("roles_approved", False),
    ("raw_text_or_blob_output_authorized", True), ("ready_for_import", True),
    ("source_version", "other-version"),
])
def test_type_probe_refuses_changed_authority(type_args, flag, value):
    path = Path(type_args.roles_file)
    decision = json.loads(path.read_text())
    decision[flag] = value
    path.write_text(json.dumps(decision), encoding="utf-8")
    type_args.roles_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        probe().prepare(type_args)
    assert not Path(type_args.output).exists()


def test_type_probe_rejects_unbound_decision_digest(type_args):
    type_args.roles_sha256 = "0" * 64
    with pytest.raises(ValueError, match="decision_identity"):
        probe().prepare(type_args)


def test_type_probe_rejects_rule_identity_mismatch(type_args):
    type_args.rule_id = "other-rule"
    with pytest.raises(ValueError, match="decision_scope"):
        probe().prepare(type_args)
    assert not Path(type_args.output).exists()
