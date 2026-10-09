import copy
from dataclasses import replace

import pytest

from xiangrugu_datamgmt.inventory import InventoryEntry, InventoryIssue


def evaluate(inventory, document):
    from xiangrugu_datamgmt.contracts import ReleaseContract
    from xiangrugu_datamgmt.disposition import DispositionLedger
    return DispositionLedger.evaluate(inventory, ReleaseContract.model_validate(document))


def test_complete_coverage_is_not_release_or_import_permission(inventory, contract_doc):
    ledger = evaluate(inventory, contract_doc)
    coverage = ledger.coverage()
    assert (coverage.total, coverage.matched, coverage.unmatched, coverage.multiple, coverage.unexplained) == (2, 2, 0, 0, 0)
    assert coverage.percent == 100
    assert coverage.conforms
    assert not ledger.ready_for_import
    assert {record.disposition.value for record in ledger.records} == {"IMPORT", "NON_TABULAR"}


def test_literal_xlsx_member_has_exact_coverage(inventory, contract_doc):
    member = replace(inventory.entries[0], relative_path="fixture.zip",
                     archive_chain=("book.xlsx", "[Content_Types].xml"), archive_ordinals=(0, 0))
    manifest = replace(inventory, entries=(member, inventory.entries[1]))
    contract_doc["inventory_sha256"] = manifest.sha256
    contract_doc["rules"][0]["selector"] = {
        "relative_path": "fixture.zip", "archive_chain": ["book.xlsx", "[Content_Types].xml"],
        "archive_ordinals": [0, 0],
    }
    ledger = evaluate(manifest, contract_doc)
    assert ledger.coverage().matched == 2
    assert ledger.coverage().conforms
    assert next(record for record in ledger.records if record.member.relative_path == "fixture.zip").member.archive_chain == ("book.xlsx", "[Content_Types].xml")


def test_bracket_selector_is_not_a_glob_character_class(inventory, contract_doc):
    manifest = replace(inventory, entries=(replace(inventory.entries[0], relative_path="a.csv"), inventory.entries[1]))
    contract_doc["inventory_sha256"] = manifest.sha256
    contract_doc["rules"][0]["selector"]["relative_path"] = "[ab].csv"
    ledger = evaluate(manifest, contract_doc)
    assert ledger.coverage().unmatched == 1
    assert "unused_rule" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_missing_and_multiply_matching_rules_are_rejected(inventory, contract_doc):
    document = copy.deepcopy(contract_doc)
    document["rules"].pop()
    coverage = evaluate(inventory, document).coverage()
    assert coverage.unmatched == 1 and coverage.percent == 50 and not coverage.conforms
    duplicate = copy.deepcopy(contract_doc["rules"][0])
    duplicate["rule_id"] = "another"
    contract_doc["rules"].append(duplicate)
    coverage = evaluate(inventory, contract_doc).coverage()
    assert coverage.multiple == 1 and not coverage.conforms


@pytest.mark.parametrize("field,value", [("sha256", "b" * 64), ("size", 4), ("signature", "sqlite"), ("kind", "directory")])
def test_stale_member_assertions_prevent_conformance(inventory, contract_doc, field, value):
    contract_doc["rules"][0]["expected"][field] = value
    if field == "kind":
        contract_doc["rules"][0]["disposition"] = "NON_TABULAR"
        contract_doc["rules"][0]["targets"] = []
    coverage = evaluate(inventory, contract_doc).coverage()
    assert coverage.unexplained == 1
    assert not coverage.conforms


def test_unused_rules_and_wrong_inventory_binding_are_rejected(inventory, contract_doc):
    extra = copy.deepcopy(contract_doc["rules"][1])
    extra["rule_id"] = "gone"
    extra["selector"]["relative_path"] = "gone"
    contract_doc["rules"].append(extra)
    ledger = evaluate(inventory, contract_doc)
    assert "unused_rule" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms
    contract_doc["rules"].pop()
    contract_doc["inventory_sha256"] = "a" * 64
    ledger = evaluate(inventory, contract_doc)
    assert "inventory_mismatch" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_blocked_member_is_accounted_for_but_cannot_pass(inventory, contract_doc):
    rule = contract_doc["rules"][0]
    rule.update(disposition="BLOCKED", targets=[], reason="Lossless reader not implemented")
    ledger = evaluate(inventory, contract_doc)
    assert ledger.coverage().percent == 100
    assert ledger.coverage().blocked == 1
    assert not ledger.coverage().conforms
    assert not ledger.ready_for_import


