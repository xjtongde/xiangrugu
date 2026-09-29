# bugs.md —— 缺陷账（B-编号）

> **状态：现行**｜as_of 2026-09-29
> **依 R-07**：本账只登**我方之错**（含"我方引入的库内不合格"）。**源数据自身的可疑处不在此列**——归 `docs/cbdb.md` 登记册 G4-xx；源生条目在本账只留**一行指针**并注明"源生·冻结"。
> **记账不需口令，修需口令**（R-01/R-03）。

## 在册

### B-15 `chgis.v5_gns.geom`／`v4_gns.geom` **已非源件之值**（我方引入）

- **归属：我方缺陷**（非源数据）。
- **实证**：`ops/harvard/load-b2/b2fix9.py:15` 执行
  `ALTER TABLE chgis.v5_gns ALTER COLUMN geom TYPE geometry(Geometry,4326) USING ST_Transform(ST_SetSRID(ST_Transform(geom,2327),2333),4326)`
  ——**两次 `ST_Transform`**；`v5_gns` **130,665 行**受影响。`v4_gns.geom` 极可能同类，**待验**。
- **违反**：`docs/import-plan.md` **H-2**（源件已声明者照存不变换——`.prj` 明示 `Xian_1980_GK_Zone_19`／`Gauss_Kruger`／`False_Easting 19500000`／`Central_Meridian 111`）。
- **状态：候令**。重建后由 H-2 自然消除；若不重建则须**重装该两表**（H-3：保真层永不 `UPDATE`，错→重装）。

### B-13 `demo/` 三页之数字**已过期**

- **归属：我方缺陷**——库内数据无误，错在页面快照未随 FIX10／FIX11 重跑（`catalog` 页断言今天重跑即不符）。
- **状态：候令修**。`demo/` 已由用户令留下（2026-09-29），故本项仍有效。

### B-02 宿主 36 的 `/etc/timezone` 系**空目录**

- 归属：环境缺陷（非我方代码）。部署标准 §9 之时区挂载对任何新部署失效。
- 状态：未修；36 上 `pg36` 已用变通（见 `docs/pg36.md`）。**32 主机无此问题**（时区两文件正常）。

### B-03 Gitea 1.27.1 wiki **API 写正文失效**

建页丢 `content`、改页错名成 `unnamed`。状态：未修（wiki 系外围知识层，**非权威**）。

### B-04 Gitea 1.27.1 wiki **API 单页读对 CJK 页名一律 404**

`GET /wiki/page/{名}` 只认 ASCII。状态：未修（同上）。

## 源生条目（依 R-07 **只登记不修改**；展开见 `docs/cbdb.md`）

| 编号 | 一句话 | 展开 |
|---|---|---|
| **B-14** | `addr_codes`「福州」坐标离群两行（`3858`／`3859`，(122.58036, 42.7167)），被 **9** 条任所记录引用 | **G4-06** |
| **B-12** | `posted_to_office_data.c_firstyear` **两行负年**（張奕 `46677` −1、劉文斗 `391542` −2） | **G4-04** |

## 已结／已作废（原 B-01…B-11 之去处）

- **B-05…B-11**（装载缺陷七条：双重后缀件致 4,099 行静默漏装／八张 xls 表头当数据致 114 个 `fieldN` 伪列／`prov_py` 不可用于筛省／台账 887 重复行／`nas-mirror` 硬编码／`v4_gns` 丢末尾变音符（值级不合格 2,288 处，见 `roots.yaml` `known_nonconformance`）／仅存安徽省前缀 ID 列）
  → **已全部提炼入 `datamgmt/PITFALLS.md` P-01…P-15**，且**重建后自动消除**（v3 不经 GDAL 默认、不做就地 `UPDATE`、显式声明编码与表头）。
- **B-01**（助手未经确认擅自执行 skill 装入）→ 已结，教训已入 `rules.md` R-01。

> 原详细条目已删（2026-09-29 用户令「能清空的就清空」）；全文可 `git show 75ecd77:docs/bugs.md` 取回。
