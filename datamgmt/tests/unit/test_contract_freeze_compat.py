"""Digest compatibility anchors and frozen-gate enforcement through the formal parse entry."""
import copy
import json
from pathlib import Path

import pytest

from xiangrugu_datamgmt.contracts import ReleaseContract, validate_first_batch_seven

ROOT = Path(__file__).parents[3]
CANDIDATE_PATH = ROOT / ".task6-contract-extension-20261123" / "candidate-contract.json"
PENDING_PATH = ROOT / ".task6-reception-precheck-20261123" / "pending-approval-seven-20261123.json"
REVIEW = {"approved_by": "isolated-test", "approved_at": "2026-11-24T00:00:00Z",
          "approval_ref": "isolated-test-only-not-a-real-approval"}
LEGACY_DRAFT_SHA = "156b6354d509bfd6cb5730ee890df8bc5c40eca93ac0489132cfd008ac3cace8"
LEGACY_FROZEN_SHA = "db5e163df3d970c03fad922b358ac97de7155af1a24826bf49e6891d3eff7530"
CANDIDATE_SHA = "bb7157992e131479877eb985a717dba6ab53af8ccdcb491e623a35e785dc8f82"
MUTATED_TARGET_SHA = "62022257d181df52636f504fcfae293fceea04c2d0b85af5282db642051545fb"
MUTATED_WIDTH_SHA = "5edcf43e4582bf6a305533a7292cef36ae0790a89a915dbb3a73f98136f2273c"


def legacy_doc(status):
    return {"version": 1, "release_id": "2026-10-06-legacy-compat-probe",
            "source_version": "probe", "inventory_sha256": "a" * 64,
            "status": status, "review": REVIEW if status == "frozen" else None,
            "exceptions": [],
            "rules": [{"rule_id": "legacy",
                       "selector": {"relative_path": "legacy.csv", "archive_chain": [], "archive_ordinals": []},
                       "expected": {"kind": "file", "sha256": "c" * 64, "size": 10, "signature": "unknown"},
                       "disposition": "IMPORT", "reason": "legacy compatibility probe",
                       "format_family": "text",
                       "encodings": [{"object_name": "legacy", "column": "name", "codec": "utf-8", "errors": "strict"}],
                       "targets": [{"object_name": "legacy", "schema": "harv", "table": "legacy__data",
                                    "expected_count": 1, "expected_sha256": "b" * 64}],
                       "validator": "canonical-value-v1"}]}


@pytest.fixture()
def candidate_doc():
    return json.loads(CANDIDATE_PATH.read_text())


@pytest.mark.parametrize("status,anchor", [("draft", LEGACY_DRAFT_SHA), ("frozen", LEGACY_FROZEN_SHA)])
def test_legacy_contract_digest_matches_pre_extension_anchor(status, anchor):
    contract = ReleaseContract.model_validate(legacy_doc(status))
    assert contract.sha256 == anchor
    raw = contract.canonical_bytes()
    for key in (b'"columns":null', b'"derived_rownum":null',
                b'"duplicate_reconciliation":null', b'"geometry":null'):
        assert key not in raw


def test_extension_values_participate_in_digest(candidate_doc):
    assert ReleaseContract.model_validate(candidate_doc).sha256 == CANDIDATE_SHA
    mutated = copy.deepcopy(candidate_doc)
    rule = next(r for r in mutated["rules"] if r["rule_id"] == "m008002")
    rule["targets"][0]["columns"][0]["target_column"] = "mutated_name"
    assert ReleaseContract.model_validate(mutated).sha256 == MUTATED_TARGET_SHA
    mutated = copy.deepcopy(candidate_doc)
    rule = next(r for r in mutated["rules"] if r["rule_id"] == "m002709")
    lat = next(c for c in rule["targets"][0]["columns"] if c["source_column"] == "LAT")
    lat["pg_type"] = "numeric(20,5)"
    lat["source_width_bytes"] = 20
    assert ReleaseContract.model_validate(mutated).sha256 == MUTATED_WIDTH_SHA


