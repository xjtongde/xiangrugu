"""Catch lost storage classes, accidental reads, truncation and raw-value leaks."""
import hashlib
import importlib
import json
import sqlite3

import pytest


def api():
    try:
        return importlib.import_module("xiangrugu_datamgmt.sqlite_profile")
    except ModuleNotFoundError:
        pytest.fail("missing bounded SQLite type profile")


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "profile ?&#.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE mixed(x, y);
        CREATE TABLE empty(z TEXT);
        CREATE TABLE secret(z TEXT);
        CREATE VIEW dangerous AS SELECT absent_function(z) FROM secret;
        CREATE TABLE generated(x, g GENERATED ALWAYS AS (x||'!') VIRTUAL);
        """)
        db.executemany("INSERT INTO mixed VALUES(?,?)", [
            (None, ""), (2**63-1, "茶\0香"), (-9, "private-sentinel"),
            (2.5, b"\xff\0"), (b"\0\1", None), ("text", 1),
        ])
    return path


def profile(path, **kwargs):
    return api().profile_sqlite(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        tables={"mixed": ("x", "y"), "empty": ("z",)}, **kwargs)


def test_profiles_all_cells_with_typed_ranges_and_no_raw_text(source):
    before = source.read_bytes()
    result = profile(source)
    assert source.read_bytes() == before
    assert result["status"] == "SELECTED_TABLES_PROFILED"
    assert result["complete_for_selected_tables"] is True
    assert result["source_sha256_before"] == result["source_sha256_after"]
    assert result["rows_read"] == 6 and result["cells_read"] == 12
    table = result["tables"][0]
    assert table["name"] == "mixed" and table["row_count"] == 6
    x, y = table["columns"]
    assert x["storage_counts"] == {"null": 1, "integer": 2, "real": 1, "text": 1, "blob": 1}
    assert x["integer_range"] == {"min": "-9", "max": "9223372036854775807"}
    assert x["real_range"] == {"min_hex": (2.5).hex(), "max_hex": (2.5).hex()}
    assert y["text_lengths"] == {"min_codepoints": 0, "max_codepoints": 16,
                                 "min_sqlite_api_utf8_bytes": 0, "max_sqlite_api_utf8_bytes": 16}
    assert y["text_embedded_nul_count"] == 1
    assert y["blob_lengths"] == {"min_bytes": 2, "max_bytes": 2}
    assert result["tables"][1]["row_count"] == 0
    assert all(value == 0 for value in result["tables"][1]["columns"][0]["storage_counts"].values())
    assert "private-sentinel" not in json.dumps(result)
    assert "茶" not in json.dumps(result)
    assert result["postgresql_connected"] is False
    assert result["value_contract_approved"] is False


@pytest.mark.parametrize("statement", [
    "SELECT z FROM secret", "SELECT * FROM dangerous", "SELECT count(*) FROM mixed",
    "SELECT rowid FROM mixed", "DELETE FROM mixed", "PRAGMA writable_schema=ON",
    "ATTACH ':memory:' AS other", "SELECT load_extension('missing')",
])
def test_scoped_authorizer_blocks_other_tables_views_functions_and_writes(source, statement):
    from xiangrugu_datamgmt.sqlite_diagnostic import _metadata_connection
    with _metadata_connection(source) as db:
        db.set_authorizer(api().scope_authorizer({"mixed": ("x", "y")}))
        with pytest.raises(sqlite3.DatabaseError):
            db.execute(statement).fetchall()


@pytest.mark.parametrize("tables", [
    {}, {"mixed": ("missing",)}, {"mixed": ("x",)},
    {"dangerous": ("z",)}, {"generated": ("x", "g")},
])
def test_missing_or_unsupported_scope_is_not_silent_success(source, tables):
    with pytest.raises(ValueError):
        api().profile_sqlite(source, expected_size=source.stat().st_size,
            expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), tables=tables)


@pytest.mark.parametrize("budget", [
    {"max_rows": 1}, {"max_cells": 1}, {"max_cell_bytes": 1},
    {"max_total_value_bytes": 1}, {"max_vm_steps": 1}, {"max_file_bytes": 1},
])
def test_budget_failure_never_returns_partial_profile(source, budget):
    with pytest.raises(ValueError, match="limit"):
        profile(source, limits=api().ProfileLimits(**budget))


def test_cancel_identity_sidecar_and_source_change_fail(source, monkeypatch):
    module = api()
    with pytest.raises(ValueError, match="cancelled"):
        profile(source, cancelled=lambda: True)
    with pytest.raises(ValueError, match="identity_mismatch"):
        module.profile_sqlite(source, expected_size=1, expected_sha256="0"*64,
                              tables={"mixed": ("x","y")})
    original = module._hash
    calls = 0
    def change(path, guard):
        nonlocal calls
        calls += 1
        if calls == 2:
            with path.open("ab") as stream:
                stream.write(b"changed")
        return original(path, guard)
    monkeypatch.setattr(module, "_hash", change)
    with pytest.raises(ValueError, match="source_changed"):
        profile(source)


def test_vm_budget_boundary_rejects_before_next_callback(source, monkeypatch):
    """A query ending before the next callback must not pass at the boundary."""
    module = api()
    original = module._metadata_connection
    class BoundaryConnection:
        def __enter__(self):
            self.context = original(source)
            self.db = self.context.__enter__()
            return self
        def __exit__(self, *args):
            return self.context.__exit__(*args)
        def __getattr__(self, name):
            return getattr(self.db, name)
        @property
        def text_factory(self):
            return self.db.text_factory
        @text_factory.setter
        def text_factory(self, value):
            self.db.text_factory = value
        def set_progress_handler(self, callback, interval):
            # Deterministically model reaching the budget at the final callback.
            for _ in range(1000 // interval):
                if callback():
                    raise sqlite3.OperationalError("interrupted")
    monkeypatch.setattr(module, "_metadata_connection", lambda path: BoundaryConnection())
    with pytest.raises(ValueError, match="vm_limit"):
        profile(source, limits=module.ProfileLimits(max_vm_steps=1000))


def test_invalid_utf8_is_not_replaced_and_not_exported(tmp_path):
    path = tmp_path / "invalid.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE t(x TEXT)")
        db.execute("INSERT INTO t VALUES(CAST(x'80' AS TEXT))")
    result = api().profile_sqlite(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), tables={"t": ("x",)})
    col = result["tables"][0]["columns"][0]
    assert col["invalid_utf8_text_count"] == 1
    assert col["text_lengths"]["max_codepoints"] is None
    assert result["lossless_text_decoding_confirmed"] is False


def test_quoted_identifiers_and_duplicates_are_preserved(tmp_path):
    path = tmp_path / "quoted.sqlite"
    name, col = '表"名', '列"名'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE "表""名"("列""名")')
        db.executemany('INSERT INTO "表""名" VALUES(?)', [(7,), (7,), (None,)])
    result = api().profile_sqlite(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), tables={name: (col,)})
    assert result["rows_read"] == 3
    assert result["tables"][0]["columns"][0]["storage_counts"]["integer"] == 2
