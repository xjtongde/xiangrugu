# 第 6/6 块首盒 · lead 预核与裁定（2026-11-21，30 分钟盒）

- 起表 17:18:23 UTC，硬停 17:48:23 UTC。基线 c8b8fe8f6583c81fdd7d5158e13127fc17ca42cd（M=2 完好、暂存空）。
- 授权范围：只读核查+DSH clone 整理+Gitea 交付；正式落盘/依赖/服务/历史对象处置/数据库写入均须另获授权。

## 三条历史阻断 lead 独立预核（32 :ro 实测，17:20–17:26 UTC）

### ①② SHA256SUMS-b2 line173 + 126 NUL（同一缺陷两面）
- 原件：22,071 B，sha256 900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb（a03 全值同）。
- 172 有效行（171 harvard-full + 1 chgis-v6/China_Periods_ReignDates.zip）；lead 32 逐行独立流式重算 **172/172 sha OK**（a03 独立 172/172 唯一关联+抽 3 重算同）。
- **末 126 字节 offset 21945–22070 全 NUL**（set(b[21945:])=={0}），前行以 b'.txt\n' 完整结束——第 173 行区域被 NUL 覆盖。
- **唯一重构链**：README-b2.md（同目录，216 行）§二声明 **173 件=125 数据+48 随附账 / 2,764,772,927 B / 172 harvard-full（36 DOI）+1 chgis-v6 / 2026-09-28 核验 173/173**；§四「完整清单（173 件，绝对路径）」逐件表（路径/大小/sha16/原树路径/装数去向）。lead 程序化差集：表 173 行 − ledger 172 行 = **恰 1 件 harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db（837.2MB，sha16 5207eacebbe82ec6）**；反向差集空。
- **字节闭合**：2,764,772,927 − 1,886,910,015（172 件 32 实测 size 和）= **877,862,912 B** == 837.2 MiB 声明。
- **本体缺席**：快照全盘 size-877862912 搜索 0 命中；PAGGQS 目录不存在；inventory 无 sha-5207eace 件。快照 CBDB 载体=**另一版本** harvard/cbdb/cbdb_20260919.sqlite3（586,485,760 B，sha bde1bb8eece3820d…，块1 已验收），非该内容副本。
- **结论**：line173 成员身份可唯一重构（README 表路径+大小+sha16 三重闭合）；**全 sha256 不可恢复**（README 仅 16 位前缀，全值在被覆盖行内）；**本体缺席当前快照无法重算核销**。status=UNRESOLVED_DECLARED_MEMBER_ABSENT。
- **源枚举差异（单列）**：README-b2 声明 173 外层件 vs 快照 172（差 PAGGQS 件）；2026-09-28 账称 173/173 verified，2026-10-07 快照已无——移除时点/原因/授权待茶香/Codex 裁定，登记不臆断。32 原历史账路径（/root/xiangrugu/ops/harvard/load-b2/src_paths.tsv、docs/data-sources.md）在 32 不存在（原执行主机件），38 仓库亦无。
- 原账保留：inventory issues 3 项与 complete=false 原样不动。

### ③ harvard/chgis/SHA256SUMS.txt line4
- 原件 551 B，sha 694c101f04e63601…；7 LF 行；line4 原始字节 = 7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e + 双空格 + China_Periods_ReignDates.zip。
- harvard/chgis/ 8 件无此 zip；**chgis-v6/China_Periods_ReignDates.zip 全 sha 逐字==line4 声明**（inventory 证；a03 32 独立重算同；a03 全文 6/6 行唯一关联+实算全匹配）。
- 布局成因 README-b2 明载：chgis-v6 五随附账首批收 usedata/harvard/chgis/，数据 zip 本批收 usedata/chgis-v6/；发布方总账随附账走 → line4 相对路径在账目录不解析。
- **结论**：ASSOCIATED_BY_SHA_PATH_MISMATCH——内容经唯一 sha 关联可核销，路径指称与布局不符注记保留；原 issue 事实（账目录相对路径缺件）不改写。

## 归属口径裁定（a03 ROUND 24 观察）
- a03 独立派生：块4 core_members 键=**7**（MDB5+SQL2）；4 件内层容器 ZIP 在 related_members 标 structural_container（V3!access_dbase/v3_chgis_dbase.ZIP[76]、V4!access_database/v4_chgis_dbase.zip[3]、V4!shapefiles/v4_chgis_dbase.zip[109]、CHGIS_V2!access_dbase/chgis_v2_database.ZIP[0]）。
- **lead 裁定**：块4 归属=**11=core 7+structural_container 4**；rollup primary_owner_block=4 + sub_lane（core_data 7 / structural_container 4）；等式 **3+174+5294+11+2522=8004** 保持，组成显式；两两交集 0、指纹失配 0（a03 全量证）。

## 32 版本化落盘拟案（本盒仅提案，正式落盘须另授权）
- 拟用绝对路径：`/opt/mydocker/xiangrugu/releases/2026-10-06-bootstrap/rollup/<full-git-commit>/`
- 预期文件：rollup 八件（all-members.json / reconciliation.json / historical-blockers.json / mirror-adjudication.json / name-conflicts.json / pending-items.json / SUMMARY.md / build_rollup.py）+ inventory.json（fb5e6b33… 原值副本）+ manifest.sha256（逐件 64 位）。
- 摘要方案：逐件 sha256 + manifest 总账 + git commit 锚（VCS_REF）+ 32 双跑字节一致证据；落盘后独立 sha256sum -c manifest 全 OK 方认接收；源快照 :ro 不触；deploy 目录不动。