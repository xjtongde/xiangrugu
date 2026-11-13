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


def bind_budget(args, **changes):
    # Synthetic permission only; production source authority is never accessed.
    from xiangrugu_datamgmt.sqlite_profile import ProfileLimits
    limits = dict(vars(ProfileLimits()))
    limits.update(changes)
    budget = Path(args.roots).parent / "budget.json"
    budget.write_text(json.dumps(dict(version=1, limits=limits)), encoding="utf-8")
    args.budget_file = str(budget)
    roles = Path(args.roles_file)
    decision = json.loads(roles.read_text())
    decision["profile_budget_sha256"] = hashlib.sha256(budget.read_bytes()).hexdigest()
    roles.write_text(json.dumps(decision), encoding="utf-8")
    args.roles_sha256 = hashlib.sha256(roles.read_bytes()).hexdigest()
    return budget


def test_type_probe_records_bound_budget(type_args):
    budget = bind_budget(type_args, max_rows=2000000, max_cells=128000000,
        max_total_value_bytes=1073741824, max_vm_steps=1000000000, max_seconds=900)
    result = probe().prepare(type_args)
    assert result["profile_budget_sha256"] == hashlib.sha256(budget.read_bytes()).hexdigest()
    assert result["profile_limits"]["max_rows"] == 2000000


@pytest.mark.parametrize("violation", ["changed", "unbound", "missing", "over_cap", "boolean", "unknown", "duplicate"])
def test_type_probe_refuses_invalid_budget_before_source_access(type_args, violation):
    budget = bind_budget(type_args)
    roles = Path(type_args.roles_file)
    if violation == "changed":
        budget.write_text(budget.read_text() + " ", encoding="utf-8")
    elif violation == "unbound":
        decision = json.loads(roles.read_text())
        del decision["profile_budget_sha256"]
        roles.write_text(json.dumps(decision), encoding="utf-8")
        type_args.roles_sha256 = hashlib.sha256(roles.read_bytes()).hexdigest()
    elif violation == "missing":
        type_args.budget_file = None
    elif violation in ("over_cap", "boolean", "unknown"):
        key, value = {"over_cap": ("max_seconds", 901), "boolean": ("max_rows", True),
                      "unknown": ("ignore_budget", 1)}[violation]
        bind_budget(type_args, **{key: value})
    else:
        budget.write_text('{"version":1,"version":1,"limits":{}}', encoding="utf-8")
        decision = json.loads(roles.read_text())
        decision["profile_budget_sha256"] = hashlib.sha256(budget.read_bytes()).hexdigest()
        roles.write_text(json.dumps(decision), encoding="utf-8")
        type_args.roles_sha256 = hashlib.sha256(roles.read_bytes()).hexdigest()
    # An absent selected source distinguishes rejection before opening SQLite.
    source = Path(type_args.roots).parent / "snapshots" / type_args.snapshot_id / type_args.relative_path
    source.unlink()
    with pytest.raises(ValueError, match="budget"):
        probe().prepare(type_args)
    assert not Path(type_args.output).exists()


def test_type_probe_applies_bound_row_limit(type_args):
    import sqlite3
    from xiangrugu_datamgmt.snapshots import digest
    from xiangrugu_datamgmt.sqlite_diagnostic import SQLiteDiagnosticError
    source = Path(type_args.roots).parent / "snapshots" / type_args.snapshot_id / type_args.relative_path
    with sqlite3.connect(source) as db:
        db.executemany("INSERT INTO example VALUES (?)", [("a",), ("b",), ("c",)])
    type_args.expected_size = source.stat().st_size
    type_args.expected_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    entry = dict(path=type_args.relative_path, kind="file", size=type_args.expected_size,
                 sha256=type_args.expected_sha256)
    cert = Path(type_args.certificate)
    certificate = json.loads(cert.read_text())
    certificate.update(members=[entry], manifest_sha256=digest([entry]))
    cert.write_text(json.dumps(certificate), encoding="utf-8")
    type_args.certificate_sha256 = hashlib.sha256(cert.read_bytes()).hexdigest()
    type_args.manifest_sha256 = certificate["manifest_sha256"]
    roles = Path(type_args.roles_file)
    decision = json.loads(roles.read_text())
    decision["source_identity"] = entry
    roles.write_text(json.dumps(decision), encoding="utf-8")
    bind_budget(type_args, max_rows=2)
    with pytest.raises(SQLiteDiagnosticError, match="row"):
        probe().prepare(type_args)
    assert not Path(type_args.output).exists()


def test_type_probe_budget_cannot_be_output(type_args):
    budget = bind_budget(type_args)
    budget.unlink()
    type_args.output = str(budget)
    with pytest.raises(ValueError, match="output_path"):
        probe().prepare(type_args)
