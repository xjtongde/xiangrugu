# `docs/holdings.md` —— 已持有资料索引（我们手上到底有什么）

> **定位**：本文件是**"已经落到盘上的资料"的唯一索引账**（2026-09-25 用户定："现在 docs 里只要有一个我们已有资料的索引文档就可以了"）。
> **与 wiki 的分工**：**发现新源**＝只往 wiki《中国古典语料资源索引》记一笔（一条一源四栏），**不下载**；**下载统一延后**（同日为令）。等真正下成一件，**回本文件加一行**。
> **数据落盘纪律**：外部件一律不入工作区（`/root/xiangrugu`），只落 `WD61`；本文件只记路径与凭据，不存数据。

## 一、根与镜像

| 位置 | 说明 |
|---|---|
| `/mnt/wd61workmetadata/` | **主存放盘**（WD61）。下表除注明者外全在此根下 |
| `/mnt/nas-mirror/61/workmetadata/` | 32 主机上的本地镜像，每日 12:00 `rsync`（出处＝`usedata/harvard/README.md`）。**镜像新鲜度本轮未复核** |

**两类角色要分清**：`usedata/harvard/` 是**装数工作集**（唯一取数源）；其余为**原数据备份树**（只读，不用于装数）。工作集按 2026-09-24 用户令自备份树复制而来。

## 二、在册资料（按体量排序）

| 本地目录 | 体量 | 上游出处 | 许可（以本地读到者为准） | 完整性凭据 | 状态／用途 |
|---|---|---|---|---|---|
| `harvard-full/` | **约 11GB** | Harvard Dataverse `dataverse.harvard.edu`（API 取；官方项目站拒机器访问） | **逐集不同**，见该树 `datasets.tsv` 与本文件 §三 | `datasets.tsv`（**65 集**清单：DOI／树／件数／字节／标题／本地目录）、`harvard_dl.tsv`（逐件）、`harvard_manifest.txt`、`README_provenance.md`（**出生纸**，2026-09-23 单日采购批） | 全量备份树。**65 集未逐集核许可，只登记在账** |
| `daizhigev20/` | **7.0GB**（tar.gz 2,298,099,751B ＋ 解包 `text/daizhigev20-master`；**两种口径并记，2026-09-26 复测**：**磁盘占用** `du -s` 5,051,968 KiB ＝ 4.82 GiB，即 `du -sh` 显示的 **4.9G**／**表观字节** `find -printf %s` 求和 **5,140,890,453 B** ＝ 4.79 GiB ＝ 5.14 GB；**15,697 文件**＝txt 15,694＋md 2＋yml 1，另有 217 个目录、含目录共 15,914 条） | GitHub `garychowcmu/daizhigev20`（master 归档） | ⚠ **仓内无 LICENSE**（wiki 索引页列为避雷件）⇒ **仅作对照底账，不得再分发、不得并入任何产出** | 标记件 `.gh_dl_done`=`DONE`、`.extract_done`=`DONE`；顶层含 `佛藏` 等分类与 `使用须知.md` | 备份树（**许可真空**） |
| `cbdb-project/` | **560MB** | HuggingFace `datasets/cbdb/cbdb-sqlite` 之 `latest.zip` → `cbdb_20260919.sqlite3`（**586,485,760B**）＋同名 `.json`（385B） | ⚠ HF 侧标 `other`（`cbdb-data-licensing-terms` **403 且零快照**）＋**CBDB 数据在大陆有独家商业授权**（Yuanyin Tech.）⇒ **不得写作可再发布** | 我方一手库内计数可复算（`BIOG_MAIN` **661,969**、`ADDR_CODES` 30,157 其中 `CHGIS_PT_ID` 有值 10,996、`TEXT_CODES` 62,377、`BIOG_TEXT_DATA` 53,354、`NIAN_HAO` 682） | **主数据源**；已装数入 pg32b（见 `docs/cbdb-load.md`） |
| `chinese-classical-corpus/` | **786MB** | HuggingFace `gujilab/chinese-classical-corpus`（`corpus.jsonl` 53,918,993／`punctuate.jsonl` 61,420,969／`translate.jsonl` 707,778,938；配套 `gujilab/chinese-classical-bench`） | ⚠ 仓内 README front-matter **自标 `license: cc0-1.0`**，但其来源链含上面那个无授权仓 ⇒ **CC0 声明存疑**（wiki 索引页同条已注） | 标记件 `.hf_dl_done`=`ALLDONE` | 备份树（**许可待判**，未装数） |
| `usedata/harvard/` | **594MB** | 自 `cbdb-project/`＋`chgis-v6/`＋`harvard-full/` 复制（2026-09-24 用户令） | 同各原件 | 自带 `README.md`、`SHA256SUMS`、`chgis/SHA256SUMS.txt`、`chgis/VERIFICATION.md` | **装数唯一工作源**。内含 `cbdb/cbdb_20260919.sqlite3`、`chgis/` 五件、`tab/` 三件：`ACADEMY_Data.tab` 714,962／`Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab` 2,619,410／`writings of the 19c missionaries in China.tab` 193,811 |
| `poetry-source/` | **357MB** | GitHub `snowtraces/poetry-source`（master zip **374,309,777B**） | 该仓许可**未记**，用前须回源核 | `SHA256.txt`；`VERIFICATION.md` 载 `zipfile.testzip()` 通过，结构 `source/诗/` **1467 个 JSON**（宋 523／明 487／清 181／元 118／唐 118／五代 7／隋 7／三国 4），schema `{id,title,authorName,authorId,dynasty,content[]}` | 备份树。⚠ **上游许可未核 ⇒ 暂不入产出** |
| `chinese-poetry/` | **217MB** | GitHub `chinese-poetry/chinese-poetry`（711 文件） | ✅ **`LICENSE` 在仓内（1,076B，MIT）** ⇒ 本盘里唯一许可干净的一件 | 仓内文件自校；⚠ **其 `.git` 是 0 字节占位，非 git 工作副本** ⇒ 无法用 `git status` 校改动，核对上游须重新比对 | 备份树 |
| `chgis-v6/` | **1.1MB** | Harvard Dataverse CHGIS V6（`v6_time_cnty_pts_utf_wgs84.zip` 544,703／`v6_time_pref_pts_utf_wgs84.zip` 288,343／`CHGIS_data_dictionary.zip` 47,149／`China_Periods_ReignDates.zip` 155,774） | ✅ **EULA 原文已在本地**（`CHGIS_V6_EULA.txt`）：`academic research and educational purposes`；`No commercial use or repackaging of this dataset is allowed, in any form`；`You may not incorporate the entirety of CHGIS Data Layers in a work of your own intended for public dissemination, whether modified or not, without the express permission of the Management Committee in a separate License Agreement` ⇒ **引用条款不必再联网** | 目录内自带件 | 备份树。**与 `usedata/harvard/chgis/` 为同一批的两份存在** |
| `爱因斯坦/`、`霍金/` | 1.6MB／260KB | 用户自置文本（非项目语料） | — | — | **登记以清盘账**，不入项目数据流 |

