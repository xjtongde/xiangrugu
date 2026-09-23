# memos.md —— 会话纪要备忘账（memos/）

> **定位（2026-09-22 开设于 docs/notes.md，同日用户令迁改为本路径并定性，迁移行见 docs/log.md）**：用户交录入档的跨会话纪要之唯一存档处。**性质＝项目讨论与分析之备忘，不作项目实施之指导**。照录原则：**不改写、不评注、不删减**；纪要内部的 ✅实测／⚠未实测／❌证伪 标注属备忘级实测结论，后续会话未经复核不得改判。新纪要加最上面；编号 `N-01` 起。
> 本账是"备忘"不是"需求账"：纪要中可立项的方向条目按 R-02 另挂 `docs/features.md` / `docs/improvements.md`，本账只作其内容展开的单一源（R-04，性质上非实施指导）。

---

## N-02 · 2026-09-22 · 会话纪要 · 文言文语料与工具书资源四档盘点

来源：另一 AI 会话的回答（问题语境＝有无现成可直接使用的文言语料/工具书资源），用户当日交引归档。**本纪要未经收录方实测标注**——依 N-01 数据落盘纪律精神：所列资源拉数前一律以实测为准，**存档≠证实**。原文照录如下。

> 有，而且这一类反而比模型更成熟。按「能不能直接拿来用」分四档：

### 一、可整体下载的全文数据库（自建检索/RAG 首选）

- **殆知阁 daizhigev20 ⭐**：中国古代文献原始数据，数十亿字（二十四史、十三经注疏、诸子、文集、笔记、佛道藏都有），纯文本按书组织，长期更新（README 标注 2026-09 更新）。做文言文语料/检索库，这一个基本就够了。
- **chinese-poetry**：唐诗 5.5 万+、宋词 2.1 万+、全唐诗补编、赋等，JSON 格式，规整好解析。
- **Corpus_of_Literary_Chinese**：千万字文言语料（上次提过，适合训练）。
- **先秦兩漢暨二十四史 Walking Text 語料庫**：在台湾 data.gov.tw 开放资料上可下载，带词性标注——这是少数"已标注"的文言开放语料，做 NLP 训练比裸文本值钱。
- **siku-quanshu-ocr（GitHub 搜同名）**：四库全书 440 册的 OCR 数据工程，量大但质量参差，适合做底本再校。
- **CBETA**：大正藏 XML 全文 + DCloud RESTful API，佛经文言自成一系，文本校勘质量极高。

### 二、有官方 API 的

- **中国哲学书电子化计划 ctext.org**：先秦两汉核心文本，提供 XML/JSON API（含对照翻译、篇目结构），是目前最稳定的汉文古籍接口。
- **CBDB 中国历代人物传记资料库**：50 万+历史人物、社会关系、地理，注册即可用 API，且提供整库 dump（SQL 文件）免费下载——结构化程度最高的历史数据库。
- **古文岛 API（guwendao.net/api/open）**：古诗文网体系，原文+注释+翻译+赏析打包成 JSON，申请 token 即用。做"文言→白话"问答对数据，这是最省事的来源。
- **gushi.wiki 诗词吾爱 wiki**：开放 API，诗词+古文，社区维护带注解。
- **教育部《重編國語辭典》API**：现代词典但文言用例、异体字、注音齐全，CC BY-SA 授权，可放心入库。
- **Hanzi Project**：汉字字源数据库（说文/金文/甲骨文构形解析），开放数据 + API。

### 三、字典/工具书数据集（GitHub 裸数据）

- **说文解字、康熙字典**：GitHub 上都有整理好的 JSON/数据库版本（搜 shuowen、kangxi），可配合殆知阁做字词级查询。
- **Unihan**：Unicode 官方 CJK 数据库，字形/读音/跨词典映射的底层依赖。
- **kanripo（京都大学）**：先秦两汉全部字头+上古音拟构，做音韵可用。

### 四、只能看不能抓、但值得知道的

- **文澜阁四库全文数码化图书馆（浙大图书馆）**：1.02 亿字《四库全书》全文可检，免费，质量高——适合人工校数据。
- **史语所「汉籍全文资料库 / Scripta Sinica」**：质量顶级，但需机构订阅。
- **国家图书馆·中华古籍资源库**：影像为主，无 API。

### 组合建议（如果是在做一个产品级的东西）

- 底座语料：殆知阁（下载入库，Elasticsearch/向量库）
- 精确检索与对齐翻译：ctext API
- 注释/译文训练数据：古文岛 API 批量拉「原文↔译文」对
- 人名/地名实体链：CBDB dump

---

## N-01 · 2026-09-22 · 会话纪要 · 历史数据资源盘点

来源：cbdb-demo 盘点会话（2026-09-22），用户当日交引归档。原文照录如下。

