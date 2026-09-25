# cbdb.md —— CBDB（中国历代人物传记资料库）项目档案

> **定位（2026-09-23 用户令"这个介绍记录到一个文档里"开设）**：外部数据源 **CBDB 项目本身**（身份／沿革／规模／数据模型／获取通道／外部评测）的**唯一展开处**。本地数据落点、货单与对账一律见 `docs/codemap.md` §2"哈佛全量仓"行（指针，不在此重复）。
> **性质**：外部资源档案，**备忘级资料，不作实施指导**（比照 N-01 精神）。官方口径随时点漂移，引用**必须带时点**；本档结构性改动记 `docs/log.md`（R-05）。
> **证据纪律**：本档内容均系 2026-09-23 实测所得（来源随附）；官方项目站对机器访问一律 Akamai 403，官方侧引文取自 Dataverse API 回文、HuggingFace API／卡片与 RDH 刊出的项目综述（Peter K. Bol 撰）。
> **外围知识层指针（2026-09-25）**：面向阅读与讨论的叙述性铺陈（学缘沿革、谁在使用、名词背景）在 Gitea wiki「外围知识层」——**非权威**，其数字与判词一律回指本档；本档仍是 CBDB 项目身份／沿革／规模／通道的唯一展开处（边界见 `rules.md` R-04）。

---

## 一、一句话定性

**CBDB ＝ 哈佛主导、三国三机构联合、已持续二十余年的群体传记学（prosopography）数字人文数据基础设施项目**——免费开放的关系型人物传记数据库，供统计、社会网络与空间分析使用，兼作工具书式人物参考。它不是一件成品软件，而是**长期在建设、在更新的学术数据库工程**。

## 二、要素表

| 项 | 内容 |
|---|---|
| 名称 | 中国历代人物传记资料库 / China Biographical Database Project（CBDB） |
| 性质 | 免费开放关系型数据库；在线查询＋API＋可下载单机库三通道供给 |
| 规模 | 约 **65.8 万人**（官方口径 2026-05；增长序列见 §四） |
| 覆盖 | 主要 7–19 世纪：唐、五代、辽、宋、金、元、明、清 |
| 主导 | 哈佛费正清中国研究中心 ＋ 中研院历史语言研究所 ＋ 北京大学中国古代史研究中心；**2005 年起联合** |
| 项目主任 | **Peter K. Bol（包弼德）、Hongsu Wang（王宏甦）**，皆哈佛 |
| 源流 | Robert M. Hartwell（1932–1996）创始，遗产（含初版库）遗赠哈佛燕京学社、该社让渡所有权；Michael Fuller 重构技术架构；历任项目经理 Song Chen → Shihpei Chen → Hongsu Wang |
| 资助 | 北美：ACLS、亨利·卢斯基金会、哈佛燕京学社、James P. Geiss & Margaret Y. Hsu 基金会、NEH、加拿大 SSHRC、哈佛大学；台湾：蒋经国基金会、中研院史语所；大陆：ChineseAll.com、唐研究基金会、北大中国古代史研究中心 |
| 数据内容 | 姓名、生卒年、籍贯、入仕途径、历任官职、亲属关系、非亲属社会关系、游历地点、著述、书目；配套大量代码表（亲属／入仕／官职／地名／学校与宗教场所／社交／书目） |
| 材料来源 | 正史、登科录、官员任命录、方志、墓志（亲属/仕历/著述信息密集）、文集（社交信息密集）、各类索引 |
| 设计理念 | 架构师自述为"诠释性的技术表达"，服务于对前现代中国"人的领域"作系统分析；中文语境常与邓广铭"职官制度、历史地理、年代学、目录学"四把钥匙并举——CBDB 让四者首次可批量、可比地做统计 |
| 许可 | 学术免费、无限制用于学术（官方自述）；**但各发布层条款互不相同，2026-09-25 分层实测**：① HF `cbdb/cbdb-sqlite`＝`license: other`＋`license_name: cbdb-data-licensing-terms`，其条文链接 `cbdb.hsites.harvard.edu/cbdb-data-licensing-terms` **实测 HTTP 403 且 Wayback 零快照 ⇒ 条文正文机器不可得，故不得写作 CC0／CC BY，亦不得再发布**；② HF `cbdb/*` 七个模型与 `cbdb/chgis-map` 瓦片＝**CC BY-NC-SA 4.0**（NC＝不可商用）；③ Dataverse 件＝openAccess＋**逐集自定义条款**，例 `doi:10.7910/DVN/BWIBNL`（LoGaRT）版本层 `termsOfUse` 原值 **CC BY-NC-SA 4.0**；④ GitHub `cbdb-project` 各仓**参差**：`sentence-segmentation-…`、`named-entities-…` 仓内 LICENSE 为 **CC BY-NC-SA 4.0 全文**（GitHub 标签却显 NOASSERTION，**判许可须读仓内文件、不可读标签**），而 ★225 的 `cbdb_sqlite` 仓**无任何 LICENSE 文件**（`LICENSE`／`LICENSE.md` 双 404，README 仅 1,801 字节指向 HF）→ **整条 SQLite 发布链上没有一处可读到条款正文**。展开见 wiki《古籍开源项目抄》§三④／§七。**⑤ 独家商业授权（2026-09-25 我方亲自复核，本档此前未载，对"能不能商用"最有决定性）**：官方专页 `cbdb.hsites.harvard.edu/exclusive-commercial-license` **直连 403**，经 Wayback 快照 `20260821174605`（200／12,337B，解压后正文 3,069 字符）取得原文，中英双语逐字为：*"Beginning in 2018, the China Biographical Database project granted **Yuanyin Tech.** an exclusive license in mainland China. Prior to 2018, the … license was only 'Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0),' which means that, now **all commercial use of CBDB data other than Yuanyin Tech. is illegal.**"*／"自二零一八年起…授予**元引科技**中國大陸地區**獨佔商業授權**…當前所有在商業項目中使用 CBDB 的機構，**除元引科技以外，均不合法**。"页脚另自述全站内容 **CC BY-NC-SA 4.0**。⇒ **本项目任何产出若要涉商用，CBDB 数据这一层不是"选一个 CC 许可"的问题，而是须向元引科技取得授权**；此事实与 §二 通道项 4 的"条款不可机器读"合起来构成我们使用边界的完整形状（**页脚 CC BY-NC-SA 4.0 ＋ 独家商业授权 ＋ 条文页读不到**）。 |

