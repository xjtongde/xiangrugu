# 普通表格整理摘要（第 2/6 块，仅整理不写库）

生成：build_tabular_package.py 确定性合并；旧文件零改动。候选口径=archive_chain[-1] 末链名扩展名（**大小写不敏感**；.tab 合计 147，按功能精确分叉：大写 .TAB=MapInfo 空间表定义⇒块3，小写 .tab=文本表候选）。

## 计数（candidates=1640）
| 类 | 数量 | 去向 |
|---|---|---|
| csv | 7 | 本轮快照核实：6 表格候选⇒organized(提案态)，1 NGIA 严格解析 6×632 规整⇒organized 并记方言注记 |
| xls | 14 | **茶香授权后全可读**：锁定 xlrd==2.0.2（sha ea762c3d…入 requirements.lock）+32 构建独立候选镜像 runtime-tabular-xls-20261119-a（Id 6144346a501c…，VCS_REF a163f00e…），快照 :ro 挂载、on_demand 只读清点⇒14 件 organized(提案态)，逐 sheet nrows/ncols/列类型分布留证；公式语义统一标注 cached_value_semantics（xlrd 仅缓存结果，公式原文不可得）；空零维 Sheet2/Sheet3 记结构事实不建对象 |
| xlsx | 13 | stdlib zipfile+xml 解析成功⇒organized(提案态)，sheet/字段/行数留证 |
| ods | 4 | stdlib content.xml 解析成功：3 数据表⇒organized(提案态)；**CountryFilesFormat_2016-07-16.ods 内容证据判为字段格式说明文档（表头 Field Name/Description/Type/MaxLength；SSH 复测：**39 table-row 总数**（a03 口径）、其中 **37 含内容行**（1 表头+36 字段说明行，末 2 行全空）、**38 数据行**=总行减表头——三值如实并列）⇒块5**；与同 basename xlsx/csv 分别处置不认重复；Manshu.ods 附 __Anonymous_Sheet_DB__0 database-range 结构事实留证 |
| dbf | 704 | **全部为 Shapefile 空间组件⇒块3**（统一目录键的 shp/shx 兄弟扫描 704/704 命中，与 lead 侦察一致；独立 DBF=0） |
| .TAB 大写 | 142 | MapInfo 空间表定义⇒块3 |
| .tab 小写 | 5 | 全部已整理（权威 5 件，含 2 附加 .tab；无待证据 .tab） |
| txt | 751 | 内容级核实：**132 表格候选⇒organized(提案态)**；非表格⇒块5（其中 10 件由 pending 升级为内容证据、607 件名称模式获内容复核、2 件 irregular Notes.txt 亦升级块5） |

处置分布：organized=174、handoff-block3=846、handoff-block5=620、pending-evidence=0（合计 1640=candidates ✓）。

