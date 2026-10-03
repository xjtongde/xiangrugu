# 阶段三 · 预演 段A（小样试跑）演练报告

**结论：段A 通过**。两源（一 sqlite 属性表 + 一 shapefile 属性＋几何）端到端
「读源件字节 → 判定表解码 → 落 cbdb_reh 临时库 → 闸0/1/2/3 → diff 归零」全链路跑通；
且故意注错四类，各被对应闸独立抓到。段B（全量彩排）可据此授权推进。

---

## 一、段A 边界（§7.4）

- 靶库＝`pg32b` 上临时库 **`cbdb_reh`**（真实库 `cbdb` 全程未动，已复核 db 列表）。
- 唯一通过线＝**闸3 值级全等**（库值 == 源件字节按判定表/类型映射读出之值，差异 0）。
- 命名口径（本段定，两侧同用）：目标 schema/表/列一律**小写**；源名仅作 sources.yaml 映射键。
- CSV 装载口径（实证固定）：`COPY … FROM STDIN (FORMAT csv)` **不写 `NULL` 子句**——
  空字段=NULL、`""`=空串、含`,`/`"`/换行/首尾空格者全字段加引号、内引号翻倍。曾遇
  `null '\N'` 经 subprocess→ssh→docker exec 被吞（"invalid command \N"），故弃用。
- 几何口径：`.shp` Point 双精度原值直读，`ST_SetSRID(ST_Point(x,y), srid)` **照存不转**（§12口径一）。

## 二、两源结果

| 源 | 载具 | 行/要素 | 解码 | 闸1结构 | 闸2计数 | 闸3值级 | 几何 |
|---|---|---|---|---|---|---|---|
| CBDB `NIAN_HAO` | sqlite(腿A) | 682 | UTF-8 原生 | ✅ | 682=682 ✅ | diff 0 ✅ | — |
| `v5_gns_anhui_gbk` | shapefile(腿B) | 12511 | GBK/cp1252 混 | ✅ | 12511=12511 ✅ | diff 0 ✅ | 12511 点 SRID2333/ST_Point/顶点 diff 0 ✅ |

**解码判定表真数据实证**（§5.4 判定法落地）：

- `NAME`＝`Hsüan-ti-miao`（cp1252，含 0xFC ü；GBK 解出「Hs黙n」即乱码）——命中的是 exceptions。
- `CNTY_CH`＝`砀山县`（GBK 双字节；cp1252 解出「í¸É½ÏØ」即乱码）——命中的是 default。
- `SORT_NAME` 本文件全 ASCII（如 HSUANTIMIAO），GBK/cp1252 皆可，无需例外——与判定表一致。
- 数值列原样保真：`DLAT/DLONG`＝`N(19,7)`→`numeric(19,7)`（如 34.5591667，禁 float）；`UFI`＝
  `N(8,0)`→`bigint`（如 -1934670，忠实搬运不判断正负语义，R-08）。

## 三、故意注错演练（§7.2「闸抓不到的错等于闸不存在」）

逐类向 `__stg` 注入故障，确认独立抓到：

| 注错 | 手法 | 结果 |
|---|---|---|
| 值级 | UPDATE 改 c_nianhao_chn='篡改' | **闸3 FAIL**（diff_db_only=1） |
| 计数 | DELETE 删一行 | **闸2 FAIL**（681≠682，@g2 停） |
| 结构少列 | ALTER DROP COLUMN | **闸1 FAIL**（@g1 停） |
| 结构多列 | ALTER ADD COLUMN | **闸1 FAIL**（@g1 停） |

闸不过即停（短路），先结构→计数→值级，与 §6.1.5 一致。

## 四、独立性（§6.1 铁律）复核

- importer(`load.py`) 与 verifier(`verify.py`) **零共用**：两侧各自读 `sources.yaml`＋同一份
  `decoding.yaml`，各自独立实现「字节→字符」列级解码（strict，无替换；判不定→该列不装）。
- `decode.py` 只做**判定表读取**（config 层，同 roots.py 级），不替任何一侧解码。
- `truth/`（dbf/shp/sqlite 直读源件字节）为两侧共用的**源真值地基**；期望值一律现算，绝不取库计数。

## 五、本段修出的真问题（已处理）

1. `rows()` 末尾多一空行（psql `-At` 每行一换行、末行后多 `\n`）→ `rstrip("\n")` 修；曾误报闸1/闸3。
2. 闸3 在闸1/闸2 已 FAIL 时仍跑 SELECT → 改短路。
3. 每 db.py 调＝独立 psql 会话，跨调用 TEMP 表不存续 → 几何装载改持久 scratch（用毕 DROP）。
4. **sources.yaml 缺口**：shapefile 条目不挂解码族 → 补 `decoding` 字段（705 条），重生；CBDB 78 表与
   mapinfo/tab 各凭现有 charset/encoding 或 UTF-8 原生，不受影响。

## 六、遗留 → 段B（不再猜测，列出待段B裁决/落地）

1. **几何与属性最终合并**：本段几何独立 `__geom_stg`（__rid 1:1 对齐）；段B 起落同一正表（几何列并入）。
2. **key_cols**（§6.3 值级对账键）：v5_gns UFI 非唯一（8616/12511），本段用「行哈希多重集差集」避开键依赖；段B 各源需定键。
3. **131 层非标准 CRS**（Krasovsky/Transverse_Mercator/Clarke1866/NAD27 等）＋4 层无 `.prj`→SRID 0：逐案裁决后再装几何。
4. 载具 C（xls 直读单元格）、D（tsv）、E（栅格 统计+分块抽样）、MapInfo（harv，已有 charset）未在段A 触达，段B 补。
5. `/tmp/xlsdeps`（xlrd）按用户「用完即删」规则，留至腿C 装完再删。
6. 段B 附加项：幂等重跑同值、loadavg/nice/ionice 记录、时间与资源量测（§7.4）。

## 七、复现命令

```bash
python3 - <<'PY'
import sys; sys.path.insert(0,'datamgmt')
from importer import load
from verifier import verify
db='cbdb_reh'
entries=load.load_entries()
sy=next(x for x in entries if x['carrier']=='sqlite' and x['target'].endswith('NIAN_HAO'))
sp=next(x for x in entries if x['carrier']=='shapefile' and 'v5_gns_anhui' in x['target'])
load.load_sqlite_staging(db, sy); print(verify.verify_sqlite(db, sy)['verdict']); load.promote(db, sy)
load.load_shapefile_staging(db, sp); print(verify.verify_shapefile(db, sp)['verdict']); load.promote(db, sp)
load.load_shapefile_geom(db, sp); print(verify.verify_shapefile_geom(db, sp)['verdict'])
PY
```

临时库 `cbdb_reh` 现留正表 `public.nian_hao`(682)、`chgis.v5_gns_anhui_gbk`(12511) 为段A证据；
演练期 scratch/staging 与 COPY 试跑表已清。