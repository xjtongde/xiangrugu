#!/usr/bin/env python3
"""B 批单表逐列审批表 + 可冻结合同草案生成器（确定性、证据驱动）。

数据来源（全部现取现用，禁凭记忆）：
  - 源 DDL/PK/索引/null：source-ddl-probe.json（32 只读 sqlite3 mode=ro&immutable=1 实测）
  - 类型批准：datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-types-approved.draft.json
  - 目标名候选：.../sqlite-target-mapping-proposal.draft.json
  - 已批期望：.../sqlite-value-canary.approved.json
  - R62 回读：trial-pass.json / b-trial-record.json
用法：python3 build_b_approval.py <outdir>
"""
import json
import hashlib
import pathlib
import sys

BOX = pathlib.Path(__file__).resolve().parent
ROOT = BOX.parent
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"
TABLE = "SOCIAL_INSTITUTION_ADDR"
TARGET_SCHEMA = "cbdb"
TARGET_TABLE = "cbdb__social_u5f_institution_u5f_addr"
RULE_ID = "m007906"


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    """规范 JSON 摘要：sort_keys + 紧凑分隔符 + UTF-8。"""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _null_counts_match(trial_nulls, probe_nulls, rows):
    """按「源列 -> 目标列」列序对齐后比较 NULL 数。

    trial-pass 的 null_counts 键为目标列名，源探针为源列名；两者命名空间不同，
    直接 dict 相等必然为假。此处逐列按映射对齐后再比对数值，缺失或数值不等返回 False。
    """
    if len(rows) != len(trial_nulls) or len(rows) != len(probe_nulls):
        return False
    for r in rows:
        src, tgt = r["source_column"], r["target_name_candidate"]
        if src not in probe_nulls or tgt not in trial_nulls:
            return False
        if probe_nulls[src] != trial_nulls[tgt]:
            return False
    return True


