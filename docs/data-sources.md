# data-sources.md —— pg32b 数据来源对照表（人读摘要）

> **定位（2026-09-26 用户令开设："专门做一个文档……简单直接，让人一目了然"）**：一页说清三件实事——① 以 32 主机 `/mnt/wd61workmetadata/` 下**什么文件**为依据，导入到了**哪个位置**的数据库；② 这些文件**来自哪里、记录了什么**；③ 数据库与文件的**对应关系**。
> 本表系**摘要层**（R-04）：逐文件穷举账（**1,770 行**；原 1,757 行，2026-09-27 FIX10／FIX11 批增 13 行）的权威在 `docs/cbdb-load.md` §13/§15 与 `ops/harvard/load-b2/` 审计件（recon_b2a.tsv／src_paths.tsv／tree_coverage.tsv），本表数字全部由彼处机械汇总＋库内实测而来，口径注记见 §四。

## 一、两端与总账

| | |
|---|---|
| **数据源目录** | 32 主机 `/mnt/wd61workmetadata/`（NAS 61 共享之直挂）。装载实跑经同机每日镜像 `/mnt/nas-mirror/61/workmetadata/` 读取——**同一份数据的两条路径**（实测：两侧同文件 sha256 相同、65 个 DOI 树同数）。**2026-09-27 用户裁决：nas-mirror＝用户自建之 32 本地 NAS 备份区，项目禁用（读写皆不碰）——此后项目唯一读取路径＝直挂**；前句"实跑经镜像盘"系两批装载之史实（与直挂字节级同一：文件数 16,822＝同、纯文件字节和 21,492,791,579＝同、rsync 干跑零差异，09-27 复测），本表路径口径＝用户所指直挂路径，恰即镜像盘之同步源（裁决权威＝`docs/codemap.md` §2 专行） |
| **导入目的地** | 32 主机（192.168.3.32）Docker 容器 **pg32b**（端口 5433），PostgreSQL 18.6＋PostGIS 3.6.4，数据库 **cbdb** |
| **库内四个 schema** | `public`＝CBDB 人物传记库＋独立小表；`chgis`＝CHGIS 历史地理信息系统（矢量＋栅格）；`harv`＝哈佛 Dataverse 各专题集；`ogr_system_tables`＝GDAL 自建之元数据表（1 表 184 行）。〔**2026-09-27 补正**：原书"三个 schema"，与下行为总账自列之 `ogr_system_tables` 及 `docs/pg32b.md` §13"chgis 211＋harv 97＋public 86＋ogr_system_tables 1＝395"自相矛盾，今从实测作**四个**〕 |
| **总账（库内实数）** | **395 张表／8,584,097 行／4,771 MB**。＝首批 84 表 5,686,842 行（**本批未动**）＋第二批 309 表 2,888,570 行＋系统 2 表 8,685 行（PostGIS `spatial_ref_sys` 8,501＋`ogr_system_tables` 184，非导入数据）。〔**2026-09-27 补正**：原书 8,580,012 行／4,770 MB／第二批 2,884,485 行。本批 FIX10 补装 `v4_gns` 广西 **＋4,099**、FIX11 删八表非数据行 **−14**，净 **＋4,085**；表数 395 不变。逐表明细见 §六〕 |
| **两批** | 首批 2026-09-24（工作集 7 件）；第二批 2026-09-25～26（"能装尽装"全量，12 组） |

## 二、首批（2026-09-24）：`usedata/harvard/` 工作集 7 件

工作集＝用户令设立的"在用数据"选辑副本（原树只读备份）；13 件 sha256 双端核验全同。路径相对 `/mnt/wd61workmetadata/`。

