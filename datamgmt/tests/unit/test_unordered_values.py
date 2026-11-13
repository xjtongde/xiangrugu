"""Catch coercion, ambiguous boundaries and changed binary representations."""
import importlib
import json
import math
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.unordered_values")
    assert spec is not None, "Strict unordered values are not implemented"
    return importlib.import_module(spec.name)


def column(m, kind="text", null=True):
    return m.UnorderedColumn(0, "a" * 64, kind, null)


def schema(m, kind="text", null=True):
    return m.UnorderedSchema("b" * 64, (column(m, kind, null),))


def golden():
    return json.loads((Path(__file__).parents[1] / "fixtures/unordered_v1_golden.json").read_text())


def test_null_empty_and_literal_symbol_golden():
    m = api()
    got = [m.encode_unordered_cell(column(m), v, limits=m.UnorderedLimits()).hex()
           for v in (None, "", "␀")]
    assert got == [golden()["cells"][key] for key in ("null", "empty", "symbol")]
    assert len(set(got)) == 3
    with pytest.raises(m.UnorderedValueError):
        m.encode_unordered_cell(column(m, null=False), None, limits=m.UnorderedLimits())


def test_binary64_exact_bits_without_numeric_coercion():
    m = api()
    c = column(m, "double precision")
    enc = lambda v: m.encode_unordered_cell(c, v, limits=m.UnorderedLimits())
    for key, value in [("one_float", 1.0), ("positive_zero", 0.0),
                       ("negative_zero", -0.0), ("subnormal", float.fromhex("0x0.0000000000001p-1022"))]:
        assert enc(value).hex() == golden()["cells"][key]
    assert enc(1.0) != enc(math.nextafter(1.0, 2.0))
    assert len(enc(float.fromhex("0x1.fffffffffffffp+1023"))) == 9


@pytest.mark.parametrize("value", [True, 1, "1.0", Decimal("1.0"), math.nan, math.inf, -math.inf])
def test_bad_float_inputs_fail_instead_of_coercing(value):
    m = api()
    with pytest.raises(m.UnorderedValueError):
        m.encode_unordered_cell(column(m, "double precision"), value, limits=m.UnorderedLimits())


@pytest.mark.parametrize("value", [True, 1.0, "1", Decimal(1), -(2**63)-1, 2**63])
def test_bad_bigint_inputs_fail_instead_of_coercing(value):
    m = api()
    with pytest.raises(m.UnorderedValueError):
        m.encode_unordered_cell(column(m, "bigint"), value, limits=m.UnorderedLimits())


def test_bigint_text_and_schema_strictness():
    m = api()
    limits = m.UnorderedLimits()
    assert m.encode_unordered_cell(column(m, "bigint"), -1, limits=limits).hex() == golden()["cells"]["minus_one"]
    assert m.encode_unordered_cell(column(m, "bigint"), -(2**63), limits=limits).hex() == "028000000000000000"
    assert m.encode_unordered_cell(column(m, "bigint"), 2**63-1, limits=limits).hex() == "027fffffffffffffff"
    text = " \t\n\r\x00\""
    assert m.encode_unordered_cell(column(m), text, limits=limits) == b"\x01" + (6).to_bytes(8, "big") + b' \t\n\r\x00"'
    assert m.encode_unordered_cell(column(m), "é", limits=limits) != m.encode_unordered_cell(column(m), "e\u0301", limits=limits)
    for v in (1, b"secret", "\ud800"):
        with pytest.raises(m.UnorderedValueError):
            m.encode_unordered_cell(column(m), v, limits=limits)


@pytest.mark.parametrize("change", [{"source_ordinal": True}, {"source_ordinal": -1},
                                   {"column_key": "bad"}, {"pg_type": "numeric"},
                                   {"allow_null_value": 1}])
def test_invalid_columns_do_not_enter_stream(change):
    m = api()
    with pytest.raises(m.UnorderedValueError):
        replace(column(m), **change)


def test_schema_rejects_duplicate_keys_discontinuous_order_and_versions():
    m = api()
    for cols in [(column(m), column(m)), (replace(column(m), source_ordinal=1),), ()]:
        with pytest.raises(m.UnorderedValueError):
            m.UnorderedSchema("b"*64, cols)
    for version in (True, 0, 2):
        with pytest.raises(m.UnorderedValueError):
            replace(schema(m), format_version=version)


def test_hand_constructed_row_header_and_empty_stream():
    m = api()
    s = schema(m)
    descriptor = ('[[0,"' + "a"*64 + '","text",true]]').encode("ascii")
    assert m.schema_bytes(s) == descriptor
    import hashlib
    header = b"XRGSET\x00\x01" + bytes.fromhex("b"*64) + hashlib.sha256(descriptor).digest()
    assert m.header_bytes(s) == header and len(header) == 72
    assert m.trailer_bytes(0) == b"E" + b"\x00"*8
    frame = bytes.fromhex(golden()["empty_text_row"])
    assert m.encode_unordered_row(s, ("",), limits=m.UnorderedLimits()) == frame
    m.validate_unordered_frame(s, frame, limits=m.UnorderedLimits())
    for count in (-1, True, 2**64):
        with pytest.raises(m.UnorderedValueError):
            m.trailer_bytes(count)


@pytest.mark.parametrize("frame", [b"", b"R"+b"\x00"*12,
    bytes.fromhex("5200000001000000000000000104"),
    bytes.fromhex("5200000001000000000000000a010000000000000001ff"),
    bytes.fromhex("52000000010000000000000009010000000000000000ff")])
def test_malformed_frames_fail_before_comparison(frame):
    m = api()
    with pytest.raises(m.UnorderedValueError):
        m.validate_unordered_frame(schema(m), frame, limits=m.UnorderedLimits())


def test_value_width_and_byte_limits_are_checked():
    m = api()
    s = schema(m)
    limits = m.UnorderedLimits(max_field_bytes=3)
    assert len(m.encode_unordered_cell(column(m), "中", limits=limits)) == 12
    for vals in [("中a",), (), ("a", "b"), ["a"]]:
        with pytest.raises(m.UnorderedValueError):
            m.encode_unordered_row(s, vals, limits=limits)
    with pytest.raises(m.UnorderedValueError):
        m.encode_unordered_row(s, ("",), limits=replace(limits, max_row_bytes=8))


@pytest.mark.parametrize("kwargs", [{"max_rows": True}, {"max_rows": 0},
    {"merge_fan_in": 1}, {"chunk_bytes": 13}, {"workers": 2}, {"max_seconds": 0}])
def test_invalid_limits_cannot_silently_expand_resources(kwargs):
    m = api()
    with pytest.raises(m.UnorderedValueError):
        m.UnorderedLimits(**kwargs)