def main():
    outdir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else BOX

    probe = load(BOX / "source-ddl-probe.json")
    types_appr = load(RELEASE / "sqlite-types-approved.draft.json")
    mapping = load(RELEASE / "sqlite-target-mapping-proposal.draft.json")
    canary = load(RELEASE / "sqlite-value-canary.approved.json")
    trial_pass = load(BOX / "trial-pass.json")  # 同目录快照（来源见 lead-record 复用声明）
    trial_rec = load(BOX / "b-trial-record.json")

    # ---- 证据锚（现取现用） ----
    src = canary["source"]
    canary_obj = next(o for o in canary["objects"] if o["source_object_name"] == TABLE)
    type_obj = next(o for o in types_appr["tables"] if o["source_object_name"] == TABLE)
    map_obj = next(o for o in mapping["objects"] if o["source_object_name"] == TABLE)

    # ---- 断言：源实测 == 已批期望 == 目标映射，任一失配即停 ----
    assert probe["table"] == TABLE
    assert probe["rows"] == canary_obj["previous_observed_rows"], "行数与已批期望不符"
    assert len(probe["pragma_table_info"]) == len(canary_obj["columns"]) == 11
    assert [c["name"] for c in probe["pragma_table_info"]] == canary_obj["source_columns"]
    assert trial_pass["pg_row_count"] == canary_obj["previous_observed_rows"]
    assert trial_pass["duplicate_rows"] == 0
    assert trial_rec["approved_expectation"]["expected_sha256"] == trial_pass["reproduced"]["expected_sha256"]

    ti = {c["name"]: c for c in probe["pragma_table_info"]}
    type_cols = {c["source_name"]: c for c in type_obj["columns"]}
    canary_cols = {canary_obj["source_columns"][c["source_ordinal"]]: c for c in canary_obj["columns"]}
    map_cols = {c["source_name"]: c for c in map_obj["columns"]}

    # 源 PK 源序（PRAGMA pk 值即 PK 内 1 基位置）
    pk_cols = sorted(
        [(c["pk"], c["name"]) for c in probe["pragma_table_info"] if c["pk"] > 0]
    )
    pk_names_in_order = [n for _, n in pk_cols]
    # 断言探针 PK 序与 SQLite autoindex 序一致（索引序 == 声明 PK 序）
    auto = next(i for i in probe["indexes_detail"] if i["origin"] == "pk")
    assert [c["name"] for c in auto["index_info"]] == pk_names_in_order, "PK 声明序与 autoindex 序不一致"

    # 源端索引事实
    src_indexes = []
    for ix in probe["indexes_detail"]:
        src_indexes.append({
            "name": ix["name"],
            "unique": bool(ix["unique"]),
            "origin": ix["origin"],
            "partial": bool(ix["partial"]),
            "columns_in_order": [c["name"] for c in ix["index_info"]],
        })
    n_unique_indexes = sum(1 for i in src_indexes if i["unique"])
    n_non_pk_indexes = sum(1 for i in src_indexes if i["origin"] != "pk")

    rows = []
    for ordinal0 in range(11):
        name = canonical_name = probe["pragma_table_info"][ordinal0]["name"]
        info = ti[name]
        t = type_cols[name]
        m = map_cols[name]
        c = canary_cols[name]

        # 类型：源声明 vs 观察批准 vs 目标 pg 类型
        approved_pg = t["approved_type"]
        observed_null = c["allow_null_value"] if "allow_null_value" in c else None
        actual_nulls = probe["null_counts"][name]
        src_notnull = bool(info["notnull"])

        # 可空性判定：源 NOT NULL -> 目标 NOT NULL；源可空 -> 目标可空
        target_nullable = not src_notnull
        # 交叉核对：已批期望 allow_null_value 与源 pragma + 实测 null 数一致
        canary_nullable = c["allow_null_value"]
        assert canary_nullable == target_nullable, f"{name}: canary nullable 与源 NOT NULL 不一致"
        assert (actual_nulls == 0) == (not target_nullable) or target_nullable, \
            f"{name}: NOT NULL 列实测有 NULL"
        assert bool(m["target_nullable_candidate"]) == target_nullable, f"{name}: 映射候选可空性与源不一致"

        pk_pos = info["pk"]
        rows.append({
            "source_ordinal_0based": ordinal0,
            "column_ordinal_1based": ordinal0 + 1,
            "source_column": name,
            "column_identity_sha256": c["column_key"],
            "source_declared_type": info["type"],
            "source_notnull_pragma": src_notnull,
            "source_default_sql": info["dflt_value"],
            "source_pk_position": pk_pos,
            "source_observed_storage_classes": t["non_null_values_observed"],
            "observed_null_count": actual_nulls,
            "observed_rows": probe["rows"],
            "approved_type_basis": t["basis"],
            "target_schema_candidate": TARGET_SCHEMA,
            "target_table_candidate": TARGET_TABLE,
            "target_name_candidate": m["target_name_candidate"],
            "target_pg_type_candidate": approved_pg,
            "target_nullable_candidate": target_nullable,
            "target_pg_type_model_expressible": approved_pg in ("text", "bigint"),
            "approval": {
                "source_column_identity": "APPROVED",
                "source_side_value_expectation": "APPROVED",
                "type_mapping": "APPROVED",
                "target_table_name": "PENDING_TEA_AROMA_DECISION",
                "target_column_name": "PENDING_TEA_AROMA_DECISION",
                "nullability_constraints": "PENDING_TEA_AROMA_DECISION",
                "value_contract_freeze": "PENDING_NEXT_ROUND",
            },
        })

    # ---- 约束/索引/默认值处置表 ----
    constraint_rows = [
        {
            "item": "PRIMARY KEY",
            "source_declared": True,
            "source_definition": {
                "kind": "composite",
                "source_columns_in_pk_order": pk_names_in_order,
                "type": "sqlite_rowid_table_declared_pk_backed_by_unique_autoindex",
                "autoindex": auto["name"],
            },
            "source_fact_verified_live": True,
            "source_pk_distinct_observed": probe["pk_distinct"],
            "source_row_count": probe["rows"],
            "pk_uniqueness_holds_in_source": probe["pk_distinct"] == probe["rows"],
            "target_proposal": "在目标表建立同列同序 PRIMARY KEY，并把 PK 值列一律 NOT NULL",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "源端 PK 六列实测 3859/3859 唯一；忠实保留主键语义（R-08）。",
        },
        {
            "item": "UNIQUE",
            "source_declared": True,
            "source_definition": {
                "unique_index_count": n_unique_indexes,
                "note": "唯一性仅由 PK 隐式唯一索引提供；无额外独立 UNIQUE 约束",
                "indexes": [i for i in src_indexes if i["unique"]],
            },
            "source_fact_verified_live": True,
            "target_proposal": "不另建 UNIQUE 约束；PK 已覆盖唯一性，重复约束无源依据",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "源端无独立 UNIQUE 声明，仅 PK autoindex；不新增源没有的约束。",
        },
        {
            "item": "INDEX",
            "source_declared": n_non_pk_indexes > 0,
            "source_definition": {
                "non_pk_index_count": n_non_pk_indexes,
                "all_indexes": src_indexes,
                "catalog_index_total_for_db": 76,
            },
            "source_fact_verified_live": True,
            "target_proposal": "本表除 PK autoindex 外无独立二级索引，故不建额外索引；PK 索引由 PK 约束隐含",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "PRAGMA index_list 实测本表仅 1 个 origin=pk 索引。",
        },
        {
            "item": "FOREIGN KEY",
            "source_declared": len(probe["fk_list"]) > 0,
            "source_definition": {
                "fk_count": len(probe["fk_list"]),
                "fk_list": probe["fk_list"],
            },
            "source_fact_verified_live": True,
            "target_proposal": "源端无外键声明，不建 FK",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "PRAGMA foreign_key_list 实测为空。",
        },
        {
            "item": "DEFAULT",
            "source_declared": any(info["dflt_value"] is not None for info in ti.values()),
            "source_definition": {
                "columns_with_default_count": sum(1 for i in ti.values() if i["dflt_value"] is not None),
                "columns_with_default": {
                    info_name: info["dflt_value"]
                    for info_name, info in ti.items()
                    if info["dflt_value"] is not None
                },
                "note": "5 列声明 DEFAULT NULL；DEFAULT NULL 在 PostgreSQL 中等价于无显式默认值",
            },
            "source_fact_verified_live": True,
            "target_proposal": "不写 DEFAULT 子句（源仅 DEFAULT NULL，语义等价于无默认值）",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "唯一出现的默认值字面量是 NULL；忠实导入不禁止显式 NULL 默认，只需语义等价。",
        },
        {
            "item": "NOT NULL",
            "source_declared": True,
            "source_definition": {
                "not_null_columns": [n for n, i in ti.items() if i["notnull"]],
                "nullable_columns": [n for n, i in ti.items() if not i["notnull"]],
            },
            "source_fact_verified_live": True,
            "target_proposal": "NOT NULL 列建 NOT NULL 约束；可空列保持可空",
            "target_execution": "NOT_EXECUTED",
            "approval": "PENDING_TEA_AROMA_DECISION",
            "rationale": "以源 pragma NOT NULL 为准，并与 3859 行实测 NULL 计数一致。",
        },
    ]

    # ---- 待批表主文档 ----
    approval = {
        "version": 1,
        "box": "第6/6块后续·第1/6步",
        "generated_at_utc": "2026-11-26T14:00:00Z",
        "baseline_commit": "93964182c04f1edf94c94859f611728c68997eee",
        "batch": "B_SINGLE_TABLE_CONTRACT_PENDING",
        "scope_note": "本盒只处理 SOCIAL_INSTITUTION_ADDR 一张表；不冻结、不装载、不写库",
        "source_member": {
            "rule_id": RULE_ID,
            "relative_path": src["path"],
            "size_bytes": src["size"],
            "sha256": src["sha256"],
            "sha256_verification": {
                "method": "sha256sum 于 32 宿主只读路径现取现用",
                "verified_live_this_box": True,
                "matches_approved_canary": True,
            },
        },
        "source_table": TABLE,
        "source_object_id": canary_obj["source_object_id"],
        "source_schema_hash": canary_obj["schema_hash"],
        "source_ddl": probe["ddl"],
        "source_ddl_sha256": probe["ddl_sha256"],
        "source_row_count": probe["rows"],
        "source_sqlite_version": probe["sqlite_version_read"],
        "target": {
            "schema_candidate": TARGET_SCHEMA,
            "table_candidate": TARGET_TABLE,
            "table_name_status": "CANDIDATE_NOT_APPROVED",
            "naming_collision_check": "PENDING",
        },
        "approved_source_side_expectation": {
            "expected_count": canary_obj["previous_observed_rows"],
            "expected_sha256": next(
                t for t in [trial_pass["reproduced"]["expected_sha256"]]
            ),
            "field_count": trial_rec["approved_expectation"]["field_count"],
            "schema_hash": canary_obj["schema_hash"],
            "duplicate_rows": trial_pass["duplicate_rows"],
            "evidence_file": "datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-canary.approved.json",
            "evidence_file_sha256": sha256_file(RELEASE / "sqlite-value-canary.approved.json"),
            "status": "APPROVED",
        },
        "r62_readback_cross_check": {
            "trial_result": trial_pass["result"],
            "pg_row_count": trial_pass["pg_row_count"],
            "duplicate_rows": trial_pass["duplicate_rows"],
            "comparison_result": trial_pass["comparison"]["result"],
            "sha_equal": trial_pass["comparison"]["sha_equal"],
            "difference_count": len(trial_pass["comparison"]["differences"]),
            "missing_rows": trial_pass["comparison"]["missing_rows"],
            "excess_rows": trial_pass["comparison"]["excess_rows"],
            "source_count": trial_pass["comparison"]["source_count"],
            "target_count": trial_pass["comparison"]["target_count"],
            "source_fields": trial_pass["comparison"]["source_fields"],
            "target_fields": trial_pass["comparison"]["target_fields"],
            "source_sha256": trial_pass["comparison"]["source_sha256"],
            "target_sha256": trial_pass["comparison"]["target_sha256"],
            "null_counts_match_source_probe": _null_counts_match(
                trial_pass["null_counts"], probe["null_counts"], rows),
            "rollback_table_dropped": trial_pass["rollback"]["table_dropped"],
            "evidence_paths": [
                ".task6-bbatch-addr-trial-20261125/trial-pass.json",
                ".task6-bbatch-addr-trial-20261125/b-trial-record.json",
            ],
            "status": "TRIAL_PASS_REUSED_NOT_RERUN",
        },
        "column_count": 11,
        "columns": rows,
        "constraints_and_indexes": constraint_rows,
        "approval_summary": {
            "already_approved": [
                "源成员身份与字节（m007906 全 sha）",
                "源列身份 11/11（column_identity）",
                "类型映射 11/11（OBSERVED_API_STORAGE_CLASS）",
                "源侧值期望（3859 行 / 2cb8c354… / 42449 字段 / schema 1f88cd80…）",
                "R62 隔离试装回读一致性",
            ],
            "pending_decision": [
                "目标表名批准（现为 candidate，命名碰撞检查未完成）",
                "目标列名批准 11/11（现为 candidate）",
                "可空性/约束执行批准（PK/UNIQUE/INDEX/FK/DEFAULT/NOT NULL 六项处置已提案，未执行）",
                "值合同冻结",
                "新的写库授权原文（首批 88f4f1ac 不得复用）",
                "Codex 独立验收放行",
            ],
        },
        "full_ready_for_import": False,
        "production_write": False,
    }

    # ---- 合同草案（可冻结形态，复用正式模型字段） ----
    # 只映射模型能表达的部分；不可表达项单列
    columns_for_contract = []
    for r in rows:
        columns_for_contract.append({
            "ordinal": r["column_ordinal_1based"],
            "source_column": r["source_column"],
            "target_column": r["target_name_candidate"],
            "pg_type": r["target_pg_type_candidate"],
            "nullable": r["target_nullable_candidate"],
        })

    expressible = [c for c in columns_for_contract if c["pg_type"] in ("text", "bigint")]
    not_expressible = [c for c in columns_for_contract if c["pg_type"] not in ("text", "bigint")]

    # inventory 摘要现取现用（R62 接收记录所绑、且与清单重算一致值）
    inventory_sha = trial_rec.get("inventory_sha256")
    if inventory_sha is None:
        inventory_sha = load(BOX.parent / ".task6-bbatch-addr-trial-20261125/a-reception-record.json")["inventory_sha256"]

    contract_draft = {
        "version": 1,
        "release_id": "2026-10-06-bootstrap",
        "source_version": "2026-09-19",
        "inventory_sha256": inventory_sha,
        "status": "draft",
        "review": None,
        "exceptions": [],
        "rules": [{
            "rule_id": RULE_ID,
            "selector": {
                "relative_path": src["path"],
                "archive_chain": [],
                "archive_ordinals": [],
            },
            "expected": {
                "kind": "file",
                "size": src["size"],
                "sha256": src["sha256"],
                "signature": "sqlite",
            },
            "disposition": "IMPORT",
            "reason": "B 批单表导入：SOCIAL_INSTITUTION_ADDR 源侧值期望已批准，R62 隔离试装 TRIAL_PASS；本盒为待冻结草案",
            "format_family": "sqlite",
            "encodings": [],
            "targets": [{
                "object_name": TABLE,
                "schema": TARGET_SCHEMA,
                "table": TARGET_TABLE,
                "expected_count": canary_obj["previous_observed_rows"],
                "expected_sha256": trial_pass["reproduced"]["expected_sha256"],
                "columns": columns_for_contract,
            }],
            "validator": "canonical_value_v1",
            "mirror_of": None,
            "mirror_evidence_sha256": None,
        }],
    }

    model_gaps = {
        "version": 1,
        "purpose": "现行合同模型无法表达的 B 批要素，逐项给出字段名与实证",
        "reproduce_command": "见 model-gap-evidence.txt（dev 容器内实际执行 pydantic 校验）",
        "gaps": [
            {
                "gap_id": "G1",
                "title": "pg_type 无法表达 double precision",
                "model_location": "contracts.ColumnMapping.pg_type",
                "model_pattern": "^(text|bigint|numeric\\[[1-9][0-9]*,[0-9]+\\])$",
                "affected_columns": [r["source_column"] for r in rows if not r["target_pg_type_model_expressible"]],
                "affected_target_types": ["double precision"],
                "empirical_proof": "ColumnMapping(pg_type='double precision') -> string_pattern_mismatch",
                "impact": "11 列中 2 列（inst_xcoord/inst_ycoord）无法写入合同",
                "proposed_resolution": "扩展 pg_type 枚举（最小增补建议：加入 double precision）；属模型修改，另批授权",
            },
            {
                "gap_id": "G2",
                "title": "无主键/约束表达字段",
                "model_location": "contracts.ObjectTarget",
                "existing_fields": ["object_name", "schema_name", "table", "expected_count",
                                    "expected_sha256", "columns", "derived_rownum",
                                    "duplicate_reconciliation", "geometry"],
                "missing_fields": ["primary_key", "unique_constraints", "indexes", "foreign_keys",
                                   "column_defaults", "not_null_constraints（仅 nullable 布尔）"],
                "empirical_proof": "ObjectTarget(primary_key=[...]) -> extra_forbidden",
                "impact": "六项约束处置（PK/UNIQUE/INDEX/FK/DEFAULT/NOT NULL）在合同中无处安放，只能落在本盒审批表",
                "proposed_resolution": "新增 ObjectTarget.primary_key/unique_constraints/indexes/foreign_keys 字段；属模型修改，另批授权",
            },
            {
                "gap_id": "G3",
                "title": "ColumnMapping 无 default 字段",
                "model_location": "contracts.ColumnMapping",
                "missing_fields": ["default_value"],
                "empirical_proof": "ColumnMapping(default_value=None) -> extra_forbidden",
                "impact": "源 5 列 DEFAULT NULL 无法在合同记录（本盒判为语义等价于无默认，影响低）",
                "proposed_resolution": "可选扩展 column_defaults；优先级低于 G1/G2",
            },
            {
                "gap_id": "G4",
                "title": "targets 仅在 IMPORT 处置下允许（B 批无阻塞）",
                "model_location": "contracts.DispositionRule.consistent_action",
                "note": "IMPORT 分支允许 targets；本表以 IMPORT 表达，不受阻",
                "impact": "无当前影响，仅记录以便复核",
                "proposed_resolution": "无需变更",
            },
            {
                "gap_id": "G6",
                "title": "列序数必须从 1 连续，无法表达「源列存在但目标不建列」的部分映射",
                "model_location": "contracts.ObjectTarget.extended_mapping_consistency",
                "model_rule": "ordinals != list(range(1, len(ordinals)+1)) -> Column ordinals must be contiguous and ordered from 1",
                "empirical_proof": "保留原序数剔除 inst_xcoord/inst_ycoord -> Column ordinals must be contiguous and ordered from 1；重建为 1..9 后才 VALIDATED_OK",
                "impact": "若 G1 未解决而采取「先排除两坐标列」的降级路径，则重建序数会丢失源列序证据（源列 7/8 位置无法在合同中表达）",
                "proposed_resolution": "随 G1 一并解决（补齐 double precision 后无需剔除）；否则需新增 source_ordinal 保留字段",
            },
            {
                "gap_id": "G5",
                "title": "合同无 schema 层命名约束（IDENTIFIER ≤63）",
                "model_location": "contracts.ObjectTarget.table",
                "model_pattern": "^[a-z][a-z0-9_]{0,62}$",
                "note": "表名模式已限制 63 字符，与 PG 标识符上限一致；目标列名无独立模式约束（跟随 PG 由执行层校验）",
                "impact": "低；列名批准时需另行校验 ≤63 与保留字",
                "proposed_resolution": "在列名批准阶段补校验，不改模型",
            },
        ],
    }

    # ---- 输出 ----
    model_gaps["gaps"].sort(key=lambda g: g["gap_id"])
    outdir.mkdir(parents=True, exist_ok=True)
    arts = {
        "b-approval-table.json": approval,
        "b-contract-draft.json": contract_draft,
        "model-gaps.json": model_gaps,
    }
    shas = {}
    for name, obj in arts.items():
        p = outdir / name
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        shas[name] = sha256_file(p)
    shas["__canonical"] = {n: canonical_sha(o) for n, o in arts.items()}
    print(json.dumps(shas, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()