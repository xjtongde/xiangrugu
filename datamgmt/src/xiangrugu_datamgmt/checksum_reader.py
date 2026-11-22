"""Task 6 narrow-scope runtime reader: the single fixed-digest trailing-NUL exception.

The whitelist is exactly one fixed ledger identity (SHA256SUMS-b2). Verification
reuses checksum_candidates.preview_checksum_candidates unchanged; nothing here
generalizes to other ledgers, digests, or exception kinds. Approval (a frozen
contract with its review record) and exact raw bytes are mandatory; any mismatch
keeps the exception_not_implemented block. The CHGIS path-binding exception is
separately pending implementation and is never closed by this reader.

This module never opens files: the caller supplies raw ledger bytes from a
verified read-only snapshot. It does not modify strict inventory evidence;
inventory.complete=False keeps incomplete_inventory and ready_for_import=False.
"""
from .checksum_candidates import (ChecksumCandidates, PathBindingCandidate, TrailingNulCandidate,
                                  preview_checksum_candidates)

NUL_EXCEPTION_WHITELIST = {
    "ledger": "SHA256SUMS-b2",
    "raw_sha256": "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb",
    "raw_size": 22071,
    "valid_lines": 172,
    "trailing_nul_bytes": 126,
    "tail_offset": 21945,
}


def _whitelisted_rule(exception, contract):
    fixed = NUL_EXCEPTION_WHITELIST
    if exception.code != "checksum_nul" or exception.raw_sha256 != fixed["raw_sha256"]:
        return None
    rule = next((r for r in contract.rules if r.rule_id == exception.rule_id), None)
    if rule is None or rule.selector.location[0] != fixed["ledger"]:
        return None
    return rule


def run_fixed_nul_exception(manifest, contract, raw_ledgers):
    """Return machine evidence for the single whitelisted NUL exception.

    Raises ValueError on any mismatch (the caller keeps the block). The evidence
    binds the exact contract and inventory digests plus the per-record results.
    """
    fixed = NUL_EXCEPTION_WHITELIST
    if contract.status != "frozen" or contract.review is None:
        raise ValueError("fixed NUL exception requires an approved frozen contract")
    matches = [e for e in contract.exceptions
               if e.code == "checksum_nul" and e.raw_sha256 == fixed["raw_sha256"]]
    if len(matches) != 1:
        raise ValueError("exactly one whitelisted NUL exception declaration required")
    exception = matches[0]
    rule = _whitelisted_rule(exception, contract)
    if rule is None:
        raise ValueError("exception rule must target the fixed ledger identity")
    if manifest.sha256 != contract.inventory_sha256:
        raise ValueError("input inventory digest differs from the contract binding")
    if rule.selector.location != (fixed["ledger"], (), ()):
        raise ValueError("exception rule must select the exact outer ledger location")
    if (rule.expected.kind, rule.expected.size, rule.expected.sha256) != (
            "file", fixed["raw_size"], fixed["raw_sha256"]):
        raise ValueError("exception rule expectations differ from the fixed identity")
    candidate = TrailingNulCandidate(
        rule_id=exception.rule_id, ledger=fixed["ledger"], raw_sha256=fixed["raw_sha256"],
        raw_size=fixed["raw_size"], reason=exception.reason, kind="trailing_nul",
        valid_lines=fixed["valid_lines"], trailing_nul_bytes=fixed["trailing_nul_bytes"])
    candidates = ChecksumCandidates(
        version=1, status="draft", release_id=contract.release_id,
        source_version=contract.source_version, inventory_sha256=manifest.sha256,
        rules=(candidate,))
    preview = preview_checksum_candidates(manifest, candidates,
                                          {fixed["ledger"]: raw_ledgers.get(fixed["ledger"])})
    check = preview["checks"][0]
    if check["tail_offset"] != fixed["tail_offset"]:
        raise ValueError("trailing NUL offset differs from the fixed identity")
    return {"version": 1, "status": "RUN_EVIDENCE_FIXED_EXCEPTION",
            "exception_rule_id": exception.rule_id, "exception_code": exception.code,
            "contract_sha256": contract.sha256, "inventory_sha256": manifest.sha256,
            "ledger": fixed["ledger"], "raw_sha256": fixed["raw_sha256"],
            "raw_size": fixed["raw_size"], "valid_lines": check["valid_lines"],
            "trailing_nul_bytes": check["trailing_nul_bytes"],
            "tail_offset": check["tail_offset"],
            "prefix_assertions_matched": check["prefix_assertions_matched"],
            "strict_inventory_complete": manifest.complete,
            "ready_for_import": False}


