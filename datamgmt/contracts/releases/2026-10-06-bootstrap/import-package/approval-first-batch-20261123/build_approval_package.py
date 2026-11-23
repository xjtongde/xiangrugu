#!/usr/bin/env python3
"""First-batch seven-object approval package generator (evidence review only).

Reads already-delivered evidence, emits approval-table.json / evidence-list.json.
No source reads, no rollup changes, no formal contract modification.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent.parent  # .../2026-10-06-bootstrap
REPO = REL.parents[3]  # repo root (bootstrap -> releases -> contracts -> datamgmt -> root)
ROLLUP = REL / "import-package" / "rollup"
VCS_REF = "8f3d014"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, doc):
    text = json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    (HERE / name).write_text(text, encoding="utf-8")


def main():
    approved = json.loads((REL / "text-value-contract-approved.draft.json").read_text())
    fb = json.loads((ROLLUP / "first-batch-preload-table.json").read_text())
    crs = json.loads((REL / "spatial-crs-approved.draft.yaml").read_text())
    attrs = json.loads((REL / "spatial-attributes-approved.draft.yaml").read_text())
    binding = json.loads((REL / "approved-spatial-binding-context.json").read_text())
    text_by_rule = {o["rule_id"]: o for o in approved["objects"]}
    crs_by_sid = {o["source_object_id"]: o for o in crs["objects"]}
    attrs_by_sid = {o["source_object_id"]: o for o in attrs["objects"]}
    binding_by_sid = {o["source_object_id"]: o for o in binding["bound_objects"]}
    sv_path = REPO / ".task6-spatial-values-20261123" / "source-side-expectations.json"
    sv_by_sid = {}
    if sv_path.exists():
        sv = json.loads(sv_path.read_text())
        sv_by_sid = {o["source_object_id"]: o for o in sv["objects"]}
    row_sum = sum(o["expected"]["row_count"] for o in approved["objects"])
    assert row_sum == approved["totals"]["data_record_count"] == 47607

    items = []
    for t in fb["text_items"]:
        o = text_by_rule[t["rule_id"]]
        items.append({
            "kind": "text", "rule_id": t["rule_id"],
            "source_sid": o["source_object_id"],
            "source_path": o["source"]["path"],
            "candidate_table_name_full": t["schema"] + "." + t["object_name"],
            "proposed_mapping": {"schema": o["approved_schema"],
                                 "source_column_count": o["source_column_count"],
                                 "target_columns": "待正式合同 target_mapping 批准（现 target_mapping_approved=false）"},
            "source_side_expectation_approved": True,
            "formal_contract_pending": True,
            "approved_mapping": {"schema": o["approved_schema"],
                                 "source_column_count": o["source_column_count"],
                                 "schema_sha256": o["schema_sha256"]},
            "pending_value_expectations": {
                "formal_contract_expected_count": "待生成（装载侧行数含重复计数）",
                "formal_contract_expected_sha256": "待接入正式合同 frozen 目标",
                "source_side_reference": {"row_count": o["expected"]["row_count"],
                                          "sha256": o["expected"]["sha256"],
                                          "field_count": o["expected"]["field_count"],
                                          "stream_bytes": o["expected"]["stream_bytes"]}},
            "precise_field_mapping_refs": {"value_columns": o["value_columns_ref"],
                                           "approved_schema_object": o["approved_object_ref"]},
            "approval_basis": {
                "file": "text-value-contract-approved.draft.json",
                "sha256": sha256_file(REL / "text-value-contract-approved.draft.json"),
                "approved_fields": ["value_contract_approved=true", "schema_sha256=" + o["schema_sha256"],
                                    "expected.row_count=" + str(o["expected"]["row_count"]),
                                    "expected.sha256=" + o["expected"]["sha256"],
                                    "expected.field_count=" + str(o["expected"]["field_count"]),
                                    "source.sha256=" + o["source"]["sha256"]],
                "canonical_format": approved["canonical_format"],
                "decision_sha256": approved["approval_decision_sha256"]},
            "technical_gaps": [
                "loader GAP：production PostgreSQL loader 未实现（importer/load.py 为 staging 原型）",
                "expected_count MISSING：装载侧行数含重复计数未生成（源侧期望 " + str(o["expected"]["row_count"]) + " 已批）",
                "expected_sha256 MISSING：规范值投影摘要待接入正式合同（源侧 XRGVALUE-v1 期望 " + o["expected"]["sha256"][:16] + "… 已批）",
                "table_names_approved=false / target_mapping_approved=false（表名与映射待批）"],
            "closure_evidence": [
                "装载侧 expected_count（含重复次数对账）生成并绑定正式合同",
                "规范值投影 expected_sha256 接入正式合同 frozen 目标",
                "表名批准事件 + target_mapping 批准事件（分账）",
                "正式合同 frozen+review 后 DispositionLedger 目标门通过"],
            "ledgers": {"table_name_approved": False, "formal_contract_frozen": False,
                        "load_authorized": False}})
    for s in fb["spatial_items"]:
        sid = s["source_object_id"]
        c, a, b = crs_by_sid[sid], attrs_by_sid[sid], binding_by_sid[sid]
        items.append({
            "kind": "spatial", "rule_id": c["primary_rule_id"],
            "source_sid": sid,
            "source_path": s["primary_member"]["relative_path"],
            "candidate_table_name_full": s["candidate_table_name_full"],
            "proposed_mapping": {"schema": "chgis", "target_column": c["target_column"],
                                 "srid": c["srid"], "dimensions": c["dimensions"],
                                 "geometry_type": c["geometry_type_proposal"],
                                 "coordinate_storage": c["coordinate_storage"],
                                 "attribute_columns": "已批列映射（spatial-attributes-approved.draft.yaml）"},
            "source_side_expectation_approved": True,
            "formal_contract_pending": True,
            "approved_mapping": {"components": 6, "attribute_columns": len(a["source_columns"]),
                                 "srid": c["srid"], "dimensions": c["dimensions"],
                                 "geometry_type": c["geometry_type_proposal"],
                                 "coordinate_storage": c["coordinate_storage"]},
            "source_side_value_expectations": (
                {"status": "GENERATED_PENDING_FORMAL_CONTRACT",
                 "row_count": sv_by_sid[sid]["row_count"],
                 "count_matches_known_59": sv_by_sid[sid]["count_matches_known"],
                 "duplicate_counts": sv_by_sid[sid]["duplicate_counts"],
                 "alignment": sv_by_sid[sid]["alignment"],
                 "attribute_sha256": sv_by_sid[sid]["attribute_expectation"]["sha256"],
                 "attribute_stream_bytes": sv_by_sid[sid]["attribute_expectation"]["stream_bytes"],
                 "geometry_sha256": sv_by_sid[sid]["geometry_expectation"]["sha256"],
                 "geometry_stream_bytes": sv_by_sid[sid]["geometry_expectation"]["stream_bytes"],
                 "evidence_ref": ".task6-spatial-values-20261123/source-side-expectations.json"}
                if sid in sv_by_sid else {"status": "NOT_GENERATED"}),
            "approval_basis": {
                "files": {"spatial-crs-approved.draft.yaml": sha256_file(REL / "spatial-crs-approved.draft.yaml"),
                          "spatial-attributes-approved.draft.yaml": sha256_file(REL / "spatial-attributes-approved.draft.yaml"),
                          "approved-spatial-binding-context.json": sha256_file(REL / "approved-spatial-binding-context.json")},
                "approved_fields": ["crs_srid_approved=true", "geometry_mapping_approved=true",
                                    "srid=" + str(c["srid"]), "dimensions=" + str(c["dimensions"]),
                                    "geometry_type_proposal=" + c["geometry_type_proposal"],
                                    "coordinate_storage=" + c["coordinate_storage"],
                                    "source_record_count=" + str(c["source_record_count"]),
                                    "component_binding_approved=true（6 组件）",
                                    "column_name_mapping_approved=true（属性列）",
                                    "crs_approval_decision_sha256=" + c["crs_approval_decision_sha256"]]},
            "canonical_value_evidence_gap": {
                "geometry_expected_hash": c["geometry_expected_hash"],
                "independent_read_scope": "独立读件：1884route.zip 内 " + s["primary_member"]["archive_chain"][0] + "（.shp 主件 " + s["primary_sha256"][:16] + "…/" + str(s["primary_size"]) + "B）+ 同名 .dbf 属性件；不复用旧库值，源件只读",
                "canonical_projection": "属性按已批列映射投影 XRGVALUE-v1 有序流（含 __src_rownum，一基物理记录）；geom 按 Point 二维 IEEE754 原始 X/Y（不交换不变换）+ SRID 4326 规范字节投影",
                "duplicate_reconciliation": "装载侧行数含重复计数 vs source_record_count=" + str(c["source_record_count"]) + "（观测值）逐项对账",
                "expected_evidence": "expected_count + expected_sha256（属性流与 geom 投影分列）生成并绑定正式合同 frozen 目标"},
            "new_source_read_or_impl_scope_for_approval": [
                "真源读取（新授权面）：1884route.zip 内 .shp/.dbf 独立解析（容器隔离，源件只读，逐组件 sha 对账）",
                "实现（新授权面）：Point 几何规范投影器 + 属性 XRGVALUE-v1 投影器（仅此一对象族，不泛化）",
                "对账证据：59 物理记录逐行 __src_rownum + 重复次数计数 + 双投影摘要"],
            "technical_gaps": [
                "geometry_expected_hash=null（规范几何投影摘要未生成）",
                "装载侧行数含重复计数未生成（source_record_count=59 为观测值）",
                "production geometry reader 未实现（production_readers_implemented=false）",
                "table_names_approved=false（目标名未批）"],
            "closure_evidence": [
                "独立读件 + 双投影摘要生成（geometry_expected_hash 非空）",
                "重复次数对账证据（59 记录）绑定正式合同",
                "表名批准事件（分账）+ 正式合同 frozen+review",
                "装载授权事件（分账）后 loader 实施"],
            "ledgers": {"table_name_approved": False, "formal_contract_frozen": False,
                        "load_authorized": False}})

    table = {"version": 1, "status": "APPROVAL_PACKAGE_DRAFT_NOT_APPROVED",
             "baseline_git": VCS_REF, "scope": "first-batch-seven-objects-approval-package-only",
             "text_row_total_check": {"sum_of_expected_row_count": row_sum,
                                      "totals_data_record_count": approved["totals"]["data_record_count"],
                                      "equal": row_sum == 47607},
             "three_ledgers_separate": {
                 "table_name_approval": "七件均 false（候选名 DRAFT，批准事件另录）",
                 "formal_contract_freeze": "false（contract_frozen=false，冻结事件另录）",
                 "load_authorization": "false（loader GAP，装载授权另录）"},
             "value_expectations_ledger": {
                 "text_source_side": "五件引用既有已批期望（text-value-contract-approved.draft.json，47607 行）",
                 "spatial_source_side": "两件源侧期望已生成（59 行/零重复/属性+几何摘要，.task6-spatial-values-20261123/）",
                 "formal_contract_integration": "七件均待接入正式合同 frozen 目标（expected_count/expected_sha256）"},
             "items": sorted(items, key=lambda x: (x["kind"], x["rule_id"]))}
    dump("approval-table.json", table)

    evidence_files = [
        (REL / "text-value-contract-approved.draft.json", "五件文本源侧期望批准（XRGVALUE-v1 行数/摘要/schema）"),
        (REL / "text-value-contract-decisions.draft.json", "文本值批准决定（decision sha e4c666c0…）"),
        (REL / "spatial-crs-approved.draft.yaml", "两空间 CRS/SRID 4326/Point 二维/原始 X/Y 批准"),
        (REL / "spatial-attributes-approved.draft.yaml", "两空间属性列映射批准"),
        (REL / "spatial-geometry-approved.draft.yaml", "空间几何映射批准"),
        (REL / "approved-spatial-binding-context.json", "六组件绑定批准上下文"),
        (ROLLUP / "first-batch-preload-table.json", "首批七对象候选名/缺口/批准范围照录"),
        (ROLLUP / "naming-draft.json", "命名草案（approved_spatial_special  lane）"),
        (ROLLUP / "object-index.json", "对象索引（approved_spatial_objects 绑定）"),
        (REL / "inventory.json", "原清单（fb5e6b33…，complete=false 三 issue 保留）"),
    ]
    for rel, _ in approved["input_sha256"].items():
        p = REPO / rel
        if p.exists():
            evidence_files.append((p, "文本期望输入绑定（input_sha256）"))
    entries = []
    for p, purpose in evidence_files:
        if p.exists():
            entries.append({"path": str(p.relative_to(REPO)),
                            "sha256": sha256_file(p), "purpose": purpose})
    dump("evidence-list.json", {"version": 1, "baseline_git": VCS_REF,
                                "entries": sorted(entries, key=lambda e: e["path"])})
    print("ITEMS", len(items), "EVIDENCE", len(entries), "ROWS", row_sum)


if __name__ == "__main__":
    main()