def test_frozen_candidate_with_isolated_test_review_passes_formal_entry(candidate_doc):
    candidate_doc["status"] = "frozen"
    candidate_doc["review"] = REVIEW
    contract = ReleaseContract.model_validate(candidate_doc)
    assert contract.status == "frozen"
    with pytest.raises(ValueError, match="unfrozen"):
        validate_first_batch_seven(contract)


@pytest.mark.parametrize("mutation", [
    "missing_columns", "missing_rownum", "missing_duplicates",
    "spatial_missing_geometry", "unapproved_srid", "text_with_geometry", "width_contradiction",
])
def test_frozen_first_batch_counterexamples_rejected_by_formal_entry(candidate_doc, mutation):
    candidate_doc["status"] = "frozen"
    candidate_doc["review"] = REVIEW
    if mutation == "missing_columns":
        candidate_doc["rules"][0]["targets"][0]["columns"] = None
    elif mutation == "missing_rownum":
        candidate_doc["rules"][0]["targets"][0]["derived_rownum"] = None
    elif mutation == "missing_duplicates":
        candidate_doc["rules"][0]["targets"][0]["duplicate_reconciliation"] = None
    elif mutation == "spatial_missing_geometry":
        next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")["targets"][0]["geometry"] = None
    elif mutation == "unapproved_srid":
        next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002717")["targets"][0]["geometry"]["srid"] = 4327
    elif mutation == "text_with_geometry":
        next(r for r in candidate_doc["rules"] if r["rule_id"] == "m008002")["targets"][0]["geometry"] = \
            next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")["targets"][0]["geometry"]
    elif mutation == "width_contradiction":
        rule = next(r for r in candidate_doc["rules"] if r["rule_id"] == "m002709")
        lat = next(c for c in rule["targets"][0]["columns"] if c["source_column"] == "LAT")
        lat["source_width_bytes"] = 20
    with pytest.raises(ValueError):
        ReleaseContract.model_validate(candidate_doc)


def test_frozen_candidate_matches_pending_table_mappings_and_digests(candidate_doc):
    candidate_doc["status"] = "frozen"
    candidate_doc["review"] = REVIEW
    contract = ReleaseContract.model_validate(candidate_doc)
    pending = json.loads(PENDING_PATH.read_text())
    by_rule = {r.rule_id: r for r in contract.rules}
    for item in pending["items"]:
        rule = by_rule[item["rule_id"]]
        target = rule.targets[0]
        assert f"{target.schema_name}.{target.table}" == item["candidate_full_name"]
        assert target.expected_count == item["expected_row_count"]
        assert target.expected_sha256 == item["attribute_digest"]["expected_sha256"]
        if item["kind"] == "text":
            expected_cols = item["precise_field_mapping"]["columns"][:-1]
            assert len(target.columns) == len(expected_cols)
            for col, exp in zip(target.columns, expected_cols):
                assert (col.source_column, col.target_column, col.pg_type, col.nullable) == \
                    (exp["column_key"], exp["target_name"], exp["pg_type"], exp["nullable"])
            assert target.duplicate_reconciliation.expected_groups == item["actual_duplicates"]["groups"]
            assert target.duplicate_reconciliation.expected_extra_rows == item["actual_duplicates"]["extra_rows"]
        else:
            assert target.geometry.expected_sha256 == item["geometry_digest"]["expected_sha256"]
            assert target.geometry.srid == item["srid"] == 4326
            assert rule.expected.sha256 == item["dbf_source_identity"]["dbf_sha256"]
            assert rule.expected.size == 16937
            for col in target.columns:
                if col.pg_type.startswith("numeric("):
                    precision, scale = col.pg_type[len("numeric("):-1].split(",")
                    assert col.source_width_bytes == int(precision) and col.source_decimals == int(scale)