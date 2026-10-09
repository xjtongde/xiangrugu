"""Hand-derived bytes catch loss, implicit coercion and ambiguous framing."""
import importlib
import json
import hashlib
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.canonical")
    assert spec is not None, "Strict value canonicalizer is not implemented"
    return importlib.import_module(spec.name)


def column(kind="text", nullable=True):
    return api().ValueColumn("a" * 64, "value", kind, nullable)


def schema():
    m = api()
    return m.ValueSchema("b" * 64, (
        column(), m.ValueColumn("derived:__src_rownum", "__src_rownum", "bigint", False),
    ))


def cell(value, kind="text", nullable=True, **limits):
    m = api()
    return m.encode_cell(column(kind, nullable), value, limits=m.ValueLimits(**limits))


def test_null_empty_text_and_literal_null_symbol_have_distinct_bytes():
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/value_v1_golden.json").read_text())
    results = [cell(None).hex(), cell("").hex(), cell("␀").hex()]
    assert results == [fixture["null"], fixture["empty"], fixture["null_symbol"]]
    assert len(set(results)) == 3


@pytest.mark.parametrize("value,want", [
    (1, "020000000000000001"), (-1, "02ffffffffffffffff"),
    (-(2**63), "028000000000000000"), (2**63 - 1, "027fffffffffffffff"),
])
def test_bigint_golden_and_bounds(value, want):
    assert cell(value, "bigint").hex() == want


@pytest.mark.parametrize("value", [True, 1.0, Decimal("1"), "1", -(2**63)-1, 2**63])
def test_bigint_rejects_coercion_and_overflow(value):
    with pytest.raises(api().ValueContractError):
        cell(value, "bigint")


@pytest.mark.parametrize("value", [3, b"abc", False])
def test_text_rejects_non_strings(value):
    with pytest.raises(api().ValueContractError):
        cell(value)


def test_nonnullable_rejects_null():
    with pytest.raises(api().ValueContractError):
        cell(None, nullable=False)


@pytest.mark.parametrize("value,hex_payload", [
    (" \t\n\r\"\x00", "20090a0d2200"), ("é", "c3a9"), ("e\u0301", "65cc81"),
    ("\ufeff", "efbbbf"), ("001", "303031"),
])
def test_text_preserves_codepoints_and_controls(value, hex_payload):
    payload = bytes.fromhex(hex_payload)
    assert cell(value) == b"\x01" + len(payload).to_bytes(8, "big") + payload


def test_field_budget_measures_utf8_bytes_and_errors_hide_values():
    assert cell("字", max_field_bytes=3) == b"\x01" + bytes.fromhex("0000000000000003e5ad97")
    for value in ("字", "private-secret"):
        with pytest.raises(api().ValueContractError) as error:
            cell(value, max_field_bytes=2)
        assert error.value.code == "budget"
        assert value not in str(error.value)


def test_invalid_unicode_does_not_get_replaced():
    with pytest.raises(api().ValueContractError) as error:
        cell("\ud800")
    assert error.value.code == "unsupported_type"


@pytest.mark.parametrize("changes", [
    {"column_key": "bad"}, {"target_name": ""}, {"target_name": "a"*64},
    {"target_name": "bad\x00name"}, {"pg_type": "numeric"}, {"nullable": 0},
])
def test_column_contract_rejects_invalid_metadata(changes):
    with pytest.raises(api().ValueContractError):
        replace(column(), **changes)


@pytest.mark.parametrize("changes", [
    {"source_object_id": "B"*64}, {"format_version": True}, {"format_version": 2},
    {"columns": ()}, {"columns": []},
])
def test_schema_rejects_invalid_identity_version_and_columns(changes):
    with pytest.raises(api().ValueContractError):
        replace(schema(), **changes)


def test_schema_rejects_duplicate_names_and_misplaced_rownum():
    s = schema()
    for columns in ((s.columns[0], s.columns[0], s.columns[1]),
                    tuple(reversed(s.columns)), (s.columns[0],),
                    (replace(s.columns[0], target_name="__src_rownum"), s.columns[1])):
        with pytest.raises(api().ValueContractError):
            replace(s, columns=columns)


