#!/usr/bin/env python3
"""Validate the frozen delivery candidate through the formal parse/frozen-gate entry (32 isolated env)."""
import hashlib
import json
from pathlib import Path

from xiangrugu_datamgmt.contracts import ReleaseContract

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PENDING = json.loads((REPO / ".task6-reception-precheck-20261123" / "pending-approval-seven-20261123.json").read_text())
SV = json.loads((REPO / ".task6-spatial-values-20261123" / "source-side-expectations.json").read_text())
SV_BY_SID = {o["source_object_id"]: o for o in SV["objects"]}


def main():
    doc = json.loads((HERE / "frozen-candidate.json").read_text())
    contract = ReleaseContract.model_validate(doc)  # formal entry: frozen gate enforces first-batch checks
    out = {"formal_frozen_parse": "PASS", "status": contract.status,
           "frozen_candidate_canonical_sha256": contract.sha256,
           "review": {"approved_by": contract.review.approved_by,
                      "approved_at": contract.review.approved_at,
                      "approval_ref": contract.review.approval_ref},
           "total_expected_rows": sum(t.expected_count for r in contract.rules for t in r.targets)}
    by_rule = {r.rule_id: r for r in contract.rules}
    checks = []
    for item in PENDING["items"]:
        rule = by_rule[item["rule_id"]]
        t = rule.targets[0]
        chk = {"rule_id": item["rule_id"],
               "name_match": f"{t.schema_name}.{t.table}" == item["candidate_full_name"],
               "count_match": t.expected_count == item["expected_row_count"],
               "attr_sha_match": t.expected_sha256 == item["attribute_digest"]["expected_sha256"]}
        if item["kind"] == "text":
            exp = item["precise_field_mapping"]["columns"][:-1]
            chk["mapping_match"] = len(t.columns) == len(exp) and all(
                (c.source_column, c.target_column, c.pg_type, c.nullable) ==
                (e["column_key"], e["target_name"], e["pg_type"], e["nullable"])
                for c, e in zip(t.columns, exp))
            chk["dup_match"] = (t.duplicate_reconciliation.expected_groups,
                                t.duplicate_reconciliation.expected_extra_rows) == (
                item["actual_duplicates"]["groups"], item["actual_duplicates"]["extra_rows"])
        else:
            sv = SV_BY_SID[item["source_object_id"]]
            chk["geom_sha_match"] = t.geometry.expected_sha256 == item["geometry_digest"]["expected_sha256"] == sv["geometry_expectation"]["sha256"]
            chk["attr_source_side_match"] = t.expected_sha256 == sv["attribute_expectation"]["sha256"]
            chk["srid_match"] = t.geometry.srid == 4326
            chk["dbf_identity_match"] = rule.expected.sha256 == item["dbf_source_identity"]["dbf_sha256"] and rule.expected.size == 16937
        chk["all_match"] = all(v for v in chk.values() if isinstance(v, bool))
        checks.append(chk)
    out["item_checks"] = checks
    out["all_items_match"] = all(c["all_match"] for c in checks)
    out["total_matches_47725"] = out["total_expected_rows"] == 47725
    out["controlled_reception_performed"] = False
    out["database_written"] = False
    (HERE / "frozen-validation-report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("FROZEN_VALIDATION", out["formal_frozen_parse"], "sha", out["frozen_candidate_canonical_sha256"][:16],
          "total", out["total_expected_rows"], "all_match", out["all_items_match"])


if __name__ == "__main__":
    main()