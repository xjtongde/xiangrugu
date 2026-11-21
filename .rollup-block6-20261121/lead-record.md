# 第 6/6 块首盒 · lead 记录（2026-11-21，30 分钟盒）

- 起表 17:18:23 UTC，硬停 17:48:23 UTC。基线 c8b8fe8f6583c81fdd7d5158e13127fc17ca42cd（M=2 完好、暂存空）。
- 授权：只读核查+DSH clone 整理+Gitea 交付；正式落盘/依赖/服务/历史对象处置/数据库写入须另授权（本盒未触）。
- lead 预核突破（lead-precheck.md）：三历史阻断查清——SHA256SUMS-b2 第 173 行被 126 NUL（offset 21945–22070）覆盖；README-b2 §四 173 件表−ledger 172 差集恰 1 件=PAGGQS/CBDB_20240208_sqlite.db（837.2MB sha16 5207eacebbe82ec6），字节闭合 877,862,912；本体缺席快照（三路搜索 0 命中；CBDB 现载体为另版本 cbdb_20260919.sqlite3）；chgis 账 line4 唯一 sha 关联 chgis-v6 件（7452ae6c…c355e）。
- 归属口径裁定：块4=11=core_data 7+structural_container 4（a03 ROUND 24 观察采纳，sub_lane 显式）。
- a02 S1–S4（硬停 17:35 内）：rollup 八件；对账漏 0/余 0/重复 0/失配 0，等式 3+174+5294+11+2522==8004 断言入码；块3 5296→5294 消歧（text-owned-by-block2 2 件归块2）；块4 wrappers 经 inventory full-chain 反查唯一命中；object_mapping_refs 524 件；cross_references 4；源枚举新鲜度顶层 172vs172 差 0；三阻断 32 逐步独立复核（①② UNRESOLVED_DECLARED_MEMBER_ABSENT 三剩余原因、③ ASSOCIATED_BY_SHA_PATH_MISMATCH 全 sha 流式重算逐字全等）；inventory issues/complete=false 原样保留；mirror 381 组（377+1 V4 字节版本对+2 MapInfo 孪生+1 Peking casefold 组 2 件）全 PENDING；name 974 distinct/13 碰撞组全 V4 MDB 内部/跨块 0；pending 14 类；**set 迭代序非确定性缺陷中途修复（sorted）披露**；双跑 0/0 stderr 0/0 七件字节一致。
- lead 快核（17:33–17:34 UTC）：八件 sha 匹配；all-members 8004 owner {3,174,5294,11,2522}；historical-blockers 2 条目覆盖 3 issue_codes（①②同源合并）+原账 verbatim 保留字段在件；directional checks 全 0/true；discrepancies PAGGQS 条含字节闭合/sha16/历史注记。
- 终态 sha：all-members 580859438bbabd19… / reconciliation ba11d9715972355d… / historical-blockers ea6af2026b320b2b… / mirror-adjudication dce7e3b4d824029c… / name-conflicts ffa963dda142c57b… / pending-items 892206bdf0d71102… / SUMMARY e9a1825f50ec422b… / 生成器 7d4034dcfd5d1204…。
- TODO：块5 Codex 验收通过记入+块6 首盒进度+口径裁定+落盘拟案+讨论账。
- 32 落盘拟案（仅提案）：/opt/mydocker/xiangrugu/releases/2026-10-06-bootstrap/rollup/<full-git-commit>/，rollup 八件+inventory 副本+manifest.sha256；sha256sum -c 全 OK 方认接收。
- 边界：五块已交付零改写；entry/rehearsal M=2 未触；__pycache__ 不入追踪；源快照 :ro。

## lead 口径裁定：distinct_proposed_names 974（17:39 UTC 直算）
- a03 注记：974 vs 其 bare-name 1144（spatial 899+tabular 175+md 70）。lead 从五块 object-mapping 机器面直算：mdb table_name_proposal 96 非空 distinct **70**；spatial candidate_table_name 899 非空 distinct **899**；tabular **objects 键仅 5 条**（非空 distinct pairs 5）；(schema,name) 对键 distinct=70+899+5=**974**==a02 机器值；碰撞组 **13**、跨块 **0**（chgis 面 969 对无合并）。
- 结论：974 按 method 字段口径（五块 object-mapping 提案名 (schema,name) 分组）**正确**；a03 的 1144 系 tabular 面取数口径差（175 来自他面，object-mapping.objects 实为 5）。核心断言（13 组全 V4 MDB 内部、跨块 0）双方独立重算完全一致，不受影响。
- 处置：本盒不改产物（method 字段已述口径）；tabular 面取数差异登记于此供 Codex 复核；如须 method 字段增补「tabular 取 objects 键 5 条」明示，留待下盒 a02 一行补注（不触发本轮重跑）。
