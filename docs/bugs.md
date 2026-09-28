# bugs.md —— Bug 专职账（三本专职账之一）

> **定位（R-03）**：一切**缺陷**的唯一新增记账处（"账装坏"）。纪律＝**先记后修**：未经用户口令"修"，不得改代码、发版、部署（R-01）。
> 新条目追加于「在册」最上面；编号 `B-01` 起递增，永不复用。已闭环条目移入「已结」，正文不回改（R-04）。

**状态图例**：`挂账`（已记，未获口令）→ `已口令`（获"修"令，未动工）→ `修复中` → `已修待验收` → `已闭环`；另有 `作废`（注明依据）。

**条目格式**（字段齐全才算入账）：

```text
### B-xx 一句话标题
- 开账日期 / 状态：
- 症状与复现路径：
- 根因分析：
- 影响面：
- 候选方案（可多个，含取舍）：
- 关联：（R-xx 条款、发版号、其他账编号）
```

---

## 在册

### B-14 `addr_codes`「福州」坐标离群行（**3858＋3859 两行**）**已被 9 条宋代任所记录引用**——此前判为"1 行、0 引用、无害"系我方误判
- 开账日期 / 状态：2026-09-29 / **挂账**（源生数据缺陷；候口令）
- 症状与复现路径：`public.addr_codes` 中「福州」共 **6 行**——**3858 与 3859** 坐标 **(122.58036, 42.7167)**（北纬 42.7 落在辽宁），同名正确行 **13868／16016** 为 **(119.321577, 26.073954)**＝福州，Δ≈**16.97°**；405470／405471 无坐标。3858／3859 其余字段全同（`c_firstyear`／`c_lastyear` **908–1121**、`c_admin_type` Zhou、`c_admin_cat_code` **215**、`c_notes` 同句"XY coordinates are approximations based on centroids of approximate polygons"）。复现＝`select c_addr_id,c_name_chn,c_firstyear,c_lastyear,x_coord,y_coord from addr_codes where c_name_chn='福州' order by 1`。**引用实测（本条之要害）**：`posted_to_addr_data` 中 3858 被引 **8** 次、3859 **1** 次，共 **9 条**——劉文質(1247／965／兵馬都監)、陳烈(3076／教授)、周希孟(3242／教授)、尚大伸(12139／1117／外宗正主簿)、張讀(14514／1067／教授)、莊柔正(48272／1049／教授)、繆烈(52628／1207／教授)、張洙(480267／教授)、上官基(484860／1027／觀察推官)，**皆宋代福州任所**。籍贯侧确为 **0**（`biog_main.c_index_addr_id`／`biog_addr_data`／`assoc_data.c_addr_id`／`events_addr`／`possession_addr` 各 0）。
- 根因分析：上游 `cbdb_20260919.sqlite3` **原样即如此**（同 6 行同坐标、同 9 条引用逐一复现，2026-09-29 只读对照）→ **非导入引入**；系 CBDB 地址表一对重复行携带错置纬度（疑纬度错置或质心计算错）。**我方之错在判词不在数据**：`demo/build_A.py:57` 原话为"实测 0 人**籍贯**指向该行，本页零损害；公示为「按地名 join」者的地雷"（限定于籍贯与该页，口径本正确），2026-09-29 汇总成台账时**限定词丢失**、扩为"1 行、实测 0 引用、已披露、无害"，行数亦误（实为 2 行）——如实自认。
- 影响面：凡按 `addr_id`（3858／3859）取坐标者，**9 条宋代福州任所会落到北纬 42.7**；按**地名** join 者亦可能命中该两行（同名 6 行、坐标三套）。籍贯分析与蘇軾专题三页**不受影响**（未引用该两行）。
- 候选方案：① **不改库、文档示警＋清洗规则**——在 `docs/cbdb.md` §9.4(7) 坐标污染表**补一行**（3858／3859 福州｜仕宦 9｜籍贯 0），并在任何按 `addr_id` 取坐标的管线里显式剔除；与该节既有结论"必须按 `addr_id` 清洗、不可按地名合并"同族——**建议此项**；② 库内另建清洗视图（原表不动）；③ 只入账不示警（后续按 `addr_id` 上图者必踩）。
- 关联：`docs/cbdb.md` §9.4(7)（徐州 11242 仕宦 65／登州 11167 仕宦 23 同族，本条为其新增例）；`demo/build_A.py:50-57` 与 `demo/A-song-distribution.html` 校勘台第 3 行（**原披露文字口径正确，勿改**）；B-12（同批复核所出，同为源生缺陷之判词校正）；R-01（候令）；**R-07**（见下补正注）。
- **2026-09-29 补正注（R-07「源数据只记不改」开设后）**：本条系**源生数据缺陷**（上游 `cbdb_20260919.sqlite3` 同 6 行同坐标、同 9 条引用）→ 依 R-07 **只记录、不修改**：候选方案 ②（另建清洗视图）及一切库内／源件改动**一律冻结**，非用户逐案指定不做；方案 ① 中"在 §9.4(7) 表补一行"属**记录**性质，惟为免双账（R-04：缺陷之唯一新增记账处＝本文），补行与否候用户裁。**本条内属我方的部分只有判词失据**（`build_A.py:57` 之"0 人籍贯"限定词在汇总时丢失，扩成"0 引用／无害"，行数亦误）——与源数据缺陷**分治**，已如实自认。

