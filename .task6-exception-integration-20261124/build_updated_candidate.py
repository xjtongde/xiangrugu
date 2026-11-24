#!/usr/bin/env python3
"""Build the updated frozen candidate: approved seven business rules unchanged + two fixed exceptions.

Stdlib-only construction; formal validation runs in the 32 isolated env.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PREV = REPO / ".task6-approval-freeze-20261124" / "frozen-candidate.json"
APPROVAL = json.loads((HERE / "approval-record.json").read_text())

NUL_RAW_SHA = "900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb"
CHGIS_RAW_SHA = "694c101f04e636012e752c87958c8065c8e6926633c8b542e89978d8f8451a60"


def ledger_rule(rule_id, path, sha, size):
    return {"rule_id": rule_id,
            "selector": {"relative_path": path, "archive_chain": [], "archive_ordinals": []},
            "expected": {"kind": "file", "sha256": sha, "size": size, "signature": "unknown"},
            "disposition": "NON_TABULAR", "reason": "checksum ledger retained as evidence",
            "format_family": "checksum_ledger", "encodings": [], "targets": [], "validator": "none"}


def main():
    prev = json.loads(PREV.read_text())
    doc = json.loads(PREV.read_text())
    business = [r for r in prev["rules"]]
    doc["rules"] = business + [
        ledger_rule("r-sha256sums-b2", "SHA256SUMS-b2", NUL_RAW_SHA, 22071),
        ledger_rule("r-chgis-sha256sums", "harvard/chgis/SHA256SUMS.txt", CHGIS_RAW_SHA, 551)]
    doc["exceptions"] = [
        {"rule_id": "r-sha256sums-b2", "code": "checksum_nul", "raw_sha256": NUL_RAW_SHA,
         "reason": "126 trailing NUL bytes under the fixed digest (approved two-exceptions integration 2026-11-24)"},
        {"rule_id": "r-chgis-sha256sums", "code": "checksum_path_binding", "raw_sha256": CHGIS_RAW_SHA,
         "reason": "line 4 fixed path binding to chgis-v6/China_Periods_ReignDates.zip (approved two-exceptions integration 2026-11-24)"}]
    doc["review"] = APPROVAL["contract_review"]
    (HERE / "updated-frozen-candidate.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    seven = [r for r in doc["rules"] if r["rule_id"].startswith("m00")]
    report = {"business_rules_count": len(seven),
              "seven_business_rules_deep_equal_to_approved": seven == business,
              "added_ledger_rules": ["r-sha256sums-b2", "r-chgis-sha256sums"],
              "exceptions_added": [e["code"] for e in doc["exceptions"]],
              "changed_top_level_keys": sorted(k for k in set(prev) | set(doc) if prev.get(k) != doc.get(k)),
              "previous_review": prev["review"], "new_review": doc["review"]}
    (HERE / "update-delta-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("UPDATED_CANDIDATE_BUILT seven_equal", report["seven_business_rules_deep_equal_to_approved"],
          "delta", report["changed_top_level_keys"])


if __name__ == "__main__":
    main()