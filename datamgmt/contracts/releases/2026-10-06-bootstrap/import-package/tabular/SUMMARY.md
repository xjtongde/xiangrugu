# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（大小写敏感）。

## 计数（candidates=1636）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | 7 | 全部待证据（无读取批准件） |
| xls | 14 | 待证据（含 sheet 清单缺口） |
| xlsx | 13 | 待证据（同上） |
| dbf | 704 | **全部为 Shapefile 空间组件⇒块3**（统一目录键的 shp/shx 兄弟扫描 704/704 命中，与 lead 侦察一致；独立 DBF=0） |
| .TAB 大写 | 142 | MapInfo 空间表定义⇒块3 |
| .tab 小写 | 5 | 5 已整理（权威件）+2 待证据 |
| txt | 751 | 含大写 .TXT（大小写不敏感纳入，修复 a03 ITEM 1）：说明件⇒块5（名称模式判定）609 件；其余 142 件待内容抽样判定 |

处置分布：organized=5、handoff-block3=846、handoff-block5=609、pending-evidence=176（合计 1636=candidates ✓）。

## 5 件文本/83 源字段/5 派生行号确证
权威载体=text-schema-approved.draft.yaml（yaml 后缀 JSON 内容）：object_count=5、source_column_count=83、schema/column-mapping/nullable/types/derived-rownum approved=true；table_names/target_mapping/ready_for_import=false、global_name_allocation_complete=false、逐对象 disposition_retained=BLOCKED——原样保留未升级。5 对象：ACADEMY_Data.tab(m008002,harv,2957)、Index…Yuan_Dynasty_vol_1-60.tab(harv,40199)、writings…China.tab(m008004,harv,1033)、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab(m004812,harv,29)、GB_91_HZ_040201_UTF8.tab(m006642,**chgis**,3389)。算术确证：54+5+11+7+6=83；每对象 1 列 __src_rownum bigint（one-based data record order excluding header）。读取规则两份 decisions 文件覆盖恰此五件（TAB/DOUBLE_QUOTE/doublequote/LF/empty_string=preserve_not_null/whitespace preserve/source_order preserve/**type_inference false**）。值合同 text-value-contract-approved.draft.json：XRGVALUE-v1、header_excluded、rownum_start=1，仅五对象范围。命名实现绑定 naming.py sha 13c0b910…（本地复核一致）；表名为候选，全量碰撞留块6。

## DBF 归属与交接
approved-dbf-{character,numeric}-reading.json 仅覆盖 1884route 两诊断件（且 limitations 自述非生产验证器），两者均为空间组件⇒随块3交接，块2 不重复认领。704 dbf 经同目录 shp/shx 兄弟扫描全部命中空间组件⇒块3 对象级清单见 handoffs.json。

## GAP / 未决
1. csv7+xls14+xlsx13 无读取批准件、无 sheet 级对象清单⇒逐件列于 evidence-gaps.json。
2. txt 中非 README 名称模式者需授权后批量首行抽样判表性（不静默归类）。
3. PG 装载器未实现（沿用块1 GAP）；本包不运行任何装载。
4. 全版本命名碰撞未完成（块6）。

**ready_for_import=False 保持；类型推断禁止沿用；空串≠NULL 沿用；行序保留+派生行号单列。**