def test_inventory_errors_cannot_be_waived_by_non_tabular_disposition(inventory, contract_doc):
    inventory = replace(inventory, issues=(InventoryIssue("checksum_nul", "README", detail="count=1"),))
    contract_doc["inventory_sha256"] = inventory.sha256
    ledger = evaluate(inventory, contract_doc)
    assert "incomplete_inventory" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_frozen_review_allows_only_contract_gate_not_database_actions(inventory, contract_doc):
    contract_doc.update(status="frozen", review={"approved_by": "fixture-only", "approved_at": "2026-10-07T00:00:00Z", "approval_ref": "synthetic"})
    assert evaluate(inventory, contract_doc).ready_for_import


def test_empty_inventory_cannot_claim_vacuous_full_coverage(inventory, contract_doc):
    inventory = replace(inventory, entries=())
    contract_doc["inventory_sha256"] = inventory.sha256
    coverage = evaluate(inventory, contract_doc).coverage()
    assert coverage.total == 0 and coverage.percent == 0 and not coverage.conforms


def test_same_named_zip_members_are_matched_by_physical_ordinal(inventory, contract_doc):
    entries = (InventoryEntry("a.zip", ("same",), (0,), size=3, sha256=inventory.entries[0].sha256),
               InventoryEntry("a.zip", ("same",), (1,), size=0, sha256=inventory.entries[1].sha256))
    inventory = replace(inventory, entries=entries)
    contract_doc["inventory_sha256"] = inventory.sha256
    for rule, ordinal in zip(contract_doc["rules"], (0, 1)):
        rule["selector"] = {"relative_path": "a.zip", "archive_chain": ["same"], "archive_ordinals": [ordinal]}
    ledger = evaluate(inventory, contract_doc)
    assert ledger.coverage().matched == 2
    assert len(ledger.records) == 2


def test_directories_are_explicit_nonbusiness_members(inventory, contract_doc):
    inventory = replace(inventory, entries=(InventoryEntry("empty", kind="directory"),))
    contract_doc["inventory_sha256"] = inventory.sha256
    rule = contract_doc["rules"][1]
    rule["selector"]["relative_path"] = "empty"
    rule["expected"] = {"kind": "directory", "sha256": None, "size": None, "signature": "unknown"}
    contract_doc["rules"] = [rule]
    assert evaluate(inventory, contract_doc).coverage().conforms


def mirrored_fixture(inventory, contract_doc):
    inventory = replace(inventory, entries=(inventory.entries[0], replace(inventory.entries[0], relative_path="copy.csv")))
    mirror = copy.deepcopy(contract_doc["rules"][0])
    mirror.update(rule_id="mirror", disposition="MIRROR", targets=[], mirror_of="data", mirror_evidence_sha256="c" * 64, reason="Byte equality assertion with primary")
    mirror["selector"]["relative_path"] = "copy.csv"
    contract_doc["rules"] = [contract_doc["rules"][0], mirror]
    contract_doc["inventory_sha256"] = inventory.sha256
    return inventory, contract_doc


def test_explicit_mirror_requires_import_primary_and_identical_byte_assertions(inventory, contract_doc):
    inventory, contract_doc = mirrored_fixture(inventory, contract_doc)
    assert evaluate(inventory, contract_doc).coverage().conforms
    contract_doc["rules"][1]["expected"]["sha256"] = "b" * 64
    ledger = evaluate(inventory, contract_doc)
    assert "invalid_mirror" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