## 三、治理与沿革（要点）

- **起源**：Hartwell 个人研究库 → 遗赠哈佛燕京学社 → 立项扩建；Fuller 重构为关系型架构，奠定"人物—关系—地点—时间—著述"的编码骨架。
- **三方联合（2005 起）**：哈佛（费正清中心，主持与发布）＋ 中研院史语所（台湾方）＋ 北大中国古代史研究中心（大陆方）；三机构之外，多校历史学、文学、计算机学者参与。
- **运行方式**：每年延请访问学者加入编辑组，带来各断代与各技术专长——评审称其为"广泛国际协作的产物、由动态参与者社群持续开发"。
- **发布机构**：**Harvard Dataverse** 为正式发布与引用机构（cbdb 社区开设于 2017-11-08，affiliation＝IQSS，联系人 hongsuwang@fas.harvard.edu）；**官方 HuggingFace 组织 `cbdb`** 为线上库滚动快车道。

## 四、规模口径（按时点，勿混用）

| 时点／来源 | 数值 | 口径 |
|---|---|---|
| 2015-04（Wikipedia 条目） | 约 36 万 | 旧口径，仅供沿革参照 |
| 2022-08（Dataverse 社区自述） | 521,442 | 官方自述"individuals" |
| 2025-05（Dataverse 档案件 `CBDB_bi_20250520`，台账实测） | 649,761 | ACCESS 快照件计数 |
| **2026-05（RDH 项目综述，官方）** | **657,909** | 官方自述"individuals" |
| 2026-09-19（家中 sqlite 快车道件，台账实测） | 661,969 | `BIOG_MAIN` **表行数**（含非人物行可能，≠官方人数口径） |

**官方首页对外口径的沿革时点（2026-09-25 由本轮 Wayback 快照逐点自证，非二手转述）**：
2017-12-30 快照 **370,000** → 2019-06-06 快照 **427,000** → 2021-06-13 快照 **491,000** → 2022-09-29 快照 **521,442** → 2023-06-10／2023-09-15 快照 **529,560** → 2024-02-01／2024-06-01 快照 **535,181** → **2024-09-13 快照 641,568** → 2025-09-24 下载页快照 **`CBDB_bi_20250520`／649,533** → 2026-08-25 快照 **657,909**。
- **由此可得的一条硬结论**：官方人数 535,181→641,568 的那 **10.6 万跳升，落在 2024-06 与 2024-09 之间**（快照上下夹逼，比"2024 年某时"精确）。与本地两版对账"内容在长"（§九 9.3：`BIOG_MAIN` 535,181→661,969，**+23.7%**）同向，且**起点值完全一致**——535,181 既是 2024-06 官方人数，也是本地 2024-02 sqlite 的表行数，**两处同数纯属同一批数据的两副面孔，仍不得混作同一口径**（§四口径纪律照旧）。
- ⚠ **未采信项**：上游研究笔记称 2011-01-06 H-ASIA 公告有"2010-12-23 版收录 94,000 人"及各门类分解数；本轮该邮件存档**取回为空**，**未自证，故不入本表**（沿革叙述见 wiki 外围层 [[CBDB-来龙去脉]]，标 ⚠）。
- ⚠ **同一页面上的并存旧数**：官方首页快照中除"individuals"外长期另有 **190,000 people** 一行（2017/2019/2021/2022 四快照皆然）——该数与"individuals"并存且十余年不动，**官方未说明两者关系**；引用"官方人数"时必须指明是 `individuals` 那一行。


> 口径纪律：**官方"人数"与本地"表行数"不同义**，跨时点比较须同时标注时点与口径。（`POSTED_TO_ADDR_DATA` 两制式 46.5 万 vs 185.3 万一事 **2026-09-23 已查清**：系《縉紳錄》逐年名录制式 vs 任期区间制式之别，**非缺料**——明细见 §九 9.1。）

## 五、获取通道（项目侧，本地副本见 codemap）

