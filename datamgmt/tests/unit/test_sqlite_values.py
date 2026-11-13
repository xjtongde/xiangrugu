"""Real synthetic files catch source value loss, scope drift and false completion."""
from dataclasses import replace
import hashlib
import importlib
import sqlite3

import pytest

from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.sqlite_values")
    assert spec is not None, "Independent streaming SQLite values are not implemented"
    return importlib.import_module(spec.name)


def description(table="sample", names=("i", "r", "t"), types=("bigint", "double precision", "text"), nulls=None):
    identity = source_object_id(relative_path="fixture/input.sqlite", archive_chain=[],
                                object_name=table, carrier="sqlite")
    maps = allocate_columns(list(names), object_id=identity)
    return UnorderedSchema(identity, tuple(UnorderedColumn(i, m.identity, ty,
        True if nulls is None else nulls[i]) for i, (m, ty) in enumerate(zip(maps, types))))


def fixture(tmp_path, ddl="CREATE TABLE sample(i, r, t)", rows=None):
    path = tmp_path / "input ?&#.sqlite"
    with sqlite3.connect(path) as db:
        db.execute(ddl)
        if rows is not None:
            db.executemany('INSERT INTO sample VALUES(?,?,?)', rows)
    return path


def open_values(path, *, schema=None, columns=("i", "r", "t"), table="sample", **kwargs):
    return api().open_sqlite_values(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        relative_path="fixture/input.sqlite", table=table, source_columns=columns,
        schema=schema or description(table=table), **kwargs)


def test_native_values_empty_text_null_unicode_and_duplicates_are_preserved(tmp_path):
    want = [(2**63-1, 2.5, " 茶\0香 "), (-2**63, -1.25, "e\u0301"),
            (None, None, ""), (None, None, ""), (1, 1.0, None)]
    path = fixture(tmp_path, rows=want)
    before = path.read_bytes()
    with open_values(path) as stream:
        assert stream.summary["complete"] is False
        assert list(stream) == want
        report = stream.summary
    assert path.read_bytes() == before
    assert report["complete"] and report["rows_read"] == 5 and report["cells_read"] == 15
    assert report["source_sha256_before"] == report["source_sha256_after"]
    assert not report["postgresql_connected"]
    assert "茶" not in str(report)


def test_empty_table_gets_completion_only_after_exhaustion(tmp_path):
    path = fixture(tmp_path)
    with open_values(path) as stream:
        assert not stream.summary["complete"]
        assert list(stream) == []
        assert stream.summary["complete"] and stream.summary["rows_read"] == 0


def test_early_close_never_claims_complete_and_closes_sqlite(tmp_path):
    path = fixture(tmp_path, rows=[(1, 2.5, "a"), (2, 3.5, "b")])
    with open_values(path) as stream:
        assert next(stream) == (1, 2.5, "a")
        stream.close()
        stream.close()
        assert list(stream) == []
        assert not stream.summary["complete"]
        assert stream.summary["source_sha256_after"] is None
    with sqlite3.connect(path, timeout=0) as db:
        db.execute("BEGIN EXCLUSIVE")


@pytest.mark.parametrize("names", [("missing", "r", "t"), ("r", "i", "t"), ("i", "r")])
def test_missing_reordered_or_subset_columns_are_rejected_not_dqs_constants(tmp_path, names):
    path = fixture(tmp_path, rows=[(1, 2.5, "a")])
    s = description(names=names, types=("bigint",)*len(names))
    with pytest.raises(api().SQLiteValueReadError, match="column_scope_mismatch"):
        with open_values(path, schema=s, columns=names) as stream:
            list(stream)


@pytest.mark.parametrize("value", ["1", 1.5, b"1"])
def test_storage_class_mismatch_is_rejected_without_coercion(tmp_path, value):
    path = fixture(tmp_path, rows=[(value, 2.5, "private-sentinel")])
    with open_values(path) as stream:
        with pytest.raises(api().SQLiteValueReadError) as caught:
            list(stream)
        assert caught.value.code == "storage_type_mismatch"
        assert "private-sentinel" not in str(caught.value)
        assert not stream.summary["complete"]


def test_explicit_notnull_policy_must_match_metadata(tmp_path):
    path = fixture(tmp_path, "CREATE TABLE sample(i NOT NULL, r, t)", [(1, 2.5, "a")])
    with pytest.raises(api().SQLiteValueReadError, match="nullability_mismatch"):
        with open_values(path) as stream:
            list(stream)
    with open_values(path, schema=description(nulls=(False, True, True))) as stream:
        assert list(stream) == [(1, 2.5, "a")]


