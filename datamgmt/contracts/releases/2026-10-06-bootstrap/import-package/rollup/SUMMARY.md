# 第 6/6 块 · 全量汇总与落盘首盒（SUMMARY）

基线 git e3dd139；inventory sha256=fb5e6b334b898d62…；**只读引用五块已交付包，五块文件零改写；未正式落盘/未装依赖/未动服务与库**。

## 对账闭合（机器断言在码）
- **3 + 174 + 5294 + 11 + 2522 == 8004**（primary_owner_block exactly-once；两两交集空；inventory↔并集双向 missing 0 / extra 0；逐件 sha==inventory）。
- 块4 组成显式（lead-ruling 3ffcfc67）：core_data 7（MDB5+SQL2）+ structural_container 内层容器 ZIP 4（V3!access_dbase/v3_chgis_dbase.ZIP[76]、V4!access_database/v4_chgis_dbase.zip[3]、V4!shapefiles/v4_chgis_dbase.zip[109]、CHGIS_V2!access_dbase/chgis_v2_database.ZIP[0]），Thumbs.db 归块5。
- 交接面不重复认领：块2 handoff-block3 846 件计入块3 组成员、handoff-block5 620 件计入块5；text-owned-by-block2 2 件归属块2（组证据引块3）。
- 对象映射引用面：524 件带 object_mapping_refs。

## 三历史阻断复核（结论草案，原账不动）
- SHA256SUMS-b2（22,071B raw sha 900d98c6…）**拆两面**：①PAGGQS 声明成员→**EXCLUDED_BY_DECISION_2026-10-02**（roots.yaml L27/L49/L52/L73/L79+log.md L299 决定引文 verbatim；回溯证据：备份区原件 32 只读重算 size 877,862,912B、全 sha 5207eace…fb9a7f==README sha16 前缀合、字节闭合 877,862,912、历史用途注记 75ecd77 data-sources L44 ADDR_XY 桥已被取代）；②账尾 126 NUL（offset 21945–22070 单连续区，有效 172 行=171+1）→**FORMAT_ANOMALY_UNDER_FIXED_DIGEST**（roots.yaml format_anomaly 引文 verbatim；兼容解析留冻结合同审批不自动核销）。
- harvard/chgis/SHA256SUMS.txt（551B sha 694c101f…）line4：本盒 32 独立流式重算 chgis-v6/China_Periods_ReignDates.zip == 声明值逐字全等 ⇒ **ASSOCIATED_BY_SHA_PATH_MISMATCH**（内容可核销，路径指称与布局不符，成因 README 明载）。
- 源枚举差异单列：README-b2 声明 173 外层件 vs 快照 172（PAGGQS 件缺席；2026-09-28 账 173/173 verified→2026-10-07 快照已无，移除时因待裁定，登记不臆断）。

## 本盒增量四（导入包合同草案，基线 f54dd96）
- **manifest-draft.json**：绑定 8004 成员+1293 对象+1311 对象绑定+产物 sha256 全集（五块 23 件引用+rollup 已存件+inventory；manifest 自指排除、同轮新件下轮补录注记）。四分类派生入码：**retain 2066 / proposed_import 5635 / evidence_only 303 / pending_contract 0 = 8004**（断言合计+归属键集零漂移；续盒五注：ordinary_image 归 evidence_only 对齐块5 NON_TABULAR 账，pending_contract 现由 block2 handoff-block3 空面继承）；目标名引 naming-draft b963ed2f（83 保留+1208 草案+2 批准+39 统一，批准状态原样）；正式目录拟案 releases/2026-10-06-bootstrap/rollup/<commit>/ PROPOSED_NOT_LANDED。
- **mirror-registration-dispositions.json**：默认方案五节（379 组共享存储字节+保留来源与逻辑对象/V4 两字节版本分立 a2cc4039 直接件·04be983d 包裹对/MapInfo 术语统一 两案·五对组件·十条成员记录/Peking 六参数互证+沿用现有 GT·正式绑定留茶香/pdb2 三处本地绑定保留+V4 [159,6] UNRESOLVED_PENDING）；381 组源身份+组件链全保留；合表提案单列节（本盒空，追溯方案预登记：逐表名列被减项+inventory_key→共享对象多对一映射行）。
- **load-blockers.json**：11 项三级——**blocks_package_freeze 2**（NUL126 兼容合同/CASEFOLD-PDB2-LOCAL_CS-COLLISION 待裁面）+ **blocks_load 7**（CBDB 10 表 235 列值验证·68/78 覆盖/tabular 170 提案/MDB 96/spatial 899+SRID/raster 装载合同+NoData113/checksum 17/WMF 12）+ **explanation_only 2**（v5 缺 DBF/inventory 3 已裁定面）；每项 closure_condition 机器可验或授权事件明确。**789 纠正节**：旧条「tabular_pending_review 789」系口径混用——789=类目选择面 txt751+csv7+ods4+xlsx13+xls14（独立复核吻合），当前账分列 members（organized 174/handoff_block5 620/handoff_block3 846/pending_evidence 0）=1640 与 proposals（approved 5/proposed 170）。