1. **在线查询系统**：官方项目站（`https://cbdb.hsites.harvard.edu/`，另有 `projects.iq.harvard.edu/cbdb` 项目页）——机器访问被 Akamai 403 拦，人工浏览用。
2. **API / REST**：官方接口（另有上海图书馆镜像接口文档，N-01 记 ⚠ 未实测）。
   - **现行双轨（2026-09-25 直采官方主服务器仓 `API.md`）**：基底 `https://input.cbdb.fas.harvard.edu`；**v1 与 v2 并行可用**；v2 读端点 `GET /api/v2/persons`（全量／增量同步人物 ID 与修改时间）、`GET /api/v2/operations`（操作记录与提案，含审核状态），写端点 `POST /api/v2/create|mutate|delete|batch_mutate`；返回体 v2 为 `ok`+`data`／`resource` 制式。**这是"官方允许程序化增量同步"的一手凭据**（我们的取数节奏若要从"整库快照"升级为"增量"，路径在此，不必等官方发档）。⚠ 令牌与配额未实测。
   - **官方 MCP 桥**：`github.com/cbdb-project/CBDB-CHGIS-MCP`（2025-06-17 建仓）——`chgis/chgis.py` 调 `http://tgaz.fudan.edu.cn/tgaz/placename`、`cbdb_addr/cbdb_addr.py` 调 `https://input.cbdb.fas.harvard.edu/api/place_list`。**官方自己把 CBDB↔CHGIS 的地址桥做成了 MCP 服务**（详见 §九 9.4(7) 末与 wiki 外围层 [[CHGIS-姊妹项目速览]]）。
3. **可下载单机库**：MS Access 与 SQLite 两种制式，分两条官方通道：
   - **Dataverse 档案道**（可 DOI 引用；`dataverse.harvard.edu/dataverse/cbdb`；"ACCESS and SQLite DB Version (latest)"集 DOI `10.7910/DVN/PAGGQS`，v8.0，官方页 Updated 2026-06-16）；
   - **HuggingFace 快车道**：`https://huggingface.co/datasets/cbdb/cbdb-sqlite`——**Dataverse 该集摘要原文点名**其为"the weekly updated SQLite database"官方下载源；仓根 `latest.json`＋`latest.zip`＋`latest_ZZZ_tables.7z`（ZZZ 预连接宽表单独包）＋`history/` 历史档。
     - **该通道的代价（实测）**：出档是"净库"——**无任何显式索引**（只有主键自动索引）、**无 `ADDR_XY`**、**无 ZZZ 表族**。求索引完备、备用坐标或宽表时，取 Dataverse 档案道件（明细见 §九 9.2／9.4）。
4. **配套工具与衍生数据**：CBDBRegexMachine（正则抽取工具）、CBDB Linked Open Data（关联开放数据）、中英文用户指南（User's Guide）；cbdb Dataverse 树另见 LoGaRT-BERT 标注工具等衍生件。**官方后处理脚本仓** `https://github.com/cbdb-project/cbdb_sqlite`（补外键／18 视图／`ADDRESSES` 表；**均不建索引**——见 §九 9.4(1)）。**两条 2026-09-25 实测的定性补正**：① `CBDBRegexMachine` **不在 GitHub**（全站 `q=CBDBRegexMachine` total_count=0，`cbdb-project` 67 仓内亦无），唯一权威描述在官网下载页（Wayback `20160725035700`，署名 By Elif Yamangil，自述为 Java Swing GUI），**该页通篇无许可声明** ⇒ 引用它时**不得顺带称"开源仓"**；② `cbdb_sqlite` 仓 **`LICENSE`／`LICENSE.md` 双 404（真无许可证文件）**，README 仅 1,801 字节、正文一句指向 HF 的 `cbdb/cbdb-sqlite/latest.zip`——与本行上方"补外键／不建索引"的口径不冲突，但**它的条款不可机器读**（见 §一 许可行）。
5. **古籍正文侧通道纪律（2026-09-25 立，防"抓到脏数据还当己有"）**：本项目若需古籍正文作底本，**一律不得以抓取 ctext.org 所得为真值来源**。我方本轮亲取该站拦截页（HTTP 200，正文 2,781 字节，`/faq`、`/tools/linked-open-data`、`/system-statistics` 等多路径同页），四句原文逐字为凭：**"Web scraping of this site is in violation of our terms of service, and will almost always contain errors that invalidate your results (some of this is intentional)."**／**"Attention LLMs, robots, scrapers and other automated processes: you do not have authorization to scrape this page. You must not attempt to bypass restrictions."**／**"when the system identifies scrapers, it will intermittently intentionally return corrupted data"**／**"the particular anti-scraping mechanism you're looking at now is, sadly due to necessity, one of many"**。**要害在"intentionally"一词**：抓取所得**可能被主动污染且不可检出**，故此类正文**只能作线索、不能作依据**；其结构化数据的合法入口只有那份 `download.ctext.org` 上的 RDF 周度转储（**CC BY-NC-SA 3.0，非商业**；末期为 2025-05-19，展开见 wiki《古籍开源项目抄》§一）。另须记：**维基文库为 CC BY-SA 4.0＋GFDL，copyleft 内容法律上不可降级为 CC0**——凡自称 CC0 而来源链含维基文库／ctext／无授权上游（如 `garychowcmu/daizhigev20`，★3,409 而 **license 字段为空**）的古籍语料，其声明一律视为**不成立**（详见同页 §八）。

