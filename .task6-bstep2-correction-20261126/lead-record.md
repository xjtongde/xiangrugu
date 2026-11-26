# 第 6/6 块后续·第 2/6 步补正｜Lead 收口记录

## 判定

**PASS**

本盒三项授权任务全部完成且独立可验证。上一盒的 PARTIAL 成因（合同 review 缺批准原文登记件）已由茶香补发原文并逐字登记闭合。

## 一、逐字登记（任务 1）

| 项 | 值 |
|---|---|
| 原文登记件 | `.task6-bstep2-correction-20261126/approval-text-verbatim.txt` |
| 原文 SHA-256 | `ec0fa5cf029c37e1bdbb94102553d145bd4d901d74489ac7b98ecdb3d42d4f12` |
| 字节数 | 1799 |
| 真实转发时间 | `2026-11-26T16:55:36Z`（UTC，非旧值 `2026-11-26T14:30:00Z`）|
| 锚定提交 | `34c7cd4f403b2db6c667b294e015b224ba296449`（原文所称 Gitea 提交）|
| 绑定审批表 | `b-approval-table-v2.json` sha `a718b0c297501642dd105eb3797f96dc1de2edf8eb521bed6609ff78de1fb4a0` |
| 首批写库审批复用 | 否（`88f4f1ac…` 未被引用）|

原文涵盖：11 列名称/顺序/类型/可空性；六列复合主键按源顺序；六列 NOT NULL、五列可空；不新增 UNIQUE/二级索引/外键；五个 DEFAULT NULL 源声明留证且目标 DDL 省略显式默认值；绑定 3859 行与 `2cb8c354…`；**不批准正式库写入**。

## 二、冻结候选更新（任务 1）

- review 改为指向新审批事件 `chaxiang-approval-social-institution-addr-bstep2-correction-20261126`
- 规范摘要：`d3cdb81c4caf75c92a96e548025c39aab1d1d8a301b0f0d7b4e30286243d8bef` → **`56b0076d2e877be9fb34796e01b8ee2b37d5a817c8e80203fa21c95e4f3f8237`**
- **仅审批记录变化已验证**（双向）：
  - `git diff 34c7cd4 27532a5` 该文件只有 review 三字段
  - 回填旧 review 重算，精确复现 `d3cdb81c…`
  - 除 review 外所有字段逐字段相等
- 装载器绑定同步更新为 `56b0076d…`；单测锁定该值

## 三、正式执行命令候选（任务 2）

`datamgmt/src/xiangrugu_datamgmt/cbdb_social_addr_entry.py`

**端点固定**：`pg32b:5433/xiangrugu`。强制声明会话内端口 `5432`；把 5432 当目标端点直接拒绝（`target_port_not_5433`）。正式库名 `xiangrugu` 固定，仅 `test_only` 隔离替身可用别名。

**同一会话核验**：`verify_instance_and_role_in_session` 在执行 DDL 的同一个 psql 会话内完成——实例标记 `public.xrg_instance_marker`（必须严格一行且等于独立核实的容器 ID）、装载角色（`current_user`）、server version、in-session port、数据库集合。

**同一解析驱动**：`recompute_contract_digest` 从**实际冻结合同**用正式解析重算摘要并取 review；`target_from_parsed` 用**同一次解析结果**产出目标/列/主键/期望行数与值摘要。装载器不再二次独立读取。

**门控次序**（实测严格递增，全部先于唯一写库调用 `make_loader`）：
`validate_execution_scope` → `recompute_contract_digest` → `target_from_parsed` → `verify_instance_and_role_in_session` → `isolated_scope_from` → `make_loader`

**测试审批不可触达正式目标**：
- 非 `test_only=True` → 拒绝（`test_approval_cannot_target_production`）
- 绑定生产容器 ID `3d93fc77…` → 拒绝
- 复用首批写库审批 → 拒绝
- 会话内 marker 与生产容器不符 → 拒绝（纵深）
- 正式写库须 `approval_class=real` + `real_authority_ref`，本盒不具备

## 四、隔离试装（任务 3）

隔离容器 `e7d57aae1e22…`（v2 重建），镜像 `sha256:d562e436…`，`--network none`、无端口发布、PG 18.6，装载角色 `xrg_loader`（NOSUPERUSER），源 ro 挂载。

**13/13 用例符合预期：2 LOADED / 11 REFUSED / 0 ERROR**

