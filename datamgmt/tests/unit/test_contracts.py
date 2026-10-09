import json
from pathlib import Path

import pytest


def validate(document):
    from xiangrugu_datamgmt.contracts import ReleaseContract
    return ReleaseContract.model_validate(document)


def test_required_source_contract_fields_and_frozen_values(contract_doc):
    contract = validate(contract_doc)
    assert contract.rules[0].encodings[0].column == "name"
    assert contract.rules[0].targets[0].expected_count == 1
    with pytest.raises(ValueError):
        contract.rules[0].reason = "changed"
    assert len(contract.sha256) == 64


@pytest.mark.parametrize("field", ["source_version", "inventory_sha256", "rules", "release_id"])
def test_missing_release_provenance_is_rejected(contract_doc, field):
    del contract_doc[field]
    with pytest.raises(ValueError):
        validate(contract_doc)


@pytest.mark.parametrize("path", ["*.csv", "a?b", "../escape", "/absolute", "a\\b"])
def test_unsupported_wildcards_and_noncanonical_selectors_are_rejected(contract_doc, path):
    contract_doc["rules"][0]["selector"]["relative_path"] = path
    with pytest.raises(ValueError):
        validate(contract_doc)


@pytest.mark.parametrize("path,chain,ordinals", [
    ("data[1].csv", [], []),
    ("fixture.zip", ["book.xlsx", "[Content_Types].xml"], [0, 0]),
])
def test_literal_bracket_names_roundtrip_without_renaming(contract_doc, path, chain, ordinals):
    contract_doc["rules"][0]["selector"] = {
        "relative_path": path, "archive_chain": chain, "archive_ordinals": ordinals,
    }
    contract = validate(contract_doc)
    roundtrip = validate(json.loads(contract.canonical_bytes()))
    selector = roundtrip.rules[0].selector
    assert selector.location == (path, tuple(chain), tuple(ordinals))


@pytest.mark.parametrize("disposition", ["ignore", "reference", "quarantine", "reject"])
def test_unapproved_dispositions_have_no_fallback(contract_doc, disposition):
    contract_doc["rules"][0]["disposition"] = disposition
    with pytest.raises(ValueError):
        validate(contract_doc)


@pytest.mark.parametrize("reason", ["", "   ", "\n"])
def test_every_disposition_requires_a_real_reason(contract_doc, reason):
    contract_doc["rules"][1]["reason"] = reason
    with pytest.raises(ValueError):
        validate(contract_doc)


@pytest.mark.parametrize("mutation", ["empty", "duplicate_id", "unknown_field", "wrong_version", "bad_date", "bool_count", "lossy_encoding", "unknown_codec", "missing_import_target", "public_target", "missing_file_hash"])
def test_invalid_contracts_fail_closed(contract_doc, mutation):
    if mutation == "empty": contract_doc["rules"] = []
    elif mutation == "duplicate_id": contract_doc["rules"][1]["rule_id"] = "data"
    elif mutation == "unknown_field": contract_doc["ignore_unknown"] = True
    elif mutation == "wrong_version": contract_doc["version"] = 2
    elif mutation == "bad_date": contract_doc["release_id"] = "2026-02-30-invalid"
    elif mutation == "bool_count": contract_doc["rules"][0]["targets"][0]["expected_count"] = True
    elif mutation == "lossy_encoding": contract_doc["rules"][0]["encodings"][0]["errors"] = "replace"
    elif mutation == "unknown_codec": contract_doc["rules"][0]["encodings"][0]["codec"] = "not-a-codec"
    elif mutation == "missing_import_target": contract_doc["rules"][0]["targets"] = []
    elif mutation == "public_target": contract_doc["rules"][0]["targets"][0]["schema"] = "public"
    elif mutation == "missing_file_hash": contract_doc["rules"][0]["expected"]["sha256"] = None
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_frozen_contract_requires_review_and_complete_object_expectations(contract_doc):
    contract_doc["status"] = "frozen"
    with pytest.raises(ValueError):
        validate(contract_doc)
    contract_doc["review"] = {"approved_by": "fixture-only", "approved_at": "2026-10-07T00:00:00Z", "approval_ref": "synthetic-not-human-authority"}
    assert validate(contract_doc).status == "frozen"
    contract_doc["rules"][0]["targets"][0]["expected_count"] = None
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_rule_order_does_not_change_contract_digest(contract_doc):
    first = validate(contract_doc)
    contract_doc["rules"].reverse()
    second = validate(contract_doc)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.sha256 == second.sha256


