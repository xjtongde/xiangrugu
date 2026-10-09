"""Consume the five-object proposal; catch evidence drift and accidental release gates.

These tests read repository metadata only, never a source snapshot or database.
No proposal generator or production importer is introduced in this slice.
This is a controlled-workspace audit, not an in-image runtime contract.
"""
import hashlib
import json
from pathlib import Path

import pytest

from xiangrugu_datamgmt.contracts import load_contract


ROOT = Path(__file__).resolve().parents[3]
# The fixed /app test target intentionally excludes repository contracts/evidence.
# Never skip merely because a workspace artifact is missing: that must fail.
pytestmark = pytest.mark.skipif(
    ROOT == Path("/app"),
    reason="repository metadata audit requires the controlled workspace, not the /app test image",
)
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"
PROPOSAL = RELEASE / "text-value-contract-proposal.draft.json"
EVIDENCE = ROOT / "docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json"
PROJECTION = RELEASE / "text-schema-approved.draft.yaml"
EXPECTED = [
    ("m008002", 2957, 54, "harv", "475ea1d8b400939cb79b46b47d641d83685bc8d1a3e4478bec1cdfdd562c429a"),
    ("m008003", 40199, 5, "harv", "dcbedb5a5073a6b980d82156ffb3fa7dbaf3ca9906c2928534793b3e0a43a039"),
    ("m008004", 1033, 11, "harv", "d233ed9c81ad6f8ff22c1f8c89786dcae90b0fffaf5657666d98e6212edec5fd"),
    ("m004812", 29, 7, "harv", "b3f6ceb609a853cbb06eb7f8004a39f676d1ff5e95fbb46fc0381abbf722f667"),
    ("m006642", 3389, 6, "chgis", "3bad44a0482c1bc2479a541d2d9c9d405187eb1caeb177479fb69f7954b313fc"),
]


def document(path):
    assert path.is_file(), "missing non-executable text value contract proposal"
    return json.loads(path.read_text(encoding="utf-8"))