> 原则：本纪要只收录本会话实测通过的资源；标 ⚠ 的为"有线索但未实测"，标 ❌ 的为已证伪。

### 一、NAS 上已有的数据（`\\192.168.3.61\workmetadata`，homepc 挂载点 `/mnt/wd`，guest 可读写）

> **勘正（2026-09-23，用户令）**：挂载故障已修（常驻 fstab＋admin 开写）；**正式路径改定 `/mnt/wd61workmetadata`，`/mnt/wd` 软链已删**——本纪要旧路径照录不回改，按本注向前指。权威现状看 codemap §2"数据 NAS 挂载"行＋"哈佛全量仓"行。

| 目录 | 内容 | 备注 |
|---|---|---|
| `cbdb-project/cbdb_20260919.sqlite3` | CBDB 子集，78 表 × 736 字段，586MB | 无经济/货币表（本会话扫描确认）；`ADDR_CODES` 自带 `CHGIS_PT_ID` 桥 |
| `chinese-poetry/` | GitHub 全库克隆（MIT，⭐53.5k）：唐诗 ~5.5 万、宋诗 ~26 万（在 `全唐诗/poet.song.*.json`，历史遗留目录名）、宋词 ~2.1 万（`宋词/ci.song.*.json`，词无题目字段只有词牌＋正文），作者表含籍贯 | 苏轼＝蘇軾 2,824 首／苏轼（词）362 首 |
| `chgis-v6/` | CHGIS V6 核心包（8 文件，含 `SHA256SUMS.txt` + `VERIFICATION.md`）：县级时序点 10,522 条＋府州军监级 5,226 条（UTF-8/WGS84 完整 shapefile 套）、数据字典、`China_Periods_ReignDates`（年号↔公元表，还没拆用过）、README＋EULA | ⚠ 许可：学术免费，禁商用/转售/再分发（以 README 为准，Dataverse 的 CC0 标签不可信）；已知脏数据 `END_YR=11911`→clip 1911；公元前负数纪年 |
| `poetry-source/` | snowtraces/poetry-source 全量 zip 374MB + `SHA256.txt` + `VERIFICATION.md`（sha256 443e6629…7ce3）：诗 1467 JSON（宋523/明487/清181/元118/唐118/隋7/五代7/三国4）＋词188＋曲26＋`作者.json`＋可自部署 `api/` | 简体库；与繁体库比对须先 OpenCC s2t 归一；作者字段有少量误挂（"又赠老谦"实为苏辙），互校用不当真值 |
| `爱因斯坦/`、`霍金/` | 既有项目目录，本会话未动 | — |

本地代码产物（工作区 `cbdb-demo/`）：`su-poem-geo.html`（三源联动 demo：77 地名命中 245 诗 + CBDB×CHGIS 校勘台）、`build_su_poem_geo.py`（可重跑管线）、`su-poem-geo-template.html`。既有：`cbdb-demo.html`、`su-dating.html`（系年实验）。

本会话技术发现：CBDB 坐标惯例 `x_coord`=经度；与 CHGIS 对质抓到 CBDB 离群点——登州偏 10.07°（标到鄂西北，CHGIS 蓬莱值对）、徐州偏 4.99°（标到河北，CHGIS 值对）、凤翔府 0.51° 轻微。

### 二、外部资源（本会话实测通过 ✅）

**Harvard Dataverse**（CHGIS 官方发布地，下载端点 `https://dataverse.harvard.edu/api/access/datafile/<文件ID>`）

- 总馆 `https://dataverse.harvard.edu/dataverse/chgis` —— 只有 V2/V4/V5/V6，公开可下载的最新版就是 V6（2016），**不存在 V7 数据包**（V7 是 iCHGIS 在线服务口径）
- 已下载：县点 `doi:10.7910/DVN/Q9VOF5` · 府点 `doi:10.7910/DVN/WW1PD6` · 数据字典 `doi:10.7910/DVN/SNCEAU`
- 未拉取的备选（目录核实存在）：`doi:10.7910/DVN/3KAHBT` 谭其骧《中国历史地图集》索引 (2001)；`doi:10.7910/DVN/SC7AOU` 中国年号对照表 (2007)；`doi:10.7910/DVN/I4UIKV` GNS 地名类型码 · `doi:10.7910/DVN/TI8DFI` 多语言类型对照 · `doi:10.7910/DVN/SK7KGK` 国标区划码 GBT-2260-91
- V6 政区面：1820/1911 layers（各 ~2–9MB×多包）、Time Series Prefecture Polygons 31MB×4、明代驿站路线、1990 CITAS 人口
- CBDB 官方馆 `https://dataverse.harvard.edu/dataverse/cbdb`（13 条目，含"ACCESS and SQLite 最新库"）⚠ 未枚举细看，官方 CBDB 完整发布渠道候选，下次接完整库先查这里