| 用例 | 结果 | 残留 |
|---|---|---|
| P1 正向全量装载 | LOADED 3859 | 3859（已提交）|
| N1 目标已存在 | REFUSED `target_already_exists` | 3859（旧表原样保留）|
| N2 行数不符 | REFUSED `row_count_mismatch` | 0 |
| N3 结构不符 | REFUSED `structure_readback_mismatch` | 0 |
| N4 坐标不精 | REFUSED `coordinate_roundtrip_inexact` | 0 |
| N5 追溯不全（仅 status） | REFUSED `review_traceability_incomplete` | 0 |
| N5b 原文摘要不符 | REFUSED `approval_text_digest_mismatch` | 0 |
| N5c 合同 review ref 不符 | REFUSED `contract_review_ref_mismatch` | 0 |
| N5d 审批记录事件不符 | REFUSED `approval_record_ref_mismatch` | 0 |
| N5e 缺原文 | REFUSED `approval_text_missing` | 0 |
| N6 绑定生产容器 | REFUSED `marker_container_binding_mismatch`（会话内 marker 先于 Gate E 命中）| 0 |
| N7 端口误用 5432 | REFUSED `target_port_not_5433` | 0 |
| P2 干净重试 | LOADED 3859 | 3859（已提交）|

**正向指标**：3859 行；11 列；有序六列主键与冻结候选**逐字一致**；NULL 计数全对（begin_year 3005、end_year 3857、c_source 219、c_pages 334、c_notes 752，其余 0）；坐标往返偏差 0 行；非主索引 0；约束类型仅 `['n','p']`；`committed=True`。

**独立全量值比对**（项目自身 unordered 比对器，源 sqlite 流 vs 目标 PG 行）：`comparison_equal`，0 差异，缺失 0、多余 0，源与目标摘要同为 `2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579`。

**销毁**：容器与卷已删除，scratch 目录已清，无残留。生产从未连接。

## 五、首个缺口

**正式写库授权缺失**——这是**设计使然，非缺陷**。茶香原文明确"不批准正式库写入"，本盒仅用隔离测试审批。要把候选提升为真实写入，需另获独立授权（`approval_class=real` + `real_authority_ref`），代码已内建该门控并要求二者齐备。

次要观察（非阻断）：隔离试装镜像 `pg32b-full:18-pgdg` 不含 pydantic/jsonschema，需从 `xiangrugu-dev` 搬运纯 Python 依赖方可运行解析；这只影响测试环境搭建，不影响装载逻辑。

## 六、测试与回归

- 新增单测 **44 项全通过**（loader 21 + entry 23）
- 全量 unit 失败集 **228 → 228，新增 0，修复 0**（228 条为既有环境缺口：deploy 内缺 `.task6-*` 隐藏证据目录）
- 三个生成器（cbdb/tabular/rollup）重跑幂等

## 七、过程中修正的自身缺陷（据实记录）

1. **审查追溯门原只看 `status` 字符串** → 升级为原文摘要 / 合同 review ref / 审批记录事件三方结构化一致校验。
2. **Gate E 原实现把所有 test 审批都拒绝**（过度收紧，与"测试审批本就该允许"矛盾）→ 改为允许隔离替身、仅拒绝绑定生产容器。
3. **装载角色判定被 PG 字面量欺骗**：`current_setting('role', true)` 在未 `SET ROLE` 时返回字符串 `'none'`（既非 NULL 也非空串），原 `COALESCE/NULLIF` 写法失效 → 改用 `current_user` 并显式检出 `SET ROLE` 覆盖。
4. **曾自造全量值摘要口径**，与批准的 `2cb8c354…` 分歧 → 撤回自造实现，改用项目自身 `compare_unordered`，避免口径漂移。
5. **`dbname` 门控过严**：隔离替身库名为 `trialdb` 被拒 → 改为正式/真实审批固定 `xiangrugu`，仅 `test_only` 替身可用别名。

## 八、边界确认

| 项 | 状态 |
|---|---|
| 生产库 `xiangrugu` 内 `cbdb` schema | **0**（未写入）|
| 目标表 `cbdb.cbdb__social_u5f_institution_u5f_addr` | **不存在**（`to_regclass` = false）|
| 生产容器 | `pg32b 3d93fc7741f6`、`pg32 98418cb6f08a`、`xiangrugu-dev 29795c60ae15`（全程未变）|
| 临时容器/卷残留 | 无 |
| deploy | 未更新 |
| M=2 两件 | 未进入本盒提交，仍在工作区未暂存 |

## 九、三态

- **Gitea**：`27532a5a464fca5f6a8f7cf0f0ad9657f41b48d1`（独立 `ls-remote` 实测，本地/远端 0/0）
- **Codex 已接收**：a03 实例连续 4 次运行失败无产出；改由 a02 独立复核
- **32 工作目录**：deploy 未更新；隔离试装工作区已销毁

## 十、完整提交

`34c7cd4`（基线）→ **`27532a5`**（本盒）