### B-13 demo 三页之数字**已过期**（FIX10／FIX11 后未重跑；`catalog` 页断言今天重跑必失败）＝"demo/ 陈旧缓存"之实体条目
- 开账日期 / 状态：2026-09-29 / **挂账**（候口令"修"；此前仅 `docs/log.md` 两处"候令未动手项"提及"`demo/` 陈旧缓存"，**三本账无条目**——本条补齐）
- **归属（依 R-07）**：**我方缺陷**，非源数据——库内数据无误，错在页面快照过期未刷；属我方修复队列，候口令"修"。
- 症状与复现路径：① `demo/catalog/build_catalog.py:18` `assert TOT_ROWS == 8580233`——该值系 **2026-09-28 00:30** 之 `count(*)` 精确实测（**399 关系**），而 FIX10／FIX11 于同日 **02:11** 落库（commit `0b41d0b`）；**2026-09-29 按同口径**（`public`／`chgis`／`harv`／`ogr_system_tables` 之 BASE TABLE＋VIEW）实测＝**399 关系／8,584,318 行**（＝8,580,233＋4,099−14，分毫不差）→ **断言必失败**。② 页面逐表值三处已被库内实值超越：`chgis.v4_gns` 页面 **126,566** vs 库内 **130,665**；`public.china_pop_1999_county` **2,361** vs **2,357**；`public.thdl_tibet_adm_areas` **166** vs **165**。③ `demo/build_roam.py` 之 `assert sum(t['rows'] for t in d['tables']) == 8580012`（395 表、pg_stat 口径）同因过期（账面现值 **8,584,097**）。复现＝对 pg32b/cbdb 逐表 `count(*)` 与页面内嵌 `DATA` 比对。
- 根因分析：页面数字系**快照**，构建时刻早于数据修复批 **41 分钟**；构建管线无从感知库内后续变更，页面亦无"数字须带实测时点＋口径"之标注。**口径易混**：`count(*)` 精确口径（**8,584,318**）与账面 pg_stat 口径（**8,584,097**）差 **221**（`catalog` 页自注"比 pg_stat 估计多 221"），引用时不标口径即对不上账。
- 影响面：`demo/catalog/index.html`＋`cat-*.html`（总量与三表行数）、`demo/pg32b-roam.html`（表数与总行）；`demo/person/*` 三页**不受影响**（蘇軾专题诸数与 FIX10／FIX11 无涉，2026-09-29 逐项复核吻合）。
- 候选方案：① **重跑 catalog／roam 抽取并重建两页**，页面数字旁标注实测时点与口径（`count(*)` 抑或 pg_stat）——**建议此项**；② 只加醒目注记"数据截至 2026-09-28 00:30，FIX10／FIX11 后未刷新"（成本最低，数字仍错）；③ 不修。**须先裁一处**：页面权威口径取精确 `count(*)` 还是账面 pg_stat（两者差 221）。
- 关联：`docs/cbdb-load.md` §15.9（FIX10／FIX11 权威展开）、`docs/data-sources.md` §一／§六（账面数字权威）、I-05（可复现性与登记缺口）；R-01／R-04。

### B-12 `posted_to_office_data.c_firstyear` **两行负年**（宋·張奕 −1、清·劉文斗 −2）＝占位符／录入错，**非公元前**（此前列为"需按朝代裁决"之存疑项，实无需裁决）
- 开账日期 / 状态：2026-09-29 / **挂账**（源生数据缺陷；候口令）
- 症状与复现路径：`select c_personid,c_office_id,c_firstyear,c_lastyear from posted_to_office_data where c_firstyear<0` → **2 行**：(46677, 1001, **−1**, 0)、(391542, 80944, **−2**, NULL)。前者＝**張奕**（`c_dy=15` **宋**、`c_index_year`／`c_birthyear` 1012、官 著作佐郎），后者＝**劉文斗**（`c_dy=20` **清**、官 典史）。上游 sqlite **同 2 行同值**。
- 根因分析：同表另有 `c_firstyear=0` **116,913** 行、NULL **163,293** 行（三套"未知"写法并存），故 −1／−2 属**占位符族**而非纪年：两人朝代为宋、清，**不可能是公元前**（对照 `biog_main` 真公元前负年 **18 行**＝孔丘 −551、顏回 −522、嬴政 −259、劉邦 −256…劉秀 −4，皆先秦—西汉人）。**归类校正**：台账原置 C 类"歧义存疑（需按人物朝代裁决）"，惟朝代一查即明，应归**硬错误**。
- 影响面：仅 2 行；凡按 `c_firstyear` 排序／取 `MIN`／画时间轴者会先撞上 −2／−1（与 `docs/cbdb.md` §9.7 陷阱一"0／极大值哨兵"同族）。
- 候选方案：① **不改库**，把清洗规则写实——`docs/cbdb.md` §9.4(4) 已有"年份列须 `> 0`"，补一句"负年除先秦人物（`biog_main` 之 18 行）外一律视为占位符"——**建议此项**；② 库内 `UPDATE` 为 NULL（改上游原样，须用户裁）；③ 只入账。
- 关联：`docs/cbdb.md` §9.4(4)（`0` 哨兵规则）／§9.7（哨兵三处）；B-14（同批复核所出）；R-01；**R-07**（见下补正注）。
- **2026-09-29 补正注（R-07「源数据只记不改」开设后）**：源生缺陷（上游同 2 行同值）→ 依 R-07 **只记录、不修改**：候选方案 ②（库内 `UPDATE` 为 NULL）**冻结**，非用户逐案指定不做；方案 ①（在 §9.4(4) 补一句"负年除先秦 18 行外视为占位符"）属**记录／规则文字**，候令。

