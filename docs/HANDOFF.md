# HANDOFF —— 当前进度与下一步（2026-10-05 交接件）

> 新会话接手时：先读本文件，再读 `docs/import-plan.md`（唯一权威展开处），即可无缝续作。
> 交接给用户的唯一话术：**「继续香如故项目的数据库导入工作，先读 docs/HANDOFF.md」**。

> **补正注（2026-10-05，R-06 矛盾查）**：本文件下文 §1.2(b)、§2.1、§3 所称「表名/分区照 `ops/harvard/load-b2/recon_b2a.tsv`＋`usedata/README-b2.md` 既定定名」**已被取代**。用户已定「不管旧库里的东西，唯一依据＝usedata 源件」；现行口径＝**表名照源件自身名**，权威展开见 `docs/import-plan.md` §5.1「命名与去重口径」＋§12 口径十（已裁）。旧装载账 `recon_b2a.tsv`／`src_paths.tsv` 一律**不作命名与建库清单依据**；其源件已 **2026-10-05 随旧方案删除**（教训由 `PITFALLS.md` 蒸馏留存）。

## 0. 一句话定位

把 `/mnt/wd61workmetadata/usedata/` 里的数据**忠实、无损、一件不落**地导入 pg32b 数据库，验收标尺＝「库值 == 源件字节按列级解码判定表读出的值，差异为 0」。全部纪律见 `docs/import-plan.md` 与 `rules.md`（R-07 源数据只记不改／R-08 忠实导入优先）。

## 1. 刚确立的关键结论（务必继承，勿再踩同一坑）

1. **usedata 是唯一数据来源；建库清单必须由 usedata 逐件穷举得出，不得自扫自命名，不得未经用户就在清单里去重/改名/合并。**
2. 我此前的一版 `datamgmt/config/sources.yaml`（868 源）**作废**——它是自扫目录拼出的，缺陷有三：(a) 漏装栅格/Access 编码库/西藏地名录 SQL/朝代表/码表/xlsx 字典等一整类一整类；(b) 表名与 schema 自造，与既定权威账 `ops/harvard/load-b2/recon_b2a.tsv`＋`usedata/README-b2.md` 的定名不符；(c) 矢量图层数自己也数错（自报 665/118，实际 705/142，因擅自去重 HIMIVE 镜像）。
3. 正式库 `cbdb`（老库，395 表）**不是可照抄的金标准**：它系旧方案所装，犯过 import-plan.md H-2/H-3 明令禁止的错（几何统一转 4326、就地 UPDATE/DELETE 修 248 万行）。但它范围全（对照老库可查遗漏），出处核查结果见 `datamgmt/recon/cbdb_provenance_report.md`。
4. **usedata 完整清点（含 zip 套 zip 逐层展开，7572 成员）**：
   - 数据件：CBDB 1 .sqlite3(78 表)；shapefile **705 层**；MapInfo **142 层**；栅格 **38 .tif + 205 .jpg + 72 .gif**；Access **5 .mdb**；SQL **2 .sql**(tgaz 西藏地名录 + china_chron 朝代表)；Excel **13 .xlsx + 12 .xls**；**7 .csv + 4 .ods**；顶层 .tab 5 个 + .db 1 个。
   - 随附账：713 .txt、691 .xml、13 .pdf、README/EULA 等（不建表）。
5. 我的"段B 868/868 全等"结论**不成立**（地基错了）。重新来过。

## 2. 下一步（按序）

1. **重造源清单**：以 usedata 逐件穷举为唯一基准，产出完整底账「usedata 每一数据件 → 应建哪几张表（schema.table）」，表名/分区照 `ops/harvard/load-b2/recon_b2a.tsv`＋`usedata/README-b2.md` 既定定名；任何去重/改名/合并单列一笔、先交用户裁定。
2. 底账交用户核对通过后，再重走「列级解码判定表 → 类型映射 → 装载 → 六道闸逐值验证（闸3 值级全等为唯一通过线）」。
3. 全部过闸后，才谈正式搬库；**搬库前必须先通知用户并获其口令**（R-01）。

## 3. 关键事实/指针

- 权威方案：`docs/import-plan.md`（五阶段§10、六道闸§6、硬规则 H-1..H-4§2、五条腿§5.2 含 **raster 腿E**）。
- 权威装载账：`ops/harvard/load-b2/recon_b2a.tsv`（1,757 行）、`src_paths.tsv`、`usedata/README-b2.md`（173 件源→装数去向）。
- 老库出处核查：`datamgmt/recon/cbdb_provenance_report.md` + `cbdb_provenance.json`（395 表逐表分类）。
- 现代码（按载体装载+验证）：`datamgmt/`（`importer/load.py`、`verifier/verify.py`、`truth/*`、`rehearse.py`、`config/sources.yaml|decoding.yaml`）。
- 数据库：pg32b `192.168.3.32:5433`，`ssh 192.168.3.32 "docker exec -i pg32b psql -U postgres -d <db> ..."`。临时排练库 `cbdb_reh`，生产库 `cbdb`（只读核查，勿动）。
- 源数据只读：`/mnt/wd61workmetadata/usedata`（CIFS 只读，勿改勿删）。
- Git：仓库 `/root/xiangrugu`，最近交接提交 `6caa7d9`（出处核查报告）。
- 汇报纪律：给用户一律大白话流畅散文；用户问"哪个文件"才点名文件/行号。

## 4. 当前立即要做的第一件事

**产出「usedata 逐件全清点 → 目标表」完整底账**（纯只读，含 5 mdb、2 sql、38 tif、13+12 xls/xlsx、7 csv、4 ods 各自的落表），作为重建 sources.yaml 的输入，交用户核对。