@pytest.mark.parametrize("primary", ["missing", "mirror"])
def test_missing_or_chained_mirror_primary_is_rejected(inventory, contract_doc, primary):
    inventory, contract_doc = mirrored_fixture(inventory, contract_doc)
    contract_doc["rules"][1]["mirror_of"] = primary
    assert not evaluate(inventory, contract_doc).coverage().conforms


def test_rule_and_inventory_order_do_not_change_ledger_evidence(inventory, contract_doc):
    first = evaluate(inventory, contract_doc)
    contract_doc["rules"].reverse()
    inventory = replace(inventory, entries=tuple(reversed(inventory.entries)))
    # Manifest canonical order is owned by the scanner; bind this constructed variant.
    contract_doc["inventory_sha256"] = inventory.sha256
    second = evaluate(inventory, contract_doc)
    assert first.records == second.records
    assert first.coverage() == second.coverage()


def test_identical_business_bytes_need_one_primary_and_explicit_mirrors(inventory, contract_doc):
    inventory, contract_doc = mirrored_fixture(inventory, contract_doc)
    rule = contract_doc["rules"][1]
    target = copy.deepcopy(contract_doc["rules"][0]["targets"][0])
    target["table"] = "synthetic__copy"
    rule.update(disposition="IMPORT", targets=[target], mirror_of=None, mirror_evidence_sha256=None)
    ledger = evaluate(inventory, contract_doc)
    assert "mirror_required" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_duplicate_business_target_is_rejected(inventory, contract_doc):
    rule = contract_doc["rules"][1]
    rule.update(disposition="IMPORT", targets=copy.deepcopy(contract_doc["rules"][0]["targets"]))
    ledger = evaluate(inventory, contract_doc)
    assert "target_collision" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_typed_model_copy_cannot_bypass_contract_gate(inventory, contract_doc):
    from xiangrugu_datamgmt.contracts import ReleaseContract
    from xiangrugu_datamgmt.disposition import DispositionLedger
    contract = ReleaseContract.model_validate(contract_doc).model_copy(update={"status": "frozen", "review": None})
    with pytest.raises(ValueError):
        DispositionLedger.evaluate(inventory, contract)


def test_duplicate_inventory_locations_cannot_claim_unique_coverage(inventory, contract_doc):
    inventory = replace(inventory, entries=(*inventory.entries, inventory.entries[0]))
    contract_doc["inventory_sha256"] = inventory.sha256
    ledger = evaluate(inventory, contract_doc)
    assert "duplicate_inventory_location" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_declared_nul_exception_does_not_silently_override_inventory(inventory, contract_doc):
    contract_doc["exceptions"] = [{"rule_id": "readme", "code": "checksum_nul", "raw_sha256": inventory.entries[1].sha256, "reason": "Synthetic declaration only"}]
    ledger = evaluate(inventory, contract_doc)
    assert "exception_not_implemented" in {issue.code for issue in ledger.issues}
    assert not ledger.coverage().conforms


def test_full_scan_to_contract_to_coverage_uses_real_synthetic_bytes(tmp_path):
    from xiangrugu_datamgmt.inventory import InventoryBuilder
    (tmp_path / "unknown.bin").write_bytes(b"abc")
    manifest = InventoryBuilder(temp_root="/tmp").scan(tmp_path)
    document = {"version": 1, "release_id": "2026-10-07-synthetic", "source_version": "fixture", "inventory_sha256": manifest.sha256,
                "status": "draft", "review": None, "rules": [{"rule_id": "unknown", "selector": {"relative_path": "unknown.bin"},
                "expected": {"kind": "file", "size": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "signature": "unknown"},
                "disposition": "BLOCKED", "reason": "Unknown carrier needs lossless reader", "format_family": "unknown", "encodings": [], "targets": [], "validator": "raw-byte-sha256-v1"}]}
    ledger = evaluate(manifest, document)
    assert ledger.coverage().matched == 1 and ledger.coverage().blocked == 1
    assert not ledger.ready_for_import
    assert ledger.canonical_bytes() == evaluate(manifest, document).canonical_bytes()
    assert ledger.sha256 == evaluate(manifest, document).sha256
