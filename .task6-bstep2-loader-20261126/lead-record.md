# 第 6/6 块后续·第 2/6 步｜CBDB 单表生产装载器候选｜收口记录

- 基线：`55b7145d5dde5d42d684c3051c60e47f5ed92ba9`（= 远端 head，0/0）
- 授权范围：候选实现 + 32 隔离试装 + 账本引用口径修正
- 写授权：**本盒仅测试审批**；首批七表审批 `88f4f1ac…` 未复用；生产库未写入；deploy 未更新
- M=2 两件仍未暂存、未提交

## 结论：PARTIAL

| 项 | 结果 |
|---|---|
| 1a CBDB 生成器从 A 账实际记录派生 | PASS |
| 1b B 批单表冻结候选 IMPORT 状态单列 | PASS |
| 1c 两处生成器与 A 账真值同构 | PASS |
| 2 正式装载入口候选（绑 d3cdb81c / 3859 / 2cb8c354） | PASS |
| 2′ review 可追溯到批准原文 | **BLOCKED（缺证，未自补）** |
| 3 隔离临时 PG 试装 | PASS |
| 3′ 反例（目标已存在 / 校验失败零残留 / 干净重试） | PASS |
| 回归失败集合对照 | PASS（228→228，新增 0） |

**PARTIAL 的唯一成因**：合同 `review.approval_ref = chaxiang-authorized-20261126-bstep1-close-batch`
是标识串，仓库内没有该次批准的**原文逐字登记件**（对照 `.task6-exception-integration-20261124/approval-record.json`
的 `approval_text_verbatim` 惯例）。链路"批准内容"一环完整（11 列 + 六项约束均有 APPROVED 记录），
但"原文"一环缺失。按茶香指令**列为阻断、未自行补写**；装载器门控 `review_traceability_incomplete`
已实测能阻断且零写入。

## 关键事实

- 现行 A 账 `disposition-ledger-fa28a878-20261126.json`（sha `e9f5e289…`）：8004 条，
  匹配 23 / 未匹配 7981，分布 `{None: 7981, NON_TABULAR: 16, IMPORT: 7}`，**BLOCKED 计数 = 0**。
- `m007906` 对应成员 `harvard/cbdb/cbdb_20260919.sqlite3` 在现行 A 账中**仍未匹配**
  （`disposition=null`, `rule_ids=[]`）——与茶香判断一致。
- 修正前生成器硬编码 `NON_TABULAR`/`BLOCKED`，且 handling 把规则误写为 `m007904`；现已全部改为
  `ledger_state()` / `batch_b_import_state()` 派生，并修正为 `m007906`。
- B 批单表冻结候选 IMPORT 状态单列：`status=FROZEN_CANDIDATE_NOT_IN_A_LEDGER`，
  target `cbdb.cbdb__social_u5f_institution_u5f_addr`，**冻结 ≠ 写库授权**。
- 试装：3859 行 / 42449 字段，源与目标摘要同为 `2cb8c354…07579`，`comparison_equal`，差异 0；
  六列有序 PK 全列回读一致、3859 去重、无非主索引（`constraint_types = {n, p}`）；
  坐标 `double precision` 往返不精确行数 0；未创建 UNIQUE/INDEX/FK/DEFAULT。
- 临时容器 `c0ce44c8…`（`--network none`、无端口）与卷已销毁，scratch `unordered-*` 残留 0；
  生产容器 `pg32b 3d93fc77…`、`pg32 98418cb6…`、`xiangrugu-dev 29795c60…` ID 未变。

## 三态

| 位置 | 状态 |
|---|---|
| 已上 Gitea | 本次提交后按 `git ls-remote` 实测记录 |
| Codex 已接收 | 待 a03 独立复核 |
| 32 工作目录 | deploy 未更新（本盒不更新）；临时试装目录 `/opt/mydocker/xiangrugu/data/var/addr-trial-20261126` 为一次性工作区 |
