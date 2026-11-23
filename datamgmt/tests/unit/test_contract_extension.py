"""First-batch contract extension: backward compatibility, dedicated validation, fail-closed counterexamples."""
import copy
import json
from pathlib import Path

import pytest

from xiangrugu_datamgmt.contracts import (
    ContractError, ReleaseContract, contract_schema, validate_first_batch_seven,
)

CANDIDATE_PATH = Path(__file__).parents[3] / ".task6-contract-extension-20261123" / "candidate-contract.json"


@pytest.fixture()
def candidate_doc():
    return json.loads(CANDIDATE_PATH.read_text())


def test_existing_contract_still_parses_with_original_rules(contract_doc):
    contract = ReleaseContract.model_validate(contract_doc)
    target = contract.rules[0].targets[0]
    assert target.columns is None and target.derived_rownum is None
    assert target.duplicate_reconciliation is None and target.geometry is None
    assert contract.status == "draft"


def test_published_schema_matches_extended_runtime_model():
    schema = json.loads((Path(__file__).parents[2] / "config" / "contract.schema.json").read_text())
    assert schema == contract_schema()


def test_first_batch_candidate_parses_and_passes_dedicated_validation(candidate_doc):
    contract = ReleaseContract.model_validate(candidate_doc)
    validate_first_batch_seven(contract)
    assert contract.status == "draft"
    total = sum(t.expected_count for r in contract.rules for t in r.targets)
    assert total == 47725
    m3 = next(r for r in contract.rules if r.rule_id == "m008003").targets[0]
    assert m3.duplicate_reconciliation.expected_groups == 63
    assert m3.duplicate_reconciliation.expected_extra_rows == 74
    for rule_id in ("m002709", "m002717"):
        t = next(r for r in contract.rules if r.rule_id == rule_id).targets[0]
        assert t.geometry.srid == 4326 and t.geometry.dimensions == 2
        assert t.geometry.geometry_type == "Point"
        assert len(t.geometry.expected_sha256) == 64
    identities = {r.rule_id: r.expected.sha256 for r in contract.rules
                  if r.rule_id in ("m002709", "m002717")}
    assert identities["m002709"] != identities["m002717"]


@pytest.mark.parametrize("field", ["columns", "derived_rownum", "duplicate_reconciliation"])
def test_missing_extension_field_is_rejected(candidate_doc, field):
    candidate_doc["rules"][0]["targets"][0][field] = None
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="missing required extension field"):
        validate_first_batch_seven(contract)


def test_spatial_missing_geometry_is_rejected(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")
    rule["targets"][0]["geometry"] = None
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="geometry expectation"):
        validate_first_batch_seven(contract)


def test_text_with_geometry_is_rejected(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008002")
    rule["targets"][0]["geometry"] = next(
        r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")["targets"][0]["geometry"]
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="must not carry a geometry"):
        validate_first_batch_seven(contract)


def test_unapproved_srid_is_rejected(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002717")
    rule["targets"][0]["geometry"]["srid"] = 4327
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="approved 4326"):
        validate_first_batch_seven(contract)


def test_frozen_candidate_is_rejected_by_dedicated_validation(candidate_doc):
    candidate_doc["status"] = "frozen"
    candidate_doc["review"] = {"approved_by": "x", "approved_at": "2026-11-23T00:00:00Z",
                               "approval_ref": "x"}
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="unfrozen"):
        validate_first_batch_seven(contract)


def test_missing_rule_is_rejected(candidate_doc):
    candidate_doc["rules"] = candidate_doc["rules"][:-1]
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="seven first-batch rules"):
        validate_first_batch_seven(contract)


def test_duplicate_reconciliation_exceeding_count_is_rejected(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008003")
    rule["targets"][0]["expected_count"] = 100
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="exceeds expected_count"):
        validate_first_batch_seven(contract)


def test_ordinal_gap_is_rejected_at_parse(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008002")
    rule["targets"][0]["columns"][3]["ordinal"] = 9
    with pytest.raises(ValueError, match="contiguous"):
        ReleaseContract.model_validate(candidate_doc)


def test_duplicate_target_column_is_rejected_at_parse(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008002")
    cols = rule["targets"][0]["columns"]
    cols[1]["target_column"] = cols[0]["target_column"]
    with pytest.raises(ValueError, match="unique"):
        ReleaseContract.model_validate(candidate_doc)


def test_numeric_width_scale_contradiction_is_rejected_at_parse(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")
    lat = next(c for c in rule["targets"][0]["columns"] if c["source_column"] == "LAT")
    lat["source_width_bytes"] = 16
    with pytest.raises(ValueError, match="width/scale"):
        ReleaseContract.model_validate(candidate_doc)


def test_duplicate_arithmetic_contradiction_is_rejected_at_parse(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008003")
    rule["targets"][0]["duplicate_reconciliation"]["expected_extra_rows"] = 0
    with pytest.raises(ValueError, match="at least one extra row"):
        ReleaseContract.model_validate(candidate_doc)


def test_rownum_nullable_deviation_is_rejected_at_parse(candidate_doc):
    candidate_doc["rules"][0]["targets"][0]["derived_rownum"]["nullable"] = True
    with pytest.raises(ValueError):
        ReleaseContract.model_validate(candidate_doc)


def test_geometry_dimension_deviation_is_rejected_at_parse(candidate_doc):
    rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")
    rule["targets"][0]["geometry"]["dimensions"] = 3
    with pytest.raises(ValueError):
        ReleaseContract.model_validate(candidate_doc)


def test_empty_columns_are_rejected(candidate_doc):
    candidate_doc["rules"][0]["targets"][0]["columns"] = []
    contract = ReleaseContract.model_validate(candidate_doc)
    with pytest.raises(ContractError, match="must not be empty"):
        validate_first_batch_seven(contract)