import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest
import yaml

from xiangrugu_datamgmt.snapshots import digest


def probe():
    path = Path(__file__).resolve().parents[3] / "scripts/inspect-sqlite-structure.py"
    assert path.is_file(), "missing SQLite structure evidence probe"
    spec = importlib.util.spec_from_file_location("sqlite_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def args(tmp_path):
    snapshot_root = tmp_path / "snapshots"
    source = snapshot_root / "test-version" / "sub" / "source.sqlite"
    source.parent.mkdir(parents=True)
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE example(x TEXT)")
    entry = dict(path="sub/source.sqlite", kind="file", size=source.stat().st_size,
                 sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    certificate = dict(version=1, status="VERIFIED", snapshot_id="test-version",
        source_path="/authority/usedata", members=[entry], manifest_sha256=digest([entry]))
    certificate_path = tmp_path / "certificate.json"
    certificate_path.write_text(json.dumps(certificate), encoding="utf-8")
    roots = tmp_path / "roots.yaml"
    roots.write_text(yaml.safe_dump(dict(version=1,
        roots={"usedata": dict(path="/authority/usedata", host="synthetic",
                               role="authoritative-source")},
        target=dict(instance="pg32b", host="unused", port=5433, database="xiangrugu", user="unused"),
        deployment={"source_snapshots": dict(container_root=str(snapshot_root),
                                             container_evidence_root=str(tmp_path))})),
        encoding="utf-8")
    return argparse.Namespace(roots=str(roots), snapshot_id="test-version",
        relative_path=entry["path"], expected_size=entry["size"], expected_sha256=entry["sha256"],
        certificate=str(certificate_path),
        certificate_sha256=hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
        manifest_sha256=certificate["manifest_sha256"], output=str(tmp_path / "observation.json"),
        image_id="sha256:" + "1" * 64, git_revision="2" * 40, rule_id="synthetic-rule")


def test_probe_writes_bound_nonexecuting_evidence(args):
    probe().prepare(args)
    result = json.loads(Path(args.output).read_text())
    assert result["rule_id"] == "synthetic-rule"
    assert result["source"]["path"] == "sub/source.sqlite"
    assert result["snapshot_certificate_sha256"] == args.certificate_sha256
    assert result["full_snapshot_verified_this_run"] is False
    assert result["disposition_retained"] == "BLOCKED"
    assert result["observation"]["business_rows_read"] == 0
    assert result["source_sqlite_connected"] is True
    assert result["postgresql_connected"] is False
    assert "database_connected" not in result
    assert result["ready_for_import"] is False
    with pytest.raises(FileExistsError):
        probe().prepare(args)


@pytest.mark.parametrize("field,value", [
    ("relative_path", "../source.sqlite"), ("snapshot_id", "../test-version"),
    ("certificate_sha256", "0" * 64), ("manifest_sha256", "0" * 64),
    ("expected_sha256", "0" * 64),
])
def test_probe_rejects_wrong_scope_or_identity(args, field, value):
    setattr(args, field, value)
    with pytest.raises(ValueError):
        probe().prepare(args)
    assert not Path(args.output).exists()


def test_probe_output_cannot_target_source(args):
    args.output = str(Path(args.roots).parent / "snapshots" / args.snapshot_id / args.relative_path)
    with pytest.raises(ValueError, match="output"):
        probe().prepare(args)
