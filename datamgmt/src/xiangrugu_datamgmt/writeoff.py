"""Derived write-off for the three fixed inventory issues.

The original inventory is never modified: its bytes, digest, issues and
complete=false are preserved. The write-off result is a separate derived
artifact bound to the contract, the original inventory and freshly regenerated
run evidence for both fixed exceptions. Only the exact three issue identities,
each occurring once, under an approved frozen contract may be written off;
any extra, duplicated, missing or mismatched issue keeps the block. All other
disposition and load gates are evaluated as usual.
"""
import hashlib
import json

from . import checksum_reader
from .disposition import DispositionLedger

FIXED_ISSUES = (
    {"code": "checksum_line", "detail": "line=173", "relative_path": "SHA256SUMS-b2",
     "archive_chain": (), "archive_ordinals": (), "blocking": True},
    {"code": "checksum_nul", "detail": "count=126", "relative_path": "SHA256SUMS-b2",
     "archive_chain": (), "archive_ordinals": (), "blocking": True},
    {"code": "checksum_missing", "detail": "line=4", "relative_path": "harvard/chgis/SHA256SUMS.txt",
     "archive_chain": (), "archive_ordinals": (), "blocking": True},
)

# The write-off scope is locked to the audited original inventory; a substitute
# inventory carrying the same three issues must never be written off.
ORIGINAL_INVENTORY_SHA256 = "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db"


def _issue_key(issue):
    return (issue.code, issue.detail, issue.relative_path,
            tuple(issue.archive_chain), tuple(issue.archive_ordinals), issue.blocking)


def _fixed_key(fixed):
    return (fixed["code"], fixed["detail"], fixed["relative_path"],
            tuple(fixed["archive_chain"]), tuple(fixed["archive_ordinals"]), fixed["blocking"])


def _evidence_sha256(evidence):
    payload = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_writeoff(manifest, contract, raw_ledgers):
    """Return the derived write-off result; raise ValueError on any mismatch.

    Re-runs both fixed exceptions on the normal contract verification path with
    the same contract and the original inventory, so the evidence always binds
    the contract actually presented (cross-contract evidence cannot be reused).
    """
    if contract.status != "frozen" or contract.review is None:
        raise ValueError("write-off requires an approved frozen contract")
    if manifest.sha256 != ORIGINAL_INVENTORY_SHA256:
        raise ValueError("write-off scope is locked to the audited original inventory digest")
    if contract.inventory_sha256 != ORIGINAL_INVENTORY_SHA256:
        raise ValueError("contract must bind the audited original inventory digest")
    observed = sorted(_issue_key(issue) for issue in manifest.issues)
    expected = sorted(_fixed_key(fixed) for fixed in FIXED_ISSUES)
    if observed != expected:
        raise ValueError("inventory issues must be exactly the three fixed identities, each once")
    nul_evidence = checksum_reader.run_fixed_nul_exception(manifest, contract, raw_ledgers)
    chgis_evidence = checksum_reader.run_fixed_path_binding_exception(manifest, contract, raw_ledgers)
    ledger = DispositionLedger.evaluate(manifest, contract, raw_ledgers)
    if "exception_not_implemented" in {issue.code for issue in ledger.issues}:
        raise ValueError("exception gate still blocking; write-off refused")
    derived_codes = sorted({issue.code for issue in ledger.issues} - {"incomplete_inventory"})
    coverage = ledger.coverage()
    derived_ready = (contract.status == "frozen" and not derived_codes and coverage.total > 0
                     and coverage.matched == coverage.total
                     and not (coverage.unmatched or coverage.multiple or coverage.unexplained
                              or coverage.blocked))
    return {"version": 1, "status": "WRITEOFF_RESULT_DERIVED",
            "contract_sha256": contract.sha256, "inventory_sha256": manifest.sha256,
            "run_evidence_sha256": {"nul": _evidence_sha256(nul_evidence),
                                    "chgis": _evidence_sha256(chgis_evidence)},
            "run_evidence": {"nul": nul_evidence, "chgis": chgis_evidence},
            "closed_issues": [dict(fixed, archive_chain=list(fixed["archive_chain"]),
                                   archive_ordinals=list(fixed["archive_ordinals"]))
                              for fixed in FIXED_ISSUES],
            "original_inventory_complete": manifest.complete,
            "incomplete_inventory_written_off": True,
            "derived_issue_codes": derived_codes,
            "ready_for_import": derived_ready,
            "original_ledger_ready_for_import": ledger.ready_for_import}