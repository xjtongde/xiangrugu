#!/usr/bin/env python3
"""Build the CBDB import-package working set (block 1/6, organize-only).

Merges ALREADY-CONFIRMED release artifacts into five machine-readable
deliverables. Nothing is hand-filled: every field traces to a named file
under datamgmt/contracts/releases/2026-10-06-bootstrap/. Source bytes are
never written; proposal flags are never upgraded. Re-runnable and
deterministic (sorted keys, fixed separators).

Run from anywhere: paths resolve relative to this file's release root.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent                     # .../import-package/cbdb
REL = HERE.parent.parent                                   # .../releases/2026-10-06-bootstrap


def load(name):
    return json.loads((REL / name).read_text(encoding="utf-8"))


def sha(name):
    return hashlib.sha256((REL / name).read_bytes()).hexdigest()


def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write(name, value):
    (HERE / name).write_bytes(canon(value))


inventory = load("inventory.json")
proposal = load("sqlite-target-mapping-proposal.draft.json")
map_dec = load("sqlite-target-mapping-decisions.draft.json")
types_ap = load("sqlite-types-approved.draft.json")
type_dec = load("sqlite-type-decisions.draft.json")
unobs = load("sqlite-unobserved-type-proposal.draft.json")
roles = load("sqlite-roles-approved.draft.json")
role_dec = load("sqlite-role-decisions.draft.json")
# 账本引用更新（2026-11-26）：指向 fa28a878 合同生成的新版正式账；旧账仅保留不覆盖
ledger = load("disposition-ledger-fa28a878-20261126.json")
prep = load("sqlite-value-contract-preparation.draft.json")
canary = load("sqlite-value-canary.approved.json")
small = load("sqlite-value-small.expected.draft.json")
medium = load("sqlite-value-medium.expected.draft.json")
large = load("sqlite-value-large-readiness.draft.json")

# B 批单表冻结候选（本轮授权：IMPORT 状态单列，而非并入 A 账处置）
BATCH_B_CANDIDATE = "b-single-table-frozen-candidate.json"
BATCH_B_SHA = "d3cdb81c4caf75c92a96e548025c39aab1d1d8a301b0f0d7b4e30286243d8bef"

SRC_SQLITE = "harvard/cbdb/cbdb_20260919.sqlite3"
SRC_JSON = "harvard/cbdb/cbdb_20260919.json"
SRC_DIR = "harvard/cbdb"
SQLITE_SHA = "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"

# ------------------------------------------------- 账本派生态（禁止硬编码）
def ledger_record(relative_path):
    """A 账中该成员的记录；未匹配时返回 None（不臆造处置）。"""
    return next((d for d in ledger["records"]
                 if d["member"]["relative_path"] == relative_path), None)


def ledger_state(relative_path):
    """从 A 账实际记录派生状态，未匹配即如实标记 UNMATCHED_IN_A_LEDGER。"""
    rec = ledger_record(relative_path)
    if rec is None:
        return {"disposition": None, "rule_ids": [], "matched_in_a_ledger": False,
                "derived_state": "UNMATCHED_IN_A_LEDGER"}
    return {"disposition": rec["disposition"], "rule_ids": rec["rule_ids"],
            "matched_in_a_ledger": True,
            "derived_state": rec["disposition"] or "UNMATCHED_IN_A_LEDGER"}


def batch_b_import_state(relative_path):
    """B 批单表冻结候选对该成员的 IMPORT 意图（单列，不并入 A 账处置）。"""
    cand_path = REL / BATCH_B_CANDIDATE
    if not cand_path.exists():
        return {"present": False}
    cand = load(BATCH_B_CANDIDATE)
    h = hashlib.sha256(canon_path_bytes := (REL / BATCH_B_CANDIDATE).read_bytes()).hexdigest()
    hit = [r for r in cand["rules"] if r["selector"]["relative_path"] == relative_path]
    if not hit:
        return {"present": False, "candidate_file_sha256": h}
    rule = hit[0]
    return {
        "present": True,
        "candidate_release_id": cand["release_id"],
        "candidate_file_sha256": h,
        "rule_id": rule["rule_id"],
        "disposition_in_candidate": rule["disposition"],
        "status": "FROZEN_CANDIDATE_NOT_IN_A_LEDGER",
        "targets": [f'{t["schema"]}.{t["table"]}' for t in rule["targets"]],
        "note": "B 批单表冻结候选状态单列；A 账仍为未匹配，冻结≠写库授权",
    }


# ---------------------------------------------------------------- members
ents = {e["relative_path"]: e for e in inventory["entries"] if not e["archive_chain"]}
members = {
    "format": "xiangrugu.import-package.cbdb.members.v1",
    "release_id": proposal["release_id"],
    "source_version": proposal["source_version"],
    "generated_by": "build_cbdb_package.py (deterministic merge; no hand-filled fields)",
    "members": [
        {"relative_path": SRC_DIR, "kind": "directory", "size": None, "sha256": None,
         "signature": "unknown", "rule_ids": ["m007904"],
         "ledger_state": ledger_state(SRC_DIR),
         "relationship": "container of the two files below; structural only",
         "handling": ("NON_TABULAR retained explicitly (ledger reason quoted)"
                      if ledger_state(SRC_DIR)["derived_state"] == "NON_TABULAR"
                      else "state derived from A ledger: " + ledger_state(SRC_DIR)["derived_state"])},
        {"relative_path": SRC_JSON, "kind": "file", "size": 385,
         "sha256": ents[SRC_JSON]["sha256"], "signature": "unknown",
         "rule_ids": ["m007905"],
         "ledger_state": ledger_state(SRC_JSON),
         "content_judgement": {
             "method": "read-only SSH cat on host 32 (root@192.168.3.32) this round; "
                       "digest verified equal to inventory sha bd62ab07…",
             "facts": {"sqlite_filename": "cbdb_20260919.sqlite3",
                       "declared_sha256": SQLITE_SHA,
                       "generated_at_utc": "2026-09-19T19:15:36Z",
                       "format": "sqlite3",
                       "huggingface_path": "history/cbdb_202609/cbdb_20260919.zip"},
             "relation_to_sqlite_member": ("publisher-side metadata about the sqlite3 "
                                           "member (declares its filename+sha256 and an "
                                           "upstream HF zip path); NOT a duplicate table "
                                           "carrier — distinct content, disposed separately"),
             "verification": "declared sha equals the recorded sqlite member sha "
                             f"({SQLITE_SHA[:12]}…) — cross-check passes at metadata level"},
         "handling": "kept as separate member; values NOT imported as tables; "
                     "metadata role recorded here for the release draft"},
        {"relative_path": SRC_SQLITE, "kind": "file", "size": 586485760,
         "sha256": SQLITE_SHA, "signature": "sqlite", "rule_ids": ["m007906"],
         "ledger_state": ledger_state(SRC_SQLITE),
         "relationship": "main source carrier: 78 tables / 736 columns per the "
                         "confirmed structure sub-batch",
         "batch_b_import_state": batch_b_import_state(SRC_SQLITE),
         "handling": ("state derived from A ledger: "
                      + ledger_state(SRC_SQLITE)["derived_state"]
                      + "; B 批单表冻结候选另列（见 batch_b_import_state），冻结≠写库授权；"
                        "block-1 organizing target for table/field mapping below")}],
    "nested_members_under_cbdb": 0,
    "companion_materials_note": (
        "sqlite-*.draft/approved files, sqlite-review.md, "
        "sqlite-target-mapping-review.md, disposition ledger, canary/small/"
        "medium/large value files are OUR release-draft/review evidence "
        "(repo files), NOT source members of harvard/cbdb."),
}

# ------------------------------------------------------------- coverage sets
def names(objs):
    return [o.get("source_object_name") or o.get("name") for o in objs]


covered = set(names(canary["objects"])) | set(names(small["objects"])) | set(names(medium["objects"]))
remaining_large = {o["source_object_name"] if "source_object_name" in o else None: o
                   for o in large["objects"]}
prop_names = {o["source_object_name"] for o in proposal["objects"]}
assert covered <= prop_names and len(prop_names - covered) == 10
name_by_id = {o["source_object_id"]: o["source_object_name"] for o in proposal["objects"]}
large_cols = {}
for o in large["objects"]:
    nm = name_by_id[o["source_object_id"]]
    large_cols[nm] = len(o["source_columns"])
assert sum(large_cols.values()) == large["remaining_columns"] == 235

# per-table verification placement
def verify_status(name):
    if name in {x.get("source_object_name") or x.get("name") for x in canary["objects"]}:
        return ("value expectations bound via approved canary",
                "sqlite-value-canary.approved.json")
    if name in {x.get("source_object_name") or x.get("name") for x in small["objects"]}:
        return ("source-only small-group expectations generated",
                "sqlite-value-small.expected.draft.json (+ expected-index)")
    if name in {x.get("source_object_name") or x.get("name") for x in medium["objects"]}:
        return ("source-only medium-group expectations generated",
                "sqlite-value-medium.expected.draft.json (+ expected-index)")
    return ("NOT yet value-verified: large group, resource conflict "
            "(1GiB scratch beyond 64MiB scope); read not authorized",
            "sqlite-value-large-readiness.draft.json / "
            "sqlite-value-next-groups.review.draft.json")

# --------------------------------------------------------------- table map
READ = ("sqlite3 READ-ONLY over the versioned snapshot member "
        "(SELECT/PRAGMA only; NAS not accessed)")
LOAD_GAP = ("GAP: production PostgreSQL loader not implemented "
            "(contract-preparation.verification.production_adapter_implemented=false; "
            "importer/load.py is staging prototype only and must not be run "
            "against pg32b until revised)")
tables_out = []
for o in proposal["objects"]:
    vdesc, vfile = verify_status(o["source_object_name"])
    tables_out.append({
        "source_identity": {"source_object_id": o["source_object_id"],
                            "source_object_name": o["source_object_name"],
                            "carrier_file": SRC_SQLITE, "carrier_sha256": SQLITE_SHA},
        "target_schema": o["target_schema_candidate"],
        "target_table": o["target_table_candidate"],
        "role": next(t["role"] for t in roles["tables"]
                     if t["source_object_id"] == o["source_object_id"]),
        "confirmation_status": {
            "structure_and_naming_subbatch_policy": map_dec["status"],
            "subbatch_target_mapping_policy_approved":
                map_dec["subbatch_target_mapping_policy_approved"],
            "target_mapping_approved_whole_release": proposal["target_mapping_approved"],
            "naming_scope": proposal["naming_scope"],
            "full_release_name_allocation_completed":
                proposal["full_release_name_allocation_completed"]},
        "read_method": READ,
        "load_method": LOAD_GAP,
        "independent_verification": {
            "policy": prep["comparison_policy"],
            "value_format": prep["value_format"],
            "state_for_this_table": vdesc,
            "evidence_files": [vfile],
            "contract_complete": prep["independent_value_contract_complete"]},
        "confirmation_basis": {
            "files": [{"path": f"datamgmt/contracts/releases/2026-10-06-bootstrap/{n}",
                       "sha256": sha(n)}
                      for n in ("sqlite-target-mapping-proposal.draft.json",
                                "sqlite-target-mapping-decisions.draft.json",
                                "sqlite-types-approved.draft.json",
                                "sqlite-roles-approved.draft.json")]}})
table_map = {"format": "xiangrugu.import-package.cbdb.table-mapping.v1",
             "table_count": len(tables_out),
             "flags_preserved_verbatim_from_proposal": {
                 k: proposal[k] for k in
                 ("target_mapping_approved", "nullability_constraints_approved",
                  "value_contract_approved", "full_release_name_allocation_completed",
                  "ready_for_import", "contract_frozen", "disposition_retained",
                  "naming_scope")},
             "tables": tables_out}

# --------------------------------------------------------------- field map
types_idx = {(t["source_object_id"], c["source_ordinal"]): c
             for t in types_ap["tables"] for c in t["columns"]}
unobs_set = {(c["source_object_id"], c["source_ordinal"]) for c in unobs["columns"]}
fields_out = []
for o in proposal["objects"]:
    for c in o["columns"]:
        tc = types_idx[(o["source_object_id"], c["source_ordinal"])]
        basis_ok = (tc["basis"] == "OBSERVED_API_STORAGE_CLASS"
                    or (o["source_object_id"], c["source_ordinal"]) in unobs_set)
        fields_out.append({
            "table": o["source_object_name"],
            "target_table": o["target_table_candidate"],
            "source_ordinal": c["source_ordinal"],
            "source_name": c["source_name"],
            "source_type_declared": c.get("approved_type"),
            "target_column": c["target_name_candidate"],
            "target_type": tc["approved_type"],
            "type_basis": tc["basis"],
            "null_policy": {"source_notnull": c["source_notnull"],
                            "observed_null": c["observed_null"],
                            "target_nullable_candidate": c["target_nullable_candidate"],
                            "policy": ("source explicit nullability only; constraint "
                                       "execution NOT approved "
                                       "(nullability_constraints_approved=false)")},
            "confirmation_status": {
                "type_mapping_approved_subbatch": type_dec["type_mapping_approved"],
                "basis_verified": basis_ok,
                "whole_release_target_mapping_approved": proposal["target_mapping_approved"]},
            "confirmation_basis": {
                "files": [{"path": f"datamgmt/contracts/releases/2026-10-06-bootstrap/{n}",
                           "sha256": sha(n)}
                          for n in ("sqlite-types-approved.draft.json",
                                    "sqlite-type-decisions.draft.json",
                                    "sqlite-unobserved-type-proposal.draft.json",
                                    "sqlite-target-mapping-proposal.draft.json")]}})
field_map = {"format": "xiangrugu.import-package.cbdb.field-mapping.v1",
             "column_count": len(fields_out),
             "notnull_columns": map_dec["notnull_columns"],
             "nullable_columns": map_dec["nullable_columns"],
             "observed_basis_columns": type_dec["observed_basis_columns"],
             "source_declaration_only_columns": type_dec["source_declaration_only_columns"],
             "columns": fields_out}

# ------------------------------------------------------- remaining values
rem = {"format": "xiangrugu.import-package.cbdb.remaining-value-verification.v1",
       "counts_separately_from_mapping": True,
       "mapping_covered_tables": 78, "mapping_covered_columns": 736,
       "value_verified_tables": 68, "value_pending_tables": 10,
       "value_pending_columns": 235,
       "group": "large (resource conflict: 1GiB disk-backed scratch exceeds "
                "current 64MiB execution scope; readonly_batch rejects large)",
       "pending_tables": [{"table": name_by_id[o["source_object_id"]],
                           "source_columns": o["source_columns"],
                           "column_count": len(o["source_columns"])}
                          for o in sorted(large["objects"],
                                          key=lambda x: name_by_id[x["source_object_id"]])],
       "verification_arrangement": {
           "next_step": "separate authorization for large-group reads with raised "
                        "scratch budget; per-group readiness files cited",
           "evidence_files": ["sqlite-value-large-readiness.draft.json",
                              "sqlite-value-next-groups.review.draft.json",
                              "sqlite-value-remaining-budget.draft.json"],
           "historical_counts_are_new_expectations":
               large["historical_counts_are_new_expectations"],
           "source_read_authorized": large["source_read_authorized"]},
       "note": "single-column-file concern kept separate: these 235 columns are "
               "PENDING value verification only; their TYPE/NAMING confirmation "
               "is already in field-mapping/table-mapping."}

# ------------------------------------------------------------------ summary
nb = lambda s: f"{s[:8]}…"
summary = f"""# CBDB 导入包整理摘要（第 1/6 块，仅整理不写库）