### B-11 `chgis.v4_gns.name` 系统性**丢失末尾变音符**（全表 2,287 行；源系混合编码，新旧两条装载路径各以其法丢之）
- 开账日期 / 状态：2026-09-28 / **挂账**（候口令；含本批新装 324 行，余 1,964 行系原装旧行之既有缺陷）
- 症状与复现路径：库内 `Hsü-t'uan` 实作 `Hs-t'uan`、`Mo-li-hsü` 作 `Mo-li-hs`、`Ling Ch'ü` 作 `Ling Ch'`；全表 **2,287 行**（**30 省皆有**：guangxi 323／shanxi 241／guangdong 240／jiangsu 169／jiangxi 134／shaanxi 128／tibet 109／hebei 105／anhui 96／sichuan 76／zhejiang 67／hunan 55…），另 `pref_py` **1 行**（`Wuzhou Diqu …`î` 丢了 `î`）。复现＝直读源 DBF 之**原始字节**、按 latin1 解码与库内逐行比对（`(ufi,uni)` 为键）。
- 根因分析（**源系混合编码，两条路径各以其法丢字**）：源件虽名 `_gbk`，实测其 `NAME`／`NM_ASCII`／`SORT_NAME`／`PREF_PY` 诸列系**单字节 latin1/cp1252**——威妥玛拼音之 `ü` 存作**裸字节 `0xFC`**（guangxi 一件即 360 记录含之，其中 **309 处 `0xFC` 落在字段末尾**）；唯 `CNTY_CH` 系**真 GBK 中文**（4,099 记录全含高位字节）。① **原装路径**：enc=None → GDAL 按 latin1 存入，后 FIX5 期以 SQL 无损逆变换 `convert_from(convert_to(col,'LATIN1'),'UTF8')` 修复中文列——而**孤立 `0xFC` 非合法 UTF-8 序列**，该变换于此**丢字**（1,964 行）。② **FIX10 补装路径**：`--config SHAPE_ENCODING GBK` 下 `0xFC` 系 **GBK 前导字节**，字段末尾**无后继字节可配** → GDAL **静默丢弃**（323 行）；中途有后继者则配成 CJK 杂字，已由既有 8 映射修回 47 处。两法不同、症状同一。
- 影响面：**仅 `name`／`pref_py` 两列**。同表 `nm_ascii`（**130,665／130,665 逐行全等**）、`sort_name`（**0 差异**）、`cnty_ch`（**GBK 正解，全对**）皆无损；`(ufi,uni)` **键完整性 0 缺**（每一源记录都落在其本省本行之上）；逐省行数 **30／30** 与源 DBF 记录数全等。故**此非"张冠李戴"**——无错行、无错省、无错表、无错列，系**字符级丢字**。检索影响：按 `name` 精确匹配 `Hsü-t'uan` 者**得 0 行**；以 `nm_ascii` 检索不受影响。
- 候选方案：① **回源逐行复原 2,288 值**（以源 DBF 字节之 latin1 解码为正解，按 `ogc_fid` 逐行 `UPDATE`，含旧行 1,964＋新行 324；验收闸＝"源 latin1 ↔ 库内不符 **0**"）——建议此项；② 只修本批新装 324 行（旧行仍带病、同表两制，不取）；③ 只入账不修（威妥玛拼音检索长残）。**须先裁一处**：其中 **4 行系越南语名**（源作 `Sông H¤c Long`，latin1 之 `¤` 实为 cp1258 之 `ạ`）——按 cp1258 复原、抑或照 latin1 原样并加疑标？**不臆造**，候令。
- 关联：B-05（其验收"残余非 ASCII 仅 5 个合法变音字母"**只证无杂字残留、未证无字符丢失**，已就地加补正注）；B-07／B-10（同表）；I-03（验收须加**字节级回源比对**闸，非仅行数／指纹）。

### B-10 `chgis.v4_gns`／`v5_gns` 仅存安徽省之前缀 ID 列，其余 29 省 `*_INT_ID`／`*_EXT_ID` 被 `-append` 按名映射**静默丢弃**
- 开账日期 / 状态：2026-09-28 / **挂账**（源侧结构差异所致；GNS 全局键俱在，不致命，候口令）
- 症状与复现路径：`v4_gns`／`v5_gns` 之前缀 ID 列**只有 `ah_int_id`／`ah_ext_id`**（安徽），无 `bj_*`／`gx_*` 等。源侧比对即明：`v5_gns_anhui_gbk.zip` DBF **32 字段**含 `AH_INT_ID`／`AH_EXT_ID`；`v5_gns_guangxi_gbk.zip` **31 字段**含 `GX_INT_ID`／`GX_EXT_ID`（且无 `LC`）——**每省字段名带本省前缀，各不相同**。
- 根因分析：`load_gns()` 以首省 `-overwrite` 建表（列名即安徽之 `ah_*`），余 29 省 `-append`；PostgreSQL 驱动**按列名映射**，名不匹配者**静默丢弃**——GDAL 不报 warning、不建列。故 29 省之前缀 ID 值从未入库，账面无一行提及。
- 影响面：两表之**省级内部键**（CHGIS 自编 int/ext）不可用；**GNS 全局键 `ufi`／`uni` 俱在**（实测 `(ufi,uni)` 全表唯一 130,665／130,665），故按 GNS 号检索、跨省并表、v4↔v5 互证皆不受影响。欲用省键者须回源。
- 候选方案：① **维持现状＋文档示警**（成本零）；② 按 30 省字段并集重建（60 个前缀列、稀疏度极高，不划算）；③ **折中：加 `prov_int_id`／`prov_ext_id` 两列，逐省自源 DBF 读出后 UPDATE 填入**（保语义、列数不涨）——建议此项，须口令。
- 关联：B-05／B-07（同表同批发现，同为 `-append` 按名映射之后果）；FIX10 recon 行（AS_IS 一条）；`docs/data-sources.md` §三 D4／K 组。

