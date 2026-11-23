#!/usr/bin/env python3
"""Reception pre-check deliverables: deploy state + seven-item pending-approval table.

Read-only reuse of committed trial evidence and approved drafts. No deploy
replacement, no service change, no contract freeze, no database write.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REL = REPO / "datamgmt/contracts/releases/2026-10-06-bootstrap"
APPROVED = json.loads((REL / "text-value-contract-approved.draft.json").read_text())
EXPECT = json.loads((REPO / "docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json").read_text())
VC = {o["rule_id"]: o["value_columns"] for o in EXPECT["objects"]}
FB = json.loads((REL / "import-package/rollup/first-batch-preload-table.json").read_text())
T5 = json.loads((REPO / ".task6-trial-text5-20261123/trial-evidence.json").read_text())
SP2 = json.loads((REPO / ".task6-trial-spatial2-20261123/trial-evidence.json").read_text())
SV = json.loads((REPO / ".task6-spatial-values-20261123/source-side-expectations.json").read_text())
T5_BY = {it["rule_id"]: it for it in T5["items"]}
SP_BY = {it["rule_id"]: it for it in SP2["items"]}
SV_BY = {o["object_name"]: o for o in SV["objects"]}
MANIFEST = HERE / "deploy-content-manifest.txt"
PAT = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


def dump(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def main():
    lines = MANIFEST.read_text().splitlines()
    total_bytes = 0  # recorded from host find -printf at pre-check time
    deploy = {
        "version": 1, "path": "/opt/mydocker/xiangrugu/deploy", "inspection": "read-only",
        "git_commit": "UNKNOWN",
        "git_commit_reason": "deploy 非 Git 仓库（无 .git，git rev-parse 致命错误）；无法证明现役 Git 提交，按派单记为未知",
        "publishable_version_markers": {
            "content_manifest_sha256": "62737bd0c16ac23f1c9ba4fd92e73abadb6a6eace014494f605f29e6aa00396f",
            "file_count": len(lines), "total_bytes": 87798110,
            "key_file_sha256": {"AGENTS.md": "2043155a8ebc6d96", "docker-compose.yml": "67212d2871b2dd10",
                                "Dockerfile": "51a1df8e5a0f51a1"},
            "key_file_note": "key_file_sha256 为前 16 位截断展示；全量以 content manifest 为准",
            "mtime_range": "2026-10-06..2026-10-15 (+0800)，早于当前交付分支，内容代际另行核对"},
        "active_image": {"container": "xiangrugu-dev", "image_tag": "xiangrugu:dev",
                         "image_id": "sha256:89f1a0978cb817871d50d6468f3dec19e3ea1e67d5bc73457a62fd10b5b8732d"},
        "mounts": {"deploy_to_workspace": "ro（只读挂载，容器不写 deploy）",
                   "outside_deploy": "data/persistent 与 data/var 为独立 rw 绑定，不在 deploy 保护范围"},
        "protection_scope": {"files": len(lines), "bytes": 87798110,
                             "definition": "deploy 下全部 7719 文件（datamgmt/demo/docs/scripts/根文件）；恢复以内容清单全量为准",
                             "manifest_ref": ".task6-reception-precheck-20261123/deploy-content-manifest.txt"},
        "recovery_point": {"kind": "content_snapshot", "git_anchor": "UNKNOWN",
                           "verifiable": True,
                           "basis": "内容 sha256 清单（62737bd0…）+ 接收时 R0 tar 快照；恢复校验=全量 sha256sum -c + 文件数 + 字节和",
                           "note": "Git 锚不可证时以内容快照为可验证恢复点；若接收时清单漂移或快照不可形成→受控接收停在预检"},
        "deploy_replaced": False, "service_changed": False, "contract_frozen": False, "database_written": False}
    dump(HERE / "deploy-state.json", deploy)

    items = []
    for t in FB["text_items"]:
        rule = t["rule_id"]
        obj = next(o for o in APPROVED["objects"] if o["rule_id"] == rule)
        trial = T5_BY[rule]
        rb = trial["readback"]
        cols = VC[rule]
        items.append({
            "kind": "text", "rule_id": rule, "source_object_id": obj["source_object_id"],
            "candidate_full_name": f'{t["schema"]}.{t["object_name"]}',
            "precise_field_mapping": {
                "ref": obj["value_columns_ref"], "approved_object_ref": obj["approved_object_ref"],
                "column_count_including_rownum": len(cols),
                "columns": [{"column_key": c["column_key"], "target_name": c["target_name"],
                             "pg_type": c["pg_type"], "nullable": c["nullable"]} for c in cols]},
            "expected_row_count": obj["expected"]["row_count"],
            "attribute_digest": {"expected_sha256": obj["expected"]["sha256"],
                                 "trial_readback_sha256": rb["stream_sha256_from_db_values"],
                                 "match": rb["matches_approved_expectation"],
                                 "stream_bytes": obj["expected"]["stream_bytes"],
                                 "format": "XRGVALUE-v1"},
            "actual_duplicates": {"groups": int(rb["duplicate_groups_value_cols_only"]),
                                  "extra_rows": int(rb["duplicate_extra_rows_value_cols_only"]),
                                  "key": "实际值列全集，排除唯一 __src_rownum",
                                  "row_count_semantics": "expected_count 含重复行（40199 口径）"},
            "trial_evidence_ref": ".task6-trial-text5-20261123/trial-evidence.json",
            "contract_expressiveness": {
                "candidate_name_pattern": {"length": len(t["object_name"]),
                                           "matches": bool(PAT.match(t["object_name"]))},
                "expected_count_and_sha256": "EXPRESSIBLE（ObjectTarget.expected_count/expected_sha256）",
                "precise_field_mapping": "NOT_EXPRESSIBLE（ObjectTarget 无列结构；ColumnEncoding 仅 codec；column_key/target_name/pg_type/nullable/width/scale/派生行号无字段）",
                "duplicate_ledger": "NOT_EXPRESSIBLE（仅 count 数值可承载，重复组/多余行口径无字段）",
                "derived_src_rownum": "NOT_EXPRESSIBLE"}})
    for s in FB["spatial_items"]:
        rule = s.get("primary_rule") or s.get("primary_rule_id")
        if rule is None:
            rule = "m002709" if s["candidate_table_name_full"].endswith("1251") else "m002717"
        trial = SP_BY[rule]
        rb = trial["readback"]
        sv = SV_BY[trial["object_name"]]
        schema, table = s["candidate_table_name_full"].split(".", 1)
        items.append({
            "kind": "spatial", "rule_id": rule, "source_object_id": s["source_object_id"],
            "candidate_full_name": s["candidate_table_name_full"],
            "precise_field_mapping": {
                "ref": {"file": "datamgmt/contracts/releases/2026-10-06-bootstrap/spatial-attributes-approved.draft.yaml",
                        "pointer": f'/objects/{0 if rule == "m002709" else 1}/source_columns'},
                "column_count_including_rownum_and_geom": 14,
                "types": "text×7 + numeric(19,5)×2(LAT/LONG) + bigint×3(POS_CERT/DATE_CERT/DATE_) + geometry(Point,4326) + __src_rownum bigint",
                "numeric_width_scale": "LAT/LONG 19,5；POS_CERT/DATE_CERT/DATE_ 16,0；右对齐空格填充重建源字段文本"},
            "expected_row_count": 59,
            "attribute_digest": {"expected_sha256": sv["attribute_expectation"]["sha256"],
                                 "trial_readback_sha256": rb["attr_stream_sha256_from_db_values"],
                                 "match": rb["attr_matches_approved"],
                                 "stream_bytes": rb["attr_stream_bytes"], "format": "XRGVALUE-v1"},
            "geometry_digest": {"expected_sha256": sv["geometry_expectation"]["sha256"],
                                "trial_readback_sha256": rb["geom_stream_sha256_from_db_values"],
                                "match": rb["geom_matches_approved"],
                                "stream_bytes": rb["geom_stream_bytes"], "format": "XRGGEOM-v1"},
            "srid": 4326, "dimensions": 2, "geometry_type": "Point",
            "dbf_source_identity": {"dbf_sha256": sv["components"]["dbf"]["sha256"],
                                    "cpg_sha256": sv["components"]["cpg"]["sha256"],
                                    "codec": sv["codec"],
                                    "shp_sha256": sv["components"]["shp"]["sha256"],
                                    "note": "两件 SHP 字节相同（109d74b1…）也各自独立核对；两份 DBF 来源身份分别保留"},
            "original_coordinates": {"storage": "preserve_original_ieee754_xy_no_swap_or_transform",
                                     "load_method": "hex EWKB（01+0x20000001+SRID LE+原始 X/Y LE 字节，无十进制转换）",
                                     "per_point_original_bytes_match": rb["per_point_xy_original_bytes_match"]},
            "actual_duplicates": {"attribute_groups": int(rb["duplicate_groups_attr_value_cols"]),
                                  "xy_pair_groups": int(rb["duplicate_groups_xy_pairs"]),
                                  "key": "值列/坐标对，排除唯一 __src_rownum"},
            "trial_evidence_ref": ".task6-trial-spatial2-20261123/trial-evidence.json",
            "contract_expressiveness": {
                "candidate_name_pattern": {"length": len(table), "matches": bool(PAT.match(table))},
                "expected_count_and_sha256": "EXPRESSIBLE（属性流 count/sha 可承载）",
                "precise_field_mapping": "NOT_EXPRESSIBLE（同文本；numeric 宽度标度/类型无字段）",
                "geometry_expectation": "NOT_EXPRESSIBLE（SRID/维数/类型/XRGGEOM-v1 sha 无字段）",
                "duplicate_ledger": "NOT_EXPRESSIBLE", "derived_src_rownum": "NOT_EXPRESSIBLE"}})
    items.sort(key=lambda i: (i["kind"], i["rule_id"]))
    table = {
        "version": 1, "status": "PENDING_APPROVAL", "trial_only": True,
        "ledgers": {"table_name_approved": False, "formal_contract_frozen": False, "load_authorized": False},
        "items": items,
        "text_row_total": sum(i["expected_row_count"] for i in items if i["kind"] == "text"),
        "spatial_row_total": sum(i["expected_row_count"] for i in items if i["kind"] == "spatial"),
        "contract_expressiveness_check": {
            "contract_ref": "datamgmt/src/xiangrugu_datamgmt/contracts.py + datamgmt/config/contract.schema.json",
            "expressible": "rule_id/selector/expected raw sha+size/disposition/format_family/encodings(逐列 codec)/targets(object_name/schema/table≤63 正则/expected_count/expected_sha256)/review/frozen/exceptions(checksum_nul,checksum_path_binding)",
            "first_inexpressible_position": {
                "item": "m008002（首批首件）",
                "aspect": "精确字段映射（value_columns 55 列：column_key→target_name/pg_type/nullable/序）",
                "reason": "ObjectTarget 仅 object_name/schema/table/expected_count/expected_sha256；ColumnEncoding 仅 object_name/column/codec/errors；无列映射/类型/宽度标度/派生 __src_rownum 结构",
                "downstream": "空间几何期望（SRID/维数/类型/XRGGEOM sha）与重复口径账亦无字段；七件候选全名均合 table 正则（≤63）不构成缺口"},
            "integration_path": "合同结构扩展（列映射+几何期望+派生列+重复口径）须另行设计批准；本盒不冻结合同不改 schema"},
        "reception_precheck_ref": ".task6-reception-precheck-20261123/deploy-state.json",
        "source_read_only": True, "deploy_replaced": False, "service_changed": False,
        "contract_frozen": False, "database_written": False}
    dump(HERE / "pending-approval-seven-20261123.json", table)
    print("DEPLOY_STATE_OK ITEMS", len(items), "TEXT_ROWS", table["text_row_total"], "SPATIAL_ROWS", table["spatial_row_total"])


if __name__ == "__main__":
    main()