# data-sources.md —— pg32b 数据来源对照表（人读摘要）

> **定位（2026-09-26 用户令开设："专门做一个文档……简单直接，让人一目了然"）**：一页说清三件实事——① 以 32 主机 `/mnt/wd61workmetadata/usedata/`（**pg32b 导入之权威数据源目录**，2026-09-28 用户令设立）下**什么文件**为依据，导入到了**哪个位置**的数据库；② 这些文件**来自哪里、记录了什么**；③ 数据库与文件的**对应关系**。
> **路径书写规约（2026-09-28 用户令："目录与文件一定用绝对路径描述"）**：本文所有**数据源文件、数据源目录、审计件**一律写**绝对路径**，不用缩写、不用相对记号（zip 之内层成员链如 `metadata/v4_data_dictionary.xlsx` 系**档案内路径**、非文件系统路径，不在此列）；唯 `docs/*.md` 之**文档互引**照全项目惯例用仓内相对路径（仓根＝`/root/xiangrugu/`，见 `AGENTS.md` §2）。
> 本表系**摘要层**（R-04）：逐文件穷举账（**1,770 行**；原 1,757 行，2026-09-28 FIX10／FIX11 批增 13 行）的权威在 `docs/cbdb-load.md` §13/§15 与 `/root/xiangrugu/ops/harvard/load-b2/` 审计件（`/root/xiangrugu/ops/harvard/load-b2/recon_b2a.tsv`／`/root/xiangrugu/ops/harvard/load-b2/src_paths.tsv`／`/root/xiangrugu/ops/harvard/load-b2/tree_coverage.tsv`），本表数字全部由彼处机械汇总＋库内实测而来，口径注记见 §四。

## 一、两端与总账

| | |
|---|---|
| **数据源目录（权威）** | **`/mnt/wd61workmetadata/usedata/`** —— **2026-09-28 用户令设立为 pg32b 导入之唯一权威数据源目录**（令文照录：「我现在要你把我们导入到pg32b里的源数据移动到/mnt/wd61workmetadata/usedata目录里。这个目录就是我们pg32b导入的权威数据源。」）。内含两批工作集：**首批 15 件**在 `/mnt/wd61workmetadata/usedata/harvard/`（2026-09-24 立，语义名布局；账＝`/mnt/wd61workmetadata/usedata/harvard/README.md`＋`/mnt/wd61workmetadata/usedata/harvard/SHA256SUMS`）；**第二批 173 件**在 `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/`（**36** 个 DOI 目录）与 `/mnt/wd61workmetadata/usedata/chgis-v6/`（2026-09-28 拷入，**镜像源树布局**；账＝`/mnt/wd61workmetadata/usedata/README-b2.md`＋`/mnt/wd61workmetadata/usedata/SHA256SUMS-b2`）。全目录现 **190 件／3.2 GB**（含两份账）。**换算规则**：`usedata 内绝对路径 ＝ /mnt/wd61workmetadata/usedata ＋ /root/xiangrugu/ops/harvard/load-b2/src_paths.tsv 之 nas_path 列`。<br>**纪律（用户令照录）**：「我们下载下来的源数据决不能修改。」→ 故系**拷入而非搬移**：下载原树 `/mnt/wd61workmetadata/harvard-full/`（仍 **65** 棵 DOI 树）与 `/mnt/wd61workmetadata/chgis-v6/` **完整保留为只读备份**；拷后**源端 sha256 复算 173/173 相符 → 原树内容零改动**，目标端 sha256 亦 **173/173 相符**，逐件体积 0 缺失、0 不符。<br>**历史口径（原文不回改）**：32 主机 `/mnt/wd61workmetadata/`（NAS 61 共享之直挂）。装载实跑经同机每日镜像 `/mnt/nas-mirror/61/workmetadata/` 读取——**同一份数据的两条路径**（实测：两侧同文件 sha256 相同、65 个 DOI 树同数）。**2026-09-27 用户裁决：nas-mirror＝用户自建之 32 本地 NAS 备份区，项目禁用（读写皆不碰）——此后项目唯一读取路径＝直挂**；前句"实跑经镜像盘"系两批装载之史实（与直挂字节级同一：文件数 16,822＝同、纯文件字节和 21,492,791,579＝同、rsync 干跑零差异，09-27 复测），本表路径口径＝用户所指直挂路径，恰即镜像盘之同步源（裁决权威＝`docs/codemap.md` §2 专行） |
| **导入目的地** | 32 主机（192.168.3.32）Docker 容器 **pg32b**（端口 5433），PostgreSQL 18.6＋PostGIS 3.6.4，数据库 **cbdb** |
| **库内四个 schema** | `public`＝CBDB 人物传记库＋独立小表；`chgis`＝CHGIS 历史地理信息系统（矢量＋栅格）；`harv`＝哈佛 Dataverse 各专题集；`ogr_system_tables`＝GDAL 自建之元数据表（1 表 184 行）。〔**2026-09-28 补正**：原书"三个 schema"，与下行为总账自列之 `ogr_system_tables` 及 `docs/pg32b.md` §13"chgis 211＋harv 97＋public 86＋ogr_system_tables 1＝395"自相矛盾，今从实测作**四个**〕 |
| **总账（库内实数）** | **395 张表／8,584,097 行／4,771 MB**。＝首批 84 表 5,686,842 行（**本批未动**）＋第二批 309 表 2,888,570 行＋系统 2 表 8,685 行（PostGIS `spatial_ref_sys` 8,501＋`ogr_system_tables` 184，非导入数据）。〔**2026-09-28 补正**：原书 8,580,012 行／4,770 MB／第二批 2,884,485 行。本批 FIX10 补装 `v4_gns` 广西 **＋4,099**、FIX11 删八表非数据行 **−14**，净 **＋4,085**；表数 395 不变。逐表明细见 §六〕 |
| **两批** | 首批 2026-09-24（工作集 7 件）；第二批 2026-09-25～26（"能装尽装"全量，12 组） |

