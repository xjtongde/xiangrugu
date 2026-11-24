#!/usr/bin/env python3
"""Formal write-off invocation + load-entry precheck with the updated frozen candidate.

Runs in the 32 isolated container. Inputs: original inventory.json (read-only),
raw ledger bytes from the verified read-only snapshot, updated frozen candidate.
Never modifies the inventory; never connects to any database.
"""
import hashlib
import json
import sys
from pathlib import Path

from xiangrugu_datamgmt.contracts import ReleaseContract
from xiangrugu_datamgmt.disposition import DispositionLedger
from xiangrugu_datamgmt.inventory import (ChecksumAssertion, InventoryEntry, InventoryIssue,
                                          InventoryManifest)
from xiangrugu_datamgmt.writeoff import ORIGINAL_INVENTORY_SHA256, run_writeoff

HERE = Path(__file__).resolve().parent


def rebuild_manifest(doc):
    entries = tuple(InventoryEntry(
        relative_path=e["relative_path"], archive_chain=tuple(e.get("archive_chain", ())),
        archive_ordinals=tuple(e.get("archive_ordinals", ())), kind=e.get("kind", "file"),
        size=e.get("size"), sha256=e.get("sha256"), signature=e.get("signature", "unknown"))
        for e in doc["entries"])
    issues = tuple(InventoryIssue(
        code=i["code"], relative_path=i["relative_path"],
        archive_chain=tuple(i.get("archive_chain", ())), archive_ordinals=tuple(i.get("archive_ordinals", ())),
        detail=i.get("detail", ""), blocking=i.get("blocking", True)) for i in doc["issues"])
    checksums = tuple(ChecksumAssertion(
        ledger=c["ledger"], line=c["line"], raw_name=c["raw_name"], target=c["target"],
        expected_sha256=c["expected_sha256"], matched=c["matched"],
        archive_chain=tuple(c.get("archive_chain", ())), archive_ordinals=tuple(c.get("archive_ordinals", ())))
        for c in doc["checksums"])
    limits = tuple(sorted((k, int(v)) for k, v in doc["limits"]))
    return InventoryManifest(entries=entries, issues=issues, checksums=checksums, limits=limits)


def main():
    inv_path, nul_path, chgis_path, cand_path = (Path(p) for p in sys.argv[1:5])
    inv_bytes = inv_path.read_bytes()
    manifest = rebuild_manifest(json.loads(inv_bytes))
    doc = json.loads(cand_path.read_text())
    contract = ReleaseContract.model_validate(doc)  # formal frozen entry
    raw_ledgers = {"SHA256SUMS-b2": nul_path.read_bytes(),
                   "harvard/chgis/SHA256SUMS.txt": chgis_path.read_bytes()}
    out = {"inventory_file_sha256": hashlib.sha256(inv_bytes).hexdigest(),
           "manifest_reconstructed_sha256": manifest.sha256,
           "original_inventory_lock": manifest.sha256 == ORIGINAL_INVENTORY_SHA256,
           "contract_inventory_binding": contract.inventory_sha256 == ORIGINAL_INVENTORY_SHA256,
           "contract_canonical_sha256": contract.sha256,
           "nul_raw_sha256": hashlib.sha256(raw_ledgers["SHA256SUMS-b2"]).hexdigest(),
           "chgis_raw_sha256": hashlib.sha256(raw_ledgers["harvard/chgis/SHA256SUMS.txt"]).hexdigest(),
           "formal_frozen_parse": "PASS"}
    result = run_writeoff(manifest, contract, raw_ledgers)
    out["writeoff_result"] = result
    out["closed_issue_count"] = len(result["closed_issues"])
    out["exactly_three_fixed_closed"] = sorted(
        (i["code"], i["detail"], i["relative_path"]) for i in result["closed_issues"]) == [
        ("checksum_line", "line=173", "SHA256SUMS-b2"),
        ("checksum_missing", "line=4", "harvard/chgis/SHA256SUMS.txt"),
        ("checksum_nul", "count=126", "SHA256SUMS-b2")]
    out["original_complete_false_preserved"] = manifest.complete is False
    out["inventory_bytes_untouched"] = hashlib.sha256(inv_path.read_bytes()).hexdigest() == out["inventory_file_sha256"]
    (HERE / "nul-evidence.json").write_text(json.dumps(result["run_evidence"]["nul"], ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    (HERE / "chgis-evidence.json").write_text(json.dumps(result["run_evidence"]["chgis"], ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    (HERE / "writeoff-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    ledger = DispositionLedger.evaluate(manifest, contract, raw_ledgers)
    cov = ledger.coverage()
    uncovered = sorted(r.member.relative_path for r in ledger.records if not r.rule_ids)
    (HERE / "uncovered-members.txt").write_text("\n".join(uncovered) + "\n")
    first_batch = [r for r in contract.rules if r.rule_id.startswith("m00")]
    load_check = {
        "formal_batch_entry": "batch_execution.execute_batch（approved-readonly-batch-v1）",
        "entry_gates_verbatim": {
            "scope_authority": "source_read_authorized=False, synthetic_data_authorized=True, postgresql_authorized=False, ready_for_import=False",
            "invalid_staging": "result.ready_for_import=False, postgresql_connected=False",
            "consequence": "现役正式批入口为只读合成面；PG 写入路径结构性关闭"},
        "production_loader": "GAP：PG 生产装载器未实现（importer/load.py 仅 staging 原型且须修订，禁直跑；IMPORT-PACKAGE-TODO 未决项①）",
        "first_batch_rules": len(first_batch),
        "coverage": {"total": cov.total, "matched": cov.matched, "unmatched": cov.unmatched,
                      "multiple": cov.multiple, "unexplained": cov.unexplained, "blocked": cov.blocked},
        "uncovered_member_count": len(uncovered),
        "uncovered_list_ref": "uncovered-members.txt",
        "ledger_issue_codes": sorted({i.code for i in ledger.issues}),
        "ledger_ready_for_import": ledger.ready_for_import,
        "derived_issue_codes": result["derived_issue_codes"],
        "writeoff_ready_for_import": result["ready_for_import"],
        "first_actual_blocker": "PG 生产装载器未实现（loader GAP）；叠加 ready_for_import=False（unmatched_member 派生阻断）与 postgresql_authorized=False（装载授权事件未到）",
        "closure_conditions": [
            "①装载授权事件（茶香另行批准，postgresql_authorized 翻正）",
            "②PG 生产装载器实现并通过隔离试装→正式验收（loader GAP 关闭）",
            "③全成员处置覆盖（8004 成员逐一定处置，unmatched_member 清零）或经批准的处置范围合同",
            "④两条例外已入本冻结候选（本盒完成）；核销结果≠写库批准，装载门保持"],
        "database_connected": False}
    (HERE / "load-entry-check.json").write_text(json.dumps(load_check, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    (HERE / "writeoff-call-report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("WO_EXIT_OK closed", out["closed_issue_count"], "exactly3", out["exactly_three_fixed_closed"],
          "complete_false", out["original_complete_false_preserved"],
          "derived", result["derived_issue_codes"], "ready", result["ready_for_import"],
          "coverage", cov.total, cov.matched, cov.unmatched)


if __name__ == "__main__":
    main()