| 源文件 | 来自哪里 · 记录什么 | 导入到 | 行数 |
|---|---|---|---:|
| `usedata/harvard/cbdb/cbdb_20260919.sqlite3` | CBDB 项目官方 HuggingFace 滚动发布，2026-09-19 构建（586MB）。**中国历代人物传记资料库**：66 万人物＋任职／亲属／社交／著作／地址等 | `public.*` 78 张表（表名照旧；**2026-09-27 补注**：PostgreSQL 折叠标识符大小写，sqlite 之 `BIOG_MAIN` 入库为 `biog_main`，"照旧"指词形不指大小写） | 5,623,075（＝官方值，验收相符） |
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
| F | `chgis-v6/China_Periods_ReignDates.zip`（家中旧库原树） | **中国历史纪年**：纪年表／重大分期表／字段说明 | `chgis.china_chron` 等 | 3 | 749 |
| G | `DVN/E1FHML/DEM_QGIS-3_REVISED.zip` | CHGIS **V5 真高程 DEM**（GeoTIFF 栅格） | `chgis.dem` | 1 | 3,358（栅格瓦片） |
| H | `DVN/29302/v5_Hartwell_2010.zip` | **Hartwell 宋辽金历史 GIS**（包内 352 图层，同构归并） | `chgis.hartwell_*` | 9 | 21,497 |
| I | `DVN/` 14 专题树：SB8ZTM 明驿路驿站／VJHPVK 茶马古道／2CVTR0 日本德川／J5U79Z 天然气管线／JIISNB 高铁／W6PFXR 藏传寺院 TBRC／25413 DCW 数字世界地图／KUFJTG 北京史迹／5RUXK8 明代卫所／VAYEUZ BGIS／PRCLTU 西藏地名对照／PJ8D45 图幅索引／G9RKCW 科兹洛夫 1899／WP1ASG 等 | 各**专题矢量**集 | `chgis.ming_routes_2016` 等＋`harv.*` | 30 | 219,063 |
| J | `DVN/H3OB28/tgaz_bak_2018.zip`＋`3KAHBT`＋`I4UIKV`＋`EOH3FV`＋`SK7KGK`＋`MI56KU` | **TGAZ 时序地名库**（MySQL dump 33 表：spelling 24.5 万等）＋谭其骧图集名称表＋GNS／NIMA 特征码表＋1999 县级人口＋1991 国标政区码＋2001 工作坊索引＋THDL 西藏政区 | `harv.tgaz_*` 等＋`public.china_pop_1999_county`／`gb_91_codes`／`thdl_tibet_adm_areas` | 41 | 1,065,728 |
| K | `DVN/ZZKZ6U/CHGIS_V2.zip`＋`DVN/HIMIVE/V3_Data_Archive.zip`＋`DVN/PDGOZ0/V4_Data_Archive.zip` | CHGIS **V2（2003）／V3（2005）／V4（2007）三代档案**：旧代层＋随附关系库抽取（`v2db_/v3db_/v4db_*`）＋V2 DEM 六瓦片 | `chgis.v2_*`／`v3_*`／`v4_*` | 146 | 1,254,873 |
| L | `DVN/23340/1926_China_Atlas.zip`、`H4WVUP`（北京 1875）、`ABPR9F`／`LVYYZC`／`RXP4AA`／`E7HDYD`／`ELTD3L`／`G9RKCW`（俄测地图系列）、`PDGOZ0` gtopo30、`HIMIVE` v3_dem_all | **历史地图扫描配准**（普尔热瓦尔斯基／科兹洛夫／波德布内／布雷茨施耐德诸图，栅格）＋DEM 补瓦 | `harv.ras_*`＋`chgis.dem_*`／`v3_dem_topo30` | 28 | 21,328 |

**第二批小计：309 表／2,888,570 行。**（**2026-09-27 补正**：原 2,884,485 行；FIX10 **＋4,099**〔K 组 `v4_gns` 广西〕、FIX11 **−14**〔K 组 8／J 组 5／F 组 1〕，表数 309 不变。对账 recon **1,770** 行中另 310 个"目标名"含 1 个多层占位名；其余为 SKIP／FIX 类事件行，见 §四。）

## 四、数据库与文件的对应关系（怎么查）