## 二、首批（2026-09-24）：`/mnt/wd61workmetadata/usedata/harvard/` 工作集 7 件

工作集＝用户令设立的"在用数据"选辑副本（原树只读备份）；13 件 sha256 双端核验全同。**本表及全文所有目录与文件一律以绝对路径描述**（2026-09-28 用户令："目录与文件一定用绝对路径描述"）。

| 源文件（绝对路径） | 来自哪里 · 记录什么 | 导入到 | 行数 |
|---|---|---|---:|
| `/mnt/wd61workmetadata/usedata/harvard/cbdb/cbdb_20260919.sqlite3` | CBDB 项目官方 HuggingFace 滚动发布，2026-09-19 构建（586MB）。**中国历代人物传记资料库**：66 万人物＋任职／亲属／社交／著作／地址等 | `public.*` 78 张表（表名照旧；**2026-09-28 补注**：PostgreSQL 折叠标识符大小写，sqlite 之 `BIOG_MAIN` 入库为 `biog_main`，"照旧"指词形不指大小写） | 5,623,075（＝官方值，验收相符） |
| `/mnt/wd61workmetadata/usedata/harvard/chgis/v6_time_pref_pgn_utf_wgs84.zip` | 哈佛 Dataverse `DOI I0Q7SM`。CHGIS V6 **时序府级面**（UTF-8＋WGS84 变体） | `chgis.v6_pref_pgn` | 3,830 |
| `/mnt/wd61workmetadata/usedata/harvard/chgis/v6_time_pref_pts_utf_wgs84.zip` | `DOI WW1PD6`。CHGIS V6 **时序府级点** | `chgis.v6_pref_pts` | 5,226 |
| `/mnt/wd61workmetadata/usedata/harvard/chgis/v6_time_cnty_pts_utf_wgs84.zip` | `DOI Q9VOF5`。CHGIS V6 **时序县级点** | `chgis.v6_cnty_pts` | 10,522 |
| `/mnt/wd61workmetadata/usedata/harvard/tab/Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab` | `DOI HTGBQ3`。**《全元文》1–60 册地名／人名索引**（TSV） | `public.quan_yuan_wen_index` | 40,199 |
| `/mnt/wd61workmetadata/usedata/harvard/tab/ACADEMY_Data.tab` | `DOI J6XRIV`。**历代书院 2,957 所**（含经纬度） | `public.academies_2957` | 2,957 |
| `/mnt/wd61workmetadata/usedata/harvard/tab/writings of the 19c missionaries in China.tab` | `DOI CE4ZNG`。**19 世纪来华传教士著述目录** | `public.missionary_writings` | 1,033 |

