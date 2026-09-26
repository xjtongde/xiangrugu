# data-sources.md —— pg32b 数据来源对照表（人读摘要）

> **定位（2026-09-26 用户令开设："专门做一个文档……简单直接，让人一目了然"）**：一页说清三件实事——① 以 32 主机 `/mnt/wd61workmetadata/` 下**什么文件**为依据，导入到了**哪个位置**的数据库；② 这些文件**来自哪里、记录了什么**；③ 数据库与文件的**对应关系**。
> 本表系**摘要层**（R-04）：逐文件穷举账（1,757 行）的权威在 `docs/cbdb-load.md` §13/§15 与 `ops/harvard/load-b2/` 审计件（recon_b2a.tsv／src_paths.tsv／tree_coverage.tsv），本表数字全部由彼处机械汇总＋库内实测而来，口径注记见 §四。

## 一、两端与总账

| | |
|---|---|
| **数据源目录** | 32 主机 `/mnt/wd61workmetadata/`（NAS 61 共享之直挂）。装载实跑经同机每日镜像 `/mnt/nas-mirror/61/workmetadata/` 读取——**同一份数据的两条路径**（实测：两侧同文件 sha256 相同、65 个 DOI 树同数） |
| **导入目的地** | 32 主机（192.168.3.32）Docker 容器 **pg32b**（端口 5433），PostgreSQL 18.6＋PostGIS 3.6.4，数据库 **cbdb** |
| **库内三个 schema** | `public`＝CBDB 人物传记库＋独立小表；`chgis`＝CHGIS 历史地理信息系统（矢量＋栅格）；`harv`＝哈佛 Dataverse 各专题集 |
| **总账（库内实数）** | **395 张表／8,580,012 行／4,770 MB**。＝首批 84 表 5,686,842 行＋第二批 309 表 2,884,485 行＋系统 2 表 8,685 行（PostGIS `spatial_ref_sys` 8,501＋`ogr_system_tables` 184，非导入数据） |
| **两批** | 首批 2026-09-24（工作集 7 件）；第二批 2026-09-25～26（"能装尽装"全量，12 组） |

## 二、首批（2026-09-24）：`usedata/harvard/` 工作集 7 件

工作集＝用户令设立的"在用数据"选辑副本（原树只读备份）；13 件 sha256 双端核验全同。路径相对 `/mnt/wd61workmetadata/`。

| 源文件 | 来自哪里 · 记录什么 | 导入到 | 行数 |
|---|---|---|---:|
| `usedata/harvard/cbdb/cbdb_20260919.sqlite3` | CBDB 项目官方 HuggingFace 滚动发布，2026-09-19 构建（586MB）。**中国历代人物传记资料库**：66 万人物＋任职／亲属／社交／著作／地址等 | `public.*` 78 张表（表名照旧） | 5,623,075（＝官方值，验收相符） |
| `usedata/harvard/chgis/v6_time_pref_pgn_utf_wgs84.zip` | 哈佛 Dataverse `DOI I0Q7SM`。CHGIS V6 **时序府级面**（UTF-8＋WGS84 变体） | `chgis.v6_pref_pgn` | 3,830 |
| `usedata/harvard/chgis/v6_time_pref_pts_utf_wgs84.zip` | `DOI WW1PD6`。CHGIS V6 **时序府级点** | `chgis.v6_pref_pts` | 5,226 |
| `usedata/harvard/chgis/v6_time_cnty_pts_utf_wgs84.zip` | `DOI Q9VOF5`。CHGIS V6 **时序县级点** | `chgis.v6_cnty_pts` | 10,522 |
| `usedata/harvard/tab/Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab` | `DOI HTGBQ3`。**《全元文》1–60 册地名／人名索引**（TSV） | `public.quan_yuan_wen_index` | 40,199 |
| `usedata/harvard/tab/ACADEMY_Data.tab` | `DOI J6XRIV`。**历代书院 2,957 所**（含经纬度） | `public.academies_2957` | 2,957 |
| `usedata/harvard/tab/writings of the 19c missionaries in China.tab` | `DOI CE4ZNG`。**19 世纪来华传教士著述目录** | `public.missionary_writings` | 1,033 |

**首批小计：84 表／5,686,842 行。**（另 `cbdb_20260919.json`＝同仓元数据，出处凭证，未装。）

## 三、第二批（2026-09-25～26）：12 组

源路径相对 `/mnt/wd61workmetadata/`；`DVN/` ＝ `harvard-full/doi_10_7910/DVN/`（哈佛 Dataverse 全量下载 65 树）。行数为**库内实数**。

