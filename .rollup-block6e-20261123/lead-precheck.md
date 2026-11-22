# 第 6/6 块续盒四（导入包合同草案）· lead 预核（2026-11-22/23，30 分钟盒）

- 起表 17:29:53 UTC，硬停 17:59:53 UTC。基线 f54dd968094c78f8e20912cb50926c734d53eb8b（M=2 完好、暂存空）。
- 只读核查+草案交付；合同冻结/正式落盘/数据库写入另行授权。

## 789 旧口径来历确证（lead 17:31 UTC 机器核）
- tabular/members.json class_counts：**txt 751 + csv 7 + ods 4 + xlsx 13 + xls 14 = 789**（纯表格类目成员选择面；另 dbf 704 + tab-mapinfo-spatial-definition 142 + tab-text 5 = 851，合 1640）。
- disposition_counts：**organized 174 / handoff_block5 620 / handoff_block3 846 / pending_evidence 0**（合 1640；789 面=organized 174+handoff_block5 615，tab-text 5 并入 block5 成 620；handoff_block3 846=dbf704+tab-mapinfo142）。
- 映射提案面：object-mapping approved **5** + proposed **170**（proposed_objects_from_snapshot_verification=170，tables_reviewed 170）。
- **判定**：pending-items 旧条「tabular_pending_review count=789」系把类目选择面成员数混作「待审提案数」——当前账应分记：成员处置 {174,620,846} 与映射提案 {5 批准,170 待批}；789 标历史口径（原值来历=上列类目和）。

## CBDB 值验证面（TODO L19/L54 + cbdb 交付）
- 78 表 736 列已有类型及名称/空值政策；**68/78 源侧值验证覆盖**（既非导入表数亦非 usedata 完成比例）；剩 **10 表/235 列**值验证未决（大组值验证授权待批）；36 declaration-only 列；**ready_for_import=False 保持**。
- 第 1 块 Codex 已验收（3 成员/78 表/736 字段），剩余入库缺口另列：PG 装载器/大组 10 表值验证授权/全版本命名/约束执行/36 declaration-only 列。

## 现有 pending 14 类（rollup/pending-items.json 基线态）
wmf_reader_tool_gap 12 / v5_missing_dbf 1 / unapproved_mappings_spatial 899 / unapproved_mappings_mdb 96 / unapproved_mappings_raster 43 / tabular_pending_review 789（本盒纠正）/ loader_contract_undecided 43 / checksum_deferred 17 / nodata_source_undeclared_bands 113 / inventory_historical_issues 3（已裁定）/ casefold_binding_adjudication 2 / pdb2_georeference 1 / crs_local_cs_non_epsg (null) / shapename_collision_allocation 13。

## 本盒交付控制
- manifest-draft：8004 成员四分类（retain/proposed_import/evidence_only/pending_contract）+1293 对象+1311 引用+产物 sha；目标名引 naming-draft b963ed2f（批准状态保留）；目录拟案 PROPOSED_NOT_LANDED。
- mirror-registration-dispositions：默认共享存储+来源逻辑保留；V4 两版本分立；MapInfo 两案/五对/十记录；Peking 六参互证沿用现有 GT；pdb2 三绑定+V4 未决；合表若提单列减表+追溯。
- load-blockers：逐项 block_level（blocks_package_freeze/blocks_load/explanation_only）+可验证 closure_condition；789 纠正节。
- lead 件：装载与核验顺序+待审批决定表（.rollup-block6e 目录）+TODO+SUMMARY 整合。
- 归属账+1311 引用+1293 对象零漂移；五块与既有 draft 零改写（只引用）。