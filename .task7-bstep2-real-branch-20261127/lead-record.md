# 第 6/6 块后续·第 2/6 步｜打通 B 批正式执行分支｜Lead 收口记录

## 判定

**PASS**

正式分支已打通并在隔离替身上走完整事务验证；两条分支各自独立核验审批与目标，共用已验收的单事务装载与回读。

## 一、修正的缺陷

**原实现**：`run_execution_candidate` 无条件调用 `isolated_scope_from()`，导致正式审批也会被塞进隔离测试路径——正式分支事实上不存在，只是被贴了"隔离"标签走了一遍。

**现实现**：按 `write_approval.approval_class` 分流

| 审批类别 | 分支函数 | 审批核验 | 目标核验 |
|---|---|---|---|
| `real` | `production_scope_from()` | 真实写库授权**原文**摘要 + 单表范围 | 必须是生产端点三元组 |
| `test` | `isolated_scope_from()` | `test_only=True` + 隔离替身 | 禁止生产库名可见 |

两条分支共用 `loader.run_single_table`（DDL→COPY→回读→COMMIT/ROLLBACK）与会话内 instance/role 核验，**未复制第二份实现**。`evidence["execution_branch"]` 记录实际走的分支。

**保持不变**：冻结候选 `56b0076d…`、本次映射审批 `chaxiang-approval-social-institution-addr-bstep2-correction-20261126`、源侧摘要 `2cb8c354…`、3859 行、11 列。

## 二、正式分支的授权核验（仅填字符串不得通过）

正式分支必须提供**真实写库授权原文**，逐层核验：

1. 原文缺失 → `real_authorization_text_missing`（**仅给引用字符串或仅填 `approval_class=real` 都在此拒绝**）
2. 摘要缺失 → `real_authorization_digest_missing`
3. 摘要与原文不符 → `real_authorization_digest_mismatch`
4. 摘要未绑定到 `write_approval` → `real_authorization_digest_not_bound_to_write_approval`
5. 授权 ref 不一致 → `real_authorization_ref_mismatch`
6. 类别不是 real → `real_authorization_class_mismatch`
7. 标记 test_only → `real_authorization_marked_test_only`
8. **单表范围**：`authorized_tables` 必须恰好等于 `{cbdb.cbdb__social_u5f_institution_u5f_addr}`，多一张即 `real_authorization_scope_not_single_table`
9. 规则范围必须恰好 `{m007906}` → `real_authorization_rule_scope_mismatch`
10. **原文内容必须指名该表与 m007906** → 防止拿无关文档的摘要蒙混
11. 端点必须是生产三元组，`test_only` 端点拒绝
12. 复用首批写库审批 `88f4f1ac…` → `first_batch_approval_reuse_forbidden`

## 三、正式分支隔离替身实测（7/7）

| 用例 | 结果 | 残留 |
|---|---|---|
| F1 正式分支完整事务 | **LOADED** `branch=real`，3859 行 | 3859 |
| FN1 目标已存在 | REFUSED `target_already_exists` | 3859（旧表原样保留）|
| FN2 授权原文缺失 | REFUSED `real_authorization_text_missing` | 0 |
| FN3 授权摘要错误 | REFUSED `real_authorization_digest_mismatch` | 0 |
| FN4 仅填 `approval_class=real` | REFUSED `real_authorization_text_missing` | 0 |
| FN5 错实例 | REFUSED `artifact_drift: instance_fingerprint` | 0 |
| FN6 回读失败整表回滚 | REFUSED `row_count_mismatch`，表不存在 | **0** |

**F1 正向指标**：3859 行、11 列、主键去重 3859、坐标往返偏差 0、非主索引 0、约束仅 `['n','p']`、`shared_single_transaction=True`。

**独立全量值比对**（项目 `compare_unordered`，源 sqlite 流 vs 目标行）：`comparison_equal`，源与目标摘要同为 `2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579`，3859/3859，缺失 0、多余 0、差异 0。

## 四、隔离分支回归（13/13）

分流改造后隔离分支全部仍然符合预期：P1/P2 各装载 3859 行，11 个负例（含四个结构化追溯分支、绑定生产容器、端口误用）全部拒绝且零残留。

## 五、正式命令与最小权限方案

**固定**：`pg32b:5433/xiangrugu`，会话内 5432；会话内 `xrg_instance_marker` 必须等于独立核实的容器 ID；`current_user` 必须等于 `xrg_loader` 且无 `SET ROLE` 覆盖。

**仅允许**：`cbdb.cbdb__social_u5f_institution_u5f_addr`。

**装载角色**：`xrg_loader`，`LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION`。

**先决配置（必须预先存在，装载不得代建）**：
- `DATABASE xiangrugu`
- `SCHEMA cbdb`（owner 为 `xrg_loader` 或该角色有 CREATE）
- `public.xrg_instance_marker`（严格一行 = 生产实例真实容器 ID）
- `GRANT SELECT ON public.xrg_instance_marker TO xrg_loader`
- `GRANT USAGE ON SCHEMA public TO xrg_loader`

超出以上范围的权限一律不需要（不需要 CREATEDB／CREATEROLE／SUPERUSER）。

**退出码约定**：`0` 装载提交 / `2` 门控拒绝（未写库）/ `3` 异常（已回滚）。

详见 `real-branch.json`。

## 六、发现并修正的一个真实问题

在替身上跑正式分支时，`xiangrugu` 这个名字在两条分支中语义相反：对隔离分支它是**禁止可见的生产库名**，对正式分支它是**目标库**。原实现只有一份硬编码禁止清单，导致要么正式分支永远打不通，要么必须削弱隔离校验。改为**按分支判定**——隔离分支仍禁止 `xiangrugu`，正式分支在禁止 `pg32b/cbdb/cbdb_reh` 之后把目标名从集合比对中剔除。这样两边都保住了正确语义，没有降低强度。

（过程中还暴露过：正式分支的 `execution_branch` 标记一开始没传到 `check_instance_identity`，被 `production_database_visible` 误拦——已修正为随 `instance_identity` 一起传递。）

## 七、测试与回归

- 新增单测总计 **59 项全通过**（loader 21 + entry 38，本盒新增 17 项正式分支用例）
- 全量 unit 失败集 **228 → 228，新增 0**（228 为既有环境缺口）

## 八、边界

| 项 | 状态 |
|---|---|
| 生产 PG 连接 | **未连接** |
| 正式库写入 | **未写**（`xiangrugu` 内 `cbdb` schema 数 0，目标表不存在）|
| 生产容器 | `pg32b 3d93fc7741f6`、`pg32 98418cb6f08a`、`xiangrugu-dev 29795c60ae15`（未变）|
| deploy | 未更新 |
| 生产权限/服务 | 未改 |
| 临时容器/卷/scratch | 全部销毁，无残留 |
| M=2 | 未进入本盒提交，仍在工作区 |
| 首批写库审批 | 未复用 |

## 九、首个缺口

**正式写库仍需独立授权**。本盒证明的是"正式分支的代码路径能在隔离替身上跑通完整事务"，不是"已经写好正式库"。要真实执行，需茶香另发一份真正授权生产写入的原文；届时把它填入 `real_write_authorization.approval_text_verbatim`，正式分支的门控（原文摘要、单表范围、规则范围、内容指名、生产端点）会全部生效。

## 十、三态

- **Gitea**：见本次提交（独立 `ls-remote` 实测）
- **Codex 已接收**：待独立复核人（a03 实例本盒未使用；a02 可选）
- **32 工作目录**：deploy 未更新；隔离工作区已销毁