## 5 件文本/83 源字段/5 派生行号确证
权威载体=text-schema-approved.draft.yaml（yaml 后缀 JSON 内容）：object_count=5、source_column_count=83、schema/column-mapping/nullable/types/derived-rownum approved=true；table_names/target_mapping/ready_for_import=false、global_name_allocation_complete=false、逐对象 disposition_retained=BLOCKED——原样保留未升级。5 对象：ACADEMY_Data.tab(m008002,harv,2957)、Index…Yuan_Dynasty_vol_1-60.tab(harv,40199)、writings…China.tab(m008004,harv,1033)、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab(m004812,harv,29)、GB_91_HZ_040201_UTF8.tab(m006642,**chgis**,3389)。算术确证：54+5+11+7+6=83；每对象 1 列 __src_rownum bigint（one-based data record order excluding header）。读取规则两份 decisions 文件覆盖恰此五件（TAB/DOUBLE_QUOTE/doublequote/LF/empty_string=preserve_not_null/whitespace preserve/source_order preserve/**type_inference false**）。值合同 text-value-contract-approved.draft.json：XRGVALUE-v1、header_excluded、rownum_start=1，仅五对象范围。命名实现绑定 naming.py sha 13c0b910…（本地复核一致）；表名为候选，全量碰撞留块6。

## DBF 归属与交接
approved-dbf-{character,numeric}-reading.json 仅覆盖 1884route 两诊断件（且 limitations 自述非生产验证器），两者均为空间组件⇒随块3交接，块2 不重复认领。704 dbf 经同目录 shp/shx 兄弟扫描全部命中空间组件⇒块3 对象级清单见 handoffs.json。

## 第 2 块续做（32 项目快照只读核实 180 件）
快照=/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap（SSH 32 实测存在；嵌套件经 zipfile 提取到 /tmp，快照字节零接触；sha256 对账 inventory 全数一致）。工具面：宿主 python3.11.2 仅 chardet（openpyxl/xlrd/odf/pandas/lxml 缺、容器全缺、无 soffice/ssconvert/catdoc/xls2csv/in2csv/xlsx2csv），**未安装任何依赖**；xlsx/ods 走 stdlib zipfile+xml.etree（现有能力非新依赖）。分布（以终态文件为准）：可映射提案态 **169**（按格式分解以机器件 object-mapping.proposed_objects 为准：csv 7 + xlsx 13 + ods 3 + txt 132 + xls 按非空工作表每表一对象）；ods 第 4 件 CountryFilesFormat_2016-07-16.ods 经内容判定为字段格式说明文档⇒块5（documentation，带 pending_review）；改判块5 另有 **12**（10 非表格+2 irregular，名称模式升级为内容证据）；XLS 14 件经茶香授权锁定镜像（xlrd==2.0.2，候选 Id 6144346a…）全可读、逐非空工作表各一对象，gaps 已归零（详见 XLS 补齐轮专节）。全部新映射确认态=**PROPOSED_NOT_AUTHORIZED**（schema/表名/类型/值合同一律 False，未伪造批准；表名候选按 naming.py 现行规则现场复算——已用该规则精确重现权威件 5/5 的 source_object_id 与列名映射，配方可信）。Manshu .ods/.xlsx 双载体内容比对留证：表头同、60 OBJECTID 键集同、其余 8 列逐字同，仅 Y1/Y2 为 IEEE-754 序列化差异（float 相等）且行序不同⇒分别处置不认重复。CHGIS v6/V4 六对字典簿行级全同，同样保留双成员。派生 __src_rownum 政策沿用（行序 preserve）。块3/块5 交接项均带 pending_review=true 待复核标记。

## 收尾轮：列身份整表分配（修复上轮逐字段配方缺陷）
上轮 `allocate_columns([name])` 逐列单元素调用，使重复表头名共享同一 column_id。本轮改为**每表一次整表调用**（以函数实际语义为准：同 slug 基底者由 `__c{ordinal}` 后缀消歧；identity 含序号+源名故天然唯一），全部 155 提案对象重分配；批准 5 件权威映射未动。**lead 方言裁定（a03 ROUND 4 注记(a)）**：两份 ChinaW.Master.Beta.csv 的 naive split(',') 176 列系伪影（引号内含逗号表头 w302/w304 被错切），RFC4180 引号感知 csv.reader=**159 列且零重复源名**——与项目已确认文本读取语义（quotechar DOUBLE_QUOTE/doublequote=true）及 R-08 忠实一致；**引号感知为正，裁定披露入件（dialect_resolution：前后 176→159 对照+strict_widths [[159,2404]]+证据 sha），提案态可逆待茶香讨论确认**。china_chron.txt——首行按数据保留（header_row=null、data_records=676 不变），naming/identity **无现行无表头规则**（两模块已查），采用稳定序号名 col_001…col_020 经**同一整表配方**分配（target col_u5f_001…），提案态披露。全量逗号 txt 复核：naive==strict 列数（107 件抽核 0 差异）⇒无同类伪影需改；2 件全文件宽度存在个别 ragged 行（v3/v4_time_cnty_pts_utf，strict 24×2811+23×2 / 25×4889+26×3）如实记入 quote_artifact_audit.full_file_width_profile 供块6 值合同复核。
全量唯一性复核（机器件 object-mapping.uniqueness_review）：**170 表 / 4065 列，column_id 违例 0、target_column 违例 0、真重复源名消歧计数 23**（**5 对象 23 处全部在 XLS 面**——xlrd 首行空表头单元格 ''×n 所致，逐件对象+重复名清单入机器件 uniqueness_review.disambiguation_detail；csv/txt 面经 ChinaW 引号感知修正后为 0；跨表同 schema 候选名碰撞留块6）。计数终态（工作表收尾轮）：candidates 1640 = organized **174**(批准5+提案**170**) + block3 846 + block5 620 + pending **0**；proposed 字段 **4065**。

ROUND-5 名级修复（a03 三方比对发现、lead 基线对照）：上轮审计仅比**列数** naive==strict，漏掉名级引号包裹/尾 /编码失真——如实披露入机器件 name_level_audit（method+prior_round_defect_disclosed）。本轮 139 对象（txt132+csv7）**名级全量三方比对：clean 128 / diff 11**，diff 全部重导并整表重分配：①Tibet_twns_2009_utf8.csv 13 净名 [THL_ID,Tibetan,Wylie,Pinyin,Twn_GB_ext,…]、933 数据行（与 lead 基线逐元素等）；②MingGarrisons/hist_sites 末列  清除；③tan_GBK_names1/2、nima_feat_desig 末列  清除（tab 件同病）；④**ChinaWBeta.Field.Definitions.txt ×2：BOM fffe UTF-16LE 嗅探+严格解码重判**——latin-1 NUL 碎片名消除，实为 TAB 分隔 7 列真实数据字典表（[Variable,COLUMN,ITEMNAME,WIDTH,OUTPUT,TYPE,DECIMALS]、159 数据行），处置按内容证据=**organized 提案态**（先例 v4/v6_data_dictionary.xlsx），encoding_resolution 披露含双副本 17580B 字节同、保留双成员镜像比对留块6。china_chron 首行数据判定不受影响（仅观测单元格尾  注记）。修复后字段总数 **4065**（11 件重导净增减为 0：CHW 176→159 已在上一轮计入，本轮名级修正不改列数）。

## 工作表映射收尾轮（拆分/补名/扫描）
**MingGarrisonsSheet_29jan08.xls（KML/ming_garrisons_KML.zip 嵌套件）横拼缺陷修复**：原单对象 25 字段=Sheet1(14列)+Sheet2(11列)拼接⇒拆为**两个独立导入对象**——各自 source_object_id 以工作表限定身份输入 `'<member>#<sheet>'` 经 identity.py **真函数**分配（0e2674e1…/04e26d04…，convention 逐对象披露于 worksheet_split 字段）、候选表名经 naming.py 真函数+同限定名生成（…__minggarri__0e2674e1 / …__04e26d04，零碰撞）、字段按各自 sheet 源序整表 allocate_columns、行数 nrows 773/376→data_records 772/375。**禁止横拼/按行号合并**。归档成员登记不变（members.json 该件仍一条）。
**同类扫描（方法修正如实披露）**：上轮 multi-sheet 扫描误用证据键（nrows/rows 在交付记录中不存在）导致全漏——本轮以正确键 worksheets_observed[].columns/data_records_observed 复扫全部提案对象：**多非空 sheet 合并仅 MingGarrisons 一处**；xlsx 13 件每簿均单命名 sheet、ods 3 数据件各取 table:table 已逐表成对象（CountryFiles 文档件在块5）、其余 XLS 件各仅 1 非空 sheet——无其他拆分需求。
**补名**：csv/txt 平面件 worksheet=null 共 139 处⇒**138 件真平面件**统一改标 'TABLE'（机器可寻址）；**例外 76ed534c…（Ming_Garrisons.zip!MingGarrisonsSheet_29jan08.csv）系工作簿导出件非平面件**——复用授权镜像只读回测同 zip 兄弟簿 MingGarrisonsSheet_29jan08.xls（sha 740b18d3af11…）sheet_names=[Sheet1,Sheet2,Sheet3]，该 csv 11 列表头与其 **Sheet2 逐列一致（wei_id…end_yr，11 列/375 行同构）**⇒worksheet 补真名 **'Sheet2'** 并注内容比对；与嵌套件拆分出的 Sheet2 对象（04e26d04…）构成双成员保留（不同归档链，镜像比对留块6）。carrier_wb 判定含"同外层归档兄弟工作簿"规则入代码。china_chron.txt 保持 header_row=null。
**空 sheet**：零维 Sheet2/Sheet3（5 处）保留 members 清点结构事实，不建对象。
对象级计数：proposed **169→170**、字段 **4065 不变**（拆分净增减 0）、唯一性重跑 **170 表/4065 列双 0 违例**；成员级闭合 1640=174+846+620+0 不变。

## GAP / 未决
1. ~~XLS 14 件 BIFF 读取缺口~~ **已闭合（茶香授权轮）**：requirements.lock/in 锁 xlrd==2.0.2（官方 wheel sha256 ea762c3d…逐字）、32 构建独立标签候选镜像（未触 deploy/别名，runtime/dev/test Id 基线复核未变）、容器内 xlrd.__version__=2.0.2 实证；14 件全部只读清点成功（sha 对账 14/14 匹配）。嵌套链解析器在本目录格式上迭代七版方正确（inventory chain 末元素含目录前缀+外层 relative_path 已含末段——如实记录防复发）。剩余缺口仅为批准面：全部新映射 PROPOSED_NOT_AUTHORIZED，正式读取/装载批准件待茶香派工。2. PG 装载器未实现（沿用块1 GAP）；本包不运行任何装载。
3. 全版本命名碰撞未完成（块6）。

**ready_for_import=False 保持；类型推断禁止沿用；空串≠NULL 沿用；行序保留+派生行号单列。**