- **孪生草案更正**：groups-derived 旧式字符串 identities×2 由 SID 结构化案组取代——真实 PROPOSED SID（f13db8a5…/5039b37a…）引用、五对同角色组件逐对完整归档链+序号+size+SHA-256、两内层 ZIP inventory 成员 sha 一致（69b5119f…/6,089,146B 机器核得）；counts 显式 **案数 2/镜像对数 10/候选记录数 10**；evidence_ref 更正为 proposed_objects[].components_exact_identity。**组账 381 保持**（377+1+孪生 1+Peking 按件 2；前盒 Peking 合 1 条系计数口径不一，披露）。
- **V4 命名统一**：主命名表 draft_entries 与冲突表同源派生，**13 组 39 SID 逐条对账全等断言入码**；直接件与包裹件两字节版本分别保留、两同摘要包裹副本各留来源身份。批准空间 2 件改 **.shp 主件词干派生**+显式 schema=chgis（object_name/批准范围不动）。**1293 全量联查新碰撞 0**（name≤63 断言；最长 schema.name 69 如实登记）。
- **配准证据入草案**：Peking 两案世界文件像素中心→角点换算 GT=[C−A/2,A,D,F−E/2,B,E] 与内部 GeoTransform **六项 repr 级全等**（本盒独立复算），升级建议附证据、最终确认留茶香；pdb2 三份 exact-stem tifw 绑定各自保留、**V4 [159,6] 标配准 UNRESOLVED_PENDING**；存储复用方案与逻辑表合并单列分离（policy 注）。

- **S1 孪生补链**：MapInfo 2 案按 components_exact_identity 全组件四元绑定（完整归档链+成员序号+sha256+size 唯一命中断言），每案 3→**5** 条、合计新增 **4** 条（TAB/ID×2 案）；根因实证=组内清单缺大写词干 V3_…（大小写敏感结构差异）。反向索引同步：孪生成员 mapped_objects 10 件全命中。coverage_semantics 节入 object-index v2（普通/组/孪生显式/批准六组件/容器五面覆盖语义）。归属账零漂移断言在码（3/174/5294/11/2522 五块计数+七字段+8004）。
- **S2 mirror-adjudication-draft.json**：381 组三分类草案——byte_identical_content_reuse **379** / mixed(V4 MDB 版本对)**1** / association_pending_sidecar_or_casefold **1**。四案详证：①V4 MDB 三载体 sha 实测=access_database 直接件独立版本 + zip-wrapped 两副本字节相同对（同 sha 子对机器核得）；②孪生 2 组 5 组件全等补链后证据；③pdb2 四副本独立核对：内部 GT=null/GCP=0/CRS null 一致，三份伴 pdb2.tifw(exact-stem)、V4 副本无世界文件——原读值照录；④Peking 2 件独立核对：**tif 均有内部 GT 且 CRS 非 null**，tfw casefold binding_basis/status/probe_text 原文保留——pdb2 与 Peking 分别核对不共享结论。DRAFT 不预决合并。
- **S3 naming-draft.json**：83 已命名 RETAIN_UNCHANGED；**1208 常规逐件可复算候选名**（derive_candidate 函数：leaf stem/ext slug+对象标识前 8+源身份 sha256 前 8）+2 批准空间单列；13 组 V4 同名冲突=_x+sha256(载体完整归档链)[:8] 恒长 10 后缀区分（三副本三名唯一断言）；全量 1293 联查新碰撞 **0**。DRAFT_NOT_APPROVED。

- 镜像候选统一账 **381** 组：块5 同 sha 377 组 + pdb2 四副本（sha bd56086a…，组内含于前者，显式点名）+ V4 MDB 两字节版本对 + MapInfo 孪生批准 2 组 + Peking casefold 2 关联；全部 PENDING_ADJUDICATION，合并/配准不预决。
- 对象索引：**1293** 对象（78+175+901+96+43；派工文「1393」系笔误——其分解式和即 1293，以机器断言为准），绑定解析失败 **0** 项逐项登记（禁静默丢弃）；成员→对象反查入 all-members.mapped_objects。
- 命名扫描 v2：三分类 已命名 **83** / schema 未定 **1165** / 名称未定 **43**（已批准空间 2 单列）；对照值 1144 复算==预期（spatial899+tabular175+mdb distinct bare-name 70）；对键碰撞组 **13**（V4 MDB 同名 13 保留、tabular proposed 170 面补齐后无新增跨块碰撞；明细 naming-scan.json）。
- 未决带账 14 类：WMF 12/v5 缺 DBF/批准面 899+96+43/装载合同/checksum 17/NoData 113/inventory 3/casefold 2/pdb2 配准/命名分配等。