def test_invalid_utf8_text_is_not_replaced(tmp_path):
    path = fixture(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO sample VALUES(1,2.5,CAST(X'ff' AS TEXT))")
    with pytest.raises(api().SQLiteValueReadError, match="invalid_utf8"):
        with open_values(path) as stream:
            list(stream)


@pytest.mark.parametrize("ddl", ["CREATE VIEW sample AS SELECT 1 i, 2.5 r, 'a' t",
    "CREATE TABLE sample(i, r, t GENERATED ALWAYS AS (i||'a') VIRTUAL)"])
def test_views_and_generated_columns_are_not_executed(tmp_path, ddl):
    path = fixture(tmp_path, ddl)
    with pytest.raises(api().SQLiteValueReadError, match="unsupported_object|column_scope_mismatch"):
        with open_values(path) as stream:
            list(stream)


@pytest.mark.parametrize("budget", [{"max_rows": 1}, {"max_cells": 3},
    {"max_value_bytes": 1}, {"max_file_bytes": 1}, {"max_vm_steps": 1}])
def test_explicit_budgets_fail_closed(tmp_path, budget):
    path = fixture(tmp_path, rows=[(1, 2.5, "a"), (2, 3.5, "b")])
    with pytest.raises(api().SQLiteValueReadError, match="limit"):
        with open_values(path, limits=api().SQLiteValueLimits(**budget)) as stream:
            list(stream)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecar_files_are_rejected(tmp_path, suffix):
    path = fixture(tmp_path)
    path.with_name(path.name+suffix).write_bytes(b"synthetic")
    with pytest.raises(api().SQLiteValueReadError, match="sidecar_present"):
        with open_values(path) as stream:
            list(stream)


def test_source_replacement_after_last_row_prevents_completion(tmp_path):
    path = fixture(tmp_path, rows=[(1, 2.5, "a")])
    with open_values(path) as stream:
        assert next(stream) == (1, 2.5, "a")
        with path.open("ab") as out:
            out.write(b"synthetic-change")
        with pytest.raises(api().SQLiteValueReadError, match="source_changed"):
            next(stream)
        assert not stream.summary["complete"]


def test_identity_mismatch_prevents_reading(tmp_path):
    path = fixture(tmp_path)
    m = api()
    with pytest.raises(m.SQLiteValueReadError, match="identity_mismatch"):
        with m.open_sqlite_values(path, expected_size=path.stat().st_size,
            expected_sha256="0"*64, relative_path="fixture/input.sqlite", table="sample",
            source_columns=("i", "r", "t"), schema=description()) as stream:
            list(stream)


def test_cancellation_stops_midstream_without_success(tmp_path):
    path = fixture(tmp_path, rows=[(1, 2.5, "a"), (2, 3.5, "b")])
    stop = [False]
    with open_values(path, cancelled=lambda: stop[0]) as stream:
        assert next(stream) == (1, 2.5, "a")
        stop[0] = True
        with pytest.raises(api().SQLiteValueReadError, match="cancelled"):
            next(stream)
        assert not stream.summary["complete"]


def test_schema_identity_and_column_identity_cannot_be_substituted(tmp_path):
    path = fixture(tmp_path)
    s = description()
    for wrong in (replace(s, source_object_id="a"*64),
                  replace(s, columns=(replace(s.columns[0], column_key="a"*64),)+s.columns[1:])):
        with pytest.raises(api().SQLiteValueReadError, match="invalid_scope"):
            with open_values(path, schema=wrong) as stream:
                list(stream)


def test_source_iterator_connects_to_existing_comparison_with_manual_values(tmp_path):
    from xiangrugu_datamgmt.unordered_validate import UnorderedInput, UnorderedEvidence, compare_unordered
    from xiangrugu_datamgmt.unordered_values import UnorderedLimits
    path = fixture(tmp_path, rows=[(1, 2.5, "a"), (1, 2.5, "a"), (2, 3.5, "b")])
    s = description()
    with open_values(path) as stream:
        source = UnorderedInput(s, stream, stream.evidence)
        target = UnorderedInput(s, iter([(2, 3.5, "b"), (1, 2.5, "a"), (1, 2.5, "a")]),
                                UnorderedEvidence("synthetic", "manual-values", "1"*64))
        result = compare_unordered(s, source, target, limits=UnorderedLimits(),
                                   scratch_parent=tmp_path).to_dict()
        assert result["result"] == "comparison_equal", result
        assert stream.summary["complete"]


@pytest.mark.parametrize("cancelled", [lambda: "yes", lambda: 1,
    lambda: (_ for _ in ()).throw(RuntimeError("private-sentinel"))])
def test_bad_cancel_callback_is_a_safe_input_error(tmp_path, cancelled):
    path = fixture(tmp_path)
    with open_values(path, cancelled=cancelled) as stream:
        with pytest.raises(api().SQLiteValueReadError, match="input_error") as caught:
            list(stream)
        assert "private-sentinel" not in str(caught.value)
        assert not stream.summary["complete"]


def test_column_budget_is_checked_before_source_read(tmp_path):
    path = fixture(tmp_path)
    with pytest.raises(api().SQLiteValueReadError, match="column_limit"):
        with open_values(path, limits=api().SQLiteValueLimits(max_columns=2)) as stream:
            list(stream)


def test_timeout_after_a_yield_cannot_claim_success(tmp_path, monkeypatch):
    path = fixture(tmp_path, rows=[(1, 2.5, "a"), (2, 3.5, "b")])
    now = [0.0]
    monkeypatch.setattr(api().time, "monotonic", lambda: now[0])
    with open_values(path, limits=api().SQLiteValueLimits(max_seconds=1)) as stream:
        assert next(stream) == (1, 2.5, "a")
        now[0] = 2.0
        with pytest.raises(api().SQLiteValueReadError, match="time_limit"):
            next(stream)
        assert not stream.summary["complete"]


def test_cell_size_limit_and_nonfinite_float_are_rejected(tmp_path):
    path = fixture(tmp_path, rows=[(1, float("inf"), "a"*8192)])
    with pytest.raises(api().SQLiteValueReadError, match="cell_byte_limit"):
        with open_values(path, limits=api().SQLiteValueLimits(max_cell_bytes=4096)) as stream:
            list(stream)
    with pytest.raises(api().SQLiteValueReadError, match="storage_type_mismatch"):
        with open_values(path) as stream:
            list(stream)


def test_symlink_and_corrupt_file_are_rejected_without_source_details(tmp_path):
    path = fixture(tmp_path)
    link = tmp_path / "link.sqlite"
    link.symlink_to(path)
    with pytest.raises(api().SQLiteValueReadError, match="unsafe_path"):
        with open_values(link) as stream:
            list(stream)
    path.write_bytes(b"private-sentinel-not-a-database")
    with pytest.raises(api().SQLiteValueReadError, match="sqlite_error") as caught:
        with open_values(path) as stream:
            list(stream)
    assert "private-sentinel" not in str(caught.value)


def test_quoted_identifiers_without_rowid_are_read_without_sql_injection(tmp_path):
    path = fixture(tmp_path, 'CREATE TABLE sample(i INTEGER PRIMARY KEY, r, t) WITHOUT ROWID', [(1, 2.5, "a")])
    # WITHOUT ROWID makes the primary-key column explicitly notnull in xinfo.
    with open_values(path, schema=description(nulls=(False, True, True))) as stream:
        assert list(stream) == [(1, 2.5, "a")]
    table, col = 'odd"; DROP TABLE sample;--', 'text"name'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE "odd""; DROP TABLE sample;--"("text""name" TEXT)')
        db.execute('INSERT INTO "odd""; DROP TABLE sample;--" VALUES(?)', ("unchanged",))
    s = description(table, (col,), ("text",))
    with open_values(path, schema=s, table=table, columns=(col,)) as stream:
        assert list(stream) == [("unchanged",)]
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM sample").fetchone() == (1,)


def test_real_connection_is_closed_on_completion_and_abandonment(tmp_path, monkeypatch):
    from contextlib import contextmanager
    m = api()
    original = m._metadata_connection
    connections = []
    @contextmanager
    def observed_connection(path):
        with original(path) as db:
            connections.append(db)
            yield db
    monkeypatch.setattr(m, "_metadata_connection", observed_connection)
    path = fixture(tmp_path, rows=[(1, 2.5, "a")])
    for exhaust in (True, False):
        with open_values(path) as stream:
            next(stream)
            if exhaust:
                assert list(stream) == []
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connections[-1].execute("SELECT 1")


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_budget_values_are_rejected(value):
    with pytest.raises(ValueError):
        api().SQLiteValueLimits(max_rows=value)


@pytest.mark.parametrize("stop_kind", ["cancel", "timeout"])
def test_final_source_hash_cancellation_or_timeout_cannot_claim_complete(tmp_path, monkeypatch, stop_kind):
    path = fixture(tmp_path, rows=[(1, 2.5, "a")])
    m = api()
    original = m._hash
    state = dict(calls=0, cancelled=False, now=0.0)
    def hash_then_stop(path, guard):
        digest = original(path, guard)
        state["calls"] += 1
        if state["calls"] == 2:
            state["cancelled"] = stop_kind == "cancel"
            state["now"] = 2.0 if stop_kind == "timeout" else 0.0
        return digest
    monkeypatch.setattr(m, "_hash", hash_then_stop)
    monkeypatch.setattr(m.time, "monotonic", lambda: state["now"])
    with open_values(path, cancelled=lambda: state["cancelled"],
                     limits=m.SQLiteValueLimits(max_seconds=1)) as stream:
        assert next(stream) == (1, 2.5, "a")
        with pytest.raises(m.SQLiteValueReadError, match="cancelled|time_limit"):
            next(stream)
        assert not stream.summary["complete"]
        assert stream.summary["source_sha256_after"] is None