1. **命名即对应**：表名≈源文件名——`v6_1820_cnty_pts_utf.zip` → `chgis.v6_1820_cnty_pts`；`tgaz_spelling`（dump 内表）→ `harv.tgaz_spelling`。前缀规则：`chgis.v2_…v6_`＝CHGIS 第几代；`*_db_/v?db_`＝档案随附关系库；`harv.ras_`＝扫描栅格；`harv.tgaz_`＝TGAZ；`public.*`＝CBDB 原名照旧＋独立小表。
2. **任意一表反查源，三步**：表名 → `ops/harvard/load-b2/recon_b2a.tsv`（target 列：何文件→何表、行数、状态、注记）→ `ops/harvard/load-b2/src_paths.tsv`（src→NAS 完整路径＋档案内层成员链，1,770 行未解析 0）。过程与裁决＝`docs/cbdb-load.md` §15（第二批）／§12–13（首批）。（**2026-09-27 补注**：① recon 现 **1,770 数据行**，惟其中 **887 行系同一事件之重复记录**，按 `(leg,src_zip,target,status,src_fc)` 五键去重后为 **883**——**按表名反查取其一即可，求和前必须先去重**；② recon 有 **4 个幻影 target**〔`harv.china_gas_2013` 系拆表父名而非真表、`117表`／`同表`／`cbdb库` 系注记文字误入 target 列〕，按此四名反查会落空。二者详 `docs/bugs.md` B-08。）
3. **行数口径**：本表＝**库内实数**（VACUUM ANALYZE 后 `n_live_tup`，2026-09-26 复测）。recon 逐行 pg_count 之和＝**装载事件累计**（同表多源对证／编码修复重载各记一行），大于库内数——两者皆真，口径不同。（**2026-09-27 复测**：FIX10／FIX11 后全库 **8,584,097 行／395 表／4,771 MB**，本表数字已随之更新。另 recon 之**计数基准有四种并存**——原始行 1,770／五键去重 883／按 target／按源件，**引用须注明基准**，详 `docs/bugs.md` B-08。）
4. **没装的部分（同样有账）**：源目录 65 树中 **24 树未触碰**——版本堆 5（存档不装裁决）／软件 2／文档树 7／同内容已装 7（sha 字节级实证）／GBK 编码变体 2（一份制）／**缺口挂账 1**（TI8DFI 多语言特征类型对照表，候令）＝`tree_coverage.tsv` 全对账。触碰而未装者逐行记 SKIP（重复 265／纯格式 532／编码变体 67／无地理 64 等）于 recon。（**2026-09-27 补正**：① 上列 SKIP 四数系 recon **原始行**基准；`docs/cbdb-load.md` §15① 之 110／186／65／55 则系**按 target／去重行**基准（实测：`SKIP_DUP` 按 target＝110、按源件＝131、原始行＝265）——**两书数字皆可复现，惟基准不同且均未声明**，引用须注明，详 B-08。② "**逐行记 SKIP**"一句对**广西 GNS 件不成立**：`v4_gns_guangxi_gbk.zip.zip` 因双重后缀被三处 `$` 锚正则漏掉、又被 `b2b3.py:145` 主路径让路跳过，**两条路都不入，故连 SKIP 行都没留下**——4,099 条静默漏装，已于 FIX10 补装并八项验收，详 B-05。③ §三"表数"栏中 **`D4`／`I`／`K`／`L` 四组不能由 recon 机械复现**〔D4 之 30 个 target 无一实表（真表唯 `chgis.v5_gns`）、I 组含 1 个幻影父名 `harv.china_gas_2013`、K 组实表 147 而账面 146、L 组栅格按组记仅 11 个 target 对应 28 表〕，余 `D1/D2/D3/E/F/G/H/J` 八组**精确相符**；该栏系人工归组计数，详 I-01。）

## 五、审计件（`ops/harvard/load-b2/`，39 件，依政策不入 git）

`recon_b2a.tsv`（**1,770** 行逐文件对账总账；原 1,757，2026-09-27 增 FIX10 4 行＋FIX11 9 行）· `src_paths.tsv`（行→NAS 路径映射，**1,770 行已同步**，表尾附两条前向补正注）· `tree_coverage.tsv`（65 树＋目录覆盖审计）· `b2*.py` 22 支装载脚本（**当时硬编码源路径＝历史口径之权威**；惟该路径＝`/mnt/nas-mirror/`，2026-09-27 起项目读写皆禁，**重跑须换直挂** `/mnt/wd61workmetadata/`——本轮已改 `b2b3.py`／`b2fix2.py`／`b2fix4.py` 三支且改处留原值注释，余 12 支候令，详 B-09）· `resolve_src.py`（映射表生成器，可复跑）。

## 六、2026-09-27 补正明细（FIX10 广西补装＋FIX11 表头去污）

> 依 R-04：上文旧数字**一律不回改**，改动处皆已就地加〔2026-09-27 补正／补注〕；本节为逐表明细之唯一展开处。根因、验收八项与回滚线详 `docs/bugs.md` B-05／B-06；余缺陷候令项详 B-07…B-10 与 I-01…I-03。