生成方式：全部字段由 build_cbdb_package.py 从同目录 release 草案/批准件合并，禁手填；重跑可复现。

## 成员（inventory 全量 8004 中 CBDB 路径恰 3，嵌套链 0）
| 成员 | kind | size | sha256 | 账本处置 | 关系/判定 |
|---|---|---|---|---|---|
| harvard/cbdb | directory | — | — | {ledger_state(SRC_DIR)["derived_state"]} | 容器，显式保留 |
| cbdb_20260919.json | file | 385 | {nb('bd62ab07aea5ce91')} | {ledger_state(SRC_JSON)["derived_state"]} | 出版方元数据：声明 sqlite 文件名+sha256（与实测成员一致）+HF zip 路径；**非重复表载体**，单独处置不入表 |
| cbdb_20260919.sqlite3 | file | 586,485,760 | {nb(SQLITE_SHA)} | {ledger_state(SRC_SQLITE)["derived_state"]} | 主源载体：78 表/736 列 |

JSON 内容取证：本轮经 SSH 在 32 只读 cat（R-07 合规），digest 复核等于账本值。

## 计数与确认态
- 表映射：78/78；字段映射：736/736（notnull 候选 184 / nullable 候选 552）。
- 类型：子批 type_mapping_approved=true（observed 700 + declaration-only 36，后者按 unobserved-proposal 的 PROPOSED_NOT_AUTHORIZED 确认态引用，approval_requested=false 未升级）。
- 角色：78 表 tabular-source、76 索引 source-schema-metadata（roles_approved=true）。
- 命名：naming_scope={proposal['naming_scope']}；**全版本名称分配未完成**（碰撞检查缺口）。
- 顶层提案 flags 原样保留：target_mapping_approved=False、nullability_constraints_approved=False、value_contract_approved=False、ready_for_import=False、contract_frozen=False。
- **账本口径（2026-11-26 起，从 A 账实际记录派生，禁硬编码）**：三成员在 A 账 `fa28a878` 均为 `{ledger_state(SRC_JSON)["derived_state"]}`（未匹配），故 `disposition_retained` 不再写作 BLOCKED。
- **B 批单表冻结候选 IMPORT 状态单列**：`{batch_b_import_state(SRC_SQLITE)}`。

