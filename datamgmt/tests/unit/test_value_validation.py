"""Independent synthetic iterators expose incorrect equality and false EOF."""
import importlib
import json
from dataclasses import replace

import pytest

from xiangrugu_datamgmt import canonical as c


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.validate")
    assert spec is not None, "Independent ordered value comparison is not implemented"
    return importlib.import_module(spec.name)


def schema():
    return c.ValueSchema("b"*64, (
        c.ValueColumn("a"*64, "value", "text", True),
        c.ValueColumn(c.ROW_KEY, "__src_rownum", "bigint", False),
    ))


def compare(left, right, *, count, cap=100, target_schema=None, source_schema=None,
            cancelled=None, limits=None):
    m = api()
    s = schema()
    source = m.ValueInput(source_schema or s, iter(left), m.ValueEvidence("synthetic", "source-fixture", "1"*64))
    target = m.ValueInput(target_schema or s, iter(right), m.ValueEvidence("synthetic", "target-fixture", "2"*64))
    return m.compare_ordered(s, source, target, expected_count=count,
                             limits=limits or c.ValueLimits(max_differences=cap),
                             cancelled=cancelled)


@pytest.mark.parametrize("rows", [(), (("x", 1),), (("x", 1), ("x", 2))])
def test_equal_rows_have_complete_counts_and_only_synthetic_equality(rows):
    report = compare(rows, rows, count=len(rows))
    assert report.result == "comparison_equal"
    assert report.difference_count == 0
    assert report.source_count == report.target_count == len(rows)
    assert report.source_partial is report.target_partial is False
    assert report.source_sha256 == report.target_sha256
    assert report.compared_fields == 2 * len(rows)
    raw = json.dumps(report.to_dict())
    assert "CONFORMS" not in raw and "ready_for_import" not in raw


@pytest.mark.parametrize("target", [None, "␀", " ", "e\u0301", "private-secret"])
def test_changed_text_and_null_are_detected_without_value_disclosure(target):
    report = compare((("", 1),), ((target, 1),), count=1)
    assert report.result == "comparison_failed"
    assert report.difference_count == 1
    assert report.differences[0].column_key == "a"*64
    assert report.differences[0].code == "value"
    raw = json.dumps(report.to_dict())
    assert "private-secret" not in raw


def test_unicode_normalization_is_not_equality():
    assert compare((("é", 1),), (("e\u0301", 1),), count=1).result == "comparison_failed"


@pytest.mark.parametrize("rows", [((4, 1),), (("x", 2),), (("x", 1), ("x", 1)),
                                  (("x",),), (("x", True),)])
def test_bad_type_rownum_width_and_duplicates_fail_closed(rows):
    report = compare((("x", 1),), rows, count=1)
    assert report.result == "comparison_failed"
    assert report.target_partial and report.target_sha256 is None


def test_structure_mismatch_never_consumes_rows():
    def forbidden():
        raise AssertionError("must not consume")
        yield
    s = schema()
    wrong = replace(s, columns=(replace(s.columns[0], nullable=False), s.columns[-1]))
    report = compare(forbidden(), forbidden(), count=1, target_schema=wrong)
    assert report.error_code == "structure"
    assert report.source_count == report.target_count == 0
    assert report.source_partial and report.target_partial


@pytest.mark.parametrize("changes", [
    {"source_object_id": "c"*64},
    {"columns": (c.ValueColumn("c"*64, "renamed", "text", True),
                 c.ValueColumn(c.ROW_KEY, "__src_rownum", "bigint", False))},
])
def test_actual_identity_and_column_metadata_must_match(changes):
    assert compare((), (), count=0, target_schema=replace(schema(), **changes)).error_code == "structure"


@pytest.mark.parametrize("left,right,want", [
    ((), (("x", 1), ("x", 2), ("x", 3)), 3),
    ((("x", 1), ("x", 2)), (), 2),
    ((("x", 1),), (("x", 1), ("x", 2)), 1),
])
def test_unmatched_rows_are_all_counted_and_longer_side_reaches_eof(left, right, want):
    report = compare(left, right, count=len(left))
    assert report.result == "comparison_failed"
    assert report.source_count == len(left) and report.target_count == len(right)
    assert report.source_partial is report.target_partial is False
    assert sum(d.code == "count" for d in report.differences) >= want


