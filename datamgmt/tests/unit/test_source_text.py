"""Hand-derived source values; no source layouts or database dependencies."""
import importlib

import pytest


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.source_text")
    assert spec is not None, "Independent source text reader is not implemented"
    return importlib.import_module(spec.name)


def read(raw, *, bom=False, escape=False, **limits):
    module = api()
    return module.read_utf8_tsv(
        raw, bom_as_signature=bom, backslash_escape=escape,
        limits=module.TextReadLimits(**limits),
    )


def test_preserves_empty_values_whitespace_leading_zeros_and_duplicate_rows():
    raw = 'a\tb\tc\n001\t\t 文 \n001\t\t 文 \n'.encode()
    assert read(raw) == (("a", "b", "c"), ("001", "", " 文 "), ("001", "", " 文 "))


@pytest.mark.parametrize("bom,want", [(False, "\ufeffid"), (True, "id")])
def test_bom_interpretation_is_explicit_and_interior_bom_is_preserved(bom, want):
    raw = b'\xef\xbb\xbfid\n' + '\ufeff字'.encode() + b'\n'
    assert read(raw, bom=bom) == ((want,), ("\ufeff字",))


def test_preserves_empty_and_duplicate_header_names_by_position():
    assert read(b'a\ta\t\n1\t2\t\n') == (("a", "a", ""), ("1", "2", ""))


def test_quotes_escape_tabs_newlines_and_doubled_quotes_without_trimming():
    raw = b'a\tb\n"x\ty"\t"line1\nline2 ""quoted"""\n'
    assert read(raw) == (("a", "b"), ("x\ty", 'line1\nline2 "quoted"'))


def test_backslash_quote_is_only_enabled_by_explicit_policy():
    raw = b'a\n"say \\"hi\\""\n'
    assert read(raw, escape=True) == (("a",), ('say "hi"',))
    with pytest.raises(api().TextReadError) as caught:
        read(raw, escape=False)
    assert caught.value.code == "after_quote"


def test_disabled_backslashes_are_literal_and_unquoted_quotes_are_literal():
    assert read(b'a\nC:\\data\\file "x"\n') == (("a",), ('C:\\data\\file "x"',))


def test_enabled_backslash_retains_escaped_unicode_and_newline():
    assert read('a\n"\\字\\\n尾"\n'.encode(), escape=True) == (("a",), ("字\n尾",))


@pytest.mark.parametrize("raw,want", [
    (b'a\tb\n1\t', (("a", "b"), ("1", ""))),
    (b'a\n"x"', (("a",), ("x",))),
    (b'a\n', (("a",),)),
])
def test_eof_retains_last_field_without_inventing_a_trailing_record(raw, want):
    assert read(raw) == want


@pytest.mark.parametrize("raw,code,offset", [
    (b'a\n"bad', "unclosed_quote", 6),
    (b'a\n"x" extra\n', "after_quote", 5),
    (b'a\n"x\\', "dangling_escape", 4),
    (b'a\n\x00\n', "nul_byte", 2),
    (b'a\r\n', "unsupported_cr", 1),
    (b'a\n\xff\n', "invalid_utf8", 2),
])
def test_rejects_bad_syntax_with_original_byte_offset(raw, code, offset):
    with pytest.raises(api().TextReadError) as caught:
        read(raw, escape=True)
    assert caught.value.code == code
    assert caught.value.byte_offset == offset


@pytest.mark.parametrize("raw", [b'a\tb\n1\n', b'a\n1\t2\n', b'a\n\n'])
def test_rejects_missing_extra_and_blank_records_without_padding_or_skipping(raw):
    with pytest.raises(api().TextReadError) as caught:
        read(raw)
    assert caught.value.code == "record_width"
    assert caught.value.record_ordinal == 2


def test_rejects_empty_input_instead_of_claiming_an_empty_table():
    with pytest.raises(api().TextReadError) as caught:
        read(b'')
    assert caught.value.code == "missing_header"


@pytest.mark.parametrize("raw,limits,code", [
    (b'a\n', {"max_bytes": 1}, "byte_limit"),
    (b'a\n1\n', {"max_records": 1}, "record_limit"),
    (b'a\tb\n', {"max_columns": 1}, "column_limit"),
    ('a\n字\n'.encode(), {"max_field_bytes": 2}, "field_byte_limit"),
])
def test_resource_limits_fail_before_a_successful_result(raw, limits, code):
    with pytest.raises(api().TextReadError) as caught:
        read(raw, **limits)
    assert caught.value.code == code


@pytest.mark.parametrize("name,value", [("max_bytes", 0), ("max_records", -1),
                                         ("max_columns", True), ("max_field_bytes", 1.5)])
def test_rejects_invalid_resource_budgets(name, value):
    with pytest.raises(ValueError):
        api().TextReadLimits(**{name: value})


def test_size_limits_accept_exact_boundaries():
    assert read(b'a\n1\n', max_bytes=4, max_records=2, max_columns=1,
                max_field_bytes=1) == (("a",), ("1",))


def test_width_error_reports_source_column_and_record_position():
    with pytest.raises(api().TextReadError) as caught:
        read(b'a\tb\n1\n')
    assert caught.value.record_ordinal == 2
    assert caught.value.column_ordinal == 1