def test_yaml_duplicate_keys_and_unsafe_tags_are_rejected(tmp_path):
    from xiangrugu_datamgmt.contracts import load_contract
    for text in ["version: 1\nversion: 1\n", "!!python/object/apply:os.system ['false']"]:
        path = tmp_path / "contract.yaml"
        path.write_text(text)
        with pytest.raises(ValueError):
            load_contract(path)


def test_json_duplicate_keys_are_rejected(tmp_path):
    from xiangrugu_datamgmt.contracts import load_contract
    path = tmp_path / "contract.json"
    path.write_text('{"version":1,"version":1}')
    with pytest.raises(ValueError):
        load_contract(path)


def test_yaml_roundtrip_preserves_original_names(contract_doc, tmp_path):
    import yaml
    from xiangrugu_datamgmt.contracts import load_contract
    contract_doc["rules"][0]["selector"]["relative_path"] = "数据 é.csv"
    path = tmp_path / "contract.yaml"
    path.write_text(yaml.safe_dump(contract_doc, allow_unicode=True), encoding="utf-8")
    assert load_contract(path).rules[0].selector.relative_path == "数据 é.csv"


def test_published_schema_matches_runtime_model_and_has_strict_structure():
    from xiangrugu_datamgmt.contracts import contract_schema
    schema = json.loads((Path(__file__).parents[2] / "config" / "contract.schema.json").read_text())
    assert schema == contract_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["$defs"]["Disposition"]["enum"]) == {"IMPORT", "MIRROR", "NON_TABULAR", "BLOCKED"}


def test_nonimport_rules_cannot_smuggle_business_targets(contract_doc):
    contract_doc["rules"][0]["disposition"] = "NON_TABULAR"
    with pytest.raises(ValueError):
        validate(contract_doc)


@pytest.mark.parametrize("codec", ["base64_codec", "hex_codec", "rot_13", "zlib_codec"])
def test_nontext_codecs_cannot_be_declared_as_column_encodings(contract_doc, codec):
    contract_doc["rules"][0]["encodings"][0]["codec"] = codec
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_boolean_schema_version_is_not_integer_version_one(contract_doc):
    contract_doc["version"] = True
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_archive_chain_must_have_complete_physical_ordinals(contract_doc):
    contract_doc["rules"][0]["selector"]["archive_chain"] = ["data.csv"]
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_mirror_without_independent_evidence_digest_is_rejected(contract_doc):
    rule = contract_doc["rules"][0]
    rule.update(disposition="MIRROR", targets=[], mirror_of="readme")
    with pytest.raises(ValueError):
        validate(contract_doc)


def test_error_message_does_not_echo_unknown_secret_value(tmp_path):
    from xiangrugu_datamgmt.contracts import load_contract
    path = tmp_path / "contract.json"
    path.write_text('{"password":"fixture-secret-must-not-echo"}')
    with pytest.raises(ValueError) as error:
        load_contract(path)
    assert "fixture-secret-must-not-echo" not in str(error.value)


@pytest.mark.parametrize("codec", ["utf-8", "utf-16", "utf-32", "big5", "gbk"])
def test_valid_multibyte_text_codecs_are_not_rejected_by_probe_bytes(contract_doc, codec):
    contract_doc["rules"][0]["encodings"][0]["codec"] = codec
    assert validate(contract_doc).rules[0].encodings[0].codec == codec