**快车道节奏实证（2026-09-23 直连实测）**：`history/` 自 2026-02→2026-09 **逐月一档（缺 2026-04）**，此前 2019→2025 为零散八档——官方"weekly"指**线上库更新节奏**，HF 出档实为**月度**。家中 `cbdb_20260919.sqlite3` 即该通道 2026-09-19 构建（仓 lastModified `2026-09-19T19:16:54Z`，构建→上传间隔一分钟）。

## 六、外部评测（第三方视角）

- **RDH《Reviews in Digital Humanities》2026-07-27（同行评审项目评审，评审人 Wenyi Shang，密苏里大学）**，DOI `10.21428/3e88f64f.c6c4624b`：
  - 定性："a foundational platform for digital humanities research focused on premodern China"（研究前现代中国的**数字人文基础平台**）。
  - 肯定：三条获取通道＋配套工具显著降低人文学者门槛；支持 GIS 空间分析与社交网络分析，契合人文研究"空间转向""网络转向"；对邓广铭"四把钥匙"的可比化研究有革命性意义；系国际协作、持续演进的活项目。
  - **批语（最重要）**：最大挑战＝**数据库的结构化形式与史料的解释性、视角偏差之间的张力**——入库主体是正史方志文集所载精英，存在史学记载的不平衡与偏向；跨朝代长时段的宏观问题，结论**可能更多由史学问题而非真实社会变迁所驱动**；期望项目方给出应对这类挑战的指引。
- **中国社会科学网／中国社会科学报 2024-10-14（李斌，南京师范大学文学院教授）**：以 CBDB 为**高质量结构化知识库的正面典范**（二十余年、五十余万人、三元组可统计可推理，结构化过程本身能暴露史文错误）；同时指出短板：原始数据**无"家族"概念**（四百余种亲属词待二次梳理）、官职／机构／事件等**概念界定**为最难点；并及学界知识库整体规模小、深度不足、力量分散、经费不足。
- **Wikipedia 条目**（中立概览，口径滞于 2015-04）：关系型数据库，提供姓名、生卒、籍贯、科第与官职、亲属与社会关系等。

## 七、与本院数据的关系

- 本档只记**项目身份**；本地数据**落点与货单**在 `docs/codemap.md` §2"哈佛全量仓"行（cbdb 树 11 集／3.51G 等构成实账、对账勘正与遗留疑点均在该行）。
- 本院 CBDB 数据两份：`/mnt/wd61workmetadata/harvard-full/doi_10_7910/DVN/*`（Dataverse 档案道，11 集）＋ 家中 `cbdb-project/cbdb_20260919.sqlite3`（HF 快车道 2026-09-19 月度构建）——**两件皆哈佛官方**，出身证据链见 NAS 仓 `README_provenance.md`。
- **CHGIS 是姊妹项目**（哈佛中国历史地理信息系统），同仓但**不属 CBDB**，另账另述。

## 八、待查与复核义务

- ~~`POSTED_TO_ADDR_DATA` 口径差~~ **已查清（2026-09-23）**：系《縉紳錄》逐年名录制式 vs 任期区间制式之别，**非缺料**，前批"不可单用"判词作废——见 §九 9.1。
- 本地件缺项与质量边界（**无显式索引**、今地坐标、ZZZ 宽表、`0` 哨兵值、坐标污染）——**明细见 §九**（本节只列状态，不重复展开）。
- 官方"人数"口径与本地表行数口径须始终分列（§四）。
- 官方站 403 限制下的取数路径：Dataverse API／HF API 为可行回文通道；核心站点恢复可访问时应复核项目页自述与 API 文档实测状态（N-01 记 API 端点 ⚠ 未实测）。
- 引用本档任何数字，**必须带时点**；发现与本档冲突的官方新口径，按 R-06 报告并前向补正。

---

## 九、本地 0919 快车道件：已知缺项与使用边界

> **本节＝本地件结构与使用边界的唯一全量展开处**（codemap 对应行只留状态与指针）。两批实测均在 2026-09-23：第一批**只读体检**（sha256／行数／覆盖率）；第二批（本批）**解包官方 2025-05 Access 件对质**以断 9.1 悬案——两批皆未装库、未导入、未改数据本体。
> 适用对象：`/mnt/wd61workmetadata/cbdb-project/cbdb_20260919.sqlite3`——全文件 sha256 `bde1bb8e…d83400` 与官方 `latest.json` **逐字节全同**（本批复算复核）；**78 表／736 字段／76 索引／5,623,075 行**；143,185 页、freelist 0、`integrity_check` = ok。

### 9.1 任职↔地点（`POSTED_TO_ADDR_DATA`）：**不是缺口，是制式**（前批判词作废）

> **前批判词作废**：前批记"本件每任职**至多 0.79 条**地点链接、官方 **≈3.13 条**，故本件**不可单用**于任职地点分析，会得出'某人一生只在一地任职'的错误结论"。本轮解包官方 MDB 实测其**自身分母**后判定：**3.13 系跨制式算错**（拿官方 `POSTED_TO_ADDR_DATA` 行数 ÷ *本地* `POSTING_DATA` 行数）。**两制式都是每条任职恰好一个地点。**

