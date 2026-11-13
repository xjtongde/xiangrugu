"""Catch repeated full hashing, premature batch answers and source drift."""
import hashlib
import importlib
import sqlite3

import pytest

from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
from test_sqlite_expectations import manual_hash


def api():
    module = importlib.import_module("xiangrugu_datamgmt.sqlite_expectations")
    assert hasattr(module, "summarize_sqlite_batch"), "Batch-owned verification is missing"
    return module


def fixture(tmp_path):
    path = tmp_path / "source.sqlite"
    descriptions = []
    with sqlite3.connect(path) as db:
        for table, values in (("a", ["", None, "茶", "茶"]), ("b", []), ("c", [" z "])):
            db.execute(f'CREATE TABLE "{table}"(v TEXT)')
            db.executemany(f'INSERT INTO "{table}" VALUES(?)', [(v,) for v in values])
            identity = source_object_id(relative_path="fixture/source.sqlite", archive_chain=[],
                                        object_name=table, carrier="sqlite")
            key = allocate_columns(["v"], object_id=identity)[0].identity
            schema = UnorderedSchema(identity, (UnorderedColumn(0, key, "text", True),))
            descriptions.append(dict(table=table, source_columns=("v",), schema=schema))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    return path, tuple(descriptions), scratch


def run(path, objects, scratch, **kwargs):
    return api().summarize_sqlite_batch(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        relative_path="fixture/source.sqlite", objects=objects, scratch_parent=scratch, **kwargs)


