"""Run the evidence wrapper against real synthetic snapshots, not source text."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from test_sqlite_structure_probe import args
from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.snapshots import digest


def probe():
    path = Path(__file__).resolve().parents[3] / "scripts/inspect-sqlite-values.py"
    assert path.is_file(), "Source expectation evidence wrapper is missing"
    spec = importlib.util.spec_from_file_location("sqlite_expectation_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bind(args, scope):
    path = Path(args.scope_file)
    path.write_text(json.dumps(scope), encoding="utf-8")
    args.scope_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def canary_args(args):
    certificate_path = Path(args.certificate)
    certificate = json.loads(certificate_path.read_text())
    certificate["members"].insert(0, dict(path="sub", kind="directory"))
    certificate["manifest_sha256"] = digest(certificate["members"])
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")
    args.certificate_sha256 = hashlib.sha256(certificate_path.read_bytes()).hexdigest()
    args.manifest_sha256 = certificate["manifest_sha256"]
    identity = source_object_id(relative_path=args.relative_path, archive_chain=[],
                                object_name="example", carrier="sqlite")
    column = allocate_columns(["x"], object_id=identity)[0].identity
    args.scope_file = str(Path(args.roots).parent / "scope.json")
    args.scratch_parent = str(Path(args.roots).parent / "scratch")
    Path(args.scratch_parent).mkdir()
    scope = dict(version=1, source_read_authorized=True, snapshot_id=args.snapshot_id,
        source=dict(path=args.relative_path, kind="file", size=args.expected_size, sha256=args.expected_sha256),
        rule_id=args.rule_id, postgresql_authorized=False, ready_for_import=False,
        bindings={"synthetic_descriptor": "a"*64},
        objects=[dict(source_object_id=identity, source_object_name="example",
            source_columns=["x"], columns=[dict(source_ordinal=0, column_key=column,
            pg_type="text", allow_null_value=True)])])
    bind(args, scope)
    return args


def test_canary_outputs_empty_source_expectation_after_full_snapshot_check(canary_args):
    result = probe().prepare(canary_args)
    assert result["full_snapshot_verified_this_run"] is True
    assert result["objects"][0]["expected_count"] == 0
    assert result["objects"][0]["cleanup_complete"] is True
    assert result["scope_sha256"] == canary_args.scope_sha256
    assert result["ready_for_import"] is False
    assert result["postgresql_connected"] is False
    assert json.loads(Path(canary_args.output).read_text()) == result
    assert list(Path(canary_args.scratch_parent).iterdir()) == []
    with pytest.raises(FileExistsError):
        probe().prepare(canary_args)


@pytest.mark.parametrize("field,value", [("source_read_authorized", False),
    ("postgresql_authorized", True), ("snapshot_id", "other"),
    ("ready_for_import", True), ("objects", [])])
def test_denied_or_wrong_scope_never_writes_evidence(canary_args, field, value):
    scope = json.loads(Path(canary_args.scope_file).read_text())
    scope[field] = value
    bind(canary_args, scope)
    with pytest.raises(ValueError):
        probe().prepare(canary_args)
    assert not Path(canary_args.output).exists()


def test_unbound_scope_digest_prevents_execution(canary_args):
    canary_args.scope_sha256 = "0"*64
    with pytest.raises(ValueError, match="scope_identity"):
        probe().prepare(canary_args)
    assert not Path(canary_args.output).exists()


def test_unlisted_snapshot_member_stops_before_evidence(canary_args):
    source = Path(canary_args.roots).parent / "snapshots" / canary_args.snapshot_id
    (source / "extra.txt").write_bytes(b"synthetic")
    with pytest.raises(ValueError):
        probe().prepare(canary_args)
    assert not Path(canary_args.output).exists()


def test_duplicate_object_scope_is_rejected(canary_args):
    scope = json.loads(Path(canary_args.scope_file).read_text())
    scope["objects"].append(scope["objects"][0])
    bind(canary_args, scope)
    with pytest.raises(ValueError, match="scope"):
        probe().prepare(canary_args)
    assert not Path(canary_args.output).exists()


def test_output_fsync_failure_cannot_leave_a_final_evidence_file(canary_args, monkeypatch):
    from xiangrugu_datamgmt import snapshots
    def failed_fsync(fd):
        raise OSError("synthetic-storage-failure")
    monkeypatch.setattr(snapshots.os, "fsync", failed_fsync)
    with pytest.raises(OSError):
        probe().prepare(canary_args)
    assert not Path(canary_args.output).exists()
