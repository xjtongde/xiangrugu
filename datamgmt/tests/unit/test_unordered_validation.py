"""Catch order assumptions, lost multiplicities and premature certificates."""
import importlib
import json
from dataclasses import replace

import pytest

from xiangrugu_datamgmt import unordered_values as u
from xiangrugu_datamgmt import value_sort as sort


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.unordered_validate")
    assert spec is not None, "Independent unordered comparison is not implemented"
    return importlib.import_module(spec.name)


def schema(kind="text"):
    return u.UnorderedSchema("b"*64, (u.UnorderedColumn(0, "a"*64, kind, True),))


def compare(parent, left, right, *, limits=None, target_schema=None, cancelled=None, kind="text"):
    m = api()
    s = schema(kind)
    source = m.UnorderedInput(s, iter(left), m.UnorderedEvidence("synthetic", "source-fixture", "1"*64))
    target = m.UnorderedInput(target_schema or s, iter(right), m.UnorderedEvidence("synthetic", "target-fixture", "2"*64))
    return m.compare_unordered(s, source, target, limits=limits or u.UnorderedLimits(),
                               scratch_parent=parent, cancelled=cancelled).to_dict()


@pytest.mark.parametrize("left,right,kind", [([], [], "text"),
    ([(None,), ("",), ("a",), ("a",), ("a",)], [("a",), (None,), ("a",), ("",), ("a",)], "text"),
    ([(1.0,), (-0.0,), (None,)], [(None,), (-0.0,), (1.0,)], "double precision")])
def test_equal_multiset_ignores_order_and_keeps_duplicates(tmp_path, left, right, kind):
    r = compare(tmp_path, left, right, kind=kind)
    assert r["result"] == "comparison_equal" and r["cleanup_complete"]
    assert r["source_count"] == r["target_count"] == len(left)
    assert r["source_sha256"] == r["target_sha256"] and r["source_sha256"] is not None
    assert not r["partial"] and r["difference_patterns"] == 0
    assert not list(tmp_path.iterdir())
    assert "CONFORMS" not in json.dumps(r) and "ready_for_import" not in r


def test_same_row_three_vs_two_counts_one_pattern_one_missing(tmp_path):
    r = compare(tmp_path, [("a",)]*3, [("a",)]*2)
    assert r["result"] == "comparison_failed" and not r["partial"]
    assert (r["difference_patterns"], r["missing_rows"], r["excess_rows"]) == (1, 1, 0)
    assert (r["source_count"], r["target_count"]) == (3, 2)
    assert r["differences"][0]["source_count"] == 3
    assert r["differences"][0]["target_count"] == 2
    assert r["source_sha256"] is r["target_sha256"] is None


@pytest.mark.parametrize("kind,left,right", [("text", "", None), ("text", "␀", None),
    ("text", "é", "e\u0301"), ("bigint", 1, 2), ("double precision", 0.0, -0.0)])
def test_same_count_changed_value_is_two_row_patterns_not_an_identified_update(tmp_path, kind, left, right):
    r = compare(tmp_path, [(left,)], [(right,)], kind=kind)
    assert r["result"] == "comparison_failed"
    assert (r["difference_patterns"], r["missing_rows"], r["excess_rows"]) == (2, 1, 1)
    assert {d["code"] for d in r["differences"]} == {"missing", "excess"}
    assert all("column_key" not in d and "rownum" not in d for d in r["differences"])


@pytest.mark.parametrize("cap", [0, 1, 100])
def test_detail_caps_and_auxiliary_hash_collision_keep_all_patterns(tmp_path, cap, monkeypatch):
    m = api()
    monkeypatch.setattr(m, "row_digest", lambda frame: "0"*64)
    r = compare(tmp_path, [("a",), ("b",), ("c",)], [],
                limits=u.UnorderedLimits(max_differences=cap))
    assert r["difference_patterns"] == 3 and r["missing_rows"] == 3
    assert r["source_count"] == 3 and r["target_count"] == 0
    assert len(r["differences"]) == min(cap, 3)
    assert r["details_truncated"] == (cap < 3)


def test_structure_mismatch_does_not_consume_or_create_workspace(tmp_path):
    def forbidden():
        raise AssertionError("cannot consume")
        yield
    r = compare(tmp_path, forbidden(), forbidden(), target_schema=replace(schema(), source_object_id="c"*64))
    assert r["result"] == "comparison_error" and r["error_code"] == "structure"
    assert r["partial"] and r["source_count"] is None
    assert not list(tmp_path.iterdir())


def test_report_redacts_values_and_third_party_exception_body(tmp_path):
    def broken():
        yield ("synthetic-secret",)
        raise RuntimeError("synthetic-secret")
    r = compare(tmp_path, broken(), [])
    assert r["result"] == "comparison_error" and r["partial"]
    assert r["source_sha256"] is r["target_sha256"] is None
    assert r["source_progress"]["accepted_rows"] == 1
    assert r["error_side"] == "source" and r["scan_index"] == 2
    assert "synthetic-secret" not in json.dumps(r)
    assert r["cleanup_complete"] and not list(tmp_path.iterdir())