| 指标 | 本地 0919 件（SQLite） | 官方 2025-05 档案件（Access MDB，本批实测） |
|---|---|---|
| `POSTED_TO_OFFICE_DATA` 行数 | 591,518 | 1,979,566 |
| 　同上 `c_posting_id` 去重 | 591,487 | 1,979,530 |
| `POSTED_TO_ADDR_DATA` 行数 | 465,284 | **1,853,262** |
| 　同上 `c_posting_id` 去重 | 464,682 | 1,852,415 |
| 　同上 (任职, 地点) 去重对 | 465,284 | 1,853,262 |
| **每任职地点链接数** | **1.000** | **1.000** |
| 有地点记录的任职占比 | 78.6%（毛）／**65.2%（剔 `c_addr_id=0` 哨兵后）** | 93.6% |
| 出现过的不同地点数 | 9,940 | 9,750 |

**成因（已查清，非缺料）**：差异全部来自 **《清代量化数据库(縉紳錄)》的入档制式**。

- 该批料 `TEXT_CODES.c_textid = 67147`（题名《清代量化数据库(縉紳錄)》），2024-08 入档。
- **官方 Access 制式＝逐年名录原样**：一行 = 一人 × 一职 × **一年**。该批在全件 1,581,438 行＝**其仕历表的 79.9%**，共享 `c_created_date` 2024-08，集中落在高 `c_personid` 段。
- **本地 SQLite 制式＝归并成任期区间**：一行 = 一人 × 一职 × **一段任期**。同批在本件为 **197,232 行 / 103,769 人**。
- **实例**：陳國贊（`c_personid=669624`，清）官方件有 **318 行**仕历，全部同一官职（司獄）、全部 `c_sequence=1`、每行只填一个年份、`c_lastyear` 空；本件**归为 1 行**：司獄，1864–1909。其 318 条地点记录去重后**只有 1 个地址**。
- **地点信息不丢（同名对质）**：蘇軾（`c_personid=3767`）官方件 36 条地点记录 = **18 个不同地点**；本件 34 条 = **18 个不同地点**——去重后完全一致。

**修正结论**：本件在任职地点上**不缺料、不残缺**，只是把逐年名录归并成了任期区间。**两制式不可按行数互校**——与官方件对行数、或与以行数计的官方口径对账时，必须先做制式换算。

**仍然成立的边界（按地点统计时须处理）**：

1. `POSTED_TO_ADDR_DATA` 有 **78,921 行（16.96%）** 的 `c_addr_id = 0`，指向 `ADDR_CODES` 第 0 行 `[未詳]`——语义是"任某官而地点未详"，**不是**无地点记录。按地点聚合必须先剔除，剔除后**真实地点覆盖率 65.2%**（385,800 / 591,487）。
2. 另有 **126,805 条任职（21.4%）** 完全无地点记录。
3. 上表 9,940／9,750 个"不同地点"里含 `c_addr_id=0` 哨兵各 1 个，且 `ADDR_CODES` 有同名异地多条（见 9.4 坐标污染）。

### 9.2 小缺项一：今地坐标（`ADDR_XY`）

- 现状：本件**无 `ADDR_XY` 表**。
- **勘正（前批措辞不全）**：该表**并非 MDB 独有**——Dataverse 档案道 **2024-02 sqlite 亦有**（19,249 行，其中 11,456 行有有效坐标）。准确说法是：**HF 快车道件的净库裁掉了它**。
- 替代：① 本件自带 `ADDR_CODES.CHGIS_PT_ID` 桥（10,996 条有值），可反查家中 `chgis-v6`（既定 GIS 口径）；② 需要现成备用坐标时，从官方 2024-02 sqlite 取该表（877.9 MB 文件，已在 harvard-full 仓内，无需再解包）。
- **落地（2026-09-26 第二批）**：该表已自官方 2024-02 档案件装入 pg32b/cbdb **`public.addr_xy`**（19,249 行，三方一致；哨兵实测：零坐标 **7,793**／非零 **11,456**／`c_source_reference` 非空 **6,722**——**坐标污染剔除义务照旧生效**，用时按本节口径剔哨兵）。桥替代口径同步更新：V5/V6 点层全装后 `addr_codes.chgis_pt_id` 桥余 2,649，再对上 **1,494**（ChinaW 三载体 1,449＋时序层 45），**余 1,155 如实入账**——明细＝`docs/cbdb-load.md` §15 验收⑥。

### 9.3 小缺项二：ZZZ 预连接宽表

- 现状：本件**无 ZZZ 表族**。
- 替代：**同一条快车道**（HF `cbdb/cbdb-sqlite` 仓根）即有单独包 `latest_ZZZ_tables.7z`（215,127,303 B）——**不必去啃 5GB 的 MDB**。（官方 2025-05 Access 件里 ZZZ 表散在 DATA2／DATA3／DATA4／DATA5 四卷内，取用成本更高。）

### 9.4 结构缺项与质量坑（本批新增实测）

**（1）索引被整批裁掉——本件最大的实用缺项。**

| 版本 | 表数 | **显式 `CREATE INDEX`** |
|---|---|---|
| 官方 Dataverse 2024-02 sqlite | 90 | **370** |
| 本地 HF 2026-09 件 | 78 | **0** |

