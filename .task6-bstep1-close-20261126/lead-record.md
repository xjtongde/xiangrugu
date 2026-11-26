# 第 6/6 块后续·第 1/6 步收口｜B 批合同补正 + A 批正式账迁移

- 基线：`608d191de29f1206b6075223c0e007b3e071c371`
- box 起：2026-11-26T14:30:49Z
- 授权：茶香"第 6/6 块后续·第 1/6 步收口"（B 补正 + A 正式账迁移）；lead 执行，a03 独立复核
- 边界：不更新 deploy、不改服务/权限、不写数据库、不复用首批写库审批 `88f4f1ac`

## B 面

1. **目标名全量碰撞检查**（`collision-check.json`，canonical `6c597f68…`）
   扫描面：object-index 1293 对象 / 1224 唯一 (schema,table) 对 / 413 cbdb 候选列名池。
   表名 `cbdb.cbdb__social_u5f_institution_u5f_addr` 在索引中存在且唯一、与既有命名账逐字一致、37 字符合规；
   11 列目标名表内唯一、最长 38。跨表同名（c_source×20/c_pages×21/c_notes×33 等）为列作用域内正常，非冲突。
   **判定 PASS_NO_COLLISION，未触发停止条件。**
2. **最小扩展合同模型**（`b-model-extension-and-regression.json`）
   - `ColumnMapping.pg_type` 正则增补 `double precision`；
   - 新增 `PrimaryKey`（有序目标列元组）+ `ObjectTarget.primary_key`（可选，默认 None）；
   - PK 列须为已映射目标列且 NOT NULL；PK 内不得重复（三项负例实测均被拒）。
   - **规范字节不漂移**：`abatch-frozen-candidate` 在旧/新模型下 canonical 均为 `fa28a878…`，字节 57339 逐字节一致。
   - **11 列原序保留**：ordinals 1..11 连续，2 列 double precision 全部入合同，**未删列**。
   - schema 再生：33 行新增 + 1 行 pattern 修改。
3. **回归**：同环境下（新 schema）旧代码 `2 failed/140 passed`（schema/runtime 不匹配），补丁后 **142 passed**，证明补丁必需且无回归。
   说明：容器全量 unit 基线本身有 87 项预存失败，与本补丁无关。
4. **单表冻结候选** `b-single-table-frozen-candidate.json`
   正式 `ReleaseContract` 校验 **validated=true / schema_domain_ok=true**，sha `d3cdb81c4caf75c9…`；
   绑 3859 行、重复 0、源侧 `2cb8c354…`、inventory `fb5e6b33…`、本次审批（`b-approval-table-v2.json` sha 入证）。
   六项约束 `target_execution` 全部保持 `NOT_EXECUTED`；约束与默认值来源依据见 `b-frozen-binding-evidence.json`。

## A 面

1. **新版正式处置账** `datamgmt/contracts/releases/2026-10-06-bootstrap/disposition-ledger-fa28a878-20261126.json`
   由已接收合同 `fa28a878…` 经正式 `DispositionLedger.evaluate` 生成；记录 8004。
   **覆盖 23 / 未覆盖 7981 / 重复归属 0**；23 条规则逐条恰命中 1 成员且互斥。
   issue_codes：`exception_not_implemented` / `incomplete_inventory` / `unmatched_member`。
2. **两条例外同一合同重生**：NUL raw `900d98c6…`/22071B、chgis raw `694c101f…`/551B，白名单全等；
   证据摘要独立重算：nul `679dca4d…`、chgis `fae3502e…`。
3. **正式核销**：`exactly_three_fixed_closed=true`，恰闭合 3 条历史问题
   （checksum_line line=173 / checksum_nul count=126 / checksum_missing line=4）；
   派生只余 `unmatched_member`，**ready_for_import=false 保持**。
4. **旧账与原清单保留**：`disposition-ledger-after-selector-fix.json` `0b093077…`、`inventory.json` `fb5e6b33…` 字节未变；complete=false 保持。
5. **账本引用更新**：cbdb/tabular 两个 build 脚本指向新账；`artifact-hashes-after-selector-fix.json` 追加新账摘要（旧条目保留）。

## 判定

**B: PASS**｜**A: PASS**（详见 `b-model-extension-and-regression.json`、`a-verification.json`，A 面 10 项检查全 True）

## 首个剩余缺口

B 面：G3（无 `default_value`）与 UNIQUE/INDEX/FK 未建模 → 六项约束的执行仍 `NOT_EXECUTED`，需下一批写库授权原文（不得复用 `88f4f1ac`）。
A 面：7981 未覆盖成员仍为 `unmatched_member`，全量 `ready_for_import=false`。