| 组 | 源目录／文件 | 来自哪里 · 记录什么 | 导入到 | 表数 | 行数 |
|---|---|---|---|---:|---:|
| D1 | `DVN/ST5KKM/`＋`DVN/HHVVHX/`＋`DVN/T27RQO/` 下 18 件 `v6_*.zip` | CHGIS **V6 其余层**：1820／1911／1990CITAS 三套 UTF-8 层（府县乡镇点、省面、河湖、海岸等） | `chgis.v6_*` | 18 | 65,305 |
| D2 | `DVN/M7WEFY/`（V5 树）29 件 | CHGIS **V5（2012）层**：1820／1911／1926／1990／1997 等 | `chgis.v5_*` | 29 | 69,780 |
| D3 | `DVN/M7WEFY/` 3 件 time zip | V5 **时序**（府面／府点／县点） | `chgis.v5_time_*` | 3 | 16,975 |
| D4 | `DVN/M7WEFY/` v5_gns 30 省分片 | **GNS 美军地名库**中国部分，30 省分片并装一表 | `chgis.v5_gns` | 1 | 130,665 |
| E | `DVN/PAGGQS/CBDB_20240208_sqlite.db` | CBDB 2024-02 官方 SQLite 之 **ADDR_XY**：人物↔地点坐标桥 | `public.addr_xy` | 1 | 19,249 |
| F | `chgis-v6/China_Periods_ReignDates.zip`（家中旧库原树） | **中国历史纪年**：纪年表／重大分期表／字段说明 | `chgis.china_chron` 等 | 3 | 750 |
| G | `DVN/E1FHML/DEM_QGIS-3_REVISED.zip` | CHGIS **V5 真高程 DEM**（GeoTIFF 栅格） | `chgis.dem` | 1 | 3,358（栅格瓦片） |
| H | `DVN/29302/v5_Hartwell_2010.zip` | **Hartwell 宋辽金历史 GIS**（包内 352 图层，同构归并） | `chgis.hartwell_*` | 9 | 21,497 |
| I | `DVN/` 14 专题树：SB8ZTM 明驿路驿站／VJHPVK 茶马古道／2CVTR0 日本德川／J5U79Z 天然气管线／JIISNB 高铁／W6PFXR 藏传寺院 TBRC／25413 DCW 数字世界地图／KUFJTG 北京史迹／5RUXK8 明代卫所／VAYEUZ BGIS／PRCLTU 西藏地名对照／PJ8D45 图幅索引／G9RKCW 科兹洛夫 1899／WP1ASG 等 | 各**专题矢量**集 | `chgis.ming_routes_2016` 等＋`harv.*` | 30 | 219,063 |
| J | `DVN/H3OB28/tgaz_bak_2018.zip`＋`3KAHBT`＋`I4UIKV`＋`EOH3FV`＋`SK7KGK`＋`MI56KU` | **TGAZ 时序地名库**（MySQL dump 33 表：spelling 24.5 万等）＋谭其骧图集名称表＋GNS／NIMA 特征码表＋1999 县级人口＋1991 国标政区码＋2001 工作坊索引＋THDL 西藏政区 | `harv.tgaz_*` 等＋`public.china_pop_1999_county`／`gb_91_codes`／`thdl_tibet_adm_areas` | 41 | 1,065,733 |
| K | `DVN/ZZKZ6U/CHGIS_V2.zip`＋`DVN/HIMIVE/V3_Data_Archive.zip`＋`DVN/PDGOZ0/V4_Data_Archive.zip` | CHGIS **V2（2003）／V3（2005）／V4（2007）三代档案**：旧代层＋随附关系库抽取（`v2db_/v3db_/v4db_*`）＋V2 DEM 六瓦片 | `chgis.v2_*`／`v3_*`／`v4_*` | 146 | 1,250,782 |
| L | `DVN/23340/1926_China_Atlas.zip`、`H4WVUP`（北京 1875）、`ABPR9F`／`LVYYZC`／`RXP4AA`／`E7HDYD`／`ELTD3L`／`G9RKCW`（俄测地图系列）、`PDGOZ0` gtopo30、`HIMIVE` v3_dem_all | **历史地图扫描配准**（普尔热瓦尔斯基／科兹洛夫／波德布内／布雷茨施耐德诸图，栅格）＋DEM 补瓦 | `harv.ras_*`＋`chgis.dem_*`／`v3_dem_topo30` | 28 | 21,328 |

**第二批小计：309 表／2,884,485 行。**（对账 recon 1,757 行中另 310 个"目标名"含 1 个多层占位名；其余为 SKIP／FIX 类事件行，见 §四。）

## 四、数据库与文件的对应关系（怎么查）

1. **命名即对应**：表名≈源文件名——`v6_1820_cnty_pts_utf.zip` → `chgis.v6_1820_cnty_pts`；`tgaz_spelling`（dump 内表）→ `harv.tgaz_spelling`。前缀规则：`chgis.v2_…v6_`＝CHGIS 第几代；`*_db_/v?db_`＝档案随附关系库；`harv.ras_`＝扫描栅格；`harv.tgaz_`＝TGAZ；`public.*`＝CBDB 原名照旧＋独立小表。
2. **任意一表反查源，三步**：表名 → `ops/harvard/load-b2/recon_b2a.tsv`（target 列：何文件→何表、行数、状态、注记）→ `ops/harvard/load-b2/src_paths.tsv`（src→NAS 完整路径＋档案内层成员链，1,757 行未解析 0）。过程与裁决＝`docs/cbdb-load.md` §15（第二批）／§12–13（首批）。
3. **行数口径**：本表＝**库内实数**（VACUUM ANALYZE 后 `n_live_tup`，2026-09-26 复测）。recon 逐行 pg_count 之和＝**装载事件累计**（同表多源对证／编码修复重载各记一行），大于库内数——两者皆真，口径不同。
4. **没装的部分（同样有账）**：源目录 65 树中 **24 树未触碰**——版本堆 5（存档不装裁决）／软件 2／文档树 7／同内容已装 7（sha 字节级实证）／GBK 编码变体 2（一份制）／**缺口挂账 1**（TI8DFI 多语言特征类型对照表，候令）＝`tree_coverage.tsv` 全对账。触碰而未装者逐行记 SKIP（重复 265／纯格式 532／编码变体 67／无地理 64 等）于 recon。

## 五、审计件（`ops/harvard/load-b2/`，39 件，依政策不入 git）

`recon_b2a.tsv`（1,757 行逐文件对账总账）· `src_paths.tsv`（行→NAS 路径映射）· `tree_coverage.tsv`（65 树＋目录覆盖审计）· `b2*.py` 22 支装载脚本（**当时硬编码源路径＝权威**）· `resolve_src.py`（映射表生成器，可复跑）。