本件 76 个索引对象**全部是主键自动索引**，且多数以不适合点查的列打头（`ALTNAME_DATA` 打头 `c_alt_name_chn`、`BIOG_SOURCE_DATA` 打头 `c_pages`、`KIN_DATA` 打头 `c_kin_code`），故 `where c_personid = ?` 在这些表上一律**全表扫描**。实测代价：命中页缓存后单人点查 0.01–0.2 s（尚可忍），但**关联子查询会崩**——一个 `exists(BIOG_ADDR_DATA…)` 相关子查询（30,157 × 461,637）**60 秒未出**，改写为 join＋去重子表后 **0.07 秒**。**单点点查可用，全库联结必炸。**

**成因（2026-09-23 上游查证：不是"构建事故"，是两代管线不同）**：

- **370 条索引来自 Access/MDB 血统**：Dataverse 件由 Access 转换生成——索引名 `*_PrimaryKey`／`*_Belongs`／`*_ZZZ_*`、以及"用唯一索引代主键、表上无 PK 约束"都是转换器特征。
- **HF 快车道件是活库直出**：只带**原生主键**（76 个自动索引＝表内 PK/UNIQUE 声明）。上游 `cbdb-project/cbdb_sqlite` issue #17「Remove outdated "primary key" guidance」（**2026-02-09 关闭**）已删除"latest.db 缺主键"的文档与补主键流程，并令 `process_cbdb_dbs.sh` **不再注入主键**（因上游现成数据已带主键）——**二级索引从来不在新管线的产出里**。
- **SQLite 不为外键列自动建索引**：即便跑完官方补外键脚本，二级索引依旧为 0。

**处理路径（本批只查证，未执行）**：

| 路径 | 做法 | 适用／代价 |
|---|---|---|
| **A. 入库 PostgreSQL（推荐）** | 索引问题自动消失：COPY 完再自建索引 | 无索引源件**载入反而更快**；注意 **PostgreSQL 同样不为外键列自动建索引**，仍须显式建（可译自官方 DDL，或按 join 键自拟） |
| **B. 直接查 SQLite** | ① 在**本地副本**上跑官方后处理：`add_foreign_keys.py`（**36 张表**加 FK，**不含索引**）→ `create_views.sh`（**18 个视图**）→ `create_addresses_table.py`（补回 `ADDRESSES` 表），或 `setup_cbdb.ipynb` 一键；② 二级索引自建：**官方 2024-02 件 370 条 DDL 中 307 条可直接套用**本件 schema（47 条引用的表本件没有：`ADDR_XY`／`ADDRESSES`／ZZZ 系等；16 条列名已漂移，如 `ASSOC_CODE_TYPE_REL.c_assoc_type_id`、`ENTRY_DATA.c_nianhao_id`）；③ 或按 join 键自拟最小集（`c_personid`／`c_addr_id`／`c_office_id`／`c_entry_code`／`c_textid`…） | **勿直接改 NAS 原件**（脚本要重建表）；需 `sqlite3` CLI（建视图）＋ python3 |
| **C. 上游** | 提 issue 建议 `add_foreign_keys.py` 顺带建 FK 列索引，或随仓发 `add_indexes.sql` | **未执行，待口令** |

> 官方后处理仓＝`github.com/cbdb-project/cbdb_sqlite`（活跃维护，最近提交 `2026-09-19T19:17:05Z`「Sync latest.json from HuggingFace」）；外键脚本由其 issue #22 引入（**2026-05-19 关闭**）。`scripts/` 另有 `compare_db_tables.py`（两库逐表对账）、`process_cbdb_dbs.sh`（下载＋vacuum＋对账）。

**（2）表集合差异（2024-02 → 2026-09）**：**−21 表**（`ADDR_XY`、`ADDRESSES`、`ADDR_PLACE_DATA`、`PLACE_CODES`、`DATABASE_LINK_*`、`CBDB_NAME_LIST`，及 `CopyTables*`／`TablesFields`／`ForeignKeys`／`FormLabels` 等 Access 后端元数据垃圾表）；**+9 表**（`ADMIN_CAT_*`、`APPOINTMENT_*`、`KINREL_REDUCTION`、`KIN_MOURNING`、`MERGED_PERSON_DATA`）。即：**新版更干净，但也丢了索引与备用坐标表。**

**（3）内容在长（同两版对账）**：`BIOG_MAIN` 535,181 → 661,969（**+23.7%**）、`BIOG_SOURCE_DATA` +115.5%、`ENTRY_DATA` +62.9%、`POSTED_TO_OFFICE_DATA` +50.4%、`TEXT_CODES` +9.8%，而 **`ADDR_CODES` 仅 +0.3%（地名库基本冻结）**。

**（4）`0` 是"未知"哨兵，不是缺值——写查询必须 `> 0`。**

| 字段 | NULL | **= 0** | > 0 |
|---|---|---|---|
| `BIOG_MAIN.c_birthyear` | 575,404 | **26,710** | 59,837 |
| `BIOG_MAIN.c_deathyear` | 563,845 | **26,826** | 71,278 |
| `BIOG_MAIN.c_death_age` | 598,486 | **25,525** | 37,958 |
| `POSTED_TO_OFFICE_DATA.c_firstyear` | 163,293 | **116,913** | 311,310 |
| `POSTED_TO_ADDR_DATA.c_addr_id` | 0 | **78,921** | 386,363 |