**首批小计：84 表／5,686,842 行。**（另 `/mnt/wd61workmetadata/usedata/harvard/cbdb/cbdb_20260919.json`＝同仓元数据，出处凭证，未装。）

## 三、第二批（2026-09-25～26）：12 组

**下列源路径皆为绝对路径**（2026-09-28 用户令："目录与文件一定用绝对路径描述"），指向权威源目录 `/mnt/wd61workmetadata/usedata/`；**不使用任何缩写或相对记号，每处皆写全**。逐文件之完整清单（**173 件**，每件含 usedata 绝对路径、原树绝对路径、大小、sha256、装数去向）＝`/mnt/wd61workmetadata/usedata/README-b2.md`；校验账＝`/mnt/wd61workmetadata/usedata/SHA256SUMS-b2`（`cd /mnt/wd61workmetadata/usedata && sha256sum -c SHA256SUMS-b2` → **173/173 成功**）。本节只列各组之主目录／主件。行数为**库内实数**。

| 组 | 源目录／文件 | 来自哪里 · 记录什么 | 导入到 | 表数 | 行数 |
|---|---|---|---|---:|---:|
| D1 | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ST5KKM/`（usedata 内实收 8 件）＋`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/HHVVHX/`（实收 7 件）＋`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/T27RQO/`（实收 3 件）下 18 件 `v6_*.zip` | CHGIS **V6 其余层**：1820／1911／1990CITAS 三套 UTF-8 层（府县乡镇点、省面、河湖、海岸等） | `chgis.v6_*` | 18 | 65,305 |
| D2 | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/`（V5 树）29 件（usedata 内实收 **28** 件源文件） | CHGIS **V5（2012）层**：1820／1911／1926／1990／1997 等 | `chgis.v5_*` | 29 | 69,780 |
| D3 | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_pref_pgn_utf.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_pref_pts_utf.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_cnty_pts_utf.zip` | V5 **时序**（府面／府点／县点） | `chgis.v5_time_*` | 3 | 16,975 |
| D4 | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/` 下 v5_gns 30 省分片（`v5_gns_<省名>_gbk.zip` ×30，usedata 内实收 30 件） | **GNS 美军地名库**中国部分，30 省分片并装一表 | `chgis.v5_gns` | 1 | 130,665 |
| E | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db`（837.2MB） | CBDB 2024-02 官方 SQLite 之 **ADDR_XY**：人物↔地点坐标桥 | `public.addr_xy` | 1 | 19,249 |
| F | `/mnt/wd61workmetadata/usedata/chgis-v6/China_Periods_ReignDates.zip`（原树＝`/mnt/wd61workmetadata/chgis-v6/`，家中旧库） | **中国历史纪年**：纪年表／重大分期表／字段说明 | `chgis.china_chron` 等 | 3 | 749 |
| G | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/E1FHML/DEM_QGIS-3_REVISED.zip` | CHGIS **V5 真高程 DEM**（GeoTIFF 栅格） | `chgis.dem` | 1 | 3,358（栅格瓦片） |
| H | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/29302/v5_Hartwell_2010.zip` | **Hartwell 宋辽金历史 GIS**（包内 352 图层，同构归并） | `chgis.hartwell_*` | 9 | 21,497 |
| I | 17 个专题目录（原文记"14 专题树"；**usedata 内实收 17 目录／25 件**）：<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/SB8ZTM/`（明驿路驿站，2 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/VJHPVK/`（茶马古道，3 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/2CVTR0/`（日本德川，4 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/JIISNB/`（高铁，2 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/W6PFXR/`（藏传寺院 TBRC，2 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/J5U79Z/`（天然气管线，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/25413/`（DCW 数字世界地图，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/KUFJTG/`（北京史迹，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/5RUXK8/`（明代卫所，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/VAYEUZ/`（BGIS，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PRCLTU/`（西藏地名对照，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PJ8D45/`（图幅索引，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/G9RKCW/`（科兹洛夫 1899，1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ABPR9F/`（1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/E7HDYD/`（1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ELTD3L/`（1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/LVYYZC/`（1 件）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/RXP4AA/`（1 件）<br>〔**2026-09-28 补正**：原文所列 `WP1ASG`（西藏乡镇）**不在 usedata**——账面状态 `SKIP_DUP`，同内容已由 D2 装入 `chgis.v5_2009_tibet_twns`，故按"只收实际被导入者"之规程不收〕 | 各**专题矢量**集 | `chgis.ming_routes_2016` 等＋`harv.*` | 30 | 219,063 |
| J | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/H3OB28/tgaz_bak_2018.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/3KAHBT/tan_atlas_gbk_mar01.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/I4UIKV/ngia_dsg_codes_2017-03-15.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/I4UIKV/nima_feat_desig_apr02.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/EOH3FV/1999_gb_pop_uce.xls`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/SK7KGK/GB_91_HZ_040201_UTF8.tab`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/MI56KU/2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PRCLTU/THDL_ADMareas_rev022401.xls` | **TGAZ 时序地名库**（MySQL dump 33 表：spelling 24.5 万等）＋谭其骧图集名称表＋GNS／NIMA 特征码表＋1999 县级人口＋1991 国标政区码＋2001 工作坊索引＋THDL 西藏政区 | `harv.tgaz_*` 等＋`public.china_pop_1999_county`／`gb_91_codes`／`thdl_tibet_adm_areas` | 41 | 1,065,728 |
| K | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip`（238.9MB）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip`（339.1MB）<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip`（608.2MB） | CHGIS **V2（2003）／V3（2005）／V4（2007）三代档案**：旧代层＋随附关系库抽取（`v2db_/v3db_/v4db_*`）＋V2 DEM 六瓦片 | `chgis.v2_*`／`v3_*`／`v4_*` | 146 | 1,254,873 |
| L | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/23340/1926_China_Atlas.zip`<br>`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/H4WVUP/beijing_1875.zip`（北京 1875）<br>俄测地图系列：`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ABPR9F/`、`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/LVYYZC/`、`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/RXP4AA/`、`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/E7HDYD/`、`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/ELTD3L/`、`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/G9RKCW/`<br>gtopo30：`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip`<br>v3_dem_all：`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip`<br>（L 系账面含 `L`／`L-FIX`／`L-FIX2` 三腿，usedata 内实收 **9 件／8 目录**；`ABPR9F` 等目录之件亦为 I 组矢量之源，**同一物理件两处共用**） | **历史地图扫描配准**（普尔热瓦尔斯基／科兹洛夫／波德布内／布雷茨施耐德诸图，栅格）＋DEM 补瓦 | `harv.ras_*`＋`chgis.dem_*`／`v3_dem_topo30` | 28 | 21,328 |