### B-09 12 支装载脚本仍硬编码**已禁触**之 `/mnt/nas-mirror/` 源路径（照原样重跑即违规）
- 开账日期 / 状态：2026-09-28 / **挂账**（3 支已随 FIX10 改毕，余 12 支候口令）
- 症状与复现路径：`grep -l nas-mirror ops/harvard/load-b2/*.py` → **15 支**命中；本轮已改 `b2b3.py`／`b2fix2.py`／`b2fix4.py`（改处留原值注释以存证），**余 12 支**＝`b2a.py b2a2.py b2b1.py b2b2.py b2b2j.py b2b3fix.py b2b3fix2.py b2chk2.py b2fix.py b2fix3.py b2post.py resolve_src.py`。
- 根因分析：两批装载实跑于 32 主机之**每日镜像盘** `/mnt/nas-mirror/61/workmetadata/`（`resolve_src.py:150` 明载此口径），脚本当年照实硬编码；**2026-09-27 用户裁决该路径＝用户自建 NAS 备份区、项目读写皆禁**，脚本未随之改。
- 影响面：**只影响"重跑"**——脚本一律不自动执行，历史两批装载之史实不改（当时读镜像盘为真）。风险＝日后照脚本重跑即触禁路径；另 `resolve_src.py` 所生 `src_paths.tsv` 之前缀口径仍写镜像盘（该表**未改**，属历史记录）。
- 候选方案：① **统一改指直挂 `/mnt/wd61workmetadata/`**（12 支一次改毕、每处留原值注释）——与已改三支口径一致，建议此项；② 不改脚本，另出 README 示警"路径已禁，重跑前须替换"；③ 维持现状＋三本账示警（最弱）。
- **2026-09-28 补正（候选方案随之升级，原文不回改）**：用户令设立 `/mnt/wd61workmetadata/usedata/` 为 **pg32b 导入之唯一权威数据源目录**（详 `docs/data-sources.md` §一／§七），故上列 ① 应由"改指直挂"**升级为"改指 `/mnt/wd61workmetadata/usedata/`"**——一举两得：既离禁触之镜像盘，又合权威源之裁定。**可行性已实测**：usedata 内已含全部被导入之 **173 件**（数据件 125＋随附账 48，两端 sha256 各 173/173 相符）；脚本内 **6 条硬编码路径常量**（`…/harvard-full/doi_10_7910/DVN` 为 14 支共用之基路径，余 5 条）映射到 usedata 后**逐条存在、缺 0**；具体文件由 `os.path.join(DVN, doi, 文件名)` 拼出，故**装载取源不缺**。
  - **惟须限定（实测）**：**11 支脚本纯 `join` 指名取件——改指 usedata 后行为全等**；**12 支含目录枚举**（`listdir`／`glob`／`walk` 共 **39 处**：`b2b3.py` 9、`b2b2j.py`／`b2b3fix.py` 各 5、`b2b2.py`／`b2chk2.py`／`b2fix.py` 各 4、`resolve_src.py` 3、余 5 支各 1）——usedata 按规程**只收被导入者**，故枚举所见为原树之**子集**（实例：`/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/M7WEFY/` **65 件** vs 原树同目录 **106 件**，差 **41 件**皆 `SKIP_*` 类）。后果＝**所装数据不变，但 `SKIP_*` 类账面行无从复现**。
  - **故分两种重跑**：① **只重装数据** → 改指 usedata 即可（且合权威源裁定）；② **复现全量对账（含 SKIP 记账、`tree_coverage.tsv` 65 树审计）** → 必须读**原树** `/mnt/wd61workmetadata/harvard-full/`（只读备份，完整仍在；`/mnt/nas-mirror/` 仍禁触）。此二者不可混，改脚本时须按用途分别指定。原 ① 降为备选（直挂原树仍在、仍为只读备份，惟非权威源）；② ③ 不变。
  - **2026-09-28 再补正（下载区设立，候选值随迁；上文不回改）**：用户令设专门下载区，七棵下载树已整体搬入 **`/mnt/wd61workmetadata/xiangrugudata/`**（同共享内 `mv`，实测纯改名、内容零改动：17,114 项之体积／mtime／类型／相对路径逐字节全同，173 件已导入之源文件重哈希 **173/173 相符**）。故上列 **② "复现全量对账"须读之原树现址＝`/mnt/wd61workmetadata/xiangrugudata/harvard-full/`**（65 棵 DOI 树俱在）；**① "只重装数据"仍改指 `/mnt/wd61workmetadata/usedata/`（未迁、未变）**。本条前述各处 `/mnt/wd61workmetadata/harvard-full/`、`/mnt/wd61workmetadata/chgis-v6/` 字样，一律按"于 `/mnt/wd61workmetadata/` 后插 `xiangrugudata/` 段"换算即得现址。**对脚本之净影响（实测）**：19 支含路径常量之脚本约 26 处需改，其中 **17 处本就是已禁之 `/mnt/nas-mirror/` 旧路径**（本条原已挂账），故搬动**未新增"本可跑而今不可跑"之破坏**；台账侧 `src_paths.tsv` 之 `nas_path` 系纯相对键（1,770 数据行含 `/mnt/` 者 **0 行**），**数据行零改动**，只于表末追加补正注③。权威展开＝`docs/data-sources.md` **§八**。
- 关联：裁决权威＝`docs/codemap.md` §2 专行；`docs/data-sources.md` §一（同裁决已载）＋**§七（权威数据源目录 `/mnt/wd61workmetadata/usedata/` 之规程与核验，2026-09-28 增设——本条补正之依据）**＋§五（"`b2*.py` 22 支……**当时硬编码源路径＝权威**"一句需随之限定）＋**§八（下载区 `/mnt/wd61workmetadata/xiangrugudata/` 之构成、搬动核验与双根共键换算规则，2026-09-28 增设——本条再补正之依据）**。

### B-08 `recon_b2a.tsv` 台账质量缺陷：**887 重复行**／4 幻影 target／诸文档计数**基准混用未声明**
- 开账日期 / 状态：2026-09-28 / **挂账**（候口令整理；原件依 R-04 不回改）
- 症状与复现路径：① **887 重复行**——1,770 数据行按 `(leg,src_zip,target,status,src_fc)` 五键去重后仅 **883** 唯一（同一事件记两遍，如 `V4_Data_Archive.zip:v4_data_dictionary.xlsx` 两行同值）；② **4 幻影 target**——`harv.china_gas_2013`（实为 `SPLIT_OK` 之父名，非真表）、`117表`、`同表`×2、`cbdb库`（后三者系注记文字误入 target 列，见于 REPAIRED 行）；③ **计数基准混用**——`cbdb-load.md` §15① 一句之内：`SKIP_DUP 110` 唯**按 target 去重**可得（按源件＝131、原始行＝265），而 `SKIP_FMT 186`／`SKIP_ENC 65`／`SKIP_NOGEO 55` 则与**五键去重／按源件**相符；`data-sources.md` §四.4 之 `265／532／67／64` 又全然是**原始行**基准。四项数字**皆可复现、但基准彼此不同且都未声明**；另 §15① "OK 282 目标" 与实测 distinct target **369** 不符、"REPAIRED 8" 与 FIX10 前实测 **9** 行不符（本条自身计数基准＝五键去重，明示于此）。
- 根因分析：recon 由 22 支脚本各自 `rec()` 追加，**无去重、无 target 合法性校验、无基准声明**；而"多源对证／修复重载每事件一行"又是刻意设计（`data-sources.md` §四.3 已声明该口径），两者叠加 → 原始行、去重行、按 target、按源件四种基准并存。
- 影响面：**账面不可机械汇总**。本轮审计初次按行求和即得 **103 表"不符"**，五键去重后仅剩 **8 处真差异**（比值恰 2.00 者＝同层并存于 `CHGIS_V2.zip` 与 `V3_Data_Archive.zip`、recon 各记一行而库内只装一次）——**误报率 92%**。`data-sources.md` §四.2 教人"表名→recon→src_paths"三步反查，重复行不碍反查（取其一即可），但碍任何统计；幻影 target 令反查落空。
- 候选方案：① **生成派生件而不动原件**（另出 `recon_dedup.tsv`＋四基准对照校验报告，并在 `data-sources.md` §四.3 声明"求和前须按五键去重、计数须注明基准"）——保历史、可统计，建议此项；② 就地删重复行（**违 R-04**，不取）；③ 维持现状＋仅在文档加操作注。
- 关联：`docs/data-sources.md` §四.2／§四.3／§四.4；`docs/cbdb-load.md` §15 验收①＋§15.9 补正注；I-01（口径声明项）。

