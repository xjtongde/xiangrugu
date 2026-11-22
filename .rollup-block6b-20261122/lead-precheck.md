# 第 6/6 块续盒（补齐全量映射索引）· lead 预核（2026-11-22，30 分钟盒）

- 起表 14:05:23 UTC，硬停 14:35:23 UTC。基线 227352931b4abe30edc3e60dfa05545ae21431c3（M=2 完好、暂存空）。
- 范围：汇总映射覆盖/命名扫描/历史阻断裁定落账；镜像主从/配准取舍/合同冻结/32 正式落盘留后续裁定。

## PAGGQS 排除决定——全文实证链（lead 14:05–14:06 UTC）
1. **roots.yaml L27**（usage_policy）：「2026-10-02 用户令：usedata 只含【本项目使用】件——使用件保留并记用途，不使用件清出（不判断源数据对错，仅按项目是否使用取舍）。」
2. **roots.yaml L49**（harvard-full subtrees content）：「第二批全量…2026-10-02 已清出旧版 CBDB_20240208_sqlite.db（PAGGQS 空目录随之删）」；files: 171。
3. **roots.yaml L52**（top_files）：「SHA256SUMS-b2（172 行，二批校验账，2026-10-02 清出旧版后重写）」。
4. **roots.yaml L73/79**（checksums[0]）：as_of 2026-10-02；removal_note「2026-10-02 用户令清出 harvard-full/DOI/PAGGQS/CBDB_20240208_sqlite.db（旧版），本账重写为 172 行。」
5. **docs/log.md L299**：「2026-10-02 | 清出 usedata 旧版 CBDB：删 harvard-full/DOI/PAGGQS/CBDB_20240208_sqlite.db(877MB)与空目录；重写 SHA256SUMS-b2 173→172 行；roots.yaml/holdings.md 件数 190→189、172→171；闸0 复验 172/172 | 源根清理 | 用户令『usedata 只含本项目使用件，不使用的清出』；定为 20260919 唯一 CBDB | 本 commit 起。」
6. **历史下载原件（回溯证据）**：/mnt/wd61workmetadata/xiangrugudata/harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db 存在（roots.yaml download 区 role=read-only-original），**877,862,912 B**==首盒字节闭合值；lead 32 只读流式重算 **sha256=5207eacebbe82ec6c16014b404f4bef0770fb639778b5062cb289bf051fb9a7f**，sha16==README-b2 §四表声明 5207eacebbe82ec6 ✓。
7. **历史用途注记**：git show 75ecd77:docs/data-sources.md L44（已删文档 git 历史可追）：「E | …/PAGGQS/CBDB_20240208_sqlite.db（837.2MB）| CBDB 2024-02 官方 SQLite 之 ADDR_XY：人物↔地点坐标桥 | public.addr_xy | 1 | 19,249」——旧装载案，已被 2026-10-02「定为 20260919 唯一 CBDB」决定取代。
- **结论**：首盒 UNRESOLVED_DECLARED_MEMBER_ABSENT 更正为 **EXCLUDED_BY_DECISION_2026-10-02**（排除有据、原件可回溯、全 sha 已恢复并实证）；README-b2 173 件表系清理前文档（R-04 不回改），172 重写有账。

## NUL 格式异常——roots.yaml 既定政策（checksums[0].format_anomaly 原文）
「172 条有效记录后有 126 个 NUL 字节（2026-10-07 同摘要项目快照逐字节核验，更正原 1,101 计数）；严格解析报告 1 行格式错误。源件不修，解析器必须检测并把该异常写入证据；仅当前固定摘要可由冻结合同批准兼容解析。」raw_sha256=900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb 在案。
- **结论**：账尾 126 NUL 记 **FORMAT_ANOMALY_UNDER_FIXED_DIGEST**，兼容解析留冻结合同审批，不自动核销；原账原样+inventory.complete=false 保留。

## 对象面控制总数（lead 结构核）
- CBDB table-mapping.json tables=**78**；tabular object-mapping.json objects=**5**（approved）+proposed_objects=**170**=**175**（前盒 name 扫描仅取 objects 5 致 974 vs a03 1144——本盒补齐 170）；spatial object-mapping **901**（899 proposed+2 approved）；mdb-sql **96**；raster **43**。控制总数 **78+175+901+96+43=1393**。
- 命名对照值 1144=spatial899+tabular175+md70（bare-name，a03 ROUND 24 口径）；CBDB 78/批准空间 2/栅格 43 命名状态另列。