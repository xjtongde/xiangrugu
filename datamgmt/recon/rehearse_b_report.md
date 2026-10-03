# 段B 全量彩排报告（阶段三·预演）

> 唯一标尺：库值 == 源件字节按列级解码判定表读出之值；差异 0 或挂白名单。六道闸：闸0完整性 / 闸1结构 / 闸2计数 / 闸3值级全等（唯一通过线）/ 闸4语义哨兵 / 闸5换版差分。

## 结论

**868 / 868 源全部 CONFORMS，闸0–闸3（含几何顶点多重集全等）diff = 0。** 未发生任何静默改写、删行、重排或类型漂移；全部残余差异均已逐案判定并记录（见下「闸4 逐案裁决」）。

## 五阶段进展

1. 一体检（源件编码/结构普查）—— 完成。
2. 二判定表（decode/sources 两判表）—— 完成。
3. 三预演两段（段A 小样 → 段B 全量）—— **段B 完成**。
4. 四正式装载 —— **未开始（候用户口令）**。
5. 五收口 —— 未开始。

## 各载具 tally（全部 diff=0）

| 载具 | 源数 | 结果 | 行/记录合计 |
|---|---|---|---|
| sqlite | 78 | 78 CONFORMS | 5,623,075 |
| shapefile（含几何） | 665 | 665 CONFORMS | 1,459,513 |
| mapinfo（.tab/.dat 属性） | 118 | 118 CONFORMS | 276,234 |
| tsv | 5 | 5 CONFORMS | 47,607 |
| xls | 2 | 2 CONFORMS | 2,522 |
| **合计** | **868** | **868 CONFORMS** | **7,408,951** |

> 源总数自 932 → 868：去重 64 份 HIMIVE(V3_Data_Archive) 镜像件（shapefile 40 份 REL 保留自有 DOI、mapinfo 24 份），未丢任何异质内容——38 份 shapefile REL 与留本逐字节相同，只有 2 份（下）存在 1 处差异。

## 闸4 逐案裁决（源件自身缺陷，均如实入账）

| 项 | 数量 | 处置 |
|---|---|---|
| v2_1820 县名一处读音差异（Muyang / Shuyang） | 2 层 · 1 格 | 按图层本体 DOI 入「Muyang」；V3 镜像「Shuyang」待用户拍板 |
| 退变几何（环<4/空环/空多重/Null，不可画） | 12 层 · 90 要素 | 几何入 NULL，其余属性照常 |
| dBase `******` 溢出标记（值不可知） | 1 层 · 1 列 | NULL |
| 科学计数法（AREA 1.94455e10） | citas90 系 | 还原为 numeric 19445500000 |
| 定宽字段截断多字节末字符 | 若干列 | 保留可解字节 + U+FFFD 标记，非静默改写 |
| MapInfo .map 几何 | 118 层 | 未装（同内容几何已由 shapefile 载体核，属性已全等） |

## CRS / SRID 裁决（照存不转）

4326(WGS84)×35 · 2333(Xian1980)×524 · 4214(Beijing1954)×94 · 4610×2 · 4267×2 · 0(无/未识别)×8。一律原样存储、不做重投影；无 .prj 3 层按 srid=0 处理。

## 幂等 / 资源

- 幂等重跑同值：抽样 3 层重装全等；cités 早前多次整段重启（前 67 层）结果逐字一致。
- 资源：全程本地 loadavg ≈ 0.25（远低于 4.0 门限）；single-layer 时长平均 ≈ 12–13s，大层（asia_contour 186k 行）≈ 126s；逐层时长已入库于各 rehearse_b_*.json。

## 证据文件

- `datamgmt/recon/rehearse_b_sqlite.json`（78）
- `datamgmt/recon/rehearse_b_shapefile.json`（665）
- `datamgmt/recon/rehearse_b_mapinfo.json`（118）
- `datamgmt/recon/rehearse_b_tsv.json`（5）/ `rehearse_b_xls.json`（2）
- `datamgmt/recon/retry_shapefile.json`（4 层闪断/空环重跑 → 全 CONFORMS）
- `datamgmt/recon/degenerate_geometry.json`（12 层 · 90 要素）
- `datamgmt/recon/adjudication_inventory.json`（闸4 逐案裁决清单）
- `datamgmt/recon/collisions.json` / `collisions_mapinfo.json`（去重档）