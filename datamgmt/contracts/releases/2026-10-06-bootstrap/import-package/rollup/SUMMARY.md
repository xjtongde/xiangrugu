# 第 6/6 块 · 全量汇总与落盘首盒（SUMMARY）

基线 git 17097e8；inventory sha256=fb5e6b334b898d62…；**只读引用五块已交付包，五块文件零改写；未正式落盘/未装依赖/未动服务与库**。

## 对账闭合（机器断言在码）
- **3 + 174 + 5294 + 11 + 2522 == 8004**（primary_owner_block exactly-once；两两交集空；inventory↔并集双向 missing 0 / extra 0；逐件 sha==inventory）。
- 块4 组成显式（lead-ruling 3ffcfc67）：core_data 7（MDB5+SQL2）+ structural_container 内层容器 ZIP 4（V3!access_dbase/v3_chgis_dbase.ZIP[76]、V4!access_database/v4_chgis_dbase.zip[3]、V4!shapefiles/v4_chgis_dbase.zip[109]、CHGIS_V2!access_dbase/chgis_v2_database.ZIP[0]），Thumbs.db 归块5。
- 交接面不重复认领：块2 handoff-block3 846 件计入块3 组成员、handoff-block5 620 件计入块5；text-owned-by-block2 2 件归属块2（组证据引块3）。
- 对象映射引用面：524 件带 object_mapping_refs。

## 三历史阻断复核（结论草案，原账不动）
- SHA256SUMS-b2（22,071B raw sha 900d98c6…）**拆两面**：①PAGGQS 声明成员→**EXCLUDED_BY_DECISION_2026-10-02**（roots.yaml L27/L49/L52/L73/L79+log.md L299 决定引文 verbatim；回溯证据：备份区原件 32 只读重算 size 877,862,912B、全 sha 5207eace…fb9a7f==README sha16 前缀合、字节闭合 877,862,912、历史用途注记 75ecd77 data-sources L44 ADDR_XY 桥已被取代）；②账尾 126 NUL（offset 21945–22070 单连续区，有效 172 行=171+1）→**FORMAT_ANOMALY_UNDER_FIXED_DIGEST**（roots.yaml format_anomaly 引文 verbatim；兼容解析留冻结合同审批不自动核销）。
- harvard/chgis/SHA256SUMS.txt（551B sha 694c101f…）line4：本盒 32 独立流式重算 chgis-v6/China_Periods_ReignDates.zip == 声明值逐字全等 ⇒ **ASSOCIATED_BY_SHA_PATH_MISMATCH**（内容可核销，路径指称与布局不符，成因 README 明载）。
- 源枚举差异单列：README-b2 声明 173 外层件 vs 快照 172（PAGGQS 件缺席；2026-09-28 账 173/173 verified→2026-10-07 快照已无，移除时因待裁定，登记不臆断）。

## 本盒增量（组件引用+裁定草案，基线 17097e8）
- **S1 孪生补链**：MapInfo 2 案按 components_exact_identity 全组件四元绑定（完整归档链+成员序号+sha256+size 唯一命中断言），每案 3→**5** 条、合计新增 **4** 条（TAB/ID×2 案）；根因实证=组内清单缺大写词干 V3_…（大小写敏感结构差异）。反向索引同步：孪生成员 mapped_objects 10 件全命中。coverage_semantics 节入 object-index v2（普通/组/孪生显式/批准六组件/容器五面覆盖语义）。归属账零漂移断言在码（3/174/5294/11/2522 五块计数+七字段+8004）。
- **S2 mirror-adjudication-draft.json**：381 组三分类草案——byte_identical_content_reuse **379** / mixed(V4 MDB 版本对)**1** / association_pending_sidecar_or_casefold **1**。四案详证：①V4 MDB 三载体 sha 实测=access_database 直接件独立版本 + zip-wrapped 两副本字节相同对（同 sha 子对机器核得）；②孪生 2 组 5 组件全等补链后证据；③pdb2 四副本独立核对：内部 GT=null/GCP=0/CRS null 一致，三份伴 pdb2.tifw(exact-stem)、V4 副本无世界文件——原读值照录；④Peking 2 件独立核对：**tif 均有内部 GT 且 CRS 非 null**，tfw casefold binding_basis/status/probe_text 原文保留——pdb2 与 Peking 分别核对不共享结论。DRAFT 不预决合并。
- **S3 naming-draft.json**：83 已命名 RETAIN_UNCHANGED；**1208 常规逐件可复算候选名**（derive_candidate 函数：leaf stem/ext slug+对象标识前 8+源身份 sha256 前 8）+2 批准空间单列；13 组 V4 同名冲突=_x+sha256(载体完整归档链)[:8] 恒长 10 后缀区分（三副本三名唯一断言）；全量 1293 联查新碰撞 **0**。DRAFT_NOT_APPROVED。

- 镜像候选统一账 **381** 组：块5 同 sha 377 组 + pdb2 四副本（sha bd56086a…，组内含于前者，显式点名）+ V4 MDB 两字节版本对 + MapInfo 孪生批准 2 组 + Peking casefold 2 关联；全部 PENDING_ADJUDICATION，合并/配准不预决。
- 对象索引：**1293** 对象（78+175+901+96+43；派工文「1393」系笔误——其分解式和即 1293，以机器断言为准），绑定解析失败 **0** 项逐项登记（禁静默丢弃）；成员→对象反查入 all-members.mapped_objects。
- 命名扫描 v2：三分类 已命名 **83** / schema 未定 **1165** / 名称未定 **43**（已批准空间 2 单列）；对照值 1144 复算==预期（spatial899+tabular175+mdb distinct bare-name 70）；对键碰撞组 **13**（V4 MDB 同名 13 保留、tabular proposed 170 面补齐后无新增跨块碰撞；明细 naming-scan.json）。
- 未决带账 14 类：WMF 12/v5 缺 DBF/批准面 899+96+43/装载合同/checksum 17/NoData 113/inventory 3/casefold 2/pdb2 配准/命名分配等。

## 边界
本轮仅只读核查+DSH clone 整理+Gitea 交付；正式落盘、依赖、服务、历史对象处置、数据库写入均在授权外；entry/rehearsal M=2 未触；五块已提交交付不改写（rollup 只引用）。
