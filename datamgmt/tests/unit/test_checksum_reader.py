"""Task 6 fixed-digest NUL run gate: positive, negative, and backward-compat cases.

Fixture provenance: tests/fixtures/sha256sums-b2.b64 is the base64 of the exact
22071-byte SHA256SUMS-b2 ledger read only from the 32 snapshot
/data/imports/usedata/2026-10-07-bootstrap; raw sha256
900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb, 172 valid
records, 126 trailing NUL bytes starting at offset 21945. The source file is
never modified. The real inventory (complete=False preserved) is loaded from
contracts/releases/2026-10-06-bootstrap/inventory.json.
"""
import base64
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from xiangrugu_datamgmt import checksum_reader
from xiangrugu_datamgmt.checksum_candidates import (ChecksumCandidates, TrailingNulCandidate,
                                                    preview_checksum_candidates)
from xiangrugu_datamgmt.contracts import (ContractException, ContractReview, DispositionRule,
                                          MemberExpectation, MemberSelector, ReleaseContract)
from xiangrugu_datamgmt.disposition import DispositionLedger
from xiangrugu_datamgmt.inventory import (ChecksumAssertion, InventoryEntry, InventoryIssue,
                                          InventoryManifest)
from xiangrugu_datamgmt.model import Disposition

FIXED_SHA = "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb"
ROOT = Path(__file__).resolve().parents[2]


def _raw():
    return base64.b64decode((ROOT / "tests/fixtures/sha256sums-b2.b64").read_text())


def _inventory():
    doc = json.loads((ROOT / "contracts/releases/2026-10-06-bootstrap/inventory.json").read_text())
    entries = tuple(InventoryEntry(
        relative_path=e["relative_path"], archive_chain=tuple(e.get("archive_chain", ())),
        archive_ordinals=tuple(e.get("archive_ordinals", ())), kind=e["kind"],
        size=e.get("size"), sha256=e.get("sha256"), signature=e.get("signature", "unknown"))
        for e in doc["entries"])
    issues = tuple(InventoryIssue(
        code=i["code"], relative_path=i["relative_path"],
        archive_chain=tuple(i.get("archive_chain", ())),
        archive_ordinals=tuple(i.get("archive_ordinals", ())),
        detail=i.get("detail", ""), blocking=i.get("blocking", True)) for i in doc["issues"])
    checksums = tuple(ChecksumAssertion(
        ledger=c["ledger"], line=c["line"], raw_name=c["raw_name"], target=c["target"],
        expected_sha256=c["expected_sha256"], matched=c["matched"],
        archive_chain=tuple(c.get("archive_chain", ())),
        archive_ordinals=tuple(c.get("archive_ordinals", ()))) for c in doc["checksums"])
    limits = tuple(sorted((k, int(v)) for k, v in doc["limits"]))
    return InventoryManifest(entries=entries, issues=issues, checksums=checksums, limits=limits)


def _exception(raw_sha256=FIXED_SHA, rule_id="r-sha256sums-b2"):
    return ContractException(rule_id=rule_id, code="checksum_nul", raw_sha256=raw_sha256,
                             reason="126 trailing NUL bytes under the fixed digest")


def _contract(manifest, status="frozen", exceptions=None):
    rule = DispositionRule(
        rule_id="r-sha256sums-b2", selector=MemberSelector(relative_path="SHA256SUMS-b2"),
        expected=MemberExpectation(kind="file", sha256=FIXED_SHA, size=22071, signature="unknown"),
        disposition=Disposition.NON_TABULAR, reason="checksum ledger retained as evidence",
        format_family="checksum_ledger", encodings=(), targets=(), validator="none")
    return ReleaseContract(
        version=1, release_id="2026-10-06-bootstrap", source_version="usedata-2026-10-07",
        inventory_sha256=manifest.sha256, status=status,
        review=ContractReview(approved_by="chaxiang", approved_at="2026-11-22T18:40:00Z",
                              approval_ref="task6-nul-gate-isolated-box") if status == "frozen" else None,
        exceptions=tuple(exceptions if exceptions is not None else (_exception(),)),
        rules=(rule,))


def _codes(ledger):
    return {issue.code for issue in ledger.issues}


def test_fixture_identity():
    raw = _raw()
    assert len(raw) == 22071
    assert __import__("hashlib").sha256(raw).hexdigest() == FIXED_SHA
    assert raw[21945:] == b"\x00" * 126
    assert b"\x00" not in raw[:21945]


def test_positive_run_evidence_binds_contract_and_inventory():
    manifest = _inventory()
    assert manifest.complete is False  # original preserved state
    contract = _contract(manifest)
    evidence = checksum_reader.run_fixed_nul_exception(manifest, contract, {"SHA256SUMS-b2": _raw()})
    assert evidence["contract_sha256"] == contract.sha256
    assert evidence["inventory_sha256"] == manifest.sha256
    assert evidence["valid_lines"] == 172
    assert evidence["prefix_assertions_matched"] == 172
    assert evidence["trailing_nul_bytes"] == 126
    assert evidence["tail_offset"] == 21945
    assert evidence["strict_inventory_complete"] is False
    assert evidence["ready_for_import"] is False