**第二批小计：309 表／2,888,570 行。**（**2026-09-28 补正**：原 2,884,485 行；FIX10 **＋4,099**〔K 组 `v4_gns` 广西〕、FIX11 **−14**〔K 组 8／J 组 5／F 组 1〕，表数 309 不变。对账 recon **1,770** 行中另 310 个"目标名"含 1 个多层占位名；其余为 SKIP／FIX 类事件行，见 §四。）

## 四、数据库与文件的对应关系（怎么查）

1. **命名即对应**：表名≈源文件名——`v6_1820_cnty_pts_utf.zip` → `chgis.v6_1820_cnty_pts`；`tgaz_spelling`（dump 内表）→ `harv.tgaz_spelling`。前缀规则：`chgis.v2_…v6_`＝CHGIS 第几代；`*_db_/v?db_`＝档案随附关系库；`harv.ras_`＝扫描栅格；`harv.tgaz_`＝TGAZ；`public.*`＝CBDB 原名照旧＋独立小表。
2. **任意一表反查源，四步**（2026-09-28 由三步增为四步：末步落到权威源目录之绝对路径）：表名 → `/root/xiangrugu/ops/harvard/load-b2/recon_b2a.tsv`（target 列：何文件→何表、行数、状态、注记）→ `/root/xiangrugu/ops/harvard/load-b2/src_paths.tsv`（src→`nas_path` 列＋档案内层成员链，1,770 行未解析 0）→ **`/mnt/wd61workmetadata/usedata` ＋ `nas_path` ＝ 该源件在权威数据源目录内之绝对路径**（详 §七）。过程与裁决＝`docs/cbdb-load.md` §15（第二批）／§12–13（首批）。（**2026-09-28 补注**：① recon 现 **1,770 数据行**，惟其中 **887 行系同一事件之重复记录**，按 `(leg,src_zip,target,status,src_fc)` 五键去重后为 **883**——**按表名反查取其一即可，求和前必须先去重**；② recon 有 **4 个幻影 target**〔`harv.china_gas_2013` 系拆表父名而非真表、`117表`／`同表`／`cbdb库` 系注记文字误入 target 列〕，按此四名反查会落空。二者详 `docs/bugs.md` B-08。）
3. **行数口径**：本表＝**库内实数**（VACUUM ANALYZE 后 `n_live_tup`，2026-09-26 复测）。recon 逐行 pg_count 之和＝**装载事件累计**（同表多源对证／编码修复重载各记一行），大于库内数——两者皆真，口径不同。（**2026-09-28 复测**：FIX10／FIX11 后全库 **8,584,097 行／395 表／4,771 MB**，本表数字已随之更新。另 recon 之**计数基准有四种并存**——原始行 1,770／五键去重 883／按 target／按源件，**引用须注明基准**，详 `docs/bugs.md` B-08。）
4. **没装的部分（同样有账）**：源目录 65 树中 **24 树未触碰**——版本堆 5（存档不装裁决）／软件 2／文档树 7／同内容已装 7（sha 字节级实证）／GBK 编码变体 2（一份制）／**缺口挂账 1**（TI8DFI 多语言特征类型对照表，候令）＝`/root/xiangrugu/ops/harvard/load-b2/tree_coverage.tsv` 全对账。触碰而未装者逐行记 SKIP（重复 265／纯格式 532／编码变体 67／无地理 64 等）于 recon。（**2026-09-28 补正**：① 上列 SKIP 四数系 recon **原始行**基准；`docs/cbdb-load.md` §15① 之 110／186／65／55 则系**按 target／去重行**基准（实测：`SKIP_DUP` 按 target＝110、按源件＝131、原始行＝265）——**两书数字皆可复现，惟基准不同且均未声明**，引用须注明，详 B-08。② "**逐行记 SKIP**"一句对**广西 GNS 件不成立**：`v4_gns_guangxi_gbk.zip.zip` 因双重后缀被三处 `$` 锚正则漏掉、又被 `b2b3.py:145` 主路径让路跳过，**两条路都不入，故连 SKIP 行都没留下**——4,099 条静默漏装，已于 FIX10 补装并八项验收，详 B-05。③ §三"表数"栏中 **`D4`／`I`／`K`／`L` 四组不能由 recon 机械复现**〔D4 之 30 个 target 无一实表（真表唯 `chgis.v5_gns`）、I 组含 1 个幻影父名 `harv.china_gas_2013`、K 组实表 147 而账面 146、L 组栅格按组记仅 11 个 target 对应 28 表〕，余 `D1/D2/D3/E/F/G/H/J` 八组**精确相符**；该栏系人工归组计数，详 I-01。）