def test_three_tables_hash_file_twice_and_match_independent_frames(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    import xiangrugu_datamgmt.sqlite_values as values
    calls = []
    original = values._hash
    def counted(path, guard):
        calls.append(path)
        return original(path, guard)
    monkeypatch.setattr(values, "_hash", counted)
    report = run(path, objects, scratch)
    assert len(calls) == 2
    assert report["complete"] and report["source_sha256_before"] == report["source_sha256_after"]
    assert [o["expected_count"] for o in report["objects"]] == [4, 0, 1]
    assert [o["expected_sha256"] for o in report["objects"]] == [
        manual_hash(o["schema"], v) for o, v in zip(objects, [["", None, "茶", "茶"], [], [" z "]])]
    assert all(o["source_read"]["complete"] is False for o in report["objects"])
    assert all(o["source_read"]["values_complete"] for o in report["objects"])
    assert not report["ready_for_import"] and not report["postgresql_connected"]
    assert list(scratch.iterdir()) == []


def test_standalone_reader_keeps_its_two_full_hashes(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    import xiangrugu_datamgmt.sqlite_values as values
    calls = []
    original = values._hash
    def counted(path, guard):
        calls.append(path)
        return original(path, guard)
    monkeypatch.setattr(values, "_hash", counted)
    result = api().summarize_sqlite(path, expected_size=path.stat().st_size,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        relative_path="fixture/source.sqlite", scratch_parent=scratch, **objects[0])
    assert len(calls) == 2 and result["source_read"]["complete"]


@pytest.mark.parametrize("kind", ["empty", "duplicate", "bad_columns", "bad_identity", "bad_limits"])
def test_invalid_scope_rejected_before_any_source_hash(tmp_path, monkeypatch, kind):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    changed = [dict(o) for o in objects]
    if kind == "empty":
        changed = []
    elif kind == "duplicate":
        changed[1] = changed[0]
    elif kind == "bad_columns":
        changed[1]["source_columns"] = ("missing",)
    elif kind == "bad_identity":
        changed[1]["schema"] = changed[0]["schema"]
    else:
        changed[1]["read_limits"] = "unlimited"
    import xiangrugu_datamgmt.sqlite_values as values
    def forbidden(*args):
        pytest.fail("invalid scope touched source bytes")
    monkeypatch.setattr(values, "_hash", forbidden)
    with pytest.raises(ValueError):
        module.summarize_sqlite_batch(path, expected_size=path.stat().st_size,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            relative_path="fixture/source.sqlite", objects=tuple(changed), scratch_parent=scratch)


def test_middle_table_failure_returns_no_partial_answer_and_cleans(tmp_path):
    path, objects, scratch = fixture(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO b VALUES(7)")
    # TEXT affinity would coerce 7; use an actual BLOB to violate native type.
    with sqlite3.connect(path) as db:
        db.execute("UPDATE b SET v=x'01'")
    # Existing sorter maps reader exceptions to its fail-closed input_error.
    with pytest.raises(ValueError, match="input_error"):
        run(path, objects, scratch)
    assert list(scratch.iterdir()) == []


@pytest.mark.parametrize("change", ["modify", "replace", "sidecar"])
def test_source_change_before_terminal_digest_rejects_whole_batch(tmp_path, monkeypatch, change):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    original = module._summarize_rows
    calls = 0
    def mutate(*args, **kwargs):
        nonlocal calls
        result = original(*args, **kwargs)
        calls += 1
        if calls == 3:
            if change == "modify":
                with sqlite3.connect(path) as db:
                    db.execute("UPDATE a SET v='different'")
            elif change == "replace":
                data = path.read_bytes()
                path.unlink()
                path.write_bytes(data)
            else:
                path.with_name(path.name + "-wal").write_bytes(b"x")
        return result
    monkeypatch.setattr(module, "_summarize_rows", mutate)
    with pytest.raises(ValueError):
        run(path, objects, scratch)
    assert list(scratch.iterdir()) == []


def test_cancel_during_final_hash_never_returns_batch_answer(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    import xiangrugu_datamgmt.sqlite_values as values
    stopped = False
    calls = 0
    original = values._hash
    def cancel_second(path, guard):
        nonlocal calls, stopped
        calls += 1
        if calls == 2:
            stopped = True
        return original(path, guard)
    monkeypatch.setattr(values, "_hash", cancel_second)
    with pytest.raises(ValueError, match="cancelled"):
        run(path, objects, scratch, cancelled=lambda: stopped)
    assert list(scratch.iterdir()) == []


def test_final_digest_mismatch_rejects_batch_even_with_matching_stat(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    import xiangrugu_datamgmt.sqlite_values as values
    original = values._hash
    calls = 0
    def mismatched(path, guard):
        nonlocal calls
        calls += 1
        result = original(path, guard)
        return "0"*64 if calls == 2 else result
    monkeypatch.setattr(values, "_hash", mismatched)
    with pytest.raises(ValueError, match="source_changed"):
        run(path, objects, scratch)
    assert list(scratch.iterdir()) == []


def test_incomplete_values_never_become_a_batch_answer(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    import xiangrugu_datamgmt.sqlite_values as values
    original = values._ValueRows.__next__
    def abandon(stream):
        if stream.table == "a" and stream.summary["rows_read"] == 1:
            stream.close()
        return original(stream)
    monkeypatch.setattr(values._ValueRows, "__next__", abandon)
    with pytest.raises(ValueError):
        run(path, objects, scratch)
    assert list(scratch.iterdir()) == []


def test_cleanup_failure_prevents_even_terminal_digest(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    original = module.SortWorkspace.__exit__
    def failed_cleanup(workspace, *args):
        original(workspace, *args)
        workspace.cleanup_complete = False
    monkeypatch.setattr(module.SortWorkspace, "__exit__", failed_cleanup)
    with pytest.raises(ValueError, match="cleanup_error"):
        run(path, objects, scratch)
    assert list(scratch.iterdir()) == []


def test_file_budget_is_checked_before_first_full_hash(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    changed = [dict(o, read_limits=SQLiteValueLimits(max_file_bytes=1)) for o in objects]
    import xiangrugu_datamgmt.sqlite_values as values
    def forbidden(*args):
        pytest.fail("Oversized input was hashed before file budget check")
    monkeypatch.setattr(values, "_hash", forbidden)
    with pytest.raises(ValueError, match="file_limit"):
        run(path, tuple(changed), scratch)


def test_scope_dict_is_captured_before_callbacks_can_change_it(tmp_path):
    path, objects, scratch = fixture(tmp_path)
    changed = [dict(o) for o in objects]
    def mutate():
        changed[0]["table"] = "c"
        return False
    report = run(path, tuple(changed), scratch, cancelled=mutate)
    assert [o["source_object_name"] for o in report["objects"]] == ["a", "b", "c"]
    assert [o["expected_count"] for o in report["objects"]] == [4, 0, 1]


def test_last_cancellation_check_happens_before_answer_escapes(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    original = module._BatchSource.__exit__
    stopped = False
    def cancel_after_verified_close(batch, *args):
        nonlocal stopped
        original(batch, *args)
        stopped = True
    monkeypatch.setattr(module._BatchSource, "__exit__", cancel_after_verified_close)
    with pytest.raises(ValueError, match="cancelled"):
        run(path, objects, scratch, cancelled=lambda: stopped)


def test_batch_deadline_reaches_sorting_checks_not_only_next_table(tmp_path, monkeypatch):
    path, objects, scratch = fixture(tmp_path)
    module = api()
    import xiangrugu_datamgmt.sqlite_values as values
    clock = [0.0]
    monkeypatch.setattr(values.time, "monotonic", lambda: clock[0])
    original = module.sort_rows
    def delay_after_native_read(*args, **kwargs):
        ordered = original(*args, **kwargs)
        clock[0] = 2.0
        # sort_rows has exhausted the source; only workspace checks remain.
        kwargs["workspace"].check()
        pytest.fail("Batch deadline was not enforced during sorting")
        return ordered
    monkeypatch.setattr(module, "sort_rows", delay_after_native_read)
    with pytest.raises(ValueError):
        run(path, objects, scratch, max_seconds=1)
    assert list(scratch.iterdir()) == []