@pytest.mark.parametrize("changes", [
    {"max_rows": True}, {"max_rows": 0}, {"max_columns": -1}, {"max_field_bytes": 1.0},
    {"max_row_bytes": 0}, {"max_stream_bytes": "100"}, {"max_differences": -1},
])
def test_limits_reject_invalid_values(changes):
    with pytest.raises(api().ValueContractError):
        api().ValueLimits(**changes)


def test_limits_allow_zero_detail_cap_and_models_are_frozen():
    assert api().ValueLimits(max_differences=0).max_differences == 0
    with pytest.raises(AttributeError):
        column().nullable = False


def reference_header():
    raw = ('[["' + "a"*64 + '","value","text",true],'
           '["derived:__src_rownum","__src_rownum","bigint",false]]').encode("ascii")
    return raw, b"XRGVALUE\x00\x01" + bytes.fromhex("b"*64) + hashlib.sha256(raw).digest()


def test_schema_header_row_and_empty_stream_match_hand_derived_fixture():
    m = api()
    raw, head = reference_header()
    assert m.schema_bytes(schema()) == raw
    assert m.header_bytes(schema()) == head
    trailer = b"\x45" + b"\x00"*8
    assert m.trailer_bytes(0) == trailer
    empty = m.summarize_rows(schema(), iter(()), limits=m.ValueLimits())
    assert empty.sha256 == hashlib.sha256(head + trailer).hexdigest()
    assert (empty.row_count, empty.field_count, empty.stream_bytes) == (0, 0, 83)
    frame = bytes.fromhex("52 00000002 000000000000000a 00 02 0000000000000001")
    row = m.encode_row(schema(), (None, 1), expected_rownum=1, limits=m.ValueLimits())
    assert row.frame == frame
    assert row.cells == (b"\x00", bytes.fromhex("020000000000000001"))
    whole = m.summarize_rows(schema(), iter(((None, 1),)), limits=m.ValueLimits())
    assert whole.sha256 == hashlib.sha256(head + frame + b"\x45" + (1).to_bytes(8, "big")).hexdigest()
    assert (whole.row_count, whole.field_count, whole.stream_bytes) == (1, 2, 106)


def test_delimiter_ambiguity_and_metadata_are_not_equal():
    m = api()
    s = schema()
    s = replace(s, columns=(s.columns[0], m.ValueColumn("c"*64, "other", "text", True), s.columns[-1]))
    first = m.encode_row(s, ("ab", "c", 1), expected_rownum=1, limits=m.ValueLimits())
    second = m.encode_row(s, ("a", "bc", 1), expected_rownum=1, limits=m.ValueLimits())
    assert first.frame != second.frame
    assert m.header_bytes(replace(s, source_object_id="d"*64)) != m.header_bytes(s)
    for changed in (replace(s.columns[0], nullable=False),
                    replace(s.columns[0], target_name="renamed"),
                    replace(s.columns[0], pg_type="bigint")):
        assert m.schema_bytes(replace(s, columns=(changed, *s.columns[1:]))) != m.schema_bytes(s)
    assert m.schema_bytes(replace(s, columns=(s.columns[1], s.columns[0], s.columns[-1]))) != m.schema_bytes(s)


@pytest.mark.parametrize("rows", [
    (("x", 2),), (("x", True),), (("x", 1), ("x", 1)),
    (("x", 1), ("x", 10)), (("x",),), (("x", 1, 2),), (["x", 1],),
])
def test_stream_rejects_wrong_width_and_rownum(rows):
    with pytest.raises(api().ValueContractError):
        api().summarize_rows(schema(), iter(rows), limits=api().ValueLimits())


def test_duplicate_business_rows_keep_distinct_ordinals_and_single_consumption():
    def rows():
        yield ("x", 1)
        yield ("x", 2)
    summary = api().summarize_rows(schema(), rows(), limits=api().ValueLimits())
    assert summary.row_count == 2
    assert summary.field_count == 4