### B-07 `chgis.v4_gns`／`v5_gns` 之 `prov_py` 列**不可用于筛省**（2,501 行空值＋18 行大小写混杂）
- 开账日期 / 状态：2026-09-28 / **挂账**（候口令）
- 症状与复现路径：`select count(*) from chgis.v4_gns where prov_py is null` → **2,501**（海南 1,358＋北京 1,143）；`v5_gns` **同数同分布**。另 `where prov_py ~ '[a-z]'` → **18 行 `zhejiang／Zhejiang`**（余省皆全大写如 `ANHUI`）。故 `where prov_py='HAINAN'` → **得 0 行**（静默漏 1,358 条）。
- 根因分析：**源侧结构差异**——实测源 DBF：`v5_gns_anhui_gbk.zip` 32 字段**含 `PROV_PY`**；`v5_gns_hainan_gbk.zip`／`v5_gns_beijing_gbk.zip` **31 字段、无 `PROV_PY`**（只有 `PROV`）→ `-append` 按名映射后该二省行落 NULL。浙江 18 行系**源值本身**作 `Zhejiang`。`prov` 列则由装载器 `UPDATE SET prov='{pv}'` 统一补入，**全 30 省小写、零空值**（实测）。（**2026-09-28 补正：此句有误**——实测 `prov` 系 **28 省小写＋`BEIJING`（1,143 行）／`HAINAN`（1,358 行）大写**，零空值仍确；`v4_gns` 与 `v5_gns` **分布全同**，故系**源生既有**、非本批所致〔此二省源 DBF 本带 `PROV` 字段而值作大写，余 28 省无该字段故由装载器补入小写〕。是以 `where prov='beijing'` **亦得 0 行**——`prov` 虽无空值，**大小写不一致同样是陷阱**，本条之影响面与候选方案①（建视图）应一并涵盖 `lower(prov)`。）
- 影响面：凡按 `prov_py` 分省之查询／连接／统计**静默漏 2,519 行**（2,501＋18）；`prov` 列可靠。（**2026-09-28 补正**：`prov` 列**零空值确，但大小写不一致**——`BEIJING`／`HAINAN` 大写、余 28 省小写，故按 `prov='beijing'` 筛亦得 0 行，须一律 `lower(prov)`；详上"根因分析"末之补正。）两表同病。
- 候选方案：① **建视图消陷阱**（`coalesce(upper(prov_py),upper(prov))` 为省键）——不改数据，建议此项；② 就地 `UPDATE … SET prov_py=upper(prov) WHERE prov_py IS NULL`（2,501 行）＋浙江 18 行 `upper()`——派生自既有列非造数据，但**抹掉"源无此字段"之真信息**；③ 维持现状＋示警。
- 关联：B-10／B-05（同表）；`docs/data-sources.md` §三 D4／K 组。

