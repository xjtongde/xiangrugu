"""Repository evidence consumers; images explicitly lack release artifacts."""
import hashlib
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(ROOT == Path("/app"), reason="repository-only release evidence")
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"


def test_role_decision_binds_original_proposal_and_excludes_type_or_import_approval():
    raw = (RELEASE / "sqlite-object-contract-proposal.draft.json").read_bytes()
    path = RELEASE / "sqlite-role-decisions.draft.json"
    assert path.is_file(), "missing explicit role-only approval record"
    decision = json.loads(path.read_text())
    assert decision["proposal_sha256"] == hashlib.sha256(raw).hexdigest()
    assert decision["roles_approved"] is True
    for flag in ("type_mapping_approved", "value_contract_approved", "target_mapping_approved",
                 "ready_for_import", "contract_frozen"):
        assert decision[flag] is False


def test_all_roles_are_complete_and_not_silently_promoted_to_import():
    path = RELEASE / "sqlite-roles-approved.draft.json"
    assert path.is_file(), "missing non-executable role projection"
    projection = json.loads(path.read_text())
    proposal = json.loads((RELEASE / "sqlite-object-contract-proposal.draft.json").read_text())
    assert len(projection["tables"]) == 78 and len(projection["indexes"]) == 76
    assert {o["source_object_id"] for o in projection["tables"]} == {o["source_object_id"] for o in proposal["objects"]}
    assert {o["name"] for o in projection["indexes"]} == {o["source_object_name"] for o in proposal["ancillary_catalog_objects"]}
    assert all(o["role"] == "tabular-source" for o in projection["tables"])
    assert all(o["role"] == "source-schema-metadata" for o in projection["indexes"])
    assert projection["disposition_retained"] == "BLOCKED"
    assert projection["ready_for_import"] is False
    assert projection["decision_sha256"] == hashlib.sha256((RELEASE / "sqlite-role-decisions.draft.json").read_bytes()).hexdigest()


def test_approved_scan_scope_is_exactly_three_tables_and_28_columns():
    path = RELEASE / "sqlite-role-decisions.draft.json"
    assert path.is_file(), "missing approved diagnostic scope"
    decision = json.loads(path.read_text())
    scope = decision["profile_scope"]
    assert set(scope) == {"ADDR_CODES", "SOCIAL_INSTITUTION_ALTNAME_CODES",
                          "SOCIAL_INSTITUTION_ALTNAME_DATA"}
    assert sum(map(len, scope.values())) == 28
    proposal = json.loads((RELEASE / "sqlite-object-contract-proposal.draft.json").read_text())
    for name, cols in scope.items():
        obj = next(obj for obj in proposal["objects"] if obj["source_object_name"] == name)
        assert cols == [col["source_name"] for col in obj["source_columns"]]
    assert decision["profile_read_authorized"] is True
    assert decision["raw_text_or_blob_output_authorized"] is False