def test_broken_iterator_cannot_get_a_prefix_digest_and_hides_exception():
    def rows():
        yield ("x", 1)
        raise RuntimeError("private-secret")
    with pytest.raises(api().ValueContractError) as error:
        api().summarize_rows(schema(), rows(), limits=api().ValueLimits())
    assert error.value.code == "input_error"
    assert "private-secret" not in str(error.value)
    assert error.value.__cause__ is None


@pytest.mark.parametrize("limits,rows", [
    ({"max_columns": 1}, ()), ({"max_rows": 1}, (("x", 1), ("x", 2))),
    ({"max_field_bytes": 2}, (("字", 1),)), ({"max_row_bytes": 9}, ((None, 1),)),
    ({"max_stream_bytes": 82}, ()), ({"max_stream_bytes": 105}, ((None, 1),)),
])
def test_stream_budgets_include_framing_and_trailer(limits, rows):
    with pytest.raises(api().ValueContractError) as error:
        api().summarize_rows(schema(), iter(rows), limits=api().ValueLimits(**limits))
    assert error.value.code == "budget"


def test_exact_stream_and_row_budget_boundary_passes():
    assert api().summarize_rows(schema(), iter(((None, 1),)), limits=api().ValueLimits(
        max_row_bytes=10, max_stream_bytes=106)).stream_bytes == 106


@pytest.mark.parametrize("callback", [lambda: True, lambda: "yes"])
def test_cancelled_or_invalid_callback_never_returns_complete_digest(callback):
    with pytest.raises(api().ValueContractError):
        api().summarize_rows(schema(), iter(()), limits=api().ValueLimits(), cancelled=callback)


def test_callback_error_is_sanitized_and_final_cancel_is_checked():
    def bad():
        raise RuntimeError("private-secret")
    with pytest.raises(api().ValueContractError) as error:
        api().summarize_rows(schema(), iter(()), limits=api().ValueLimits(), cancelled=bad)
    assert "private-secret" not in str(error.value)
    calls = iter((False, True))
    with pytest.raises(api().ValueContractError) as error:
        api().summarize_rows(schema(), iter(()), limits=api().ValueLimits(), cancelled=lambda: next(calls))
    assert error.value.code == "cancelled"


def test_stream_state_never_succeeds_after_finish_or_failure():
    m = api()
    state = m.ValueStreamState(schema(), m.ValueLimits())
    state.accept(("x", 1))
    assert state.finish().row_count == 1
    for action in (state.finish, lambda: state.accept(("x", 2))):
        with pytest.raises(m.ValueContractError):
            action()
    state = m.ValueStreamState(schema(), m.ValueLimits())
    with pytest.raises(m.ValueContractError):
        state.accept(("x", 2))
    with pytest.raises(m.ValueContractError):
        state.finish()


def test_column_budget_is_checked_before_header_allocation(monkeypatch):
    m = api()
    def forbidden(schema):
        pytest.fail("header allocated before column budget check")
    monkeypatch.setattr(m, "header_bytes", forbidden)
    with pytest.raises(m.ValueContractError, match="budget"):
        m.ValueStreamState(schema(), m.ValueLimits(max_columns=1))


@pytest.mark.parametrize("limits", [
    {"max_row_bytes": 10}, {"max_stream_bytes": 84},
])
def test_remaining_budget_rejects_large_cell_before_encoding(monkeypatch, limits):
    m = api()
    original = m.encode_cell
    def guarded(column, value, **kwargs):
        assert kwargs.get("max_encoded_bytes", 1048576) < 1048576
        return original(column, value, **kwargs)
    monkeypatch.setattr(m, "encode_cell", guarded)
    with pytest.raises(m.ValueContractError, match="budget"):
        m.summarize_rows(schema(), iter((("x" * 1048576, 1),)),
                         limits=m.ValueLimits(**limits))