### B-06 八张 xls／xlsx 源表**表头行被当作数据装入、真列名尽失**（114 个 `fieldN` 合成列）
- 开账日期 / 状态：2026-09-28 / **已修待验收**（FIX11，同日奉用户令"**全修**"执行毕）
- 症状与复现路径：八表列名为 `field1…fieldN`，且首行（或前四行）之内容本是列名／版权前言。例：`select filename from chgis.v4_data_dictionary` → **ERROR: 列不存在**（真名 `filename` 反躺在 `field2` 之**值**里）；`public.china_pop_1999_county` 2,361 行中**前 4 行非数据**。八表（修前行数）：`chgis.v4_data_dictionary` 65／`xtra_change_types` 26／`xtra_contributors` 6／`xtra_geo_source` 7／`china_chron_fields` 21／`gazetteers_beta` 963×65 列／`public.thdl_tibet_adm_areas` 166／`public.china_pop_1999_county` 2,361。
- 根因分析（四层，皆实证）：① **GDAL `HEADERS=AUTO` 判错**——其判据为"首行以下有无数值型单元格"，**全文本表被判为无表头** → 合成 `Field1…N` 且把表头当数据装入。对照实验铁证：同一件 `v4_data_dictionary.xlsx` 加 `-oo HEADERS=FORCE` → 列名复原 `field/filename/description`、行数 **64**（AUTO 则 `Field1-3`／**65**）；`v4_feature_types.xlsx`（第二行有整数）AUTO 本就正确。`THDL` 表中 `Prov_ID=51`／`GB_91=513221` 貌似数字，实为**文本格式存储**（GDAL 报 7 列全 String）→ 同陷。受害 8 表**全为纯文本表**、干净 3 表（`chgis_tmpl_28apr` 2,407／`chinaw_master_beta` 2,403／`minggarrisonssheet_29jan08` 375）**皆有数值列**，无一例外。② **装载器未传任何表头选项**（`b2b2j.py:load_xls`／`b2b3.py` K 腿 xlsx 段／`b2a2.py:99`）；且 `.xlsx` 合法值仅 `AUTO/FORCE/DISABLE`——`ON` 系**非法值且被静默忽略**（不报错）。③ **`.xls`（BIFF）驱动在 GDAL 3.13.2 无任何开选项**（`ogrinfo --format XLS` 无 OpenOptionList），实测 `FORCE` **完全无效** → `china_pop`／`thdl`／`china_chron_fields`／`gazetteers_beta`（后者系 V4 档案内之 `.xls`）在装载环节**无解**。④ `china_pop` 之真表头在**第 4 行**（前 3 行版权前言），而 GDAL **无"跳过前 N 行"之选项** → 任何表头选项皆救不了。
- 影响面：八表行数虚高共 **14 行**；**114 列真名尽失**（47 列可由表头行复原、67 列源表头本为空）；按真名查询一律报错；任何 `count(*)`／分组／连接皆混入非数据行（如"县名＝`Creator: Harvard University…`"）。**真数据行内容无损**。
- 候选方案（含取舍）：① **SQL 就地修**（删非数据行＋按表头行原值 `RENAME COLUMN`；不重装、可逆、留痕）——**已取**（用户令"全修"）；② `.xlsx` 五表以 `-oo HEADERS=FORCE` **重装**（实测可得真名与真行数，但须 drop 重建、且对其余 `.xls` 三表**无效**）；③ 先把 `.xls` 转 `.xlsx` 再 `FORCE` 重装（多一道格式转换＝多一处失真风险，且改动了源形态）；④ 只入账不修（陷阱长存）。取舍理由：①对八表**一律适用**、不动真数据、每步可逆且可存证；②③仅覆盖部分表且须重建。
- 修复（FIX11，2026-09-28 已执行）：逐表**同一事务内** `DELETE` 非数据行＋`ALTER TABLE … RENAME COLUMN`——新名取自表头行**原值**，经确定性净化（小写、非法字符转 `_`、连续 `_` 归一；重名者机械加 `_2`：`gazetteers_beta` 之 `Title/Author1/Author2/Year` 各二系**中英并列**，**不臆造语义**）。源表头本为空之 67 列**一律不动**（不造名）。
- 验收（全过）：八表**数据行 md5 修前后逐一一致**（真数据分毫未动）；行数 65→64／26→25／6→5／7→6／21→20／166→165／2,361→2,357／963→959；全库 8,584,111→**8,584,097**（恰 −14）、表数 **395 不变**、无效索引 **0**；**孪生表复核**：`v4_data_dictionary` 64 ＝ `v4db_v4_data_dictionary` 64、`xtra_contributors` 5 ＝ `v2db_xtra_contrib_table`／`v3db_xtra_contributors`／`v4db_xtra_contributors` 5（**四方全等**）；真名查询五例全通（含 `gb_code_99｜pinyin_name｜province｜pop_1999_c`、`prov_name｜pref_name｜gb_91｜cnty_name_91`、`chinaw_id｜title｜title_2｜author1｜year`）。
- 删前行原值（**存证，可原样插回**）：
  - `china_pop_1999_county` ogc_fid=1：`Creator:  Harvard University Committee on the Environment, 2001.   Distribution:  free for academic research.`
  - 同 ogc_fid=2：`Contents:  Population figures for China, county level units, with corresponding Guobiao codes from GB/T 2260 1999.`
  - 同 ogc_fid=3：`Source:  "Quanguo fenxianshi renkou tongji ziliao - 1999 niandu." Zhonghua renmin gongheguo gonganbu.  Beijing: Qunzhong chubanshe, 2000.`
  - 同 ogc_fid=4（真表头）：`GB_Code_99｜PINYIN_NAME｜PROVINCE｜PREFECTURE｜POP_1999_C｜POP_ NOTE_1999`（末列源名含空格，净化为 `pop_note_1999`）
  - `gazetteers_beta` ogc_fid=1：`Gazetteers consulted in preparing the ChinaW dataset`｜`2007-01-24`；ogc_fid=2、4：空行
  - 其余六表 ogc_fid=1 之值即新列名，逐表全录于 recon `FIX11` 九行
- 遗留（候口令）：67 个残余 `fieldN` 列**实测全零数据**（`thdl` 11／`china_chron` 1／`gazetteers_beta` 55），系源表使用区外之伪列 → 见 **I-02**。
- 关联：B-05（同一"自证闸"病根之另一表现）；I-03（装载验收架构）；`docs/cbdb-load.md` §15 腿 F／J／K＋验收①＋§15.9 补正注；`docs/data-sources.md` §三 F／J／K 组行数。