def test_proposal_binds_exact_existing_artifacts():
    draft = document(PROPOSAL)
    expected_files = {
        EVIDENCE.relative_to(ROOT).as_posix(), PROJECTION.relative_to(ROOT).as_posix(),
        *(f"datamgmt/contracts/releases/2026-10-06-bootstrap/{name}" for name in (
            "text-reading-decisions.draft.yaml", "additional-text-reading-decisions.draft.yaml",
            "sources.yaml", "sources-metadata-review.draft.yaml", "decoding.yaml", "assertions.yaml")),
    }
    assert set(draft["input_sha256"]) == expected_files
    for path, digest in draft["input_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    assert draft["input_sha256"][EVIDENCE.relative_to(ROOT).as_posix()] == "47c2401197e557be356941842d099a27db867e707682a3ef536cee2430d7ac38"
    assert draft["input_sha256"][PROJECTION.relative_to(ROOT).as_posix()] == "0f379eee0eb120eb037cd63b73299cd79a9be6aee412b24ca5e04dac9bb03189"


@pytest.mark.parametrize("index,expected", list(enumerate(EXPECTED)))
def test_each_object_binds_source_mapping_schema_and_complete_stream(index, expected):
    draft = document(PROPOSAL)
    row = draft["objects"][index]
    evidence = document(EVIDENCE)["objects"][index]
    approved = document(PROJECTION)["objects"][index]
    rule_id, count, source_columns, schema, digest = expected
    assert row["rule_id"] == evidence["rule_id"] == approved["rule_id"] == rule_id
    assert row["source_object_id"] == evidence["source_object_id"] == approved["source_object_id"]
    assert row["source"] == evidence["source"]
    assert row["source"]["path"] == approved["selector"]["relative_path"]
    assert approved["selector"]["archive_chain"] == approved["selector"]["archive_ordinals"] == []
    assert row["source"]["sha256"] == approved["raw_expected"]["sha256"]
    assert row["source"]["size"] == approved["raw_expected"]["size"]
    assert row["approved_schema"] == approved["approved_schema"] == schema
    assert row["source_column_count"] == len(approved["source_columns"]) == source_columns
    assert row["value_columns_ref"] == {
        "file": EVIDENCE.relative_to(ROOT).as_posix(), "pointer": f"/objects/{index}/value_columns"}
    assert row["approved_object_ref"] == {
        "file": PROJECTION.relative_to(ROOT).as_posix(), "pointer": f"/objects/{index}"}
    columns = evidence["value_columns"]
    assert len(columns) == source_columns + 1
    for actual, column in zip(columns[:-1], approved["source_columns"], strict=True):
        assert actual == {"column_key": column["column_id"], "target_name": column["target_name"],
                          "pg_type": "text", "nullable": False}
        assert column["target_type"] == "text" and column["nullable"] is False
        assert column["encoding"]["codec"] == "utf-8" and column["encoding"]["errors"] == "strict"
    assert columns[-1] == {"column_key": "derived:__src_rownum", "target_name": "__src_rownum",
                           "pg_type": "bigint", "nullable": False}
    # Independently reconstruct schema bytes per v1, not by calling the production canonical helper.
    wire = [[c["column_key"], c["target_name"], c["pg_type"], c["nullable"]] for c in columns]
    schema_bytes = json.dumps(wire, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert row["schema_sha256"] == evidence["schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
    assert row["expected"] == evidence["expected"]
    assert row["expected"]["sha256"] == digest
    assert row["expected"]["row_count"] == approved["source_record_count"] == count
    assert row["expected"]["field_count"] == count * (source_columns + 1)
    assert row["expected"]["stream_bytes"] >= 83
    assert evidence["independent_reference_equal"] is True
    assert approved["proposed_target"]["expected_sha256"] is None
    assert row["disposition_retained"] == "BLOCKED"
    assert "table" not in row and "target" not in row


def test_partial_proposal_cannot_claim_new_source_checks_or_release_approval():
    draft = document(PROPOSAL)
    evidence = document(EVIDENCE)
    assert draft["status"] == "DRAFT_FOR_REVIEW"
    assert draft["canonical_format"] == "XRGVALUE-v1"
    assert draft["header_excluded"] is True and draft["rownum_start"] == 1
    for gate in ("value_contract_approved", "table_names_approved", "target_mapping_approved",
                 "global_name_allocation_complete", "full_release_value_contract_complete",
                 "contract_frozen", "ready_for_import", "formal_contract_modified",
                 "source_read_this_run", "full_snapshot_verified_this_run", "database_connected",
                 "database_values_verified", "runtime_applied"):
        assert draft[gate] is False
    assert draft["source_evidence_provenance"] == {
        key: evidence[key] for key in (
            "generated_at", "image_id", "git_revision", "source_status", "source_version",
            "certificate_sha256", "snapshot_manifest_sha256", "full_snapshot_verified_this_run")}
    assert not (ROOT / "datamgmt/contracts/current.yaml").exists()


def test_exact_five_object_scope_and_count_units():
    draft = document(PROPOSAL)
    assert [r["rule_id"] for r in draft["objects"]] == [r[0] for r in EXPECTED]
    assert len({r["source_object_id"] for r in draft["objects"]}) == 5
    assert draft["totals"] == {"object_count": 5, "source_column_count": 83,
                                "data_record_count": 47607, "source_field_count": 392573,
                                "derived_rownum_field_count": 47607, "value_field_count": 440180}
    assert sum(r["expected"]["field_count"] for r in draft["objects"]) == 440180


def test_proposal_is_not_an_executable_release_contract():
    document(PROPOSAL)
    with pytest.raises(ValueError):
        load_contract(PROPOSAL)


def test_value_approval_is_bound_to_the_exact_five_object_proposal():
    decision = document(RELEASE / "text-value-contract-decisions.draft.json")
    proposal = document(PROPOSAL)
    assert decision["proposal_file"] == PROPOSAL.relative_to(ROOT).as_posix()
    assert decision["proposal_sha256"] == hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() == "c86be708b7469c095ae7bd35f4751dc17d9045f353da799cda651d6af38a2189"
    assert decision["value_contract_approved"] is True
    assert decision["approval"]["reply"] == "同意"
    assert decision["approval"]["approved_scope"] == "five-object ordered XRGVALUE-v1 source expectations only"
    assert decision["objects"] == [{key: obj[key] for key in (
        "rule_id", "source_object_id", "source", "schema_sha256", "expected")}
        for obj in proposal["objects"]]


def test_approved_value_projection_preserves_all_proposal_data_and_provenance():
    path = RELEASE / "text-value-contract-approved.draft.json"
    approved = document(path)
    proposal = document(PROPOSAL)
    decision_path = RELEASE / "text-value-contract-decisions.draft.json"
    assert approved["approval_decision_file"] == decision_path.relative_to(ROOT).as_posix()
    assert approved["approval_decision_sha256"] == hashlib.sha256(decision_path.read_bytes()).hexdigest()
    assert approved["proposal_sha256"] == "c86be708b7469c095ae7bd35f4751dc17d9045f353da799cda651d6af38a2189"
    assert approved["status"] == "DRAFT_VALUE_APPROVED"
    assert approved["value_contract_approved"] is True
    assert approved["proposal_notes"] == proposal["proposal_notes"]
    added = {"approval_decision_file", "approval_decision_sha256", "proposal_sha256", "approved_on"}
    assert set(approved) == set(proposal) | added
    for key in set(proposal) - {"status", "value_contract_approved"}:
        assert approved[key] == proposal[key]
    with pytest.raises(ValueError):
        load_contract(path)


def test_partial_value_approval_does_not_authorize_names_freeze_source_or_import():
    for name in ("text-value-contract-decisions.draft.json", "text-value-contract-approved.draft.json"):
        approved = document(RELEASE / name)
        for gate in ("table_names_approved", "target_mapping_approved",
                     "global_name_allocation_complete", "full_release_value_contract_complete",
                     "contract_frozen", "ready_for_import", "formal_contract_modified",
                     "source_read_this_run", "full_snapshot_verified_this_run", "database_connected",
                     "database_values_verified", "runtime_applied"):
            assert approved[gate] is False
    assert all(obj["disposition_retained"] == "BLOCKED" for obj in document(
        RELEASE / "text-value-contract-approved.draft.json")["objects"])
    assert document(PROPOSAL)["value_contract_approved"] is False
    assert not (ROOT / "datamgmt/contracts/current.yaml").exists()