@pytest.mark.parametrize("values", [[(1,)], [("a", "b")], [("\ud800",)]])
def test_bad_input_cannot_produce_a_complete_certificate(tmp_path, values):
    r = compare(tmp_path, values, [])
    assert r["result"] == "comparison_error" and r["partial"]
    assert r["source_sha256"] is None and r["cleanup_complete"]


def test_cancel_timeout_and_callback_failure_have_no_success_digest(tmp_path, monkeypatch):
    r = compare(tmp_path, [], [], cancelled=lambda: True)
    assert r["result"] == "comparison_error" and r["source_sha256"] is None
    ticks = iter([0, 200, 200, 200])
    monkeypatch.setattr(sort.time, "monotonic", lambda: next(ticks, 200))
    r = compare(tmp_path, [], [])
    assert r["error_code"] == "timeout" and r["partial"]


def test_cleanup_failure_never_reports_equal(tmp_path, monkeypatch):
    real_delete = sort.SortWorkspace.delete
    def fail_delete(self, file):
        if self.progress.get("target") and self.progress["target"].sort_complete:
            raise u.UnorderedValueError("cleanup_error")
        return real_delete(self, file)
    monkeypatch.setattr(sort.SortWorkspace, "delete", fail_delete)
    r = compare(tmp_path, [("a",)], [("a",)])
    assert r["result"] == "comparison_error" and not r["cleanup_complete"]
    assert r["residual_directory"] and r["source_sha256"] is None
    # Controlled test cleanup uses only the exact returned child.
    from pathlib import Path
    p = Path(r["residual_directory"])
    assert p.parent == tmp_path
    for child in p.iterdir():
        child.unlink()
    p.rmdir()


def test_common_adapter_error_is_caught_by_independent_golden(tmp_path):
    # Both adapters make the same wrong conversion; mutual equality is insufficient.
    wrong = [(None,)]
    assert compare(tmp_path, wrong, wrong)["result"] == "comparison_equal"
    assert compare(tmp_path, [("",)], wrong)["result"] == "comparison_failed"


def test_chunk_changes_do_not_change_global_canonical_digest(tmp_path):
    rows = [("c",), ("ab",), ("a",), ("b",)]*6
    a = compare(tmp_path, rows, list(reversed(rows)))
    b = compare(tmp_path, rows, rows, limits=u.UnorderedLimits(chunk_rows=2, merge_fan_in=2))
    assert a["source_sha256"] == b["source_sha256"]


def smoke_api():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).parents[3] / "scripts/smoke-unordered-values.py"
    assert path.is_file(), "Packaged unordered smoke script is missing"
    spec = importlib.util.spec_from_file_location("unordered_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_smoke_uses_packaged_modules_only(tmp_path, capsys):
    assert smoke_api().main(["--scratch-parent", str(tmp_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["equal"] == "comparison_equal"
    assert output["missing"] == "comparison_failed"
    assert not list(tmp_path.iterdir())


def test_smoke_returns_nonzero_when_comparator_is_broken(tmp_path, monkeypatch, capsys):
    module = smoke_api()
    class Broken:
        def to_dict(self):
            return {"result": "comparison_equal", "cleanup_complete": True,
                    "missing_rows": 0, "difference_patterns": 0}
    monkeypatch.setattr(module, "compare_unordered", lambda *a, **kw: Broken())
    assert module.main(["--scratch-parent", str(tmp_path)]) != 0
    assert "comparison_equal" not in capsys.readouterr().out


class OwnedInput:
    def __init__(self, values, *, fail_close=False):
        self.rows = iter(values)
        self.closed = 0
        self.fail_close = fail_close

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.rows)

    def close(self):
        self.closed += 1
        if self.fail_close:
            raise RuntimeError("close-synthetic-secret")


@pytest.mark.parametrize("mode", ["cancel", "source_error", "success", "close_error"])
def test_both_inputs_are_closed_once_on_every_exit(tmp_path, mode):
    left = OwnedInput([(1,)] if mode == "source_error" else [("a",)])
    right = OwnedInput([("a",)], fail_close=mode == "close_error")
    r = compare(tmp_path, left, right, cancelled=(lambda: True) if mode == "cancel" else None)
    assert left.closed == right.closed == 1
    if mode != "success":
        assert r["result"] == "comparison_error" and r["source_sha256"] is None
    assert "close-synthetic-secret" not in json.dumps(r)


@pytest.mark.parametrize("values", [[], [("",), ("",)]])
def test_complete_digest_matches_independent_hand_stream(tmp_path, values):
    import hashlib
    descriptor = ('[[0,"' + "a"*64 + '","text",true]]').encode("ascii")
    header = b"XRGSET\x00\x01" + bytes.fromhex("b"*64) + hashlib.sha256(descriptor).digest()
    frame = bytes.fromhex("52000000010000000000000009010000000000000000")
    stream = header + frame*len(values) + b"E" + len(values).to_bytes(8, "big")
    r = compare(tmp_path, values, values)
    assert r["source_sha256"] == r["target_sha256"] == hashlib.sha256(stream).hexdigest()


@pytest.mark.parametrize("parent", [None, 0])
def test_invalid_scratch_parent_still_closes_inputs(parent):
    left, right = OwnedInput([]), OwnedInput([])
    r = compare(parent, left, right)
    assert r["result"] == "comparison_error" and r["source_sha256"] is None
    assert left.closed == right.closed == 1
