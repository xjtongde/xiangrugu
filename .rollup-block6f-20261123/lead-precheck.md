# 第 6/6 块续盒五（对齐现行合同门）· lead 预核（2026-11-22/23，30 分钟盒）

- 起表 17:51:20 UTC，硬停 18:21:20 UTC。基线 ea40c1f9af14bb5a8fc2e7cd3b5cdf8cfa52d45e（M=2 完好、暂存空）。
- 只读核查+合同草案补正；运行门实现/冻结/正式落盘/入库另行授权。模型源码零修改。

## 现行模型门（lead 17:52–17:55 UTC 源码逐条核，行号引证）
源：datamgmt/src/xiangrugu_datamgmt/contracts.py / disposition.py / model.py
1. **Disposition 枚举**（model.py L14-18）：IMPORT / MIRROR / NON_TABULAR / BLOCKED——无 RETAIN；manifest 四分类草案须投影映射。
2. **MemberSelector**（contracts.py L37-55）：三元组 (relative_path, archive_chain, archive_ordinals)，链/序号等长，禁 glob。
3. **DispositionRule 约束**（L106-132）：非 BLOCKED 须 canonical path；file 须 sha256+size  raw 断言；symlink/special 必须 BLOCKED；**IMPORT 须 file+显式 targets**；**only IMPORT can have business targets**；**MIRROR 须 mirror_of+mirror_evidence_sha256**，mirror 字段专属 MIRROR；object/column 声明唯一；encodings 须属于已声明逻辑对象。
4. **ObjectTarget**（L85-90）：schema∈{cbdb,chgis,harv}（Literal）；table ^[a-z][a-z0-9_]{0,62}$；expected_count/expected_sha256 可空（draft）但 **frozen 须全值**（L178-179）。
5. **ContractException**（L147-151）：**code 仅 Literal["checksum_nul"]**——CHGIS 第 4 行候选不可表达为 exception。
6. **ReleaseContract**（L154-193）：version=1；status draft/frozen；frozen 须 review；canonical_bytes 排序确定性+sha256。
7. **DispositionLedger.evaluate**（disposition.py L58-118）：
   - inventory sha 不符→inventory_mismatch；**complete=false→incomplete_inventory**（现 inventory 保留态恒触发）；空→empty_inventory。
   - **任何 exceptions→exception_not_implemented**（L69-71 注释：Task 6 窄域 reader 存在前仅声明）。
   - **IMPORT 按 (sha256,size) 登记 primary_bytes，重复→mirror_required**（L81-85）。
   - **(schema,table) 全局唯一，重复→target_collision**（L86-90）。
   - **MIRROR 校验**：mirror_of 存在且为 IMPORT 且同 (sha256,size)，否则 invalid_mirror（L91-94）。
   - 每成员 location 恰一规则（unmatched_member/multiple_matches）；四元组 (kind,sha256,size,signature) 全等方 explained（stale_assertion）；unused_rule。
   - **ready_for_import = status==frozen 且 coverage.conforms**（L127-129，合同门非 G0-G7 证书）。
8. **signature 枚举**（MemberExpectation L62）：unknown/zip/sqlite/ole/tiff/pdf。
9. **text_values.py L14**：non-executable sidecar projection, not ReleaseContract validation（预览证据面）。

## 三案可表达性预判（lead，a02/a03 独立验证）
- **MapInfo 孪生**：字节层可表达（主案 5 组件 IMPORT+副案 5 组件 MIRROR，同 sha+size）；**副案独立逻辑对象目标不可表达**（MIRROR 无 targets）→两案各建表需模型扩展或裁定；逻辑对象身份保留 rollup 草案。
- **V4 MDB 两版本**：直接件 a2cc4039 IMPORT+包裹件 04be983d 一 IMPORT 一 MIRROR 可表达字节层；**三副本 39 条逻辑表名中 MIRROR 副本 13 表名不可表达为 target**（target_collision+MIRROR 无 targets）。
- **pdb2 不同伴随件**：4 TIF 同字节 bd56086a 1 IMPORT+3 MIRROR 可表达；**tif↔tifw 配准关联模型无字段不可表达**（保留 draft 证据）；V4 [159,6] 无 wf 照录 UNRESOLVED_PENDING。
- **恒门**：inventory complete=false→incomplete_inventory 恒触发→ready_for_import 永假（须 inventory 完整性裁定或新版本，R-04 原账不改）；exceptions→exception_not_implemented（Task 6 reader 运行门缺口）。

## 首批 7 对象批准范围（lead 17:54 UTC 交付件核）
- 5 文本（4 harv+1 chgis）：schema_approved/source_column_mapping_approved/derived_rownum_mapping_approved=True；**table_names_approved=False/target_mapping_approved=False/disposition_retained=BLOCKED/ready_for_import=False**；candidate_table_name 仅 CANDIDATE；objects 带 rule_id（投影可复用）；confirmation_basis 引 text-schema-approved.draft.yaml sha 0f379eee…。
- 2 空间：Ca1884route_przh_1251/utf8 各 6 组件（cpg/dbf/prj/qpj/shp/shx）component_binding_approved=True；.shp 主件 ord[6]/[14] 同 sha 109d74b1…。
- 回读标准（派工）：独立全量结构+规范值+重复次数对账→expected_count（含重复行）+expected_sha256（规范值投影摘要）+结构（列名/类型/序）；17 GDAL Band.Checksum() 与源件 SHA-256 分账。

## 两校验账候选（沿用现有，三账分离）
- NUL126：raw_sha256 900d98c6…，code checksum_nul 可表达；预览=roots.yaml format_anomaly+172 行全验证；运行门=Task 6 reader 未实现；授权=茶香固定摘要兼容解析批准。
- CHGIS 第 4 行：7452ae6c…==chgis-v6 成员 155774B，6/6 行验证；**模型 exception code 枚举不可表达**→规则+阻断+授权路径；运行门=ledger 核验器。

## 本盒交付控制
- 新三件：contract-projection-draft / checksum-exceptions-candidates / first-batch-preload-table；manifest 补正（input_baseline_git=f54dd96/generation_head=ea40c1f 分清+自指排除+正式包应验清单）；WMF12 NON_TABULAR 原件保留+解码交付条件；SUMMARY/TODO。
- 归属 8004+1311+1293 零漂移；五块+既有草案零改写；模型源码零修改；M=2 不触。