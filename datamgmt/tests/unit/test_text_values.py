"""Catch header pollution, mapping drift and lossy text-to-value bridging."""
from dataclasses import replace
import hashlib
import importlib
import importlib.util

import pytest

from xiangrugu_datamgmt.canonical import ValueColumn, ValueSchema, ValueLimits, ValueContractError
from xiangrugu_datamgmt.source_text import TextReadLimits
from xiangrugu_datamgmt.identity import source_object_id
from xiangrugu_datamgmt.naming import allocate_columns


def api():
    assert importlib.util.find_spec("xiangrugu_datamgmt.text_values"), "missing text-value bridge"
    return importlib.import_module("xiangrugu_datamgmt.text_values")


def schema():
    return ValueSchema("1"*64, (
        ValueColumn("2"*64, "mapped", "text", False),
        ValueColumn("derived:__src_rownum", "__src_rownum", "bigint", False),
    ))


def summarize(raw=b'h\n""\n', **changes):
    args = dict(schema=schema(), expected_header=("h",),
                expected_raw_sha256=hashlib.sha256(raw).hexdigest(),
                expected_raw_size=len(raw), expected_count=1,
                bom_as_signature=False, backslash_escape=False,
                limits=ValueLimits(), read_limits=TextReadLimits())
    args.update(changes)
    return api().summarize_text_values(raw, **args)


def test_header_excluded_empty_preserved_and_rownum_starts_at_one():
    raw = 'h\n""\n␀\n'.encode()
    result = summarize(raw, expected_count=2)
    # Independent literal schema and cell/frame vectors, not production builders.
    cols = ('[["' + "2"*64 + '","mapped","text",false],'
            '["derived:__src_rownum","__src_rownum","bigint",false]]').encode()
    header = b"XRGVALUE\x00\x01" + bytes.fromhex("1"*64) + hashlib.sha256(cols).digest()
    row1 = bytes.fromhex("52 00000002 0000000000000012 01 0000000000000000 02 0000000000000001")
    row2 = bytes.fromhex("52 00000002 0000000000000015 01 0000000000000003 e29080 02 0000000000000002")
    reference = header + row1 + row2 + bytes.fromhex("45 0000000000000002")
    assert result.row_count == 2 and result.field_count == 4
    assert result.stream_bytes == len(reference)
    assert result.sha256 == hashlib.sha256(reference).hexdigest()


def test_header_only_is_valid_empty_object():
    result = summarize(b"h\n", expected_count=0)
    assert result.row_count == result.field_count == 0
    assert result.stream_bytes == 83


def test_duplicate_business_rows_are_retained():
    result = summarize(b"h\nx\nx\n", expected_count=2)
    assert result.row_count == 2 and result.field_count == 4


def test_explicit_bom_and_escape_policy():
    raw = b'\xef\xbb\xbfh\n"a\\"b"\n'
    result = summarize(raw, bom_as_signature=True, backslash_escape=True)
    assert result.row_count == 1
    with pytest.raises(ValueContractError):
        summarize(raw, bom_as_signature=False, backslash_escape=True)
    with pytest.raises(ValueContractError):
        summarize(raw, bom_as_signature=True, backslash_escape=False)


@pytest.mark.parametrize("changes,code", [
    ({"expected_header": ("wrong",)}, "structure"),
    ({"expected_header": ["h"]}, "structure"),
    ({"expected_header": ("h", "extra")}, "structure"),
    ({"expected_raw_sha256": "0"*64}, "source_bytes"),
    ({"expected_raw_sha256": "bad"}, "structure"),
    ({"expected_raw_size": 999}, "source_bytes"),
    ({"expected_raw_size": True}, "structure"),
    ({"expected_count": True}, "count"),
    ({"expected_count": 0}, "count"),
    ({"expected_count": -1}, "count"),
    ({"expected_count": 100001}, "count"),
    ({"bom_as_signature": "yes"}, "structure"),
    ({"backslash_escape": 1}, "structure"),
    ({"limits": ValueLimits(max_stream_bytes=84)}, "budget"),
    ({"read_limits": TextReadLimits(max_bytes=2)}, "budget"),
])
def test_rejects_drift_without_successful_summary(changes, code):
    with pytest.raises(ValueContractError) as error:
        summarize(**changes)
    assert error.value.code == code


@pytest.mark.parametrize("raw", [
    b"h\nprivate-secret\x00\n", b"h\n\xff\n", b'h\n"private-secret\n',
    b"h\nprivate-secret\textra\n", b"",
])
def test_malformed_source_error_is_sanitized(raw):
    with pytest.raises(ValueContractError) as error:
        summarize(raw)
    assert "private-secret" not in str(error.value)
    assert error.value.__cause__ is None