## 五、审计件（`/root/xiangrugu/ops/harvard/load-b2/`，41 件，依政策不入 git）

`/root/xiangrugu/ops/harvard/load-b2/recon_b2a.tsv`（**1,770** 行逐文件对账总账；原 1,757，2026-09-28 增 FIX10 4 行＋FIX11 9 行）· `/root/xiangrugu/ops/harvard/load-b2/src_paths.tsv`（行→NAS 路径映射，**1,770 行已同步**，表尾附两条前向补正注）· `/root/xiangrugu/ops/harvard/load-b2/tree_coverage.tsv`（65 树＋目录覆盖审计）· `/root/xiangrugu/ops/harvard/load-b2/b2*.py` 22 支装载脚本（**当时硬编码源路径＝历史口径之权威**；惟该路径＝`/mnt/nas-mirror/`，2026-09-27 起项目读写皆禁，**重跑须换直挂** `/mnt/wd61workmetadata/`——本轮已改 `/root/xiangrugu/ops/harvard/load-b2/b2b3.py`／`/root/xiangrugu/ops/harvard/load-b2/b2fix2.py`／`/root/xiangrugu/ops/harvard/load-b2/b2fix4.py` 三支且改处留原值注释，余 12 支候令，详 B-09。**2026-09-28 再补正（权威源目录既立，见 §七）**："重跑须换直挂"一句应再分两种用途——**只重装数据**者改指 `/mnt/wd61workmetadata/usedata/`（实测：脚本内 **6 条**硬编码路径常量映射后**逐条存在、缺 0**；**11 支**纯 `os.path.join` 指名取件者行为全等）；**须复现全量对账**（含 `SKIP_*` 记账与 `tree_coverage.tsv` 65 树审计）者**仍须读原树** `/mnt/wd61workmetadata/harvard-full/`——因 usedata 按规程只收被导入者，**12 支含目录枚举**之脚本（`listdir`／`glob`／`walk` 共 **39 处**）在其下只见**子集**（实例：`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/` **65 件** vs 原树同目录 **106 件**，差 **41 件**皆 `SKIP_*` 类），**数据不缺而 SKIP 账面无从复现**，二者不可混（详 B-09 补正））· `/root/xiangrugu/ops/harvard/load-b2/resolve_src.py`（映射表生成器，可复跑）· `/root/xiangrugu/ops/harvard/load-b2/usedata_b2_manifest.tsv`（**173 行**；2026-09-28 拷入 usedata 之清单，两列＝源绝对路径⇥目标绝对路径）· `/root/xiangrugu/ops/harvard/load-b2/usedata_b2_copy_report.tsv`（**173 行**；拷后逐件核验报告，四列＝状态⇥sha256⇥字节⇥目标绝对路径，**173 行全 `OK`**）。

