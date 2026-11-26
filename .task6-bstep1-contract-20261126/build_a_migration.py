#!/usr/bin/env python3
"""A 批正式处置账迁移方案 + 对账预览生成器（确定性、真实模型驱动）。

本盒只出方案与预览，不改正式账、不冻结合同。

输入：
  - frozen-candidate.json         R61 冻结候选合同（23 规则）
  - inventory.json                正式清单（8004 成员）
  - disposition-ledger-after-selector-fix.json  现行正式处置账
  - ledger-replay.raw.json        dev 容器内真实模型复算结果
  - uncovered-7995-reconciliation.json  R59 三分类基线
"""
import json
import hashlib
import pathlib
import sys

BOX = pathlib.Path(__file__).resolve().parent
ROOT = BOX.parent
RELEASE = ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap"

AUTHORIZED_CANONICAL_SHA = "fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e"
EXPECTED_INVENTORY_SHA = "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db"
LEGACY_UNCOVERED = 7995
MIGRATED_UNCOVERED = 7981
TOTAL_MEMBERS = 8004
COVERED_EXPECTED = 23


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    outdir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else BOX

    frozen = load(ROOT / ".task6-abatch-freeze-20261125/abatch-frozen-candidate.json")
    inventory = load(RELEASE / "inventory.json")
    formal_ledger = load(RELEASE / "disposition-ledger-after-selector-fix.json")
    replay = load(BOX / "ledger-replay.raw.json")
    r59 = load(ROOT / ".task6-acceptance-nextbatch-20261125/uncovered-7995-reconciliation.json")

    # ---------- 硬断言：任何一条不成立即停，不产出方案 ----------
    assert replay["inventory_sha256"] == EXPECTED_INVENTORY_SHA, "清单摘要不符"
    assert replay["frozen_candidate_canonical_sha256"] == AUTHORIZED_CANONICAL_SHA, \
        "冻结候选规范摘要与授权值不符"
    assert len(inventory["entries"]) == TOTAL_MEMBERS, "成员总数非 8004"
    assert len(formal_ledger["records"]) == TOTAL_MEMBERS, "正式账记录数非 8004"
    assert formal_ledger["inventory_sha256"] == EXPECTED_INVENTORY_SHA, "正式账清单绑定不符"
    migrated = replay["migrated"]
    assert migrated["records"] == TOTAL_MEMBERS
    assert migrated["unmatched"] == MIGRATED_UNCOVERED, \
        f"迁入后未覆盖 {migrated['unmatched']} != 7981"
    assert migrated["multiple"] == 0, "存在多命中（重复归属）"
    assert migrated["unexplained"] == 0, "存在未解释命中"
    covered = TOTAL_MEMBERS - migrated["unmatched"]
    assert covered == COVERED_EXPECTED, f"已覆盖 {covered} != 23"

    by_id = {r["rule_id"]: r for r in frozen["rules"]}
    assert len(frozen["rules"]) == 23, "冻结候选规则数非 23"

    non_tabular = sorted(
        (r for r in frozen["rules"] if r["disposition"] == "NON_TABULAR"),
        key=lambda r: r["rule_id"],
    )
    imports = sorted(
        (r for r in frozen["rules"] if r["disposition"] == "IMPORT"),
        key=lambda r: r["rule_id"],
    )
    # 题目要求 14 条 NON_TABULAR；此处置账口径下有 16 条 NON_TABULAR（14 a1-* + 2 r-* 账本）
    a1_rules = [r for r in non_tabular if r["rule_id"].startswith("a1-")]
    r_rules = [r for r in non_tabular if r["rule_id"].startswith("r-")]
    assert len(a1_rules) == 14, f"a1-* 规则数 {len(a1_rules)} != 14"
    assert len(r_rules) == 2, f"r-* 规则数 {len(r_rules)} != 2"

    lookup = {x["rule_id"]: x for x in replay["rule_reverse_lookup"]}

    # ---------- 逐条规则 -> 正式账记录映射表 ----------
    rule_rows = []
    for r in sorted(frozen["rules"], key=lambda x: x["rule_id"]):
        rid = r["rule_id"]
        lk = lookup[rid]
        locs = lk["matched_locations"]
        loc = locs[0] if locs else {}
        rule_rows.append({
            "rule_id": rid,
            "category": ("FIRST_BATCH_IMPORT" if r["disposition"] == "IMPORT"
                         else ("A1_COMPANION_NON_TABULAR" if rid.startswith("a1-")
                               else "R_CHECKSUM_LEDGER_NON_TABULAR")),
            "disposition": r["disposition"],
            "targets_count": len(r.get("targets", [])),
            "selector": {
                "relative_path": r["selector"]["relative_path"],
                "archive_chain": r["selector"].get("archive_chain", []),
                "archive_ordinals": r["selector"].get("archive_ordinals", []),
            },
            "expected": {
                "kind": r["expected"]["kind"],
                "size": r["expected"].get("size"),
                "sha256": r["expected"].get("sha256"),
                "signature": r["expected"].get("signature"),
            },
            "reverse_lookup": {
                "matched_member_count": lk["matched_member_count"],
                "exclusive_single_owner": lk["exclusive"],
                "matched_relative_path": loc.get("relative_path"),
                "matched_archive_chain": loc.get("archive_chain"),
                "matched_archive_ordinals": loc.get("archive_ordinals"),
            },
            "reason_head": (r.get("reason") or "")[:120],
        })

    # ---------- 三分类核对：R59 基线 -> 迁入后 ----------
    # R59 的 7995 三分类成员身份（现取现用，不凭记忆）：
    #   - 已有处置提案 98 = 86 structural retention + 12 spatial_approved_context_companions
    #   - 待裁定 2 = m004860, m007903
    #   - 待补证 7895
    # 本次迁移的 16 条 NON_TABULAR 归属：
    #   - 14 条 a1-* == 12 个空间伴生件 + 2 个待裁定成员（m004860/m007903）
    #   - 2 条 r-* 账本（SHA256SUMS-b2、harvard/chgis/SHA256SUMS.txt）不在 R59 的 7995 分类内，
    #     它们原本在正式账中已由 BLOCKED 具名记录，不改变 7995->7981 的差值
    cls = r59["classification"]
    r59_propsal = cls["已有处置提案"]
    r59_pending_decision = cls["待裁定"]
    r59_pending_evidence = cls["待补证"]
    assert r59_propsal["count"] + r59_pending_decision["count"] + r59_pending_evidence["count"] \
        == LEGACY_UNCOVERED, "R59 三分类合计不等于 7995"

    r59_companions = set(r59_propsal["spatial_approved_context_companions"]["member_ids"])
    r59_pending_ids = set(r59_pending_decision["member_ids"])
    assert len(r59_companions) == 12, "空间伴生件数量非 12"
    assert len(r59_pending_ids) == 2, "待裁定成员数量非 2"

    a1_member_ids = set()
    for r in a1_rules:
        assert r["rule_id"].startswith("a1-m"), f"a1 规则命名不符约定: {r['rule_id']}"
        a1_member_ids.add(r["rule_id"][len("a1-"):])
    assert a1_member_ids == (r59_companions | r59_pending_ids), \
        f"a1-* 成员集合与 R59 伴生件+待裁定不一致：{sorted(a1_member_ids ^ (r59_companions | r59_pending_ids))}"

    migrated_from_7995 = len(a1_member_ids)           # 14
    r_ledgers_outside_7995 = len(r_rules)             # 2
    assert migrated_from_7995 == 14
    assert migrated_from_7995 + r_ledgers_outside_7995 == len(non_tabular) == 16

    bucket = {
        "legacy_7995": {
            "已有处置提案": r59_propsal["count"],
            "其中_structural_retention": r59_propsal["NON_TABULAR_structural_retention"]["count"],
            "其中_spatial_approved_context_companions": len(r59_companions),
            "待裁定": r59_pending_decision["count"],
            "待补证": r59_pending_evidence["count"],
            "sum": LEGACY_UNCOVERED,
        },
        "migration_effect": {
            "rules_migrated_total": len(non_tabular),
            "from_7995_members": migrated_from_7995,
            "from_7995_breakdown": {
                "spatial_approved_context_companions": len(r59_companions),
                "previously_pending_decision": len(r59_pending_ids),
            },
            "outside_7995_not_affecting_delta": r_ledgers_outside_7995,
            "r_ledger_member_ids": [r["rule_id"] for r in r_rules],
            "note": "r-* 两条账本原本已在正式账中具名（BLOCKED），迁移不改变 7995 的分类成员",
        },
        "migrated_7981": {
            "already_disposed_structural": r59_propsal["NON_TABULAR_structural_retention"]["count"],
            "note": "R59 的 98 个「已有处置提案」中，12 个空间伴生件原本仅是「读取/绑定已批、处置待正式化」，"
                    "本方案把它们转为正式 NON_TABULAR 规则，因此从「未正式覆盖」移入「已覆盖」",
            "newly_covered_by_this_plan": migrated_from_7995,
            "remaining_pending_evidence": r59_pending_evidence["count"],
            "remaining_pending_decision_after": r59_pending_decision["count"] - len(r59_pending_ids),
            "sum": r59_propsal["count"] - len(r59_companions)
                   + r59_pending_evidence["count"]
                   + (r59_pending_decision["count"] - len(r59_pending_ids)),
        },
    }
    # 精确口径：迁移后未覆盖 = 7995 - 本次真正转为已覆盖的成员数
    #   本次从「未正式覆盖」转入「已覆盖」的是 a1-* 对应的 14 个成员
    #   （12 空间伴生件原为"处置待正式化" + 2 个待裁定）
    assert bucket["migrated_7981"]["sum"] == MIGRATED_UNCOVERED, \
        f"三分类迁移后合计 {bucket['migrated_7981']['sum']} != 7981"
    assert bucket["legacy_7995"]["sum"] - bucket["migrated_7981"]["sum"] == migrated_from_7995, \
        "7995-7981 差值应恰等于从 7995 迁移的成员数"

    # ---------- 迁移文件清单与核验方法 ----------
    migration = {
        "version": 1,
        "box": "第6/6块后续·第1/6步",
        "batch": "A_FORMAL_LEDGER_MIGRATION_PLAN",
        "baseline_commit": "93964182c04f1edf94c94859f611728c68997eee",
        "status": "PLAN_ONLY_NOT_EXECUTED",
        "scope_note": "本盒只出迁移方案与对账预览；不改正式账、不冻结合同、不写库",
        "authorized_candidate": {
            "file": ".task6-abatch-freeze-20261125/abatch-frozen-candidate.json",
            "canonical_sha256_recomputed": replay["frozen_candidate_canonical_sha256"],
            "canonical_sha256_authorized": AUTHORIZED_CANONICAL_SHA,
            "match": replay["frozen_candidate_canonical_sha256"] == AUTHORIZED_CANONICAL_SHA,
            "rules": len(frozen["rules"]),
            "exceptions": len(frozen["exceptions"]),
            "composition": {"IMPORT_first_batch": len(imports),
                            "NON_TABULAR_a1_star": len(a1_rules),
                            "NON_TABULAR_r_ledgers": len(r_rules)},
        },
        "reconciliation_preview": {
            "total_members": TOTAL_MEMBERS,
            "covered_after_migration": covered,
            "uncovered_after_migration": migrated["unmatched"],
            "equation": f"{covered} + {migrated['unmatched']} = {TOTAL_MEMBERS}",
            "equation_holds": covered + migrated["unmatched"] == TOTAL_MEMBERS,
            "legacy_uncovered_before": LEGACY_UNCOVERED,
            "delta": LEGACY_UNCOVERED - migrated["unmatched"],
            "duplicate_attribution": {
                "multiple_matches": migrated["multiple"],
                "unexplained": migrated["unexplained"],
                "duplicate_inventory_location": sum(
                    1 for i in migrated["issue_codes"] if i == "duplicate_inventory_location"),
                "conclusion": "无重复归属" if migrated["multiple"] == 0 else "存在重复归属",
            },
            "issue_codes_after_migration": migrated["issue_codes"],
            "issue_code_notes": {
                "exception_not_implemented": "两条例外账本声明仍阻断：NUL/CHGIS 运行证据需绑新合同摘要，属冻结后动作",
                "incomplete_inventory": "原清单 complete=false 恒门，按 R-08/既有裁决保持",
                "unmatched_member": f"{migrated['unmatched']} 个成员无处置规则，即本方案要保留的未覆盖面",
            },
            "bucket_breakdown": bucket,
        },
        "r59_baseline_cross_check": {
            "file": ".task6-acceptance-nextbatch-20261125/uncovered-7995-reconciliation.json",
            "file_sha256": sha256_file(
                ROOT / ".task6-acceptance-nextbatch-20261125/uncovered-7995-reconciliation.json"),
            "legacy_uncovered": r59["uncovered_members"],
            "legacy_covered": r59["covered_members"],
            "legacy_ledger_records": r59["ledger_records"],
            "三分类_sum_check": r59["uncovered_members"],
        },
        "rule_to_ledger_mapping": rule_rows,
        "rule_reverse_lookup_summary": {
            "total_rules": len(frozen["rules"]),
            "exclusive_single_owner": sum(1 for x in rule_rows if x["reverse_lookup"]["exclusive_single_owner"]),
            "non_exclusive": sum(1 for x in rule_rows if not x["reverse_lookup"]["exclusive_single_owner"]),
            "requirement_14_a1_star": {
                "expected": 14,
                "actual_all_exclusive": sum(
                    1 for x in rule_rows
                    if x["category"] == "A1_COMPANION_NON_TABULAR"
                    and x["reverse_lookup"]["exclusive_single_owner"]),
                "hint": "题目所说 14 条 NON_TABULAR 指 a1-* 伴生件；另有 2 条 r-* 校验账本亦为 NON_TABULAR，一并列入以保持 23 总数闭合",
            },
        },
        "files_to_change_on_migration": [
            {
                "file": "datamgmt/contracts/releases/2026-10-06-bootstrap/disposition-ledger-<new>.json",
                "action": "新增正式处置账（不覆盖 disposition-ledger-after-selector-fix.json）",
                "content": "由 DispositionLedger.evaluate(inventory, frozen_contract) 产出",
                "expected_bindings": {
                    "contract_sha256": AUTHORIZED_CANONICAL_SHA,
                    "inventory_sha256": EXPECTED_INVENTORY_SHA,
                    "records": TOTAL_MEMBERS,
                },
                "verification": "重算 contract_sha256/inventory_sha256 与文件内值逐字相等；records==8004；unmatched==7981",
            },
            {
                "file": "正式合同文件（deploy 冻结合同 + 仓内合同）",
                "action": "以 fa28a878 候选替换现行 ba8118fb 合同（需另批授权）",
                "content": "abatch-frozen-candidate.json 原字节",
                "verification": "ReleaseContract.model_validate 通过且 .sha256==fa28a878…；原 9 规则 deep-equal 不变；两例外不变；inventory_sha256==fb5e6b33…",
            },
            {
                "file": "datamgmt/docs/IMPORT-PACKAGE-TODO.md",
                "action": "新增迁移盒记录行（文档日志）",
                "verification": "记录实际提交号与证据路径；不改历史行",
            },
            {
                "file": "docs/log.md",
                "action": "按 R-05 记一行文档变动",
                "verification": "单行 ≤300 字，含迁移事实与锚点",
            },
        ],
        "files_must_not_change": [
            {"file": "datamgmt/contracts/releases/2026-10-06-bootstrap/inventory.json",
             "reason": "原清单字节不动（inventory_sha fb5e6b33 为全局绑定）",
             "verification": "sha256 == fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db"},
            {"file": "datamgmt/contracts/releases/2026-10-06-bootstrap/disposition-ledger-after-selector-fix.json",
             "reason": "现行账保留作历史与对照；迁移写新文件",
             "verification": "sha256 迁移前后相等"},
            {"file": "首批七表 IMPORT 规则（m002709/m002717/m004812/m006642/m008002/m008003/m008004）",
             "reason": "已验收批次不变量，迁移不得改动其 selector/expected/targets",
             "verification": "7 条规则 canonical 子串与 abatch-frozen-candidate 中同名规则逐字节相等"},
            {"file": "两条例外（checksum_nul / checksum_path_binding）",
             "reason": "保持原样",
             "verification": "exceptions 数组 byte-identical；raw_sha256 分别 900d98c6…/694c101f…"},
            {"file": "首批生产 scope 的 7995 门",
             "reason": "属已验收七表批次自身不变量，与进度账 7981 双口径并存",
             "verification": "该门数值保持 7995 不被迁移改写"},
        ],
        "verification_method": {
            "step_1": "用正式模型重算候选摘要：ReleaseContract.model_validate(candidate).sha256 必须 == fa28a878…",
            "step_2": "用正式模型重算清单摘要：InventoryManifest(...).sha256 必须 == fb5e6b33…",
            "step_3": "DispositionLedger.evaluate(inventory, candidate)：records==8004，unmatched==7981，multiple==0，unexplained==0",
            "step_4": "逐规则反查：23 条规则每条恰命中 1 个清单成员（exclusive），且成员-规则构成 1:1 双射",
            "step_5": "等式闭合：已覆盖 23 + 未覆盖 7981 == 8004",
            "step_6": "不可变面复核：原清单 sha、现行账 sha、首批七表规则、两条例外、7995 门 全部不变",
            "step_7": "双跑确定性：同一输入两次运行，全部产物 sha 逐字相等",
        },
        "known_issue_codes_after_migration": [
            {"code": "exception_not_implemented",
             "reason": "两条例外账本需绑新合同摘要的运行证据；本轮未重跑（试装不重跑）",
             "closure_condition": "冻结后在新合同下重跑 writeoff/checksum_reader 取证"},
            {"code": "incomplete_inventory",
             "reason": "原清单 3 个 checksum issue + complete=false 恒门",
             "closure_condition": "按既有裁决保留，不因迁移消失"},
            {"code": "unmatched_member",
             "count": MIGRATED_UNCOVERED,
             "reason": "剩余 7981 无处置规则",
             "closure_condition": "后续批次补证/提案"},
        ],
        "full_ready_for_import": False,
        "production_write": False,
    }

    artifacts = {
        "a-migration-plan.json": migration,
    }
    outdir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name, obj in artifacts.items():
        p = outdir / name
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
        shas[name] = sha256_file(p)
    shas["__canonical"] = {n: canonical_sha(o) for n, o in artifacts.items()}
    print(json.dumps(shas, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()