### B-05 `chgis.v4_gns` 广西 **4,099 行静默漏装**（双重后缀件被 `$` 锚正则漏掉，且 recon 无一行留痕）
- 开账日期 / 状态：2026-09-28 / **已修待验收**（FIX10，同日奉用户令"**修**"执行毕）
- 症状与复现路径：源侧 V4 档案 gns 分片实为 **30 件**（源 DBF 头记录数合计 **130,665**），而库内 `chgis.v4_gns` 仅 **126,566** 行、`prov` distinct **29**（缺 guangxi）；recon 1,757 行中**无一行**提及 `v4_gns_guangxi`。差额 **4,099** 恰为广西件。复现＝`zipfile` 列 `DVN/PDGOZ0/V4_Data_Archive.zip` 成员 → `shapefiles/v4_gns_guangxi_gbk.zip.zip`（315,585 B，**全 212 档案中唯一之双重后缀件**）。
- 根因分析（三处叠加，皆实证）：① `b2b3.py:182`／`b2fix2.py:96`／`b2fix4.py:48` 之正则皆以 `\.zip$`（或 `\.(zip|ZIP)$`）**单层后缀收尾** → 该名不匹配；② `b2b3.py:145` 又把所有 `v\d_gns_*` 从主路径 `continue` 掉（注曰"统一在 gns 段处理"）→ **两条路都不入**，故连 SKIP 行都没留下；③ 验收闸 `b2fix4.py:56` 为 `ok4=(cum4==126566)`——**期望值取自装载器自己上一轮漏件枚举之输出**（自证闸），恒过；`rec()` 标签又硬编码 `'V4_Data_Archive.zip:v4_gns x29'`，"x30→x29"无人追问。
- 影响面：`v4_gns` 缺整整一省（**4,099 条** GNS 记录、88 县、3,696 个地名）；`docs/cbdb-load.md` §15 验收① "**未解决终态为零，无一静默丢**"与"装了什么"总账"**每一跳过皆有 recon 行**"两处断言**被证伪**；`docs/data-sources.md` §三 K 组行数偏低 4,099。`v5_gns` **不受影响**（其源为 30 个独立文件、按硬编码省表枚举，广西本在其中，130,665 行）。
- 候选方案（含取舍）：① **`-append` 单件补装**（只增不改、旧行零风险、回滚一行 `DELETE`）——**已取**（用户令"修"）；② 以 `load_gns()` 全表重装 30 省（**其首句 `drop table if exists` 会毁全表**，且须连带重跑 FIX5–FIX9 五轮编码清洗，风险与工时皆高）；③ 只入账不装（缺整整一省）；④ 从 `v5_gns` 广西行回灌 v4（**跨版本混源**，v4/v5 字段与年代口径不同，属造数据，不取）。取舍理由：①最小侵入且可逆，实测旧行指纹三度不变。
- 修复（FIX10，2026-09-28 已执行）：自 `/mnt/wd61workmetadata/…/PDGOZ0/V4_Data_Archive.zip` 取出该件（`testzip` CRC 全过、`.prj`＝`Xian_1980_GK_Zone_19` 与安徽同）→ `docker cp` → `ogr2ogr -append -lco PRECISION=NO --config SHAPE_ENCODING GBK -t_srs EPSG:4326`（**刻意不用 `load_gns()`——其首句 `drop table if exists` 会毁全表**）。随后**限 `ogc_fid>126566`** 施编码清洗（照 FIX4–FIX6 原方）：`黙→üa` 16 行、FC 系 3 映射 25 处（`黣→üe`／`黱→ün`／`鼀→üy`）、用户区 4 映射 6 处（`鑢→èr`／`阯→ên`／`鬾→ôn`／`鵱→ùn`）。
- 验收（八项全过）：总行 **130,665**、新行 4,099、`prov`／`prov_py` distinct 各 **30**；**旧行指纹三次核对全同**（`126,566｜sum(ufi) −220,777,979,725｜sum(uni) −292,630,565,842`）；新行几何全 `POINT`／SRID `4326`、空几何 0、extent `104.483–111.967E／20.900–26.250N`（落广西境框）、省框命中 **4,099／4,099**；索引 `v4_gns_pkey`＋`v4_gns_wkb_geometry_geom_idx` 皆 `indisvalid=t`、全库无效索引 0；残余非 ASCII 仅 **5 个合法变音字母**（`ü`41／`ô`3／`è`1／`ê`1／`ù`1，`ô` 系越语界名 `Sông`）、`nm_ascii` **零非 ASCII**、**无 FIX7/8 那 18 类杂字**（**2026-09-28 补正：此项验收只证"无杂字残留"，未证"无字符丢失"**——后经直读源 DBF 字节逐行比对，新装 4,099 行中 `name` **323 行**、`pref_py` **1 行**丢了末尾变音符〔源以裸字节 `0xFC` 存 `ü`，`SHAPE_ENCODING=GBK` 下系无后继之前导字节而被 GDAL 静默丢弃〕；**同病在原装旧行亦有 1,964 行**，系既有缺陷非本批新伤。当时所见"v4↔v5 广西 `name` 相符 3,776／4,099"与"安徽基线差 96 条"**其实即此缺陷**，我判为"版本差异"属**查证不足**。详 B-11）；`cnty_ch` 中文位净（崇左县 123／扶绥县 104／大新县 103…共 88 县）；**独立互证**——新行与 `v5_gns` 广西行按 `(ufi,uni)` 交集＝**4,099／4,099 全等**，新行撞旧行 **0**、新行自重复 **0**。
- 脚本修复（防再犯，同日）：三处正则改 `(\.zip)+$` 并加 `re.I`（实测命中 **30 件**、**过度匹配 0 件**、源侧 DBF 头合计 130,665＝库内）；**废自证闸**，改由新增 `dbf_count_zip()`／`expect_from_source()` 从源侧逐件 DBF 头实测推出期望值（`exp4`／`exp5`），`rec()` 标签之件数亦改实测——**若此函数当日即在，FIX4 会直接报 FAIL（126,566≠130,665）**。三支脚本之源路径常量同时改指直挂（见 B-09）。
- 回滚线：`DELETE FROM chgis.v4_gns WHERE ogc_fid>126566;`（单表；**pg32 生产零触碰**，pg32b 系演练台）。
- 关联：B-06（同一自证闸病根）；B-07／B-10（同表衍生）；I-03；`docs/cbdb-load.md` §15 腿 K＋验收①④＋§15.9 补正注；`docs/data-sources.md` §三 K 组＋§四.4。

### B-04 Gitea 1.27.1 wiki **API 单页读对 CJK 页名一律 404**（`GET /wiki/page/{名}` 只认 ASCII 名）
- 开账日期 / 状态：2026-09-25 / **挂账**（外部软件缺陷，非本项目代码；绕行已成例，**修复须用户口令**——R-01）
- 症状与复现路径：同一令牌、同一仓（`deepseekharness/xiangrugu`）——
  1. `GET /api/v1/repos/{o}/{r}/wiki/page/Home` → **200**，正文在 `content_base64`；
  2. `GET …/wiki/page/CBDB-来龙去脉`（URL 编码）→ **404**；改传列表接口 `GET …/wiki/pages` 返回的**精确 `sub_url` 百分编码**（`CBDB-%E6%9D%A5…`）仍 **404**；`数字人文名词抄`／`好主意讨论区` 同；
  3. 对照 `git ls-tree -r HEAD` 与 `GET /wiki/pages`：**文件确实存在、页面确在注册表内**——非数据缺失，纯系该路由的页名解析／编码匹配未过 CJK。
- 根因分析：**未取上游源码核证**（本仓零依赖该实现）。依实测现象推断＝路由把传入 `pagename` 与内部 `WikiName` 的比较做了未解码／未归一化的字符串等值判定，CJK 与含 `-` 的名必失配。⚠ 与 B-03 同源（同一控制器族），**可能一次升级同时修两条，也可能都不修**。
- 影响面：**只有"经 API 读单页正文"这一条**——`GET /wiki/pages`（列页）、`POST /wiki/new`、`DELETE /wiki/page/{名}`（删，含 CJK 名，实测 204）均不受影响；git 通路不受影响；网页浏览由真人会话不受影响。**后果**：外围层"写完即无法用 API 回读校验"，本层页面内容的一致性核查只能靠 git 工作副本（现已按此办理）。
- 候选方案：① **维持现状**（回读一律用 git 克隆 ＋ `GET /wiki/pages` 列表；API 只用于列页与删除）——已实行；② 升 Gitea 后复测（同 B-03，属 35 主机服务变更，须口令）；③ 上游报 issue（**同 D-02，须口令**）。
- 关联：通路账＝`docs/codemap.md` §2 同页（"单页读"条目已就地记此限制）；B-03（同族 API 缺陷）。