**CHGIS 官网** `https://chgis.fas.harvard.edu`（在线 gazetteer / iCHGIS；数据页列 V1–V6）

**GitHub**（实测存在且活跃）

- `https://github.com/chinese-poetry/chinese-poetry` —— MIT ⭐53.5k，2026-06 有推送
- `https://github.com/snowtraces/poetry-source` —— MIT ⭐106，2026-09-11 有推送

**在线数据库/检索**

- `https://ctext.org` 中国哲学书电子化计划 —— API 端点存活（api.ctext.org 302），诗经/楚辞/乐府/食货志全文，CC BY-NC-SA
- `https://www.shidianguji.com` 识典古籍（字节）—— 200 ✅，免费整理本全文，无官方 API，人工查对用
- `https://sou-yun.cn` 搜韵 —— 200 ✅，有官方开放 Web API（注册取 token），文档：搜韵知识图谱 Web API PDF
- `https://ccl.pku.edu.cn` 北大 CCL —— 200 ✅，2026 版语料库检索系统上线

**API 直连**

- 今日诗词：`https://v2.jinrishici.com/one.json` —— 200 ✅（header token: free），随机/按情绪地点取诗
- CBDB REST：官方接口文档（上海图书馆镜像 PDF）`https://opendata.library.sh.cn/2020/download/opendata/2020/CBDB接口文档.pdf` ⚠ 文档真实，端点未实测
- 大都会博物馆：`https://collectionapi.metmuseum.org/public/collection/v1/` —— 实测调用成功 ✅，含中国铜钱/银锭/交钞实物，CC0 图像无限量免费（demo 视觉素材直接可取）
- 大英博物馆数据下载 `https://data.britishmuseum.org` ⚠ 本会话网络不通，待复核；ANS 钱币学会 `https://numismatics.org`（钱币学标准设施）⚠ 同上

**背景数据线索**（⚠ 均未实测，用前验证）

- MeasuringWorth 中国 GDP 指数 960–1900（年度序列，起点正好北宋）
- NOAA Paleoclimate：东亚季风千年指数、中国近三千年旱涝序列、石笋 δ18O（董哥洞/葫芦洞）
- 《中国强地震目录》含古代章
- 历法转换开源库（zhdate/lunardate 一类，底据《两千年中西历表》）
- 清粮价数字化数据（彭凯利等《清代物价转变与工资水准资料汇编》配套，形态待查）

### 三、证伪黑名单（查无此资源，别再找）❌

| 名称 | 结局 |
|---|---|
| 深圳大学 ATLAS「文言文全注语料」（6000 篇逐句对齐）/ `github.com/laiproject/atlas` | 全渠道不存在（GitHub/HF/ModelScope/Gitee/中文搜索全空，laiproject 名下只有一个无关仓库）。另一 AI 会话幻觉，含伪造 README 截图 |
| ProsoCap、ChPoE 的 GitHub 库 | API 404；作为论文或存在，作为现成资源找不到 |
| `shijiebei2009/CEC-Corpus` | 存在但是"中文突发事件语料库"，不是古诗——记名错误 |
| "DBAR 中国历史文献数字词典（芝加哥 CHTS，公开 API）" | 我自己上一轮的记忆幻觉，查证不存在。其功能（术语权威表）实由 CBDB 代码表族（`OFFICE`/`ENTRY`/`KINSHIP`/`ASSOC_CODES`）＋ CHGIS 码表（GNS/年号/国标/谭图索引）＋ `c_personid`/`c_addr_id` 覆盖，已在手 |
| 哈佛 CHGIS "V7" 下载包 | Dataverse 不存在此版本；公开版止于 V6 |

### 四、方向备忘（本次讨论共识）

- **基础工作**（不急但先留口子）：地名主表 schema（含 provenance ＋ 草稿区字段）→ 简繁归一管线 → 溯源规范
- **模型接入次序**：向量先行（bge-m3 在 36 已在线：混合检索/双源互校/意象聚类）→ LLM 疑难裁决（地名消歧/系年证据/实体链接，产出只进草稿区）→ 生成内容（云上图像/视频/TTS：行迹短片、心声翻译机、故土诗、擦肩、诗星图）
- **硬件红线**：4070 12G——9B 与 TEI/TTS 并发掉过三次卡；云 API 做历史批判语料被审（鲁迅实测 data_inspection_failed），诗词题材云可用
- **钱币方向**（本轮新增）：无现成宋代货币库＝空白机会；路径＝经济词表＋物价/铸钱事件表→join 地名主表/人物表/诗库；第一步试验＝从《宋史·食货志》提 200 条样表（ctext 全文）
- **数据落盘纪律**：外部数据→先验证→NAS workmetadata 留档→临时副本清除；一切"宣传有库"实测前不当真