机械对账注记（防复核误读）：dispositions↔mirror-draft 字面 identities 对称差 10 系表示法迁移
（孪生 inventory_key dict↔legacy 串、peking 挂载位不同）；规范化口径 1532↔1532 symdiff 0
（a03 ROUND 29b 独立验证），语义账完整。

## 本盒增量五（对齐现行合同门，基线 ea40c1f）
- **contract-projection-draft.json**：以 ReleaseContract/DispositionLedger 为准的可复算投影——模型事实 12 条 verbatim；处置投影计数 NON_TABULAR 2070/BLOCKED 5934/IMPORT 0（首批目标名与 target_mapping 未批→IMPORT 恒 0 为当前合同门的忠实投影，批准前不虚构）；同字节账 distinct 4968/dup 1172/强制 MIRROR-or-other 副本 2950。三案可表达性：孪生字节层可表、副案逻辑目标不可表（MIRROR 无 targets）；V4 两版本 IMPORT+MIRROR 可表、MIRROR 副本 13 表名不可表；pdb2 1+3 可表、tif↔tifw 配准关联模型无字段不可表——不可表达关系五项 register 逐条 rule_id 级规则+阻断+保留方案；a03 复算指引入件。
- **checksum-exceptions-candidates.json**：两候选分列三账分离——NUL126@固定摘要 900d98c6 code=checksum_nul 模型可表达但运行门缺口 Task 6 reader（exception_not_implemented）；CHGIS 第 4 行 7452ae6c==chgis-v6 成员 155,774B **code 枚举无此项=不可表达**，授权路径=枚举扩展另行批准。
- **first-batch-preload-table.json**：5 文本逐项（status 七字段照录 table_names_approved=False/target_mapping_approved=False/disposition_retained=BLOCKED/CANDIDATE）+空间 2（各 6 组件 component_binding_approved=True）；回读条件改独立全量结构+规范值+重复次数对账（expected_count/expected_sha256 缺口逐项，text_values sidecar 不可替代）；GDAL Band.Checksum 另账 executed 26+deferred 17==43 断言。
- **wmf-thumbnail-record.json**：12 件 WMF NON_TABULAR+原件 sha/size 逐件记录；解码器需求条件说明（缩略图展示/图像检索交付才需）。
- **Task 6 固定摘要 NUL 运行门（本盒隔离实施，茶香授权）**：checksum_reader.py 新件（白名单仅 SHA256SUMS-b2 固定身份，复用 preview 核验逻辑）+disposition.evaluate 可选参数接线（默认 None 向后兼容）；正例证据绑定 contract/inventory sha+172 逐条 matched；反例（未审批/摘要不符/中间 NUL/行数不符/其他清点异常/CHGIS 声明）全保持阻断；**inventory.complete=false 保留、ready_for_import=false**；12 新用例+103 回归=115 passed exit 0；草案顶层歧义摘要字段清除（分字段身份保留）；CHGIS 单列待实施。真实冻结/落盘/服务/写库另行授权。
- **续盒六（校验账运行门实施准备，lead 接管 a02 两次失败创作）**：两例外完整源账身份分字段（NUL SHA256SUMS-b2 900d98c6…/22071B/172 行/偏移 21945 长 126；CHGIS harvard/chgis/SHA256SUMS.txt 694c101f…/551B/line4 verbatim/目标 chgis-v6/China_Periods_ReignDates.zip 7452ae6c…/155774B）；镜像投影文案修正（同字节仅限制 IMPORT 主件至多一个；mirror_evidence_sha256 与源件摘要分开）；**run-gate-implementation-plan.json**（白名单两固定例外非泛化+8 验收用例 C1–C8+入口/测试边界，实施另批）；首批空间 2 逐项前置补齐（SID/主件/组件/完整候选名/批准范围/expected 标缺/装载器 GAP/证据引用），文本 5 同口径。
- manifest 双锚 input_baseline_git=f54dd96/generation_head=ea40c1f；正式包应验清单见下节（sha256sum -c 口径）。

## 边界
本轮仅只读核查+DSH clone 整理+Gitea 交付；正式落盘、依赖、服务、历史对象处置、数据库写入均在授权外；entry/rehearsal M=2 未触；五块已提交交付不改写（rollup 只引用）。
