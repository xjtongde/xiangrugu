# CBDB 导入包整理摘要（第 1/6 块，仅整理不写库）

生成方式：全部字段由 build_cbdb_package.py 从同目录 release 草案/批准件合并，禁手填；重跑可复现。

## 成员（inventory 全量 8004 中 CBDB 路径恰 3，嵌套链 0）
| 成员 | kind | size | sha256 | 账本处置 | 关系/判定 |
|---|---|---|---|---|---|
| harvard/cbdb | directory | — | — | NON_TABULAR | 容器，显式保留 |
| cbdb_20260919.json | file | 385 | bd62ab07… | BLOCKED | 出版方元数据：声明 sqlite 文件名+sha256（与实测成员一致）+HF zip 路径；**非重复表载体**，单独处置不入表 |
| cbdb_20260919.sqlite3 | file | 586,485,760 | bde1bb8e… | BLOCKED | 主源载体：78 表/736 列 |

JSON 内容取证：本轮经 SSH 在 32 只读 cat（R-07 合规），digest 复核等于账本值。

## 计数与确认态
- 表映射：78/78；字段映射：736/736（notnull 候选 184 / nullable 候选 552）。
- 类型：子批 type_mapping_approved=true（observed 700 + declaration-only 36，后者按 unobserved-proposal 的 PROPOSED_NOT_AUTHORIZED 确认态引用，approval_requested=false 未升级）。
- 角色：78 表 tabular-source、76 索引 source-schema-metadata（roles_approved=true）。
- 命名：naming_scope=SQLITE_78_TABLE_SUBBATCH_NOT_FULL_RELEASE_ALLOCATION；**全版本名称分配未完成**（碰撞检查缺口）。
- 顶层提案 flags 原样保留：target_mapping_approved=False、nullability_constraints_approved=False、value_contract_approved=False、ready_for_import=False、contract_frozen=False、disposition_retained=BLOCKED。

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