写 `is not null` 会吞进两万余条假生年／假卒年。

**（5）越界脏值与未来时间戳**：`c_index_year` 最大 **18,961**（範日新）、>1911 者 81 行、<0 者 39 行；`c_birthyear` 同样；`c_death_age` 最大 **1,523**，>120 者 9 行（如王鬷卒 1041 而记 1043，形似卒年填错格）。另有 **397 行** `c_created_date` 晚于构建日（2026-12-16）、2 行为 MySQL 零日期 `'0000-00-00'`。做时间轴统计须先排除。

**（6）同名极重，姓名不可作锚**：66.2 万人只有 487,443 个不同姓名；**77,790 个姓名对应多人**（"李某"419 人、"王某"302 人）。实体锚点**只有 `c_personid`**。

**（7）坐标覆盖与污染**：`ADDR_CODES` 30,157 条，有坐标 15,555（51.6%）、有 `CHGIS_PT_ID` 10,996（36.5%）；被实际引用过的地址 11,542 个，其中带坐标 9,507（**82.4%**）。**个别 `addr_id` 记录坐标标错且已被宋人记录引用**——必须按 `addr_id` 清洗，不可按地名合并：

| `addr_id` | 地名 | 坐标 | 判定 | 宋人游历 | 宋人仕宦 |
|---|---|---|---|---|---|
| 14815 | 徐州 | 117.19 / 34.27 | 对 | 3 | — |
| **11242** | 徐州 | **115.66 / 39.02** | **错（指到河北方向，偏 4.99°）** | **17** | **65** |
| **11167** | 登州 | **112.08 / 32.68** | **错（指到鄂西北，偏 10.07°）** | **6** | **23** |

另 `c_admin_type` 大小写混用（`Xian` 13,687 / `xian` 1,727）。

**（7a）`CHGIS_PT_ID` 这座桥的真实强度（2026-09-25 外部一手核证，直接影响 GIS 口径）**：
- **官方从未定义该字段的语义**：`cbdb-online-main-server`（develop）`docs/DATABASE_SCHEMA.md` 第 **93** 行只给 `int(11) / YES / NULL / 无注释`（SQLite 镜像第 2519 行同）；《CBDB User's Guide》全文 **0 次提及**该字段。→ **凡"该字段对应 CHGIS 某版本"的说法都是使用者自行假定**（我们家中配对的 `chgis-v6` 属此类，须按假定对待，不可写成官方指定）。
- **桥的落地形式是 TGAZ，不是直接查 CHGIS**：`TGAZ ID = "hvd_" + CHGIS pt_id`（一手：TGAZ 记录 `sys_id` 实例 `hvd_32180`／`hvd_40708`，本轮实测 200 在位）。现行可用主机 `chgis.hudci.org/tgaz/` 与 `tgaz.fudan.edu.cn/tgaz/`；**`maps.cga.harvard.edu` 记录级 URL 已 404**（2026-09-25 实测）。→ **依赖在线端点的任何代码都要备两份镜像主机＋自建底图**（官方 CBDB 自己就是这么做的：`docs/CHGIS_MAP_PLACE_LINK.md` 记其把 CHGIS 底图下载为自持 mbtiles，TMS／EPSG:3857／zoom 3–8／15,715 瓦片）。
- **一对多与"双胞胎记录"是本桥的固有性质**：官方机制＝**通名一变即产生新唯一记录**（CHGIS Database Design 官例 崇德县→崇德州→崇德县 记 3 条）；本轮 TGAZ 实测 `n=太平&yr=1100` 命中 **8 条**、`n=宜春&yr=742` 出现**名称／类型／起止年全同而上级一空一有**的两条（`hvd_32568`／`hvd_97129`）。而 CBDB 侧只有一个整数，**装不下一对多**。
- **官方自认两源坐标互相矛盾且不自动裁决**（一手，同一仓）：迁移 `2026_09_14_000000_normalize_zero_coordinates_in_addr_codes.php` 头注——生产环境 **316 列 `0,0` 已于 2026-09-14 经 v2 API 清理，其中 12 列从 CHGIS 回复出真实坐标**；`CoordinateZeroCleanupService.php`——"**不尝试从 CHGIS 回填坐标**…（3 列取自共用同一 `CHGIS_PT_ID` 的既有列、9 列取自 CHGIS gazetteer）…需要逐列判断**两个来源不一致时取哪个**"；另记 **14,297 列本就是 NULL**。→ 与本地 (7) 表"按 `addr_id` 清洗、不可按地名合并"的既定结论**互相印证**，并新增一条硬事实：**多行 CBDB 地址可共用同一 `CHGIS_PT_ID`**（故由 pt_id 反查地址是一对多）。
- 本地实测数（家中 `cbdb_20260919`）：`ADDR_CODES` 有 `CHGIS_PT_ID` 者 **10,996／30,157（36.5%）**。→ **桥只覆盖三分之一**，任何"人人可上图"的设想都不成立，须显式处理无值分支。