## 六、2026-09-28 补正明细（FIX10 广西补装＋FIX11 表头去污）

> 依 R-04：上文旧数字**一律不回改**，改动处皆已就地加〔2026-09-28 补正／补注〕；本节为逐表明细之唯一展开处。根因、验收八项与回滚线详 `docs/bugs.md` B-05／B-06；余缺陷候令项详 B-07…B-10 与 I-01…I-03。

**FIX10（补装，＋4,099 行）**

| 源件 | 导入到 | 变动 |
|---|---|---|
| `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `shapefiles/v4_gns_guangxi_gbk.zip.zip`（315,585 B，**全 212 档案中唯一之双重后缀件**） | `chgis.v4_gns` | 126,566 → **130,665**（＋4,099 广西行；`prov`／`prov_py` distinct 29 → **30**；88 县、3,696 地名） |

**FIX11（表头去污，−14 行非数据行、47 列正名）**

| 表 | 源件 | 行数 | 正名 | 备注 |
|---|---|---|---:|---|
| `chgis.v4_data_dictionary` | /mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `metadata/v4_data_dictionary.xlsx` | 65 → **64** | 3 | ＝孪生 `v4db_v4_data_dictionary` **64** |
| `chgis.xtra_change_types` | /mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `metadata/xtra_change_types.xlsx` | 26 → **25** | 3 | |
| `chgis.xtra_contributors` | /mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `metadata/xtra_contributors.xlsx` | 6 → **5** | 3 | ＝`v2db_xtra_contrib_table`／`v3db_`／`v4db_xtra_contributors` **5**（四方全等） |
| `chgis.xtra_geo_source` | /mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `metadata/xtra_geo_source.xlsx` | 7 → **6** | 3 | |
| `chgis.gazetteers_beta` | /mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `Gazetteers.Beta.xls` | 963 → **959** | 10 | 删标题行＋2 空行＋表头行；重名列机械加 `_2`（`Title/Author1/Author2/Year` 各二系**中英并列**，不臆造语义）；余 **55** 列源表头本空 |
| `chgis.china_chron_fields` | `/mnt/wd61workmetadata/usedata/chgis-v6/China_Periods_ReignDates.zip` ⊃ `china_chron/china_chron_fields.xls` | 21 → **20** | 2 | `field3` 源表头空，**不动** |
| `public.thdl_tibet_adm_areas` | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PRCLTU/THDL_ADMareas_rev022401.xls` | 166 → **165** | 17 | 余 **11** 列源表头空，**不动** |
| `public.china_pop_1999_county` | `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/EOH3FV/1999_gb_pop_uce.xls`（层 `adm3`） | 2,361 → **2,357** | 6 | 删 3 行版权前言＋1 行表头（**前言全文存证于 B-06**，可原样插回） |

