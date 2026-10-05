# 正式库 cbdb 全表「出处」核查报告

> 方法：只读枚举 cbdb 全部 schema 与表（395 关系 + 4 PostGIS 视图），逐表对照 usedata 源文件目录与本项目 sources.yaml（868 源），判定每张表是否有源文件（出处），并给出源文件所在位置。全程未写、未删、未动 cbdb 一个字。

## 一、结论总览

老库 cbdb 共 **395 张表 + 4 个 PostGIS 系统视图**，分四类：

| 分类 | 张数 | 含义 |
|---|---|---|
| **A 有源·已在我 868 清单** | **283** | 源文件已彩排通过；老库只是合并/改名/去掉了编码双版本 |
| **B 有源·需新增载具** | **107** | 源文件在 usedata，但我 868 只覆盖了偏向量，这三类没装 |
| **C 无源·应避免** | **4** | 无独立源文件：派生表/测试废表/软件自建表 |
| PostGIS 系统表+视图 | 1 表 + 4 视图 | 扩展自带，随库重建，非数据 |

**「没有出处」的只有 4 张表**（见下），其余 390 张都能在 usedata 找到源。

## 二、A 类（283 张，源已核，无需补装）

- **CBDB sqlite**：78 张（`public.*`，源 `harvard/cbdb/cbdb_20260919.sqlite3`）。
- **shapefile (chgis)**：157 张（源在各 Data_Archive/Hartwell/版本 zip 内，老库把 `_gb/_utf/_gbk` 编码双版本与 v2–v6 各版合并/改名成单张）。
- **shapefile/mapinfo 改名 (harv)**：42 张（老库另起了 `russ_*/przh_*/ras_*` 等短名，且与 chgis 侧存在同源冗余，如 `russ_1871_neimeng_pts`≡`przh_1871_neimeng`≡`chgis.v4_ras_1871_neimeng_pts`）。
- **tsv/xls 改名**：6 张（`academies_2957`、`china_pop_1999_county`、`gb_91_codes`、`missionary_writings`、`quan_yuan_wen_index`、`thdl_tibet_adm_areas`，源依次为 ACADEMY_Data.tab / 1999_gb_pop_uce.xls / GB_91_HZ_040201_UTF8.tab / writings….tab / Index_of_…_Yuan….tab / THDL_ADMareas_rev022401.xls）。

## 三、B 类（107 张，有源但需新增载具）

| 子类 | 张数 | 源文件（usedata 内） |
|---|---|---|
| CHGIS Access 编码库 | 42 | `V2/V3/V4_Data_Archive.zip` 内 `access_database/*.mdb` + `CHGIS_data_dictionary.zip`(6 xlsx)。即 v2db/v3db/v4db `main_table/part_of/gis_info/source_notes/feature_types/前置关系` 与 xtra_*/data_dictionary 等 |
| 西藏地名录 tgaz | 31 | `DVN/H3OB28/tgaz_bak_2018.zip`(tgaz_bak_2018.sql) |
| 栅格（DEM + 历史图扫描） | 29 | `DVN/E1FHML/DEM_QGIS-3_REVISED.zip`(chgis_dem.tif)、`DVN/23340/1926_China_Atlas.zip`(30 jpg+jgw)、`DVN/H4WVUP/beijing_1875.zip`(.tif)、`DVN/ABPR9F/Ca1884_przh_partial.tif`，及 1876/1884 各图扫描 GeoTIFF；老库对应 `dem*`、`ras_przh_1876_map*`、`ras_1926_*`、`ras_peking_1875` 等 `rid,rast` 表 |
| 中国朝代/年号 | 3 | `chgis-v6/China_Periods_ReignDates.zip`(china_chron.sql/xls/csv/ods) → `china_chron`、`china_chron_fields`、`major_china_periods` |
| 码表 | 2 | `DVN/I4UIKV/ngia_dsg_codes_2017-03-15.csv`、`nima_feat_desig.txt` → `ngia_dsg_codes_2017_03_15`、`nima_feat_desig` |

## 四、C 类（4 张，无源，建议排除）

| 表 | 行数 | 无出处原因 |
|---|---|---|
| `public.addr_xy` | 19249 | 由 CBDB 地址表 **派生** 的坐标表，无独立源文件 |
| `harv.tgz_mv_pn_srch_new_test` | 82117 | tgaz 的 **测试** 中间表（`_new_test` 后缀） |
| `harv.tgz_mv_pn_srch_old` | 82117 | tgaz 的 **旧版** 中间表（`_old` 后缀；正主是 `tgaz_mv_pn_srch`） |
| `ogr_system_tables.metadata` | 184 | QGIS 软件自建的元数据表 |

## 五、对「清空后重新导入」的影响

- 清空 + 重装，**必须先把 B 类 107 张的去留定案**：若也要这批数据，需新增「Access .mdb」「.sql」「栅格 GeoTIFF」三类载具并彩排通过后再装；若本次明确不装，则在清单中显式登记为「有意排除」。
- C 类 4 张：按「无出处即避免」的原则，**建议不导入**。
- A 类 283 张：已全量彩排通过（含 merge/rename 的等价性已在段B 值级全等框架内验证）。

## 六、证据

- `datamgmt/recon/cbdb_provenance.json`（395 张逐表分类）
- `datamgmt/recon/prov_old_tables.json`（老库 395 关系元数据快照）
- `datamgmt/recon/prov_reh_tables.json`（彩排库 869 关系元数据快照）