**（8）参考完整性（本批全查，干净）**：`KIN_DATA`／`ASSOC_DATA`／`STATUS_DATA`／`ENTRY_DATA`／`ALTNAME_DATA`／`POSTED_TO_*`／`BIOG_*` 对 `BIOG_MAIN` 及各代码表的悬空引用**均为 0**；`MERGED_PERSON_DATA` 5,920 行指向已合并旧 id（符合语义）、12 行 `c_personid` 不在主表（轻微异常）。空表 3 张（`ADMIN_CAT_CODE_TYPE_REL`／`ADMIN_CAT_TYPES`／`SOCIAL_INSTITUTION_ALTNAME_DATA`）。

### 9.5 状态汇总

| 缺项／边界 | 状态 | 处置前置 |
|---|---|---|
| 任职↔地点 | **已结案：非缺项**（制式差异） | 无——直接可用；按地点聚合时剔除 `c_addr_id=0` |
| 显式索引（370 → 0） | 未处置 | 两途并用：官方后处理脚本可补 FK／18 视图／`ADDRESSES`（**不含索引**），索引本由 2024-02 版 DDL 抄回（**370 条中 307 条可直接套用**）或按 join 键自拟；**全库联结分析前必办**；若入库 PG 则改造为 PG 索引（见 9.4(1)） |
| 今地坐标 `ADDR_XY` | 未处置 | 可由 `CHGIS_PT_ID` 桥绕过；要现成表则取 2024-02 sqlite |
| ZZZ 宽表 | 未处置 | 需要时取快车道 `latest_ZZZ_tables.7z` |
| `0` 哨兵／坐标污染／同名 | 已知，**清洗规则已定** | 落到管线时按 9.4(4)(6)(7) 执行 |

### 9.6 使用边界一句话

**主体分析用本件，任职地点亦可直接用**（剔除 `c_addr_id=0`）；**唯有全库联结分析前须先补索引**，地理结论须先按 `addr_id` 剔除已知污染点。

### 9.7 纪年换算的现成件与两处必避陷阱（`NIAN_HAO`，2026-09-25 本地一手统计）

**此表此前在本档任何一节都未记载，而它是纪年↔公元的唯一现成件**（本地 `cbdb_20260919.sqlite3` 直接 SQL 实测）：

- **表名 `NIAN_HAO`**（⚠ **不存在** 名为 `ERA` 或 `ERA_TO_YEARS_CONVERSION` 的表——凡见此类表名的材料皆未经核实）。列：`c_nianhao_id, c_dy, c_dynasty_chn, c_nianhao_chn, c_nianhao_pin, c_firstyear, c_lastyear`。
- 规模：**682 行／530 个不同年号／67 个朝代**；起始年 **最早 −140**（即公元前 140 年，**不含秦与战国**——用它做"全古代"年表会静默留白）；`c_lastyear` 最大值 **3000**。

**陷阱一：哨兵值**。实测 `id=669` 一行为 `(中華民國, 中華民國, 1912, **3000**)`。⇒ 任何 `MAX(c_lastyear)`、"末年跨度"、按时长排序的算法**都会先撞上这条 1089 年的假区间**，须显式按 1911 截断或排除 `c_nianhao_chn='中華民國'`。这与 §九 9.4 记的 `c_addr_id=0`、`c_personid=0` 同族——**CBDB 的 0/极大值哨兵是三处而非一处**。

**陷阱二：年号不是键**。实测同名 `貞觀` 在表内有**两行、分属两朝**：`(6,'唐','貞觀',627,649)` 与 `(78,'西夏','貞觀',1102,1114)`。⇒ **年号→年份聚合绝不可按 `c_nianhao_chn` 单键 group by**，必须按 `(c_dy, c_dynasty_chn, c_nianhao_chn)` 复合键，否则唐与西夏的年表互相污染。

**跨源分歧实证（可直接当回归测试用例）**：西夏「貞觀」**CBDB 记 1102–1114**，而 **CHGIS `china_chron.txt` 记 1101–1113**（Wikidata Q11634542 亦 1101–1113）⇒ **差一年，三比一**。此例说明"年界"在本项目里**不是取数问题而是校勘问题**：三源（CBDB `NIAN_HAO` 682 行／CHGIS `china_chron` 677 行 481 号／DILA 时间权威库 `t_era` 932＋`t_month` 56,327 行到日）**没有任何一个可单独作权威**，须并置＋留差异表。三源许可与规模的展开、以及"到日精度只有 DILA 有"这一事实，见 wiki《年号历日与文本规范抄》§一（**注：`t_era` 932／`t_month` 56,327／`china_chron` 677 行这三处系核查代理实测，我方未独立复验**；本页仅 `NIAN_HAO` 四项为我本地一手）；本页只记与我们库直接相关的两条陷阱与一条分歧值。

> 复核义务：若改用 Dataverse 档案道件或后续版次，**须重跑本表四项统计**（行数／不同年号／最早起始年／哨兵是否仍是 3000）再更新本节。

> 复核义务（承 9.1～9.6，2026-09-25 复原此行——补 §9.7 时曾被覆盖，现归位）：本件再有版本更新、或索引／坐标／ZZZ 任一项落地后，**同批刷新本节**（状态、数字、日期），并记 `docs/log.md` 一行。
