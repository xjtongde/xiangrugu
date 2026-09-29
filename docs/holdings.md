# holdings.md —— 已持有资料与许可

> **状态：现行**｜as_of **2026-09-29**（本卡之目录结构与体量系本日 `du` **现算**；许可为账面值）
> **权威源根之机器可读版＝`datamgmt/config/roots.yaml`**（本文件只管"手上有什么、什么许可、在哪个根下"）。
> ⚠ **旧版本文件把七个资料树当"根级目录"记载，已过期**：2026-09-28 起 WD61 根下只 4 项，七树全在 `xiangrugudata/` 之下。

## 一、根（2026-09-29 `ls` 现算）

`/mnt/wd61workmetadata/`（NAS `//192.168.3.61/workmetadata`，唯一正路径）根下**只 4 项**：

| 项 | 体量 | 角色 |
|---|---|---|
| **`usedata/`** | **3.2G** | ★**权威数据源**（只读；**190 件**）→ 权威＝`roots.yaml` |
| **`xiangrugudata/`** | **20G** | **下载区**（只读原件；7 树／16,803 件，件数系账面 09-28） |
| `爱因斯坦/` | 1.6M | 用户自置文本（**非项目语料**，登记以清盘账） |
| `霍金/` | 260K | 同上 |

`usedata/` 根下 5 项：`chgis-v6/`（1 件）、`harvard/`（15 件）、`harvard-full/`（172 件）、`README-b2.md`、`SHA256SUMS-b2`。

⚠ `/mnt/nas-mirror/61/workmetadata/`（32 主机本地镜像，每日 12:00 `rsync`）——**项目禁用**（2026-09-27 用户裁；旧脚本 15 处仍硬编码，**该路径实测仍存在→误用不报错**）。

## 二、下载区七树（2026-09-29 `du` 现算）

| 树（`xiangrugudata/` 下） | 体量 | 上游出处 | 许可 |
|---|---|---|---|
| `harvard-full/` | **11G** | Harvard Dataverse（API 取；官方项目站拒机器访问） | 各 DOI 自定 |
| `daizhigev20/` | **7.0G** | 殆知阁古代文献藏书 2.0（tar.gz 2,298,099,751 B） | 见仓内 |
| `chinese-classical-corpus/` | **786M** | HF `gujilab/chinese-classical-corpus`（`corpus.jsonl` 53,918,993 行） | 见仓内 |
| `cbdb-project/` | **560M** | HF `datasets/cbdb/cbdb-sqlite` → `cbdb_20260919.sqlite3` | **CC BY-NC-SA 4.0** |
| `poetry-source/` | **357M** | GitHub `snowtraces/poetry-source`（master zip 374,309,777 B） | ⚠ **许可未记**（缺口，用前须查上游） |
| `chinese-poetry/` | **217M** | GitHub `chinese-poetry/chinese-poetry`（711 文件） | ✅ `LICENSE` 在仓内（1,076 B） |
| `chgis-v6/` | **1.1M** | Harvard Dataverse CHGIS V6（`v6_time_cnty_pts_utf_wgs84.zip` 等） | 见同批 DOI |

## 三、许可要点

- **CBDB**：**CC BY-NC-SA 4.0**（非商业、相同方式共享、须署名）。
- **CHGIS**：Harvard Dataverse 各 DOI 自带许可；shapefile 包内随附 `README_GNS_COPYRIGHT.txt`／`README_CHGIS_V5_DRAFT.txt`——**装载时属源件成员链之一，不得漏**（`import-plan.md` 闸1）。
- **缺口**：`poetry-source/` 许可未记。

## 四、维护规矩

1. 新增下载一律**先入 `xiangrugudata/`（下载区）**，整理后**入 `usedata/`（权威源）**；**二者皆只读**（R-07：源数据只记不改）。
2. 体量与件数系时点值；**清盘复测后同批刷新本文件并记 `docs/log.md` 一行**（R-04/R-06）。
3. 与 `roots.yaml` 冲突时**以 `roots.yaml` 为准**，并须同批改本文件（不得双账）。

> 原"十个大件明细""账目与缺口""维护规矩"之长篇叙事**已删**（2026-09-29 用户令）；可 `git show 75ecd77:docs/holdings.md` 取回。
