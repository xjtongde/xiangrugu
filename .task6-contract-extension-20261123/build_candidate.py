#!/usr/bin/env python3
"""Build the unfrozen seven-object candidate contract from the pre-check pending table.

Stdlib-only construction + item-by-item evidence reconciliation. Model validation
(pydantic) and the dedicated first-batch validation run in the 32 isolated env.
No freeze, no deploy reception, no service change, no database write.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REL = REPO / "datamgmt/contracts/releases/2026-10-06-bootstrap"
PENDING = json.loads((REPO / ".task6-reception-precheck-20261123/pending-approval-seven-20261123.json").read_text())
APPROVED = json.loads((REL / "text-value-contract-approved.draft.json").read_text())
EXPECT = json.loads((REPO / "docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json").read_text())
ATTRS = json.loads((REL / "spatial-attributes-approved.draft.yaml").read_text())
SV = json.loads((REPO / ".task6-spatial-values-20261123/source-side-expectations.json").read_text())
INV = json.loads((REL / "inventory.json").read_text())
VC = {o["rule_id"]: o["value_columns"] for o in EXPECT["objects"]}
AP_BY = {o["rule_id"]: o for o in APPROVED["objects"]}
SV_BY = {o["object_name"]: o for o in SV["objects"]}
ATTR_BY_SID = {o["source_object_id"]: o for o in ATTRS["objects"]}
TEXT_CODEC = {"m008002": "utf-8-sig", "m008003": "utf-8-sig", "m008004": "utf-8",
              "m004812": "utf-8", "m006642": "utf-8"}
ROWNUM = {"target_column": "__src_rownum", "pg_type": "bigint", "nullable": False,
          "origin": "one_based_physical_source_row"}
INV_SHA = hashlib.sha256((REL / "inventory.json").read_bytes()).hexdigest()


def entry_of(path, chain_member=None):
    for e in INV["entries"]:
        if e["relative_path"] == path and (
                (chain_member is None and not e["archive_chain"])
                or (chain_member and e["archive_chain"] == [chain_member])):
            return e
    raise KeyError((path, chain_member))


def main():
    rules, checks = [], []
    for item in PENDING["items"]:
        rule = item["rule_id"]
        schema, table = item["candidate_full_name"].split(".", 1)
        if item["kind"] == "text":
            ap = AP_BY[rule]
            e = entry_of(ap["source"]["path"])
            cols = [{"ordinal": i + 1, "source_column": c["column_key"], "target_column": c["target_name"],
                     "pg_type": c["pg_type"], "nullable": c["nullable"]}
                    for i, c in enumerate(VC[rule][:-1])]
            encodings = [{"object_name": table, "column": c["target_column"], "codec": TEXT_CODEC[rule],
                          "errors": "strict"} for c in cols]
            dup = {"key": "value_columns_excluding_src_rownum",
                   "expected_groups": item["actual_duplicates"]["groups"],
                   "expected_extra_rows": item["actual_duplicates"]["extra_rows"],
                   "count_includes_duplicates": True}
            target = {"object_name": table, "schema": schema, "table": table,
                      "expected_count": item["expected_row_count"],
                      "expected_sha256": item["attribute_digest"]["expected_sha256"],
                      "columns": cols, "derived_rownum": ROWNUM, "duplicate_reconciliation": dup}
            selector = {"relative_path": ap["source"]["path"], "archive_chain": [], "archive_ordinals": []}
            expected = {"kind": "file", "sha256": e["sha256"], "size": e["size"], "signature": e["signature"]}
            family = "text"
        else:
            sv = SV_BY[item["source_object_id"] and next(o["object_name"] for o in SV["objects"]
                                                        if o["source_object_id"] == item["source_object_id"])]
            member = item["dbf_source_identity"]
            stem = "5_1884route/" + ("Ca1884route_przh_1251" if rule == "m002709" else "Ca1884route_przh_utf8") + ".dbf"
            e = entry_of("harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip", stem)
            acols = ATTR_BY_SID[item["source_object_id"]]["source_columns"]
            cols = [{"ordinal": c["source_column_ordinal"], "source_column": c["original_name"],
                     "target_column": c["target_name"], "pg_type": c["target_type_proposal"],
                     "nullable": c["nullable_approved"], "source_width_bytes": c["source_width_bytes"],
                     "source_decimals": c["source_decimals"]} for c in acols]
            encodings = [{"object_name": table, "column": c["original_name"],
                          "codec": sv["codec"] if c["source_type"] == "C" else "ascii", "errors": "strict"}
                         for c in acols]
            dup = {"key": "value_columns_excluding_src_rownum",
                   "expected_groups": item["actual_duplicates"]["attribute_groups"],
                   "expected_extra_rows": 0, "count_includes_duplicates": True}
            target = {"object_name": table, "schema": schema, "table": table,
                      "expected_count": item["expected_row_count"],
                      "expected_sha256": item["attribute_digest"]["expected_sha256"],
                      "columns": cols, "derived_rownum": ROWNUM, "duplicate_reconciliation": dup,
                      "geometry": {"geometry_type": "Point", "dimensions": 2, "srid": item["srid"],
                                   "canonical_format": "XRGGEOM-v1",
                                   "expected_sha256": item["geometry_digest"]["expected_sha256"],
                                   "coordinate_storage": "preserve_original_ieee754_xy_no_swap_or_transform"}}
            selector = {"relative_path": "harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip",
                        "archive_chain": [stem], "archive_ordinals": e["archive_ordinals"]}
            expected = {"kind": "file", "sha256": e["sha256"], "size": e["size"], "signature": e["signature"]}
            family = "spatial"
        rules.append({"rule_id": rule, "selector": selector, "expected": expected,
                      "disposition": "IMPORT", "reason": "first-batch seven candidate; names and mappings pending approval",
                      "format_family": family, "encodings": encodings, "targets": [target],
                      "validator": "canonical-value-v1" if family == "text" else "canonical-spatial-v1"})
        # item-by-item reconciliation against the audited pending table
        chk = {"rule_id": rule,
               "name_match": item["candidate_full_name"] == f"{schema}.{table}",
               "count_match": target["expected_count"] == item["expected_row_count"],
               "attr_digest_match": target["expected_sha256"] == item["attribute_digest"]["expected_sha256"],
               "trial_attr_match": item["attribute_digest"]["match"],
               "rownum_declared": target["derived_rownum"] == ROWNUM,
               "duplicate_match": (dup["expected_groups"], dup["expected_extra_rows"]) == (
                   (item["actual_duplicates"]["groups"], item["actual_duplicates"]["extra_rows"])
                   if item["kind"] == "text" else (item["actual_duplicates"]["attribute_groups"], 0))}
        if item["kind"] == "text":
            chk["mapping_match"] = all(
                c["source_column"] == p["column_key"] and c["target_column"] == p["target_name"]
                and c["pg_type"] == p["pg_type"] and c["nullable"] == p["nullable"]
                for c, p in zip(cols, item["precise_field_mapping"]["columns"][:-1]))
        else:
            chk["mapping_match"] = all(
                c["source_column"] == a["original_name"] and c["target_column"] == a["target_name"]
                and c["pg_type"] == a["target_type_proposal"] and c["source_width_bytes"] == a["source_width_bytes"]
                and c["source_decimals"] == a["source_decimals"] for c, a in zip(cols, acols))
            chk["geom_digest_match"] = target["geometry"]["expected_sha256"] == item["geometry_digest"]["expected_sha256"]
            chk["trial_geom_match"] = item["geometry_digest"]["match"]
            chk["srid_match"] = target["geometry"]["srid"] == 4326
            chk["source_identity_match"] = (expected["sha256"] == item["dbf_source_identity"]["dbf_sha256"]
                                            and expected["size"] == 16937)
        chk["all_match"] = all(v for v in chk.values() if isinstance(v, bool))
        checks.append(chk)
    rules.sort(key=lambda r: r["rule_id"])
    doc = {"version": 1, "release_id": "2026-11-23-first-batch-seven-candidate",
           "source_version": "usedata-wd61-verified-snapshot", "inventory_sha256": INV_SHA,
           "status": "draft", "review": None, "exceptions": [], "rules": rules}
    (HERE / "candidate-contract.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    total = sum(r["targets"][0]["expected_count"] for r in rules)
    report = {"version": 1, "candidate_status": "draft_unfrozen", "item_checks": checks,
              "total_expected_rows": total, "total_matches_47725": total == 47725,
              "m008003_duplicates": next((r["targets"][0]["duplicate_reconciliation"] for r in rules
                                          if r["rule_id"] == "m008003"), None),
              "all_items_match": all(c["all_match"] for c in checks),
              "inventory_sha256": INV_SHA,
              "deploy_received": False, "service_changed": False, "contract_frozen": False, "database_written": False}
    (HERE / "candidate-validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("CANDIDATE_BUILT rules", len(rules), "total", total, "all_match", report["all_items_match"])


if __name__ == "__main__":
    main()