**验收（两批共）**：八表**数据行 md5 修前后逐一一致**（真数据分毫未动）；`v4_gns` 旧行指纹**三次核对全同**（`126,566｜sum(ufi) −220,777,979,725｜sum(uni) −292,630,565,842`）；新行与 `v5_gns` 广西行按 `(ufi,uni)` 交集 **4,099／4,099 全等**、撞旧行 0、自重复 0；新行几何全 `POINT`／SRID `4326`、空几何 0、extent `104.483–111.967E／20.900–26.250N`；残余非 ASCII 仅 **5 个合法变音字母**（`ü`41／`ô`3／`è`1／`ê`1／`ù`1）、`nm_ascii` 零非 ASCII；全库 **395 表／8,584,097 行／4,771 MB**、无效索引 **0**；真列名查询五例全通。

**遗留候令（皆已入账，未动手）**：① **67 个残余 `fieldN` 列实测全零数据**（`thdl` 11／`china_chron` 1／`gazetteers_beta` 55），可 `DROP COLUMN` 清理（I-02）；② `v4_gns`／`v5_gns` 之 `prov_py` **不可用于筛省**（海南 1,358＋北京 1,143＝2,501 行空值，源 DBF 本无该字段；另浙江 18 行作 `Zhejiang`）——可靠列为 `prov`（B-07）；③ 两表仅存安徽前缀 ID 列，余 29 省 `*_INT_ID`／`*_EXT_ID` 被 `-append` 按名映射**静默丢弃**（GNS 全局键 `ufi`／`uni` 俱在，不致命）（B-10）；④ 12 支脚本仍硬编码禁触之 `/mnt/nas-mirror/`（B-09）。

## 七、权威数据源目录 `/mnt/wd61workmetadata/usedata/`（2026-09-28 用户令设立）

> **令文照录**：「我现在要你把我们导入到pg32b里的源数据移动到/mnt/wd61workmetadata/usedata目录里。这个目录就是我们pg32b导入的权威数据源。同时你根据这个要求修订data-sources.md文档。目录与文件一定用绝对路径描述。」
>
> **纪律照录**：「我们下载下来的源数据决不能修改。我们导入到pg32b的数据源放到/mnt/wd61workmetadata/usedata里。」

**一、目录构成（2026-09-28 实测）**

| 绝对路径 | 立日 | 布局 | 件数 | 校验账（绝对路径） |
|---|---|---|---:|---|
| `/mnt/wd61workmetadata/usedata/harvard/` | 2026-09-24 | 语义名（`cbdb/`·`chgis/`·`tab/`） | 15 | `/mnt/wd61workmetadata/usedata/harvard/SHA256SUMS` |
| `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/` | 2026-09-28 | **镜像源树**（36 个 DOI 目录） | 172 | `/mnt/wd61workmetadata/usedata/SHA256SUMS-b2` |
| `/mnt/wd61workmetadata/usedata/chgis-v6/` | 2026-09-28 | 镜像源树 | 1 | `/mnt/wd61workmetadata/usedata/SHA256SUMS-b2` |
| 两份说明书 | 2026-09-24／27 | `/mnt/wd61workmetadata/usedata/harvard/README.md`、`/mnt/wd61workmetadata/usedata/README-b2.md` | 2 | — |
| **合计** | | | **190** | **3.2 GB** |

