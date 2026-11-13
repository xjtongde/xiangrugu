"""Exact approved read scopes; no source or database access."""
import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(ROOT == Path("/app"), reason="repository-only read permissions")
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"
SCOPE = ROOT / "docs/superpowers/plans/2026-10-09-sqlite-remaining-types.scope.json"
DECISION = RELEASE / "sqlite-remaining-type-read-decisions.draft.json"


def read(path):
    assert path.is_file(), "missing approved remaining-table scope"
    return json.loads(path.read_text(encoding="utf-8"))


def test_remaining_approval_binds_proposal_scope_and_role_identity():
    decision = read(DECISION)
    assert decision["profile_read_authorized"] is True
    assert decision["scope_sha256"] == hashlib.sha256(SCOPE.read_bytes()).hexdigest()
    assert decision["role_decision_sha256"] == hashlib.sha256(
        (RELEASE / "sqlite-role-decisions.draft.json").read_bytes()).hexdigest()
    assert decision["proposal_sha256"] == hashlib.sha256(
        (RELEASE / "sqlite-object-contract-proposal.draft.json").read_bytes()).hexdigest()
    assert decision["rule_id"] == "m007906"
    for flag in ("raw_text_or_blob_output_authorized", "type_mapping_approved",
                 "value_contract_approved", "target_mapping_approved", "ready_for_import", "contract_frozen"):
        assert decision[flag] is False


def test_remaining_scope_exactly_covers_75_tables_and_708_columns():
    decision = read(DECISION)
    scope = read(SCOPE)
    proposal = read(RELEASE / "sqlite-object-contract-proposal.draft.json")
    excluded = {"ADDR_CODES", "SOCIAL_INSTITUTION_ALTNAME_CODES", "SOCIAL_INSTITUTION_ALTNAME_DATA"}
    expected = [obj for obj in proposal["objects"] if obj["source_object_name"] not in excluded]
    assert len(scope["tables"]) == len(expected) == 75
    assert len({obj["source_object_id"] for obj in scope["tables"]}) == 75
    assert sum(len(obj["columns"]) for obj in scope["tables"]) == 708
    assert decision["table_object_ids"] == [obj["source_object_id"] for obj in scope["tables"]]
    for item, obj in zip(scope["tables"], expected):
        assert item["name"] == obj["source_object_name"]
        assert item["source_object_id"] == obj["source_object_id"]
        assert item["columns"] == [col["source_name"] for col in obj["source_columns"]]


def test_all_single_table_permissions_match_approved_identity_and_columns():
    decision = read(DECISION)
    scope = read(SCOPE)
    files = list((RELEASE / "sqlite-type-read-scopes").glob("*.approved.json"))
    assert len(files) == 75
    old = read(RELEASE / "sqlite-role-decisions.draft.json")
    decision_sha = hashlib.sha256(DECISION.read_bytes()).hexdigest()
    for item in scope["tables"]:
        permission = read(RELEASE / "sqlite-type-read-scopes" / f'{item["sequence"]:02d}.approved.json')
        assert permission["profile_scope"] == {item["name"]: item["columns"]}
        assert permission["source_object_id"] == item["source_object_id"]
        assert permission["remaining_decision_sha256"] == decision_sha
        assert permission["source_identity"] == old["source_identity"]
        assert permission["source_version"] == old["source_version"]
        assert permission["rule_id"] == old["rule_id"] == decision["rule_id"]
        assert permission["roles_approved"] is True
        assert permission["profile_read_authorized"] is True
        for flag in ("raw_text_or_blob_output_authorized", "type_mapping_approved",
                     "value_contract_approved", "target_mapping_approved", "ready_for_import", "contract_frozen"):
            assert permission[flag] is False


def test_planning_scope_remains_unexecuted_and_cannot_claim_read_approval():
    scope = read(SCOPE)
    assert scope["source_read_authorized"] is False
    assert scope["status"] == "PROPOSED_NOT_AUTHORIZED"
    assert all(item["status"] == "NOT_READ" and item["row_count"] is None for item in scope["tables"])
    assert [sum(item["wave"] == wave for item in scope["tables"]) for wave in range(1, 6)] == [15]*5
