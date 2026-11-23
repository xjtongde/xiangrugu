"""Task 6 write-off evaluator tests: derived result only, original inventory preserved."""
from dataclasses import replace

import pytest

import test_checksum_reader as t
from xiangrugu_datamgmt import writeoff
from xiangrugu_datamgmt.contracts import (ContractException, DispositionRule, MemberExpectation,
                                          MemberSelector, ReleaseContract)
from xiangrugu_datamgmt.inventory import InventoryIssue
from xiangrugu_datamgmt.model import Disposition

BOTH_INPUTS = {"SHA256SUMS-b2": t._raw(), t.CHGIS_LEDGER: t._chgis_raw()}


def _both_contract(manifest, status="frozen", approval_ref="task6-writeoff-isolated-box"):
    from xiangrugu_datamgmt.contracts import ContractReview
    return ReleaseContract(
        version=1, release_id="2026-10-06-bootstrap", source_version="usedata-2026-10-07",
        inventory_sha256=manifest.sha256, status=status,
        review=ContractReview(approved_by="chaxiang", approved_at="2026-11-23T15:40:00Z",
                              approval_ref=approval_ref) if status == "frozen" else None,
        exceptions=(t._exception(), t._chgis_exception()),
        rules=(t._b2_rule(), t._chgis_rule()))


def _fixed_issue(fixed):
    return InventoryIssue(code=fixed["code"], relative_path=fixed["relative_path"],
                          detail=fixed["detail"], blocking=True)


def test_positive_writeoff_only_the_three_fixed_issues():
    manifest = t._inventory()
    before_sha, before_issues, before_complete = manifest.sha256, manifest.issues, manifest.complete
    contract = _both_contract(manifest)
    result = writeoff.run_writeoff(manifest, contract, BOTH_INPUTS)
    assert result["status"] == "WRITEOFF_RESULT_DERIVED"
    assert result["contract_sha256"] == contract.sha256
    assert result["inventory_sha256"] == manifest.sha256
    assert len(result["run_evidence_sha256"]["nul"]) == 64
    assert len(result["run_evidence_sha256"]["chgis"]) == 64
    # both freshly generated evidence bodies are retrievable and recomputable
    assert writeoff._evidence_sha256(result["run_evidence"]["nul"]) == result["run_evidence_sha256"]["nul"]
    assert writeoff._evidence_sha256(result["run_evidence"]["chgis"]) == result["run_evidence_sha256"]["chgis"]
    assert result["run_evidence"]["nul"]["contract_sha256"] == contract.sha256
    assert result["run_evidence"]["chgis"]["contract_sha256"] == contract.sha256
    closed = {(c["code"], c["detail"], c["relative_path"]) for c in result["closed_issues"]}
    assert closed == {("checksum_line", "line=173", "SHA256SUMS-b2"),
                      ("checksum_nul", "count=126", "SHA256SUMS-b2"),
                      ("checksum_missing", "line=4", "harvard/chgis/SHA256SUMS.txt")}
    assert result["incomplete_inventory_written_off"] is True
    assert result["derived_issue_codes"] == ["unmatched_member"]
    assert result["ready_for_import"] is False
    assert result["original_ledger_ready_for_import"] is False
    assert result["original_inventory_complete"] is False
    # original inventory preserved byte-for-byte
    assert manifest.sha256 == before_sha
    assert manifest.issues == before_issues
    assert manifest.complete is before_complete is False