**二、换算规则（唯一，机械可核）**：`usedata 内绝对路径 ＝ /mnt/wd61workmetadata/usedata ＋ /root/xiangrugu/ops/harvard/load-b2/src_paths.tsv 之 nas_path 列`。前缀一换即得，零臆造命名——此即第二批取"镜像源树布局"而非语义分组之故（一档案常服务多腿，如 `/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip` 同为 I／K／L 三组之源，语义归组须臆造取舍）。

**三、收录范围之规程**：只收**实际被导入者**——由账面 1,770 行按装载状态筛出（`OK`／`REPAIRED`／`FIXED`／`SPLIT_OK`／`MULTI_LAYER`／`ROUTED`／`DONE`／`AS_IS`），**`SKIP_*` 类（触碰而未装）一律不收**（例：`WP1ASG` 西藏乡镇＝`SKIP_DUP`，同内容已由 D2 装入 `chgis.v5_2009_tibet_twns`，故其件不在目录内）；另按首批体例一并收入各 DOI 目录内之**随附账 48 件**（README／EULA／许可／数据字典／说明 PDF），使许可条款随数据同行（CHGIS V2–V6 各代 EULA 明载**学术用、禁商用、禁再分发**；同一 NAS 内之选辑副本非再分发）。`/mnt/wd61workmetadata/chgis-v6/` 之 5 件随附账首批已收于 `/mnt/wd61workmetadata/usedata/harvard/chgis/`，故第二批不重拷。

**四、拷入而非搬移（依纪律裁定）**：令文用"移动"，惟搬移会改动下载树、与账面 1,770 行之路径记录脱钩，且直违「下载下来的源数据决不能修改」一句，故**取拷入**（用户 2026-09-28 核准，并循 2026-09-24 首批既定规程「copy 一份……原来那些就当是下载的原数据备份」）。下载原树 `/mnt/wd61workmetadata/harvard-full/`（仍 **65** 棵 DOI 树）与 `/mnt/wd61workmetadata/chgis-v6/` **完整保留为只读备份**。

**五、核验（2026-09-28 实测）**：逐件 `cp -p`（存原时间戳）后**两端各算 sha256**——目标端 **173/173 相符**；**源端亦 173/173 相符 → 下载原树内容零改动**；逐件体积 **0 缺失、0 不符**；`cd /mnt/wd61workmetadata/usedata && sha256sum -c SHA256SUMS-b2` → **173 行全"成功"**、零失败零警告；首批子树 `/mnt/wd61workmetadata/usedata/harvard/` 仍 **15 件未被触动**。执行处＝32 主机（数据主机、与 NAS 61 同网段；`/mnt/nas-mirror/` 已禁触，读写皆走直挂）。

**六、逐件清单之权威**：`/mnt/wd61workmetadata/usedata/README-b2.md`（173 行表，每件含 usedata 绝对路径、大小、sha256 前 16 位、原树绝对路径、装数去向）。本文只列**组级**（§三）与**目录级**（本节），不复制逐件清单（R-04 单一源）。

**七、日后增补之规程**：① 新装数据前，先按上述规程把源件拷入本目录；② 拷后两端各算 sha256 比对，新行追加于 `/mnt/wd61workmetadata/usedata/SHA256SUMS-b2`（旧行不回改）；③ **装载脚本之源路径常量一律改指本目录，不再指向下载原树**——此项**待行**：`/root/xiangrugu/ops/harvard/load-b2/` 下 22 支脚本，3 支已改指直挂 `/mnt/wd61workmetadata/`、余 12 支仍指禁触之 `/mnt/nas-mirror/`，**皆尚未改指 `/mnt/wd61workmetadata/usedata/`**（详 `docs/bugs.md` B-09）；④ 同步修订本文 §三／§七 与 recon／src_paths；⑤ **严禁修改本目录内任何文件之内容**（用户纪律），如需更正另存新件并记账。