def test_positive_gate_closes_only_this_exception():
    manifest = _inventory()
    contract = _contract(manifest)
    ledger = DispositionLedger.evaluate(manifest, contract, {"SHA256SUMS-b2": _raw()})
    assert "exception_not_implemented" not in _codes(ledger)
    assert "incomplete_inventory" in _codes(ledger)  # complete=False preserved
    assert ledger.ready_for_import is False


def test_negative_unapproved_draft_keeps_block():
    manifest = _inventory()
    contract = _contract(manifest, status="draft")
    with pytest.raises(ValueError):
        checksum_reader.run_fixed_nul_exception(manifest, contract, {"SHA256SUMS-b2": _raw()})
    ledger = DispositionLedger.evaluate(manifest, contract, {"SHA256SUMS-b2": _raw()})
    assert "exception_not_implemented" in _codes(ledger)
    assert ledger.ready_for_import is False


def test_negative_frozen_without_review_rejected_by_model():
    manifest = _inventory()
    with pytest.raises(ValidationError):
        ReleaseContract.model_validate(
            _contract(manifest).model_dump(by_alias=True) | {"review": None})


def test_negative_carrier_digest_mismatch():
    manifest = _inventory()
    contract = _contract(manifest)
    bad = bytearray(_raw())
    bad[10] ^= 0xFF  # tamper one prefix byte; size unchanged, digest differs
    with pytest.raises(ValueError):
        checksum_reader.run_fixed_nul_exception(manifest, contract, {"SHA256SUMS-b2": bytes(bad)})
    ledger = DispositionLedger.evaluate(manifest, contract, {"SHA256SUMS-b2": bytes(bad)})
    assert "exception_not_implemented" in _codes(ledger)


def test_negative_mid_file_nul():
    manifest = _inventory()
    contract = _contract(manifest)
    bad = bytearray(_raw())
    bad[100] = 0  # NUL inside the prefix, tail untouched
    with pytest.raises(ValueError):
        checksum_reader.run_fixed_nul_exception(manifest, contract, {"SHA256SUMS-b2": bytes(bad)})
    assert checksum_reader.nul_exception_closed(contract.exceptions[0], contract, manifest,
                                                {"SHA256SUMS-b2": bytes(bad)}) is False


def test_negative_record_count_mismatch():
    manifest = _inventory()
    contract = _contract(manifest)
    raw = _raw()
    prefix, tail = raw[:21945], raw[21945:]
    lines = prefix[:-1].split(b"\n")
    short = b"\n".join(lines[:-1]) + b"\n"  # 171 records
    variant = short + b"\x00" * (22071 - len(short))
    with pytest.raises(ValueError):
        checksum_reader.run_fixed_nul_exception(manifest, contract, {"SHA256SUMS-b2": variant})
    # exercise the reused line-count branch directly against the real bytes
    candidate = TrailingNulCandidate(rule_id="r-sha256sums-b2", ledger="SHA256SUMS-b2",
                                     raw_sha256=FIXED_SHA, raw_size=22071, reason="probe",
                                     kind="trailing_nul", valid_lines=171, trailing_nul_bytes=126)
    candidates = ChecksumCandidates(version=1, status="draft", release_id="2026-10-06-bootstrap",
                                    source_version="usedata-2026-10-07",
                                    inventory_sha256=manifest.sha256, rules=(candidate,))
    with pytest.raises(ValueError):
        preview_checksum_candidates(manifest, candidates, {"SHA256SUMS-b2": raw})


def test_negative_other_inventory_anomalies_still_block():
    manifest = _inventory()
    contract = _contract(manifest)
    ledger = DispositionLedger.evaluate(manifest, contract, {"SHA256SUMS-b2": _raw()})
    assert "incomplete_inventory" in _codes(ledger)
    assert ledger.ready_for_import is False
    assert manifest.complete is False


def test_negative_chgis_declaration_stays_pending():
    manifest = _inventory()
    chgis = _exception(raw_sha256="7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e",
                       rule_id="r-sha256sums-b2")
    contract = _contract(manifest, exceptions=(_exception(), chgis))
    ledger = DispositionLedger.evaluate(manifest, contract, {"SHA256SUMS-b2": _raw()})
    assert "exception_not_implemented" in _codes(ledger)  # non-whitelist keeps the block
    assert ledger.ready_for_import is False


def test_negative_missing_raw_bytes():
    manifest = _inventory()
    contract = _contract(manifest)
    with pytest.raises(ValueError):
        checksum_reader.run_fixed_nul_exception(manifest, contract, {})


def test_backward_compat_no_inputs_keeps_old_behavior():
    manifest = _inventory()
    contract = _contract(manifest)
    ledger = DispositionLedger.evaluate(manifest, contract)
    assert "exception_not_implemented" in _codes(ledger)
    no_exc = _contract(manifest, exceptions=())
    ledger2 = DispositionLedger.evaluate(manifest, no_exc)
    assert "exception_not_implemented" not in _codes(ledger2)