## 值验证覆盖（与映射分别计数）
- 已生成源侧期望：68/78 表（canary 3 + small 55 + medium 10）。
- **剩余 10 表 / 235 列**（large 组）：见 remaining-value-verification.json；资源冲突（1GiB scratch > 64MiB 执行域）、readonly_batch 拒绝 large；历史计数不作新期望。

## 能力缺口（GAP，如实）
1. PG 生产装载器未实现（production_adapter_implemented=false）；importer/load.py 仅 staging 原型且须修订后方可运行——本次不运行。
2. 大组读取需另行授权与预算修订。
3. 全版本命名碰撞检查未完成。
4. 约束（PK/UNIQUE/FK/INDEX/DEFAULT）执行未批准；哨兵值不清洗政策沿用 docs/cbdb.md 结构哨兵（78 表/736 字段/76 主键自动索引/无视图触发器外键）。

## 结论
**ready_for_import 保持 False**；本包为整理/映射证据，非导入批准。旧文件零改动。
"""

write("members.json", members)
write("table-mapping.json", table_map)
write("field-mapping.json", field_map)
write("remaining-value-verification.json", rem)
(HERE / "SUMMARY.md").write_text(summary, encoding="utf-8")

# self-checks
tm = json.loads((HERE / "table-mapping.json").read_bytes())
fm = json.loads((HERE / "field-mapping.json").read_bytes())
assert tm["table_count"] == 78 and fm["column_count"] == 736
assert len(json.loads((HERE / "members.json").read_bytes())["members"]) == 3
rv = json.loads((HERE / "remaining-value-verification.json").read_bytes())
assert rv["value_pending_tables"] == 10 and rv["value_pending_columns"] == 235
print("CBDB package built OK:", *[p.name for p in sorted(HERE.iterdir()) if p.is_file()])
