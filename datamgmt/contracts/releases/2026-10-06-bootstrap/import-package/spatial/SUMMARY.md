# 第 3/6 块 · 空间矢量包（SUMMARY）

基线 git 5478271；只读证据容器镜像 sha256:6144346a501c7ba1299e28862a303007fddd6a9e8030c6b6e7c1ca52921b6cd3（复用块2授权件，未重建）。

## 三计数
- 候选组 **903**（kml 52 + mapinfo_candidate 146 + shapefile 705；shapefile/mapinfo 沿用 spatial-component-candidates.json，KML 52 件本轮按同一外层文件+链+stem 规则补查入组；inventory sha256=fb5e6b334b898d62… 核验一致后直接复用）
- 已确证组（头级只读取证全命中、sha 对账 2708/2708 匹配 0 错）：**903**
- 映射对象合计 **901** =批准逐字沿用 **2** + 提案 **899**（shapefile 702 + mapinfo_tab 142 + kml 52，均 PROPOSED_NOT_AUTHORIZED）；缺口组 **1**。组级泳道分区机器断言在码：approved 2 + proposed 899 + gap 1 + text-owned-by-block2 2 = 903，UNASSIGNED=0——每组成员处置明确，AGENTS「不能静默遗漏」达成

## KML 专段（本轮补查，52 件零遗漏）
KML 亦矢量成员：按同一外层文件+完整链+stem 规则**每件自成一组**（无伴随件），groups.json family_candidate=kml 52 组、全部 CONFIRMED_READ_ONLY（xml.etree 元素统计+sha 对账匹配）。提案映射 52 对象（carrier=kml，PROPOSED_NOT_AUTHORIZED）：geometry 依据=已采集 Placemark/Point/LineString/Polygon/LinearRing/MultiGeometry 计数；**srid=null** 政策同（KML 自身规范坐标语义注记、无 EPSG 批准可推导）；属性面如实留正式读取器合同（ExtendedData 字段化未提案，attributes_note 披露）；naming/identity 真函数、basis=镜像 Id+证据 sha。52/52 全映射、0 gap。

## 846 交接归属闭合
block3 成员 846=dbf 704+TAB 142，逐件恰属一组（无串组/遗漏/重复），机器核于 groups.json.block3_members_attributed_exactly_once=846。提案对象 846 与交接 846 数值巧合但口径不同：提案按组主件（.shp/.tab）计数——含缺 dbf 组的 shp 仍提案（属性合同入 gaps 注记），不含孪生无主件组；两套计数各自闭合。mapinfo 146 vs TAB 142 差额 4 已查明：2 组为 casefold 歧义孪生组（v3_time_pref_pgn_PRC/V3_…，仅 DAT/IND/MAP 无 .TAB）+2 组的 .TAB 系顶层平面件已被块2按 tab-text 整理（GB_91_HZ_040201_UTF8.tab、2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab）。

## 缺件统计（实算）
缺 .dbf 组 1（v5_time_pref_pts_utf）、缺 .prj 组 3（tib19pdb/v2_time_cnty_pgn_utf/v2_time_cnty_pts_utf）——与 lead 侦察一致；可选件 sbn/sbx/ind 缺失非阻塞已在各组 optional_absent 注记。KML 52 件几何元素统计入证据（Point/Polygon/LinearRing/Placemark 计数）。

## 映射政策
2 批准对象（Ca1884route_przh_1251/utf8，59 记录，SRID4326 语境、原 X/Y 不交换不转换、PRJ+QPJ 双保留、轴序差异注记不消除）**逐字沿用**自 approved-spatial-binding-context.json（sid 经 identity.py 真函数复算==批准值，断言在码）。其余组提案映射：geometry_type 按 SHP 头 offset32（分布 Point192/PolyLine24/Polygon470/MultiPoint17/PointZ1/PolygonZM1——Z/M 维 2 件目标类型留待正式合同故 target_type_proposal=null 如实注）；属性序按 DBF 字段描述符原序/TAB COLUMN 定义原序；CRS 声明逐字保留且 **srid=null**（SRID 批准仅逐案 2 件不得推导扩展）；表名 naming.py 真函数、身份 identity.py 真函数；basis=镜像 Id+证据 sha。

## 过程缺陷如实披露
取证迭代三版：①任务键误用 group location.chain 致 1279 KeyError→改从 inventory entries 直构；②解析器 endswith 兜底误抓同后缀兄弟件致 342 sha 失配→收紧精确匹配+大小写次级；③TAB 文本含 U+0085/U+2028 使 splitlines 断行损坏 jsonl→控制字符归一化。终态 2708 记录 0 错 0 失配。

## GAP
缺口组 1：见 evidence-gaps.json（casefold 孪生无主件组等）；依赖缺口：无新增（stdlib struct/xml.etree 现有能力覆盖全部取证）。
