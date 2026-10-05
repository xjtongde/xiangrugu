# 底账重建状态（唯一依据＝usedata 源件，不参考旧库）

> 原则（用户指令）：不管旧库、不参考旧载具账；任务＝把 usedata 数据忠实导入 pg32b。
> 表名/结构/行列/值一律照源件自身现读现算。schema 三区 public/chgis/harv；表名照源名；镜像 md5 判同取一。

## 已完成的完整穷举（源盘实测）

usedata 全深度展开 **7219 成员**，0 打不开。载体计数与「内部表/sheet」全部现读：

| 载体 | 件/层 | 展开内部表 |
|---|---|---|
| CBDB sqlite | 1 文件 | **78 表** → public |
| shapefile | 705 层 | 去重后 **667 层** |
| MapInfo | 147 层（含顶层 5） | 去重后 **123 层** |
| 栅格 | 38 tif + 205 jpg + 72 gif + 11 png | 去重后 tif 26 / img 167 |
| Access | 5 .mdb → 3 库（v2/v3/v4） | **36 表** |
| SQL | 2 .sql | **39 表**（china_chron 1 + tgaz 38） |
| Excel | 27 xls/xlsx → 19 件 | **25 表**（含多 sheet） |
| csv / ods | 7 / 4 | 6 / 4 |
| 顶层 | 1 .db（Thumbs.db） | 待判 |

## 最终底账

`datamgmt/recon/ledger_final.tsv` — **1172 行 / 1153 个表名**，三区：public 78 / chgis 847 / harv 247。

## 镜像判同（md5）

- 同名镜像 **64 组**：**62 组内容全同→取一**（其余并列记为镜像）；**2 组内容有异→各自保留**（`v2_1820_cnty_pts_{gb,utf}` 在 V3 仓库 vs CHGIS_V2 仓库字节不同）。
- v4_chgis_dbase.mdb 在 V4 仓库内 **3 份副本**：2 份字节全同、1 份不同（表名相同）——待裁定以谁为准。

## 待裁定（唯一剩余）

**15 组跨载体同名**：同一数据源以多种格式并存（csv+ods、xls+csv、xlsx+ods、xls+sql、mdb+xlsx、shp+mapinfo、shp+栅格索引图）。政策二选一：

1. **全装**：各格式都落库，表名加格式后缀区分（忠实「一件不落」）；
2. **取一**：每数据集只装一种权威格式，其余记镜像。

明细见 `datamgmt/recon/ledger_final.tsv`（表名重复者即此 15 组，共 33 个源单位）。

## 机器可读产物（datamgmt/recon/）

- `ledger_final.tsv` — 最终底账（1172 行，含 dedup/注记）
- `ledger_final_summary.json` — 计数
- `inventory_members.tsv` — 7219 成员穷举
- `collisions_mirrors.json` — 64 组镜像 md5 判同结果
- `xls_sheets.json` / `tgaz_objects.json` — 内部结构
- `sources_draft.tsv` — 旧草稿（已被 ledger_final 取代）