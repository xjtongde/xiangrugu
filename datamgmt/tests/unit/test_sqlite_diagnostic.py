"""Synthetic fixtures only; run on host 32, never on the Windows editor."""
import hashlib
import sqlite3

import pytest

from xiangrugu_datamgmt.sqlite_diagnostic import (
    SQLiteDiagnosticError, SQLiteLimits, inspect_sqlite_structure, _metadata_connection,
)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "结构 ?&#.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE parent(a INTEGER, b TEXT, PRIMARY KEY(a,b)) WITHOUT ROWID;
        CREATE TABLE child(id INTEGER PRIMARY KEY AUTOINCREMENT,
            a INTEGER, b TEXT UNIQUE DEFAULT '', payload BLOB,
            g TEXT GENERATED ALWAYS AS (b || 'x') STORED,
            FOREIGN KEY(a,b) REFERENCES parent(a,b), CHECK(a >= 0));
        CREATE UNIQUE INDEX child_pair ON child(a,b) WHERE a IS NOT NULL;
        CREATE VIEW unsafe_view AS SELECT absent_function(payload) FROM child;
        CREATE TRIGGER no_run AFTER INSERT ON child BEGIN SELECT absent_function(); END;
        CREATE TABLE "引号'""表"(x TEXT) STRICT;
        """)
    return path


def inspect(path, **kwargs):
    return inspect_sqlite_structure(
        path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), **kwargs,
    )


def test_complete_catalog_and_table_details_preserve_structure(source):
    before = source.read_bytes()
    result = inspect(source)
    objects = {obj["name"]: obj for obj in result["objects"]}
    assert result["status"] == "STRUCTURE_OBSERVED"
    assert result["catalog_complete"] is True
    assert result["business_rows_read"] == 0
    assert result["source_sha256_before"] == result["source_sha256_after"]
    assert source.read_bytes() == before
    assert {"parent", "child", "child_pair", "unsafe_view", "no_run",
            "sqlite_sequence", "sqlite_autoindex_child_1", '引号\'"表'} <= objects.keys()
    parent = objects["parent"]
    assert "WITHOUT ROWID" in parent["sql"]
    assert [col["pk"] for col in parent["columns"]] == [1, 2]
    child = objects["child"]
    assert next(col for col in child["columns"] if col["name"] == "g")["hidden"] == 3
    assert next(col for col in child["columns"] if col["name"] == "payload")["type"] == "BLOB"
    assert next(col for col in child["columns"] if col["name"] == "b")["dflt_value"] == "''"
    assert len(child["foreign_keys"]) == 2
    index = next(idx for idx in child["indexes"] if idx["name"] == "child_pair")
    assert index["unique"] == 1 and index["partial"] == 1
    assert [col["name"] for col in index["columns"][:2]] == ["a", "b"]
    assert objects["unsafe_view"]["detail_status"] == "PENDING_VIEW_METADATA"
    assert objects["unsafe_view"]["columns"] is None
    assert objects["no_run"]["detail_status"] == "DDL_ONLY"
    assert "absent_function" in objects["no_run"]["sql"]
    assert "STRICT" in objects['引号\'"表']["sql"]
    assert result["import_approved"] is False


@pytest.mark.parametrize("statement", [
    "SELECT * FROM child", "SELECT * FROM unsafe_view",
    "SELECT count(*) FROM child", "INSERT INTO child(a) VALUES(1)",
    "ATTACH DATABASE ':memory:' AS other", "PRAGMA writable_schema=ON",
    "SELECT load_extension('missing')",
])
def test_authorizer_denies_non_metadata_operations(source, statement):
    with _metadata_connection(source) as db:
        with pytest.raises(sqlite3.DatabaseError):
            db.execute(statement).fetchall()
        assert db.execute("PRAGMA query_only").fetchone() == (1,)
        assert db.execute("PRAGMA trusted_schema").fetchone() == (0,)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_fail_closed(source, suffix):
    source.with_name(source.name + suffix).write_bytes(b"")
    with pytest.raises(SQLiteDiagnosticError, match="sidecar_present"):
        inspect(source)


def test_digest_or_size_mismatch_fails(source):
    with pytest.raises(SQLiteDiagnosticError, match="identity_mismatch"):
        inspect_sqlite_structure(source, expected_size=source.stat().st_size,
                                 expected_sha256="0" * 64)
    with pytest.raises(SQLiteDiagnosticError, match="identity_mismatch"):
        inspect_sqlite_structure(source, expected_size=1,
                                 expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest())


@pytest.mark.parametrize("limits", [
    SQLiteLimits(max_file_bytes=1), SQLiteLimits(max_objects=1),
    SQLiteLimits(max_metadata_rows=1), SQLiteLimits(max_output_bytes=100),
    SQLiteLimits(max_vm_steps=1),
])
def test_limits_fail_without_partial_success(source, limits):
    with pytest.raises(SQLiteDiagnosticError, match="limit"):
        inspect(source, limits=limits)


def test_cancel_and_corrupt_file_fail(source, tmp_path):
    with pytest.raises(SQLiteDiagnosticError, match="cancelled"):
        inspect(source, cancelled=lambda: True)
    corrupt = tmp_path / "bad.sqlite"
    corrupt.write_bytes(b"SQLite format 3\0" + b"x" * 4096)
    with pytest.raises(SQLiteDiagnosticError, match="sqlite_error"):
        inspect(corrupt)


def test_symlink_and_directory_rejected(source, tmp_path):
    link = tmp_path / "link.sqlite"
    link.symlink_to(source)
    with pytest.raises(SQLiteDiagnosticError, match="unsafe_path"):
        inspect(link)
    with pytest.raises(SQLiteDiagnosticError, match="unsafe_path"):
        inspect_sqlite_structure(tmp_path, expected_size=0, expected_sha256="0" * 64)


def test_virtual_tables_are_explicitly_pending(tmp_path):
    path = tmp_path / "fts.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE VIRTUAL TABLE search USING fts5(body)")
    result = inspect(path)
    obj = next(obj for obj in result["objects"] if obj["name"] == "search")
    assert obj["detail_status"] == "PENDING_VIRTUAL_TABLE"
    assert obj["columns"] is None
    assert {"search_data", "search_idx", "search_content",
            "search_docsize", "search_config"} <= {obj["name"] for obj in result["objects"]}


@pytest.mark.parametrize("kwargs", [
    {"max_objects": True}, {"max_seconds": 0}, {"max_output_bytes": -1},
])
def test_limits_are_positive_integers(kwargs):
    with pytest.raises(ValueError):
        SQLiteLimits(**kwargs)


def test_changed_source_does_not_produce_success(source, monkeypatch):
    from xiangrugu_datamgmt import sqlite_diagnostic as module
    original = module._hash
    calls = 0

    def change_before_final_hash(path, guard):
        nonlocal calls
        calls += 1
        if calls == 2:
            with path.open("ab") as stream:
                stream.write(b"changed")
        return original(path, guard)

    monkeypatch.setattr(module, "_hash", change_before_final_hash)
    with pytest.raises(SQLiteDiagnosticError, match="source_changed"):
        inspect(source)