**FIX10（补装，＋4,099 行）**

| 源件 | 导入到 | 变动 |
|---|---|---|
| `DVN/PDGOZ0/V4_Data_Archive.zip` ⊃ `shapefiles/v4_gns_guangxi_gbk.zip.zip`（315,585 B，**全 212 档案中唯一之双重后缀件**） | `chgis.v4_gns` | 126,566 → **130,665**（＋4,099 广西行；`prov`／`prov_py` distinct 29 → **30**；88 县、3,696 地名） |

**FIX11（表头去污，−14 行非数据行、47 列正名）**

| 表 | 源件 | 行数 | 正名 | 备注 |
|---|---|---|---:|---|
| `chgis.v4_data_dictionary` | V4 ⊃ `metadata/v4_data_dictionary.xlsx` | 65 → **64** | 3 | ＝孪生 `v4db_v4_data_dictionary` **64** |
| `chgis.xtra_change_types` | V4 ⊃ `metadata/xtra_change_types.xlsx` | 26 → **25** | 3 | |
| `chgis.xtra_contributors` | V4 ⊃ `metadata/xtra_contributors.xlsx` | 6 → **5** | 3 | ＝`v2db_xtra_contrib_table`／`v3db_`／`v4db_xtra_contributors` **5**（四方全等） |
| `chgis.xtra_geo_source` | V4 ⊃ `metadata/xtra_geo_source.xlsx` | 7 → **6** | 3 | |
| `chgis.gazetteers_beta` | V4 ⊃ `Gazetteers.Beta.xls` | 963 → **959** | 10 | 删标题行＋2 空行＋表头行；重名列机械加 `_2`（`Title/Author1/Author2/Year` 各二系**中英并列**，不臆造语义）；余 **55** 列源表头本空 |
| `chgis.china_chron_fields` | `chgis-v6/China_Periods_ReignDates.zip` ⊃ `china_chron/china_chron_fields.xls` | 21 → **20** | 2 | `field3` 源表头空，**不动** |
| `public.thdl_tibet_adm_areas` | `DVN/PRCLTU/THDL_ADMareas_rev022401.xls` | 166 → **165** | 17 | 余 **11** 列源表头空，**不动** |
| `public.china_pop_1999_county` | `DVN/EOH3FV/1999_gb_pop_uce.xls`（层 `adm3`） | 2,361 → **2,357** | 6 | 删 3 行版权前言＋1 行表头（**前言全文存证于 B-06**，可原样插回） |

**验收（两批共）**：八表**数据行 md5 修前后逐一一致**（真数据分毫未动）；`v4_gns` 旧行指纹**三次核对全同**（`126,566｜sum(ufi) −220,777,979,725｜sum(uni) −292,630,565,842`）；新行与 `v5_gns` 广西行按 `(ufi,uni)` 交集 **4,099／4,099 全等**、撞旧行 0、自重复 0；新行几何全 `POINT`／SRID `4326`、空几何 0、extent `104.483–111.967E／20.900–26.250N`；残余非 ASCII 仅 **5 个合法变音字母**（`ü`41／`ô`3／`è`1／`ê`1／`ù`1）、`nm_ascii` 零非 ASCII；全库 **395 表／8,584,097 行／4,771 MB**、无效索引 **0**；真列名查询五例全通。

**遗留候令（皆已入账，未动手）**：① **67 个残余 `fieldN` 列实测全零数据**（`thdl` 11／`china_chron` 1／`gazetteers_beta` 55），可 `DROP COLUMN` 清理（I-02）；② `v4_gns`／`v5_gns` 之 `prov_py` **不可用于筛省**（海南 1,358＋北京 1,143＝2,501 行空值，源 DBF 本无该字段；另浙江 18 行作 `Zhejiang`）——可靠列为 `prov`（B-07）；③ 两表仅存安徽前缀 ID 列，余 29 省 `*_INT_ID`／`*_EXT_ID` 被 `-append` 按名映射**静默丢弃**（GNS 全局键 `ufi`／`uni` 俱在，不致命）（B-10）；④ 12 支脚本仍硬编码禁触之 `/mnt/nas-mirror/`（B-09）。