## 三、`harvard-full/` 的十个大件（其余 55 集见 `datasets.tsv`）

`PAGGQS` **2.4GB**（ACCESS ＋ SQLite DB Version, latest）｜`23336` **2.2GB**（黑龙江全省域图 Atlas）｜`BWIBNL` **1.9GB**（LoGaRT Tagging Tool – Based on BERT）｜`PDGOZ0` 609MB｜`M7WEFY` 431MB｜`G9RKCW` 368MB｜`HIMIVE` 343MB｜`GNPNON` 287MB｜`P8U8RC` 286MB｜`F6BBOF` 255MB。

**逐集许可不在此复述**：该树 `datasets.tsv` 与 `README_provenance.md` 是出生纸，本文件只指路（R-04 单一源）。

## 四、账目与缺口

- **合计**：`du` 口径约 **21GB**（`WD61` 根下 10 个目录）。
- **许可真空三件**：`daizhigev20`（无 LICENSE）、`poetry-source`（上游未核）、`chinese-classical-corpus`（自标 CC0 而来源链无授权）。**此三件在判清之前，不得进入任何可发布产出，亦不得据以生成"可再发布"的派生表。**
- **65 集未逐集核许可**：`harvard-full/` 只做了"下全＋记出生纸"，许可层是**批量待办**，不是已完成。
- **镜像新鲜度未核**：`/mnt/nas-mirror/61/workmetadata/` 的 rsync 是否仍在跑，本轮未查。
- 与 wiki 的关系：`docs/cbdb.md` §二 记的是"**取数通路**"（从哪能拿到），本文件记的是"**已经拿到什么**"（盘上实有）。两者不互相复制内容。

## 五、本文件的维护规矩

1. **新下载成一件 ⇒ 加一行**（本地目录／体量／上游／许可／凭据／状态六格齐才算登记完成）；**未下成之前不在本文件出现**。
2. 体量与凭据须**实测填入**（`du`／`stat`／标记件内容），**不接受上游宣传数**。
3. 许可一格**只写本地读到的条款**（文件在盘上就写路径，读不到就写"条文不可得"），**不写"应该是 CC 之类"**。
4. 删除或搬迁任何一件，须在此改状态并注明日期，不得直接抹行。
