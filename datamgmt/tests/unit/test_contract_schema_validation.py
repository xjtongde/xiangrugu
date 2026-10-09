"""Raw document validation, separate from Pydantic coercion and semantics."""
import json
from pathlib import Path

import pytest
import yaml

from xiangrugu_datamgmt import contracts


def check(document, schema=None):
    validator = getattr(contracts, "validate_contract_document", None)
    assert callable(validator), "Independent raw JSON Schema validator is missing"
    validator(document, schema if schema is not None else contracts.contract_schema())


def test_exported_schema_validates_raw_fixture_without_model(contract_doc, monkeypatch):
    schema = json.loads((Path(__file__).parents[2] / "config/contract.schema.json").read_text())
    monkeypatch.setattr(contracts.ReleaseContract, "model_validate",
                        lambda *args, **kwargs: pytest.fail("Schema gate invoked model"))
    check(contract_doc, schema)


@pytest.mark.parametrize("mutation", [
    "missing", "type", "extra", "digest", "nested_extra", "bool_count", "empty_rules",
])
def test_raw_schema_rejects_structural_errors(contract_doc, mutation):
    if mutation == "missing":
        del contract_doc["inventory_sha256"]
    elif mutation == "type":
        contract_doc["source_version"] = 42
    elif mutation == "extra":
        contract_doc["unexpected"] = "synthetic-value"
    elif mutation == "digest":
        contract_doc["rules"][0]["expected"]["sha256"] = "z" * 64
    elif mutation == "nested_extra":
        contract_doc["rules"][0]["selector"]["unexpected"] = True
    elif mutation == "bool_count":
        contract_doc["rules"][0]["targets"][0]["expected_count"] = True
    else:
        contract_doc["rules"] = []
    with pytest.raises(contracts.ContractError):
        check(contract_doc)


@pytest.mark.parametrize("schema", [
    {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "invalid"},
    {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object"},
    {"type": "object"},
])
def test_invalid_or_other_draft_schema_fails_closed(contract_doc, schema):
    with pytest.raises(contracts.ContractError):
        check(contract_doc, schema)


@pytest.mark.parametrize("reference", [
    "https://example.invalid/schema", "file:///tmp/schema", "other.json", "//example.invalid/schema",
])
@pytest.mark.parametrize("keyword", ["$ref", "$dynamicRef"])
def test_external_references_rejected_even_in_unused_definitions(contract_doc, reference, keyword):
    schema = contracts.contract_schema()
    schema["$defs"]["Unused"] = {keyword: reference}
    with pytest.raises(contracts.ContractError):
        check(contract_doc, schema)


def test_schema_id_cannot_rebase_local_references(contract_doc):
    schema = contracts.contract_schema()
    schema["$id"] = "https://example.invalid/schema"
    with pytest.raises(contracts.ContractError):
        check(contract_doc, schema)


def test_broken_local_reference_is_sanitized(contract_doc):
    schema = contracts.contract_schema()
    schema["properties"]["source_version"] = {"$ref": "#/$defs/missing"}
    with pytest.raises(contracts.ContractError) as error:
        check(contract_doc, schema)
    assert error.value.__cause__ is None


@pytest.mark.parametrize("value", [b"synthetic", float("nan"), float("inf"), {"bad"}, ("bad",)])
def test_yaml_only_values_are_not_json_instances(contract_doc, value):
    contract_doc["source_version"] = value
    with pytest.raises(contracts.ContractError):
        check(contract_doc)


def test_nonstring_mapping_keys_are_rejected(contract_doc):
    contract_doc["rules"][0]["selector"][7] = "not-json"
    with pytest.raises(contracts.ContractError):
        check(contract_doc)


def test_recursive_yaml_document_is_rejected(contract_doc):
    contract_doc["recursive"] = contract_doc
    with pytest.raises(contracts.ContractError):
        check(contract_doc)


def test_error_chain_does_not_echo_raw_document(contract_doc):
    contract_doc["source_version"] = {"secret": "synthetic-must-not-echo"}
    with pytest.raises(contracts.ContractError) as error:
        check(contract_doc)
    assert "synthetic-must-not-echo" not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
def test_loader_runs_schema_on_raw_document_before_model(contract_doc, tmp_path, monkeypatch, suffix):
    path = tmp_path / ("contract" + suffix)
    path.write_text(json.dumps(contract_doc) if suffix == ".json" else yaml.safe_dump(contract_doc))
    validator = getattr(contracts, "validate_contract_document", None)
    assert callable(validator), "Independent raw JSON Schema validator is missing"

    def reject_raw(document, schema):
        assert document == contract_doc
        raise contracts.ContractError("Synthetic raw gate rejection")

    monkeypatch.setattr(contracts, "validate_contract_document", reject_raw)
    monkeypatch.setattr(contracts.ReleaseContract, "model_validate",
                        lambda *args, **kwargs: pytest.fail("Model preceded raw Schema gate"))
    with pytest.raises(contracts.ContractError):
        contracts.load_contract(path)


def test_schema_pass_does_not_bypass_semantics(contract_doc, tmp_path):
    contract_doc["rules"][0]["encodings"][0]["codec"] = "synthetic-not-a-codec"
    check(contract_doc)
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract_doc))
    with pytest.raises(contracts.ContractError):
        contracts.load_contract(path)


def test_local_reference_to_nonschema_is_sanitized():
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "title": "not-a-schema", "$ref": "#/title"}
    with pytest.raises(contracts.ContractError) as error:
        check({"synthetic": "must-not-echo"}, schema)
    assert error.value.__cause__ is None


def test_literal_document_reference_key_in_const_is_not_a_schema_reference():
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "const": {"$ref": "literal"}}
    check({"$ref": "literal"}, schema)
    with pytest.raises(contracts.ContractError):
        check({"$ref": "wrong"}, schema)


def test_schema_validation_expansion_is_bounded(monkeypatch):
    # Small synthetic DAG; lowering the private ceiling avoids expensive work.
    monkeypatch.setattr(contracts, "_SCHEMA_STEP_LIMIT", 100, raising=False)
    definitions = {"level0": {"type": "integer"}}
    for level in range(1, 7):
        definitions[f"level{level}"] = {
            "allOf": [{"$ref": f"#/$defs/level{level - 1}"}] * 2,
        }
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "$defs": definitions, "$ref": "#/$defs/level6"}
    with pytest.raises(contracts.ContractError):
        check(0, schema)


def test_nested_dialect_declaration_cannot_bypass_execution_budget(monkeypatch):
    monkeypatch.setattr(contracts, "_SCHEMA_STEP_LIMIT", 100, raising=False)
    definitions = {"level0": {"type": "integer"}}
    for level in range(1, 7):
        definitions[f"level{level}"] = {
            "allOf": [{"$ref": f"#/$defs/level{level - 1}"}] * 2,
        }
    definitions["level5"]["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
              "$defs": definitions, "$ref": "#/$defs/level6"}
    with pytest.raises(contracts.ContractError):
        check(0, schema)
