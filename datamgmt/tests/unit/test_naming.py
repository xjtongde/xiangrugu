import pytest

from xiangrugu_datamgmt.naming import NameInput, allocate_tables, allocate_columns, slug, quote_identifier, validate_schema


def test_fixed_slug_rules():
    assert slug("ＡBC_中") == "abc_u5f__u4e2d_"
    assert slug("123") == "t_123"
    assert slug("") == "t_"


def test_name_maps_are_reversible_and_scan_order_independent():
    entries = [NameInput(dataset="Data", original="People", identity="a" * 64), NameInput(dataset="Data", original="people", identity="b" * 64)]
    first = allocate_tables(entries)
    second = allocate_tables(list(reversed(entries)))
    assert {item.identity: item.target for item in first} == {item.identity: item.target for item in second}
    assert first[0].target == "data__people__aaaaaaaa"
    assert first[1].target == "data__people__bbbbbbbb"
    assert [item.original for item in first] == ["People", "people"]


def test_long_names_and_unicode_normalization_collision():
    entries = [NameInput(dataset="数据" * 20, original="Ａ", identity="a" * 64), NameInput(dataset="数据" * 20, original="A", identity="b" * 64)]
    mapped = allocate_tables(entries)
    assert len({item.target for item in mapped}) == 2
    assert all(len(item.target.encode("utf-8")) <= 63 for item in mapped)
    assert mapped[0].original == "Ａ"


def test_short_hash_collision_is_rejected_not_silently_merged():
    entries = [NameInput(dataset="d", original="A", identity="a" * 64), NameInput(dataset="d", original="a", identity="a" * 8 + "b" * 56)]
    with pytest.raises(ValueError):
        allocate_tables(entries)


def test_duplicate_columns_follow_source_ordinals():
    result = allocate_columns(["Name", "name", "Name", "select"], object_id="a" * 64)
    assert [item.target for item in result] == ["name__c1", "name__c2", "name__c3", "select"]
    assert [item.original for item in result] == ["Name", "name", "Name", "select"]
    assert quote_identifier(result[-1].target) == '"select"'


def test_identifier_quoting_escapes_instead_of_interpolating_sql():
    assert quote_identifier('a"b') == '"a""b"'
    with pytest.raises(ValueError):
        quote_identifier("x\x00")


def test_schema_is_explicit_not_public():
    assert validate_schema("audit") == "audit"
    with pytest.raises(ValueError):
        validate_schema("public")
