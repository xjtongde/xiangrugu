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

## a03 独立复核结论（零复用，8/8 项复现）

**B = PASS｜A = PASS**。硬条件均独立证实：
- 摘要不漂移：同一候选在旧模型(608d191 blob)/新模型/work 副本三向 canonical 全等 = `fa28a878…`，len 57339。
- 冻结候选：11 列原序 1..11、双坐标 double precision、PK 六列源序==目标序，canonical `d3cdb81c…`/3529 逐字复现；旧模型拒绝它（补丁必需性实证）。
- 最小扩展：diff 仅 4 处语义点；对抗探针（空 PK/额外字段/nullable/未映射列/重复列/float4/real/大小写变体）全部正确拒绝。
- A 面：evaluate 重算 8004=23+7981、multiple 0；committed 账 records 逐条 deep-equal；run_writeoff 恰闭 3 条、派生仅剩 unmatched_member、ready=false；证据摘要 `679dca4d…`/`fae3502e…` 全等。
- 边界：全程只读，未连库/未重跑试装/未改 deploy/未动服务，临时件已删并实证 GONE。

### 已采纳的 3 条修正（本轮已提交）
- **P2（需更正的披露）**：我曾写"全量基线 87 项预存失败"，该数不可复现。同环境实测为**基线 203 failed / 补丁后 201 failed**，仅 2 项被补丁修好、**零新增回归**。已更正证据文件。
- **P1（低）**：PK 校验仅在 columns 存在时生效，纯非表格 target 带 PK 会被静默忽略 → 已加守卫 `primary_key requires an explicit columns mapping`，实证拒绝。
- **P3（低）**：cbdb build 脚本 `BLOCKED in ledger` 文案与新账 disposition 不符 → 已更正为 IMPORT 事实。

### 复核后摘要复验
`fa28a878…` 与 `d3cdb81c…` 在 P1/P3 修改后**均未漂移**，142 项定向回归仍全绿。

## 判定

**B: PASS**｜**A: PASS**
