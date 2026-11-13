"""Catch lost duplicates, unbounded skew, corrupt scratch and unsafe cleanup."""
import importlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from xiangrugu_datamgmt import unordered_values as u


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.value_sort")
    assert spec is not None, "Bounded external sorting is not implemented"
    return importlib.import_module(spec.name)


def schema():
    return u.UnorderedSchema("b"*64, (u.UnorderedColumn(0, "a"*64, "text", True),))


def limits(**kw):
    return u.UnorderedLimits(**({"max_row_bytes": 64, "max_field_bytes": 16,
        "chunk_bytes": 256, "chunk_rows": 4, "merge_fan_in": 2} | kw))


def reference(text):
    # Independent, hand-derived one-column frame, not the production encoder.
    payload = b"\x01" + len(text.encode()).to_bytes(8, "big") + text.encode()
    return b"R" + b"\x00\x00\x00\x01" + len(payload).to_bytes(8, "big") + payload


def test_external_sort_matches_independent_bytes_reference(tmp_path):
    m = api()
    values = ["b", "a", "ab", "c"] * 6
    with m.SortWorkspace(tmp_path, limits()) as w:
        result = m.sort_rows(schema(), iter((v,) for v in values), workspace=w, side="source")
        assert list(result.iter_frames()) == sorted(reference(v) for v in values)
        assert result.row_count == 24 and result.field_count == 24
        assert result.stream_bytes == 81 + sum(len(reference(v)) for v in values)
        assert w.progress["source"].input_complete and w.progress["source"].sort_complete
        assert w.stats.peak_chunk_rows <= 4 and w.stats.peak_chunk_bytes <= 256
    assert w.cleanup_complete and not w.path.exists()


def test_single_partition_skew_stays_bounded_and_globally_sorted(tmp_path, monkeypatch):
    m = api()
    monkeypatch.setattr(m, "partition_for_row", lambda frame: 0)
    values = ["b", "a", "ab", "c"]*6
    with m.SortWorkspace(tmp_path, limits()) as w:
        out = m.sort_rows(schema(), iter((v,) for v in values), workspace=w, side="source")
        assert list(out.iter_frames()) == sorted(reference(v) for v in values)
        assert w.stats.peak_chunk_rows <= 4


@pytest.mark.parametrize("mutation", ["truncate", "same_size", "bad_length", "reverse"])
def test_temp_corruption_short_write_and_disorder_fail_closed(tmp_path, mutation):
    m = api()
    with m.SortWorkspace(tmp_path, limits()) as w:
        out = m.sort_rows(schema(), iter([("a",), ("b",)]), workspace=w, side="source")
        for p in w.path.iterdir():
            data = p.read_bytes()
            if not data:
                continue
            if mutation == "truncate":
                changed = data[:-1]
            elif mutation == "same_size":
                changed = data[:-1] + bytes([data[-1] ^ 1])
            elif mutation == "bad_length":
                changed = data[:5] + b"\xff"*8 + data[13:]
            else:
                changed = reference("b") + reference("a")
            p.write_bytes(changed)
        with pytest.raises(u.UnorderedValueError):
            list(out.iter_frames())
    assert w.cleanup_complete


@pytest.mark.parametrize("kw", [{"max_temp_files": 1}, {"max_temp_bytes": 30},
    {"max_rows": 2}, {"max_stream_bytes": 81}, {"max_columns": 1, "max_field_bytes": 1}])
def test_live_temp_budgets_include_merge_input_and_output(tmp_path, kw):
    m = api()
    with m.SortWorkspace(tmp_path, limits(**kw)) as w:
        with pytest.raises(u.UnorderedValueError):
            out = m.sort_rows(schema(), iter([("ab",)]*24), workspace=w, side="source")
            list(out.iter_frames())
    assert w.cleanup_complete


def test_workspace_is_private_and_cleanup_never_touches_parent(tmp_path):
    m = api()
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"unchanged")
    paths = []
    for _ in range(2):
        with m.SortWorkspace(tmp_path, limits()) as w:
            paths.append(w.path)
            assert w.path.stat().st_mode & 0o777 == 0o700
            out = m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in w.path.iterdir())
            list(out.iter_frames())
        assert w.cleanup_complete and not w.path.exists()
    assert paths[0] != paths[1] and sentinel.read_bytes() == b"unchanged"


def test_parent_symlink_and_outside_var_are_rejected(tmp_path):
    m = api()
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    for parent in (link, Path("/workspace"), Path("/tmp")):
        with pytest.raises(u.UnorderedValueError):
            with m.SortWorkspace(parent, limits()):
                pytest.fail("unsafe parent accepted")


def test_replaced_scratch_file_does_not_delete_outside_target(tmp_path):
    m = api()
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"unchanged")
    with pytest.raises(u.UnorderedValueError):
        with m.SortWorkspace(tmp_path, limits()) as w:
            out = m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")
            p = next(w.path.iterdir())
            p.unlink()
            p.symlink_to(sentinel)
            list(out.iter_frames())
    assert sentinel.read_bytes() == b"unchanged"
    # Exact residual path retained, never following replacement links.
    if w.path.exists():
        for p in w.path.iterdir():
            p.unlink()
        w.path.rmdir()


def test_insufficient_disk_and_short_write_are_errors(tmp_path, monkeypatch):
    m = api()
    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: SimpleNamespace(free=0))
    with m.SortWorkspace(tmp_path, limits()) as w:
        with pytest.raises(u.UnorderedValueError):
            m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")
    monkeypatch.undo()
    monkeypatch.setattr(m.os, "write", lambda fd, data: 0)
    with m.SortWorkspace(tmp_path, limits()) as w:
        with pytest.raises(u.UnorderedValueError):
            m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")


@pytest.mark.parametrize("cancel", [lambda: True, lambda: 1])
def test_cancel_and_nonboolean_callback_stop_sort(tmp_path, cancel):
    m = api()
    with pytest.raises(u.UnorderedValueError):
        with m.SortWorkspace(tmp_path, limits(), cancelled=cancel) as w:
            m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")


def test_timeout_and_throwing_callback_have_no_complete_sort(tmp_path, monkeypatch):
    m = api()
    ticks = iter([0, 0, 200, 200, 200, 200])
    monkeypatch.setattr(m.time, "monotonic", lambda: next(ticks, 200))
    with pytest.raises(u.UnorderedValueError):
        with m.SortWorkspace(tmp_path, limits()) as w:
            m.sort_rows(schema(), iter([("a",)]), workspace=w, side="source")
    monkeypatch.undo()
    def broken():
        raise RuntimeError("synthetic-secret")
    with pytest.raises(u.UnorderedValueError) as error:
        with m.SortWorkspace(tmp_path, limits(), cancelled=broken):
            pass
    assert "synthetic-secret" not in str(error.value)