def test_text_projection_rejects_nontext_business_columns():
    changed = replace(schema(), columns=(
        ValueColumn("2"*64, "mapped", "bigint", False), schema().columns[-1]))
    with pytest.raises(ValueContractError, match="structure"):
        summarize(schema=changed)


def test_nonbytes_source_rejected():
    with pytest.raises(ValueContractError, match="structure"):
        api().summarize_text_values("private-secret", schema=schema(), expected_header=("h",),
            expected_raw_sha256="1"*64, expected_raw_size=14, expected_count=1,
            bom_as_signature=False, backslash_escape=False)


def projection():
    identity = source_object_id(relative_path="fixture.tab", archive_chain=[],
                                object_name="fixture.tab", carrier="tsv")
    mapped = allocate_columns(["h"], object_id=identity)[0]
    decision = dict(rule_id="test", relative_path="fixture.tab", archive_chain=[],
                    archive_ordinals=[], raw_sha256="3"*64, raw_size=6,
                    bom_as_signature=False, backslash_escape=False, codec="utf-8")
    obj = dict(rule_id="test", source_object_id=identity, object_name="fixture.tab",
               carrier="tsv", reading_decision_rule_id="test",
               selector=dict(relative_path="fixture.tab", archive_chain=[], archive_ordinals=[]),
               raw_expected=dict(sha256="3"*64, size=6, kind="file"),
               source_columns=[dict(column_id=mapped.identity, target_name=mapped.target,
                   original_name="h", source_column_ordinal=1, target_type="text", nullable=False,
                   type_approved=True, nullable_approved=True, column_mapping_approved=True,
                   encoding=dict(codec="utf-8", errors="strict", column="h", object_name="fixture.tab"))],
               source_column_types_approved=True, source_column_nullable_approved=True,
               source_column_mapping_approved=True, derived_rownum_mapping_approved=True,
               derived_columns=[dict(target_name="__src_rownum", target_type="bigint",
                    mapping_approved=True, origin="one-based data record order excluding header",
                    range=[1, 1])], source_record_count=1)
    return obj, decision


def test_approved_projection_binds_source_order_identity_and_mapping():
    obj, decision = projection()
    value_schema, header = api().schema_from_approved(obj, decision)
    assert header == ("h",)
    assert value_schema.source_object_id == obj["source_object_id"]
    assert value_schema.columns[0].target_name == "h"
    assert value_schema.columns[-1].column_key == "derived:__src_rownum"


@pytest.mark.parametrize("field,value", [
    ("source_object_id", "0"*64), ("reading_decision_rule_id", "other"),
    ("source_column_types_approved", False), ("source_column_mapping_approved", 1),
    ("derived_rownum_mapping_approved", False), ("source_record_count", True),
])
def test_projection_top_level_drift_rejected(field, value):
    obj, decision = projection()
    obj[field] = value
    with pytest.raises(ValueContractError, match="structure"):
        api().schema_from_approved(obj, decision)


@pytest.mark.parametrize("field,value", [
    ("column_id", "0"*64), ("source_column_ordinal", 2), ("source_column_ordinal", True),
    ("target_name", "other"), ("target_type", "bigint"), ("nullable", True),
    ("type_approved", False), ("original_name", "other"),
])
def test_projection_column_drift_rejected(field, value):
    obj, decision = projection()
    obj["source_columns"][0][field] = value
    with pytest.raises(ValueContractError, match="structure"):
        api().schema_from_approved(obj, decision)


@pytest.mark.parametrize("field,value", [
    ("raw_sha256", "0"*64), ("relative_path", "../fixture.tab"),
    ("bom_as_signature", True), ("backslash_escape", "yes"), ("raw_size", True),
])
def test_reading_decision_drift_rejected(field, value):
    obj, decision = projection()
    decision[field] = value
    with pytest.raises(ValueContractError, match="structure"):
        api().schema_from_approved(obj, decision)


def test_file_bom_signature_does_not_change_utf8_column_encoding():
    obj, decision = projection()
    decision.update(codec="utf-8-sig", bom_as_signature=True)
    value_schema, header = api().schema_from_approved(obj, decision)
    assert header == ("h",)
    assert value_schema.columns[0].pg_type == "text"


def test_file_signature_codec_cannot_be_applied_to_each_column():
    obj, decision = projection()
    decision.update(codec="utf-8-sig", bom_as_signature=True)
    obj["source_columns"][0]["encoding"]["codec"] = "utf-8-sig"
    with pytest.raises(ValueContractError, match="structure"):
        api().schema_from_approved(obj, decision)