def test_negative_substitute_inventory_same_three_issues():
    # Formerly the "three-member test inventory can be written off" positive;
    # the write-off scope is now locked to the audited original inventory, so a
    # substitute inventory carrying the same three issues must be refused.
    manifest = t._inventory()
    paths = {"SHA256SUMS-b2", "harvard/chgis/SHA256SUMS.txt", "chgis-v6/China_Periods_ReignDates.zip"}
    entries = tuple(e for e in manifest.entries if e.relative_path in paths and not e.archive_chain)
    checksums = tuple(c for c in manifest.checksums
                    if c.ledger in {"SHA256SUMS-b2", "harvard/chgis/SHA256SUMS.txt"})
    issues = tuple(_fixed_issue(fixed) for fixed in writeoff.FIXED_ISSUES)
    synthetic = replace(manifest, entries=entries, checksums=checksums, issues=issues)
    assert synthetic.sha256 != writeoff.ORIGINAL_INVENTORY_SHA256
    target = next(e for e in entries if e.relative_path == "chgis-v6/China_Periods_ReignDates.zip")
    zip_rule = DispositionRule(
        rule_id="r-chgis-target-zip",
        selector=MemberSelector(relative_path="chgis-v6/China_Periods_ReignDates.zip"),
        expected=MemberExpectation(kind="file", sha256=t.TARGET_SHA, size=155774,
                                   signature=target.signature),
        disposition=Disposition.NON_TABULAR, reason="target member retained pending spatial load",
        format_family="zip_archive", encodings=(), targets=(), validator="none")
    contract = t._chgis_contract(synthetic, exceptions=(t._exception(), t._chgis_exception()),
                                 rules=(t._b2_rule(), t._chgis_rule(), zip_rule))
    with pytest.raises(ValueError):
        writeoff.run_writeoff(synthetic, contract, BOTH_INPUTS)


def test_negative_contract_binds_substitute_digest():
    manifest = t._inventory()
    contract = _both_contract(manifest).model_copy(update={"inventory_sha256": "1" * 64})
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, contract, BOTH_INPUTS)


def test_negative_missing_one_evidence():
    manifest = t._inventory()
    contract = _both_contract(manifest)
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, contract, {t.CHGIS_LEDGER: t._chgis_raw()})
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, contract, {"SHA256SUMS-b2": t._raw()})


def test_negative_cross_contract_evidence_cannot_be_reused():
    manifest = t._inventory()
    contract_a = _both_contract(manifest, approval_ref="box-a")
    contract_b = _both_contract(manifest, approval_ref="box-b")
    assert contract_a.sha256 != contract_b.sha256
    result_a = writeoff.run_writeoff(manifest, contract_a, BOTH_INPUTS)
    result_b = writeoff.run_writeoff(manifest, contract_b, BOTH_INPUTS)
    assert result_a["contract_sha256"] == contract_a.sha256
    assert result_b["contract_sha256"] == contract_b.sha256
    assert result_a["run_evidence_sha256"] != result_b["run_evidence_sha256"]
    wrong_binding = contract_b.model_copy(update={"inventory_sha256": "0" * 64})
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, wrong_binding, BOTH_INPUTS)


def test_negative_inventory_digest_change():
    manifest = t._inventory()
    contract = _both_contract(manifest).model_copy(update={"inventory_sha256": "0" * 64})
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, contract, BOTH_INPUTS)


def test_negative_added_issue():
    manifest = t._inventory()
    extra = InventoryIssue(code="checksum_line", relative_path="other-ledger.txt", detail="line=9")
    variant = replace(manifest, issues=manifest.issues + (extra,))
    contract = _both_contract(variant)
    with pytest.raises(ValueError):
        writeoff.run_writeoff(variant, contract, BOTH_INPUTS)


def test_negative_duplicated_issue():
    manifest = t._inventory()
    variant = replace(manifest, issues=manifest.issues + (manifest.issues[0],))
    contract = _both_contract(variant)
    with pytest.raises(ValueError):
        writeoff.run_writeoff(variant, contract, BOTH_INPUTS)


def test_negative_missing_issue():
    manifest = t._inventory()
    variant = replace(manifest, issues=manifest.issues[:2])
    contract = _both_contract(variant)
    with pytest.raises(ValueError):
        writeoff.run_writeoff(variant, contract, BOTH_INPUTS)


def test_negative_unapproved():
    manifest = t._inventory()
    contract = _both_contract(manifest, status="draft")
    with pytest.raises(ValueError):
        writeoff.run_writeoff(manifest, contract, BOTH_INPUTS)


def test_unmatched_member_keeps_blocking():
    manifest = t._inventory()
    contract = _both_contract(manifest)
    result = writeoff.run_writeoff(manifest, contract, BOTH_INPUTS)
    assert "unmatched_member" in result["derived_issue_codes"]
    assert result["ready_for_import"] is False