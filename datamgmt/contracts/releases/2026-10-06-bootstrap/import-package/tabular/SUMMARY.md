# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（**大小写不敏感**；.tab 合计 147，按功能精确分叉：大写 .TAB=MapInfo 空间表定义⇒块3，小写 .tab=文本表候选）。

## 计数（candidates=1640）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | 7 | 本轮快照核实：6 表格候选⇒organized(提案态)，1 NGIA 严格解析 6×632 规整⇒organized 并记方言注记 |
| xls | 14 | **14 全部读不了**（BIFF，xlrd/转换器宿主+容器全缺）⇒pending-evidence 逐件入 gaps |
| xlsx | 13 | stdlib zipfile+xml 解析成功⇒organized(提案态)，sheet/字段/行数留证 |
| ods | 4 | stdlib content.xml 解析成功：3 数据表⇒organized(提案态)；**CountryFilesFormat_2016-07-16.ods 内容证据判为字段格式说明文档（表头 Field Name/Description/Type/MaxLength，37 行）⇒块5**；与同 basename xlsx/csv 分别处置不认重复；Manshu.ods 附 __Anonymous_Sheet_DB__0 database-range 结构事实留证 |
| dbf | 704 | **全部为 Shapefile 空间组件⇒块3**（统一目录键的 shp/shx 兄弟扫描 704/704 命中，与 lead 侦察一致；独立 DBF=0） |
| .TAB 大写 | 142 | MapInfo 空间表定义⇒块3 |
| .tab 小写 | 5 | 全部已整理（权威 5 件，含 2 附加 .tab；无待证据 .tab） |
| txt | 751 | 内容级核实：**132 表格候选⇒organized(提案态)**；非表格⇒块5（其中 10 件由 pending 升级为内容证据、607 件名称模式获内容复核、2 件 irregular Notes.txt 亦升级块5） |

处置分布：organized=160、handoff-block3=846、handoff-block5=620、pending-evidence=14（合计 1640=candidates ✓）。

## 5 件文本/83 源字段/5 派生行号确证
权威载体=text-schema-approved.draft.yaml（yaml 后缀 JSON 内容）：object_count=5、source_column_count=83、schema/column-mapping/nullable/types/derived-rownum approved=true；table_names/target_mapping/ready_for_import=false、global_name_allocation_complete=false、逐对象 disposition_retained=BLOCKED——原样保留未升级。5 对象：ACADEMY_Data.tab(m008002,harv,2957)、Index…Yuan_Dynasty_vol_1-60.tab(harv,40199)、writings…China.tab(m008004,harv,1033)、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab(m004812,harv,29)、GB_91_HZ_040201_UTF8.tab(m006642,**chgis**,3389)。算术确证：54+5+11+7+6=83；每对象 1 列 __src_rownum bigint（one-based data record order excluding header）。读取规则两份 decisions 文件覆盖恰此五件（TAB/DOUBLE_QUOTE/doublequote/LF/empty_string=preserve_not_null/whitespace preserve/source_order preserve/**type_inference false**）。值合同 text-value-contract-approved.draft.json：XRGVALUE-v1、header_excluded、rownum_start=1，仅五对象范围。命名实现绑定 naming.py sha 13c0b910…（本地复核一致）；表名为候选，全量碰撞留块6。

## DBF 归属与交接
approved-dbf-{character,numeric}-reading.json 仅覆盖 1884route 两诊断件（且 limitations 自述非生产验证器），两者均为空间组件⇒随块3交接，块2 不重复认领。704 dbf 经同目录 shp/shx 兄弟扫描全部命中空间组件⇒块3 对象级清单见 handoffs.json。

## 第 2 块续做（32 项目快照只读核实 180 件）
快照=/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap（SSH 32 实测存在；嵌套件经 zipfile 提取到 /tmp，快照字节零接触；sha256 对账 inventory 全数一致）。工具面：宿主 python3.11.2 仅 chardet（openpyxl/xlrd/odf/pandas/lxml 缺、容器全缺、无 soffice/ssconvert/catdoc/xls2csv/in2csv/xlsx2csv），**未安装任何依赖**；xlsx/ods 走 stdlib zipfile+xml.etree（现有能力非新依赖）。分布（以终态文件为准）：可映射提案态 **155** = csv 7 + xlsx 13 + ods 3 + txt 132；ods 第 4 件 CountryFilesFormat_2016-07-16.ods 经内容判定为字段格式说明文档⇒块5（documentation，带 pending_review）；改判块5 另有 **12**（10 非表格+2 irregular，名称模式升级为内容证据）；读不了 **14**（xls BIFF，逐件入 gaps）。全部新映射确认态=**PROPOSED_NOT_AUTHORIZED**（schema/表名/类型/值合同一律 False，未伪造批准；表名候选按 naming.py 现行规则现场复算——已用该规则精确重现权威件 5/5 的 source_object_id 与列名映射，配方可信）。Manshu .ods/.xlsx 双载体内容比对留证：表头同、60 OBJECTID 键集同、其余 8 列逐字同，仅 Y1/Y2 为 IEEE-754 序列化差异（float 相等）且行序不同⇒分别处置不认重复。CHGIS v6/V4 六对字典簿行级全同，同样保留双成员。派生 __src_rownum 政策沿用（行序 preserve）。块3/块5 交接项均带 pending_review=true 待复核标记。

## GAP / 未决
1. csv7+xls14+xlsx13 无读取批准件、无 sheet 级对象清单⇒逐件列于 evidence-gaps.json。
2. txt 中非 README 名称模式者需授权后批量首行抽样判表性（不静默归类）。
3. PG 装载器未实现（沿用块1 GAP）；本包不运行任何装载。
4. 全版本命名碰撞未完成（块6）。

**ready_for_import=False 保持；类型推断禁止沿用；空串≠NULL 沿用；行序保留+派生行号单列。**
