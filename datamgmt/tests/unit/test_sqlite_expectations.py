"""Catch missing duplicates, false completion and leaked temporary source values."""
import hashlib
import importlib
import json
import sqlite3
import struct

import pytest

from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema, UnorderedLimits


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.sqlite_expectations")
    assert spec is not None, "Source-only expectation bridge is missing"
    return importlib.import_module(spec.name)


def sample(tmp_path, rows):
    path = tmp_path / "source.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE sample(v TEXT)")
        db.executemany("INSERT INTO sample VALUES(?)", rows)
    identity = source_object_id(relative_path="fixture/source.sqlite", archive_chain=[],
                                object_name="sample", carrier="sqlite")
    column = allocate_columns(["v"], object_id=identity)[0].identity
    schema = UnorderedSchema(identity, (UnorderedColumn(0, column, "text", True),))
    return path, schema


def run(path, schema, scratch, **kwargs):
    return api().summarize_sqlite(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        relative_path="fixture/source.sqlite", table="sample", source_columns=("v",),
        schema=schema, scratch_parent=scratch, **kwargs)


def manual_hash(schema, values):
    # Independently construct v1 frames; do not call the encoder or summary.
    definition = json.dumps([[0, schema.columns[0].column_key, "text", True]],
                            separators=(",", ":")).encode("ascii")
    header = b"XRGSET\x00\x01" + bytes.fromhex(schema.source_object_id) + hashlib.sha256(definition).digest()
    frames = []
    for value in values:
        cell = b"\x00" if value is None else b"\x01" + struct.pack(">Q", len(value.encode())) + value.encode()
        frames.append(b"\x52" + struct.pack(">IQ", 1, len(cell)) + cell)
    return hashlib.sha256(header + b"".join(sorted(frames)) + b"\x45" + struct.pack(">Q", len(values))).hexdigest()


@pytest.mark.parametrize("values", [[], [None], ["", "", None, " 茶\0香 ", "e\u0301"]])
def test_complete_source_only_summary_matches_manual_bytes_and_cleans(tmp_path, values):
    path, schema = sample(tmp_path, [(v,) for v in values])
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    before = path.read_bytes()
    report = run(path, schema, scratch)
    assert report["expected_sha256"] == manual_hash(schema, values)
    assert report["expected_count"] == len(values)
    assert report["field_count"] == len(values)
    assert report["cleanup_complete"] and report["source_read"]["complete"]
    assert report["status"] == "DRAFT_SOURCE_EXPECTATION"
    assert not report["postgresql_connected"] and not report["ready_for_import"]
    assert " 茶" not in json.dumps(report, ensure_ascii=False)
    assert path.read_bytes() == before
    assert list(scratch.iterdir()) == []


def test_reordering_preserves_digest_but_missing_duplicate_changes_it(tmp_path):
    path, schema = sample(tmp_path, [("b",), ("a",), ("a",)])
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    first = run(path, schema, scratch)
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM sample")
        db.executemany("INSERT INTO sample VALUES(?)", [("a",), ("b",), ("a",)])
    assert run(path, schema, scratch)["expected_sha256"] == first["expected_sha256"]
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM sample WHERE rowid=(SELECT min(rowid) FROM sample)")
    assert run(path, schema, scratch)["expected_sha256"] != first["expected_sha256"]


@pytest.mark.parametrize("kwargs", [
    {"read_limits": SQLiteValueLimits(max_rows=1)},
    {"sort_limits": UnorderedLimits(max_rows=1)},
    {"cancelled": lambda: True},
])
def test_failures_produce_no_expectation_and_clean_owned_scratch(tmp_path, kwargs):
    path, schema = sample(tmp_path, [("a",), ("b",)])
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with pytest.raises(ValueError):
        run(path, schema, scratch, **kwargs)
    assert list(scratch.iterdir()) == []


def test_corrupt_identity_never_produces_expectation(tmp_path):
    path, schema = sample(tmp_path, [("a",)])
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with pytest.raises(ValueError):
        api().summarize_sqlite(path, expected_size=path.stat().st_size,
            expected_sha256="0"*64, relative_path="fixture/source.sqlite", table="sample",
            source_columns=("v",), schema=schema, scratch_parent=scratch)
    assert list(scratch.iterdir()) == []
