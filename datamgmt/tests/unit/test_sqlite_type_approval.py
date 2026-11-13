"""Consume the exact repository-only type approval; never open source data."""
import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(ROOT == Path("/app"), reason="repository-only type decisions")
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"


def read(name):
    path = RELEASE / name
    assert path.is_file(), "missing explicit SQLite type approval artifact"
    return json.loads(path.read_text(encoding="utf-8"))


def test_type_decision_binds_review_and_source_without_import_permission():
    decision = read("sqlite-type-decisions.draft.json")
    for name, digest in decision["bound_files"].items():
        assert hashlib.sha256((RELEASE / name).read_bytes()).hexdigest() == digest
    assert set(decision["bound_files"]) == {"sqlite-object-contract-proposal.draft.json",
        "sqlite-type-observations.draft.json", "sqlite-unobserved-type-proposal.draft.json"}
    assert decision["type_mapping_approved"] is True
    assert decision["scalar_preservation_policy_approved"] is True
    for flag in ("nullability_constraints_approved", "target_mapping_approved",
                 "value_contract_approved", "source_ddl_execution_approved",
                 "ready_for_import", "contract_frozen"):
        assert decision[flag] is False


def test_approved_types_cover_all_original_columns_in_exact_order():
    approved = read("sqlite-types-approved.draft.json")
    original = read("sqlite-object-contract-proposal.draft.json")
    observed = read("sqlite-type-observations.draft.json")
    unseen = read("sqlite-unobserved-type-proposal.draft.json")
    fallback = {(c["table"], c["column"]): c for c in unseen["columns"]}
    assert len(approved["tables"]) == len(original["objects"]) == 78
    assert sum(len(t["columns"]) for t in approved["tables"]) == 736
    assert len({t["source_object_id"] for t in approved["tables"]}) == 78
    counts = {"bigint": 0, "double precision": 0, "text": 0}
    for table, source, observation in zip(approved["tables"], original["objects"], observed["objects"]):
        assert table["source_object_id"] == source["source_object_id"] == observation["source_object_id"]
        assert table["source_object_name"] == source["source_object_name"]
        assert len(table["columns"]) == len(source["source_columns"])
        for col, raw, obs in zip(table["columns"], source["source_columns"], observation["columns"]):
            assert (col["source_ordinal"], col["source_name"]) == (raw["source_ordinal"], raw["source_name"])
            classes = obs["non_null_storage_classes"]
            if classes:
                expected = {"integer": "bigint", "real": "double precision", "text": "text"}[classes[0]]
                assert col["basis"] == "OBSERVED_API_STORAGE_CLASS"
            else:
                expected = fallback[(table["source_object_name"], col["source_name"])]["candidate_type"]
                assert col["basis"] == "SOURCE_DECLARATION_ONLY"
                assert col["non_null_values_observed"] is False
            assert col["approved_type"] == expected
            assert col["target_nullable"] is None
            counts[expected] += 1
    assert counts == {"bigint": 394, "double precision": 4, "text": 338}


def test_approval_preserves_null_empty_text_and_values_without_cleaning():
    decision = read("sqlite-type-decisions.draft.json")
    policy = decision["preservation_policy"]
    assert policy["null_and_empty_text_distinct"] is True
    assert policy["integer_encoding"] == "signed-int64-exact"
    assert policy["real_encoding"] == "binary64-exact"
    assert policy["text_length_cap"] is None
    for flag in ("trim_text", "replace_invalid_text", "convert_dates",
                 "fill_nulls", "execute_source_defaults", "transform_coordinates"):
        assert policy[flag] is False


def test_projection_is_bound_to_decision_and_keeps_historical_proposals_pending():
    projection = read("sqlite-types-approved.draft.json")
    assert projection["decision_sha256"] == hashlib.sha256(
        (RELEASE / "sqlite-type-decisions.draft.json").read_bytes()).hexdigest()
    assert projection["type_mapping_approved"] is True
    assert projection["ready_for_import"] is False
    assert projection["disposition_retained"] == "BLOCKED"
    assert read("sqlite-type-observations.draft.json")["type_mapping_approved"] is False
    assert read("sqlite-unobserved-type-proposal.draft.json")["type_mapping_approved"] is False