def test_equal_wrong_counts_are_not_accepted():
    report = compare((("x", 1),), (("x", 1),), count=2)
    assert report.result == "comparison_failed" and report.error_code == "count"


@pytest.mark.parametrize("cap", [0, 1])
def test_detail_cap_preserves_total_count_and_full_scan(cap):
    report = compare((("x", 1), ("x", 2), ("x", 3)),
                     (("y", 1), ("y", 2), ("y", 3)), count=3, cap=cap)
    assert report.difference_count == 3
    assert len(report.differences) == cap and report.details_truncated
    assert report.source_count == report.target_count == 3
    assert not report.source_partial and not report.target_partial


def test_digest_collision_does_not_bypass_cell_equality(monkeypatch):
    class Collision:
        def __init__(self, *args):
            pass
        def update(self, data):
            pass
        def digest(self):
            return b"\x00"*32
        def hexdigest(self):
            return "0"*64
    monkeypatch.setattr(c.hashlib, "sha256", Collision)
    report = compare((("x", 1),), (("y", 1),), count=1)
    assert report.source_sha256 == report.target_sha256
    assert report.result == "comparison_failed" and report.difference_count == 1


def test_iterator_failure_is_partial_and_other_side_can_finish():
    def broken():
        yield ("x", 1)
        raise RuntimeError("private-secret")
    report = compare(broken(), (("x", 1), ("y", 2)), count=2)
    assert report.source_partial and report.source_sha256 is None
    assert not report.target_partial and report.target_sha256 is not None
    assert report.source_count == 1 and report.target_count == 2
    assert report.error_code == "input_error"
    assert "private-secret" not in json.dumps(report.to_dict())


@pytest.mark.parametrize("callback", [lambda: True, lambda: "private-secret"])
def test_cancel_and_bad_callback_cannot_report_complete(callback):
    report = compare((), (), count=0, cancelled=callback)
    assert report.result == "comparison_failed"
    assert report.source_partial and report.target_partial
    assert report.source_sha256 is report.target_sha256 is None


def test_budget_failure_never_gets_full_digest():
    report = compare((("字", 1),), (("x", 1),), count=1,
                     limits=c.ValueLimits(max_field_bytes=2))
    assert report.error_code == "budget"
    assert report.source_sha256 is None and report.source_partial


def test_common_corruption_is_rejected_by_independent_golden():
    # Both hypothetical adapters wrongly change empty text to NULL.
    # Comparing their identical mistakes alone is not proof of source truth.
    report = compare(((None, 1),), ((None, 1),), count=1)
    assert report.result == "comparison_equal"
    corrupted = c.encode_cell(schema().columns[0], None, limits=c.ValueLimits())
    assert corrupted != bytes.fromhex("010000000000000000")
    assert compare((("", 1),), ((None, 1),), count=1).result == "comparison_failed"


@pytest.mark.parametrize("changes", [
    {"kind": "anything"}, {"reference": ""}, {"sha256": "secret"},
])
def test_evidence_metadata_validation(changes):
    m = api()
    with pytest.raises(c.ValueContractError):
        replace(m.ValueEvidence("synthetic", "fixture", "1"*64), **changes)


def test_bad_expected_counts_are_rejected():
    for count in (True, -1, 100001):
        with pytest.raises(c.ValueContractError):
            compare((), (), count=count)


def test_cancel_during_source_read_prevents_target_read():
    flag = False
    consumed = []
    def source():
        nonlocal flag
        flag = True
        yield ("x", 1)
    def target():
        consumed.append(True)
        yield ("x", 1)
    report = compare(source(), target(), count=1, cancelled=lambda: flag)
    assert consumed == []
    assert report.error_code == "cancelled"
    assert report.source_partial and report.target_partial
    assert report.source_sha256 is report.target_sha256 is None