def nul_exception_closed(exception, contract, manifest, raw_ledgers):
    """True only when this declared exception is the fixed NUL case and verifies."""
    if _whitelisted_rule(exception, contract) is None:
        return False
    if contract.status != "frozen" or contract.review is None:
        return False
    try:
        evidence = run_fixed_nul_exception(manifest, contract, raw_ledgers)
    except (ValueError, TypeError, KeyError):
        return False
    return evidence["exception_rule_id"] == exception.rule_id


PATH_BINDING_WHITELIST = {
    "ledger": "harvard/chgis/SHA256SUMS.txt",
    "raw_sha256": "694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60",
    "raw_size": 551,
    "line": 4,
    "raw_name": "China_Periods_ReignDates.zip",
    "declared_target": "harvard/chgis/China_Periods_ReignDates.zip",
    "resolved_target": "chgis-v6/China_Periods_ReignDates.zip",
    "expected_sha256": "7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e",
    "expected_size": 155774,
}


def _path_whitelisted_rule(exception, contract):
    fixed = PATH_BINDING_WHITELIST
    if exception.code != "checksum_path_binding" or exception.raw_sha256 != fixed["raw_sha256"]:
        return None
    rule = next((r for r in contract.rules if r.rule_id == exception.rule_id), None)
    if rule is None or rule.selector.location[0] != fixed["ledger"]:
        return None
    return rule


def run_fixed_path_binding_exception(manifest, contract, raw_ledgers):
    """Return machine evidence for the single whitelisted line-4 path binding.

    The original declaration and the explicit resolved binding are both kept in
    the evidence. Raises ValueError on any mismatch (the caller keeps the block).
    """
    fixed = PATH_BINDING_WHITELIST
    if contract.status != "frozen" or contract.review is None:
        raise ValueError("fixed path-binding exception requires an approved frozen contract")
    matches = [e for e in contract.exceptions
               if e.code == "checksum_path_binding" and e.raw_sha256 == fixed["raw_sha256"]]
    if len(matches) != 1:
        raise ValueError("exactly one whitelisted path-binding exception declaration required")
    exception = matches[0]
    rule = _path_whitelisted_rule(exception, contract)
    if rule is None:
        raise ValueError("exception rule must target the fixed source ledger identity")
    if manifest.sha256 != contract.inventory_sha256:
        raise ValueError("input inventory digest differs from the contract binding")
    if rule.selector.location != (fixed["ledger"], (), ()):
        raise ValueError("exception rule must select the exact outer ledger location")
    if (rule.expected.kind, rule.expected.size, rule.expected.sha256) != (
            "file", fixed["raw_size"], fixed["raw_sha256"]):
        raise ValueError("exception rule expectations differ from the fixed identity")
    candidate = PathBindingCandidate(
        rule_id=exception.rule_id, ledger=fixed["ledger"], raw_sha256=fixed["raw_sha256"],
        raw_size=fixed["raw_size"], reason=exception.reason, kind="exact_path_binding",
        line=fixed["line"], raw_name=fixed["raw_name"],
        declared_target=fixed["declared_target"], resolved_target=fixed["resolved_target"],
        expected_sha256=fixed["expected_sha256"], expected_size=fixed["expected_size"])
    candidates = ChecksumCandidates(
        version=1, status="draft", release_id=contract.release_id,
        source_version=contract.source_version, inventory_sha256=manifest.sha256,
        rules=(candidate,))
    preview = preview_checksum_candidates(manifest, candidates,
                                          {fixed["ledger"]: raw_ledgers.get(fixed["ledger"])})
    check = preview["checks"][0]
    return {"version": 1, "status": "RUN_EVIDENCE_FIXED_EXCEPTION",
            "exception_rule_id": exception.rule_id, "exception_code": exception.code,
            "contract_sha256": contract.sha256, "inventory_sha256": manifest.sha256,
            "ledger": fixed["ledger"], "raw_sha256": fixed["raw_sha256"],
            "raw_size": fixed["raw_size"], "line": check["line"],
            "raw_name": check["raw_name"],
            "declared_target": check["declared_target"],
            "resolved_target": check["resolved_target"],
            "expected_sha256": check["expected_sha256"],
            "expected_size": check["expected_size"],
            "strict_assertion_matched": check["strict_assertion_matched"],
            "strict_inventory_complete": manifest.complete,
            "ready_for_import": False}


def path_exception_closed(exception, contract, manifest, raw_ledgers):
    """True only when this declared exception is the fixed path binding and verifies."""
    if _path_whitelisted_rule(exception, contract) is None:
        return False
    if contract.status != "frozen" or contract.review is None:
        return False
    try:
        evidence = run_fixed_path_binding_exception(manifest, contract, raw_ledgers)
    except (ValueError, TypeError, KeyError):
        return False
    return evidence["exception_rule_id"] == exception.rule_id