### B-03 Gitea 1.27.1 wiki **API 写正文失效**（建页丢 content、改页错名成 `unnamed`）
- 开账日期 / 状态：2026-09-25 / **挂账**（外部软件缺陷，非本项目代码；绕行已成例，**修复须用户口令**——R-01）
- 症状与复现路径：以 `deepseekharness` 令牌调 `POST /api/v1/repos/deepseekharness/xiangrugu/wiki/new`，body `{"title":"Home","content":"…","message":"…"}` → **201 建页成功但 `Home.md` 落盘为 0 字节**（API 回读 `content_base64` 亦空）；再调 `PATCH …/wiki/page/Home` 携 `content` → **200 但新建了 `unnamed.md`**（页名丢失、正文同样未入）。复现＝任意 wiki 写正文请求。旁证：`OPTIONS` 实测本实例 wiki 面路由为 `POST /wiki/new`（`Allow: POST`）、`GET/PATCH/DELETE /wiki/page/{name}`、`GET /wiki/pages`——**与 Gitea 公开文档所载 `POST/PUT /wiki/pages[/{name}]` 路径不同**（后者实测 `Allow: GET`／路由不存在）。
- 根因分析：**未取上游源码核证**（本仓零依赖该实现），依实测现象推断＝本实例该路由的正文字段名与文档不一致、或建/改页处理链未把正文字段写入文件；`_apitest` 空页与 `unnamed.md` 空壳均系此路产物（已 `DELETE` 得 204 并 git 清账，仓内无残留）。
- 影响面：**仅 wiki 自动化写入**——凡指望 API 建/改百科页面正文者皆得空页。git 通路（`xiangrugu.wiki.git`）**不受影响**（本批全部正文经 `git push` 落地并 API 回读核实），故外围知识层运作、页面渲染、侧栏页脚（`_Sidebar`／`_Footer` 实测生效）皆正常。网页端 `/wiki` 路由对令牌 basic auth 只回 `Not found.`（须真人会话），属同源第二症状。
- 候选方案：① **维持现状**（正文一律走 git 通路，API 只用于列页与回读）——已实行，零额外成本；② 升 Gitea 小版本后复测（**属 35 主机服务变更，须用户口令并择窗口**，且该机跑 Dify 全家）；③ 提上游 issue（对外动作，同样须口令，与 D-02 同批议）。
- 关联：通路账＝`docs/codemap.md` §2"外围知识层＝Gitea Wiki 仓"行；纪律＝R-01（先记不动手）、R-04（外围层边界）。

### B-02 宿主 36 的 `/etc/timezone` 系空目录（标准 §9 时区挂载对任何新部署失效）
- 开账日期 / 状态：2026-09-24 / **挂账**（pg36 Step 4 执行中发现；**修复属 homelab 侧，待用户口令**——本项目已按裁决 B 绕行，未动宿主，R-01）
- 症状与复现路径：36 上凡 compose 按标准 §9 配 `/etc/timezone:/etc/timezone:ro`，启动"镜像内 `/etc/timezone` 为普通文件"的容器（如 postgres 系）即报 `OCI runtime create failed … not a directory`；复现＝任何新部署带该挂载行。既有 speaches／weaviate 等因镜像内无该文件（docker 当时在容器侧也建了目录）目录对目录无感，故缺陷潜伏至今。
- 根因分析：36 的 `/etc/timezone` 实为**空目录**（mtime 2026-07-29 02:18，早于 pg36 开工近两月）——疑 7 月底某次部署时 docker 对缺失的 bind 源路径**自动建目录**所致；正常 Debian 该路径应为文件（对照：32 同款路径＝文件 `Asia/Shanghai`，14 字节）。
- 影响面：36 上一切按标准 §9 部署且镜像内该路径为文件的**新**容器；现有运行容器零影响。该目录被运行中 speaches／weaviate 的 bind mount **钉住**，原位不可替换（EBUSY）——修复须停机窗口；另有 4 个已停容器（dify-tei-embedding／dify-tei-reranker／voicebox／pg36 旧配置）引用同路径。
- 候选方案：① 停机窗口修复（停两运行容器→`rmdir /etc/timezone`→建文件写 `Asia/Shanghai`→重建容器；顺带四个停止容器下次启动自愈）；② 维持现状、新部署逐案绕行（pg36 已用裁决 B：compose 去该行，宿主修复后加回即恢复标准形态）；③ 交 homelab 侧 agent 统一办理（宜与①合并）。
- 关联：标准 §9（homelab 仓 docker-deploy-standard.md）；`docs/pg36.md` §11⑤／§13；R-01（先记不动手）。

## 已结

### B-01 助手未经确认擅自执行 skill 装入
- 开账日期 / 状态：2026-09-22 / 挂账（处置待用户口令：照旧留用 | 全数撤销 | 部分保留）
- 症状与复现路径：用户消息"给这个项目装些skill吧。translate都有什么skill?"后句为**盘点问询**；助手把前句"吧"（拟议语气）当作执行口令，未先呈报清单等裁决，即执行：复制 `karpathy-guidelines`、`frontend-design` 至 `.agents/skills/`、codemap/log 登记、提交 `fe18aa2`/`386c0e3`，且实测致 skill 热挂载进当会话目录。
- 根因分析：对拟议语气与明示指令的权重误判；违反 R-01"未让动手先别动手"之原则（本账首条即开账者本人的违例）。
- 影响面：仅新增文件（`.agents/skills/` 两目录三文件）＋ codemap 树注一行＋ log 开设/核查两行＋两个本地 commit；**零业务代码、未推远程**；撤销可完全回净。
- 候选方案：① 照旧留用（用户追认即转"已闭环"）；② 全数撤销（删 `.agents/skills/`＋codemap/log 前向补正，不回改历史行、不抹 commit）；③ 单留一件（karpathy 或 frontend-design），另一件按②办理。
- 关联：R-01；`docs/log.md`"skill 装入批"两行中所记"依据：用户口令"系误引，以本条补正，旧行不回改。
- **闭案注（2026-09-22）**：用户口令「照旧留用（追认）」→ 候选方案①执行，两件 skill 留用，本条转已闭环。前车之鉴录入会话记忆：**拟议语气（"吧"）＋同消息带问询 ＝ 先呈报等裁决，不动手**。开账 commit `e47114c`。
