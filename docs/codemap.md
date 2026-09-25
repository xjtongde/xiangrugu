# codemap.md —— 代码地图与部署位置

> **定位（2026-09-22 用户指令"必须要有代码地图专用文档，codemap。部署位置。"）**：本文件一文两用——§1 代码地图（结构／模块／依赖的唯一展开处）＋ §2 部署位置（环境与落点的唯一事实表）。
> **更新义务**：目录/模块增删改、部署事实变化，须**同批**刷新本文件；每轮对齐核查（R-06）的锚点查与矛盾查覆盖本文件所有路径与指针。

---

## §1 代码地图

### 1.1 现状

**尚无业务代码**——工作区仅有文档骨架（2026-09-22 骨架开设批）。代码落地后必须首建：完整目录树、模块职责表（1.3）、依赖/数据流（1.4）。

### 1.2 目录树（骨架现状，2026-09-22）

```text
/root/xiangrugu/
├── .git/                 Git 仓库（main 分支）
├── .gitignore            忽略 `.agents/`（2026-09-22 用户口令"Skill不进git"）
├── .agents/              ⚠ git 不跟踪（工作区本地设施）
│   └── skills/           项目级 skill（2026-09-22 自 translate 复制装入）
│       ├── karpathy-guidelines/   LLM 编码行为纪律（想清再写/最简实现/外科手术式改动）
│       └── frontend-design/       独特视觉设计指引（去模板脸/排版个性/结构即信息）
├── AGENTS.md             AI 助手入口：项目目标（待定义）＋必读链
├── rules.md              纪律总纲 R-01～R-06（R-07+ 预留）
├── memos/
│   └── memos.md          跨会话纪要备忘账（N-编号；讨论与分析备忘，非实施指导）
└── docs/
    ├── index.md          文档索引＋权威优先级（登记处）
    ├── log.md            文档变动日志（R-05）
    ├── codemap.md        本文件：代码地图＋部署位置
    ├── cbdb.md           外部数据源档案：CBDB 项目（2026-09-23 开设）
    ├── pg32-upgrade.md   实施方案：pg32 升级全功能镜像（2026-09-23 成文，**同日搁置**）
    ├── pg36.md           实施方案：36 新建 pg36 全功能实例（2026-09-23 成文；2026-09-24 已执行建成，§13 执行记录）
    ├── pg32b.md          实施方案：32 新建 pg32b 备份/演练实例（2026-09-24 成案；同日已执行建成，§9 执行记录；复用 pg36 镜像）
    ├── cbdb-load.md      实施方案：哈佛资料装数首批→pg32b（2026-09-24 成案，用户令"36故障，你在32主机上搞"；同夜用户令"同意＋考虑到32主机的压力"开工→**首批已执行完毕，验收七项全过，执行记录＝§13**）
    ├── bugs.md           Bug 专职账（B-编号）
    ├── improvements.md   改进专职账（I-编号）
    └── features.md       新功能专职账（F-编号）
```

### 1.3 模块职责表（模板，代码落地后填行）

| 路径 | 职责 | 依赖 | 权威文档 |
|---|---|---|---|
| （空——待代码落地） | | | |

### 1.4 依赖与数据流

待代码落地后首建。届时每个模块须能回答：做什么、怎么用、依赖谁（模块隔离原则）。

## §2 部署位置

| 项 | 值 | 状态 |
|---|---|---|
| 权威开发工作区 | `/root/xiangrugu/`（文档＋源码＋测试＋Git 仓库，**项目唯一权威源**） | 已定（2026-09-22） |
| Git 本地仓库 | `/root/xiangrugu/.git`，初始分支 `main` | 已定（本批） |
| 远程代码源仓库 | Gitea `http://192.168.3.35:17080/deepseekharness/xiangrugu`（私有，默认分支 `main`；2026-09-22 用户手建、助手全量推送，远程树 12 项=10 文档＋2 目录） | 已定（2026-09-22） |
| 推送方向 | `/root/xiangrugu` ── git push ──▶ Gitea `deepseekharness/xiangrugu`（origin 已设） | 已定（2026-09-22） |
| 推送凭据 | `deepseekharness` token（本仓 local `credential.helper=store --file=/root/.git-credentials` 挂载；用户 2026-09-22 裁决**长期留用**）。权限实测边界：✅ git 读写、仓信息/提交/分支/PR/releases 读；❌ 建仓（须 `write:user`/`write:organization`，新仓走用户网页手建）。helper 每次 push 回写 lock 被沙箱拒的警告无害 | 已定（2026-09-22） |
| 工单凭据 | `xiangrugu-issues` 令牌（id=7，scopes `write:issue`，2026-09-22 用户交 key.txt 授权、以真密码一次性铸造——**真密码用完即弃、日常不再碰**）。存 `.secrets/gitea_token`（600，git 不跟踪），实测建/读/关单全通（验收单 #1 已 closed）。Gitea issues 与三本专职账分工：记账仍以专职账为准，issue 用作对外工单通道 | 已定（2026-09-22） |
| 真账密保管 | 用户令"这个key你以后用"（2026-09-22）：Gitea 账密收编 `.secrets/gitea_account`（600，git 外）。**用途纪律**：仅令牌不能之事（铸/撤令牌、建仓、账号设置）；日常 git 与工单一律走令牌 | 已定（2026-09-22） |
| **外围知识层＝Gitea Wiki 仓** | 2026-09-25 用户定性开设（"非必要材料，用学习与了解"＋"初始化一个吧……有了好主意也可以放进去大家讨论"）并当日初始化。**位置**：`http://192.168.3.35:17080/deepseekharness/xiangrugu/wiki`（网页）／独立 git 仓 `http://192.168.3.35:17080/deepseekharness/xiangrugu.wiki.git`（**默认分支 `main`**，与主仓同仓名不同仓）；页面＝markdown 文件，**文件名即页名**（空格写作 `-`），`_Sidebar.md`／`_Footer.md` 全站生效。**权威边界**：本层非权威，规矩唯一展开＝`rules.md` R-04"外围知识层的边界"段＋wiki `Home` 页四条约定；页面正文**只在 wiki 仓，工作区不留副本**。**通路实测（2026-09-25，全程用 `deepseekharness` 令牌，未碰真密码）**：✅ **git 读写全通**（正文一律走此路）；✅ API 面 `GET /api/v1/repos/{o}/{r}/wiki/pages`（列）、`GET /wiki/page/{名}`（读，正文在 `content_base64`；**⚠ 2026-09-25 复核：仅 ASCII 页名可用（`Home`），CJK 页名一律 404——连把列表接口给出的精确 `sub_url` 百分编码原样回传也一样，故中文页"单页读"不可用，回读一律靠 git 工作副本或 `GET /wiki/pages`＋本地文件**）、`POST /wiki/new`（建）、`PATCH`／`DELETE /wiki/page/{名}`（改／删，删成功返回 204）；❌ **API 写正文不可用**——`POST /wiki/new` 与 `PATCH` 的 `content` 字段被丢、页面被建成空文件或错名（本批实测留下 `unnamed.md` 空壳，已清），**故正文不得指望 API**；❌ API 无 `PUT /wiki/pages/{名}` 面（本实例路由与常见文档不同，`Allow` 头实测为凭）；⚠ 网页端 `/wiki` 路由对**令牌 basic auth 只回 `Not found.`**，须真人会话（不影响 git 与上述 API 面）。**在册页面**：**不在主仓枚举**（R-04 去重——清单的唯一展开处＝wiki `Home` 词条目录＋`_Sidebar`，加页不须回改本行）；规模时点：2026-09-25 实测 **9 件在册**（内容页 6＋站级 `Home`／`_Sidebar`／`_Footer`），远端 HEAD `0ab17aa`。 | 已启用（2026-09-25 初始化批） |
| 数据 NAS 挂载 | `//192.168.3.61/workmetadata` → **`/mnt/wd61workmetadata`（唯一正路径，2026-09-23 用户令）**。旧 `/mnt/wd` 软链同日按令**已删**（N-01 纪要内旧路径不回改，勘正注见 memos；历史 log 行保原样）。权限实测：初测挂载内 admin（`.smbkey`）整卷只读、guest 匿名可写；**2026-09-23 用户采 B 案于 NAS 端给 admin 开写**，复测 root/zky/子目录三写全通（注：服务端改 ACL 后须重挂——cifs 旧树连接缓存旧权限）。WSL 无 systemd，条目内 `x-systemd.*` 两选项休眠，开机由 WSL init 走 mount -a 生效。卷上另见项目外用户自存目录（爱因斯坦/霍金），项目不碰 | 已定（2026-09-23 路径定型） |
| 装数工作集 `/mnt/wd61workmetadata/usedata/harvard/` | 2026-09-24 用户令立（"把我们要用的数据copy一份到usedata/harvard下，这样我也知道我们是在使用这些数据。原来那些就当是下载的原数据备份"；落点经用户确认）：首批装数**数据 7 件**（CBDB 0919 sqlite/json＋V6 府面/府点/县点 utf_wgs84 zip＋三小件 TSV）＋随附 6 件（EULA/数据字典/家中验证账）共 **13 件/594MB**；拷法＝32 本地镜像盘读→写 NAS 单程；**核验三重全过**（sha256 双端全同＋府/县点与家中 SHA256SUMS 全同＋sqlite 与官方 `bde1bb8e…` 全同；本机侧 `sha256sum -c` 13/13 OK）；README 出生纸在目录；**装数唯一工作源＝本目录**（`docs/cbdb-load.md` §2 已同步），**原树（cbdb-project/harvard-full/chgis-v6）降级＝原数据备份只读**；镜像脚本实核 `rsync -a --delete` 纯镜像→写必落 NAS 侧方持久，32 每日 12:00 同步后本地可读 `nas-mirror/61/workmetadata/usedata/harvard/` | 已立（2026-09-24）；**首批已装入 pg32b/cbdb（09-25 00:24，`docs/cbdb-load.md` §13）——工作集保留＝复跑/回滚之源，原树备份未动** |
| 哈佛全量仓 `/mnt/wd61workmetadata/harvard-full/` | 2026-09-23 用户令"全部拿过来"：Harvard Dataverse 的 CHGIS 树＋CBDB 树全量已发布件——**370 文件 / 10.64 GiB 逐件尺寸核验吻合**（MD5 抽检；65 个数据集目录，形如 `doi_10_7910/DVN/*`）。**构成实账（2026-09-23 按数据集标题六分法核算，用户"必须搞清楚"令）**：CBDB 历年发布档案 3.51G（6 集——同一库 2017→2025 **九个版本堆叠**，与家中旧库同源，净新增≈0.9G 的 2025 MDB 快照）＋ 历史地图影像栅格 2.72G（12 集，黑龙江全省舆图/柯兹洛夫蒙藏图/俄藏北京地图等**扫描件大图**，全新增量）＋ CHGIS 历代向量 1.93G（10 集，V2/V3/V4/V5 **旧版本**＋V6 时序面包——家中已有 V6 核心表，旧版为演变考据储备）＋ LoGaRT **软件**权重 1.86G（是工具模型，非语料）＋ Hartwell/TGAZ 等专题 0.19G ＋ 其他 35 个小集 0.43G（书院/全元文索引/传教士著作/日本GIS/DCW/BGIS…）。**要算"真正的净新增内容"约 3.5G；其余 7G 是版本堆、扫描件和软件**——10G 不等于 10G 的新知识。含 CBDB 历年发布序列（2017→2025：最新 2025-05 为 ACCESS/MDB 包、解包 5GB；2024-02 SQLite 877.9MB 等）、CHGIS V2–V6 历代 shapefile 全套（政区面/点、DEM、GNS 地名、海岸线、铁路、图幅索引）、Hartwell 宋辽金 GIS、TGAZ、日本历史 GIS、俄藏中国地图、黑龙江舆图、LoGaRT-BERT、传教士著作、全元文索引、2957 书院等。货单随货（仓内四件）：`README_provenance.md`（出生纸：来源/验证法/复拉方法/许可）、`datasets.tsv`（65 数据集总账：DOI/树别/件数/字节/标题/目录）、`harvard_dl.tsv`（370 件逐行含 fid 可复拉）、`harvard_manifest.txt`（树形货单，标题字段不全、认件以 datasets.tsv 为准）；拉取管线与流水存档 `ops/harvard/`（git 外）。许可注意：CHGIS 系学术用禁商用禁再分发，CBDB 系 CC 类——**未逐件摘抄，启用哪件核哪件**（联动 N-01 落盘纪律）。**对账勘正（2026-09-23，三次修正·读官方自述后定骨）**：① **家中两件旧货都系哈佛官方**——`chgis-v6`＝Dataverse 官方件（VERIFICATION.md 当时已记 DOI 出处，本次复核家中两 zip 与新仓同款 **MD5 全同**）；`cbdb-project`＝**CBDB 官方 HuggingFace 仓 `cbdb/cbdb-sqlite` 的最新滚动发布**（org 名即"China Biographical Database Project (CBDB)"、档案链回哈佛官网、许可 CC BY-NC-SA；家中 JSON 与 HF 根 `latest.json` 逐字节同、sqlite 实算 SHA256 `bde1bb8e…` 与官方记载全同，构建日 2026-09-19）——**前记"线上库自导出/非官方打包"系误判，作废**；② **CBDB 官方实为两速通道**：HF＝快车道（月度滚动，家中即最新 0919 版，zip 139MB→库 586MB）；Dataverse＝档案/引用慢车道（bi 2025-05 系 ACCESS 快照，比家中**旧一年**，SQLite 停更在 2024-02）——新仓 CBDB 件价值＝可引用 DOI 档案＋版本序列＋MDB 制式（含家中 sqlite 所无的 `ADDR_XY`、ZZZ 预连接宽表族、说明书中英文 PDF），**不是"更多的数据"**；③ ~~遗留疑点挂查：`POSTED_TO_ADDR_DATA` 两官方制式行数悬殊（家中 sqlite 46.5 万 vs bi2025 MDB 185.3 万）~~ **已结案（2026-09-23）**——解包官方 MDB 实测其自身分母后判定：系《縉紳錄》逐年名录制式 vs 任期区间制式之别（**两制式均 1.0 地点/任职**），**非缺料**；前批"家中件仕宦地点不可单用"判词**作废**。**明细唯一展开于 `docs/cbdb.md` §九 9.1**，本行只记状态：**启用仕宦地点分析无需补数**；待办转为**显式索引缺项（官方 2024-02 版 370 条 → 家中 2026-09 版 0 条，全库联结分析前必办）**＋ `ADDR_XY`／ZZZ 两小缺项（明细见 §九 9.2–9.5）；④ chinese-poetry/poetry-source 系社区产物与哈佛无干，本批零增量。原语料四库不动 | 已定（2026-09-23） |
| 主机 36 实勘（主机名 `one`） | 2026-09-23 用户令"上 36 主机上看看"，**全程只读**（两轮 ssh 勘察，未装未改未起停）。**定性＝AI/GPU 主力机，无 PostgreSQL**（无二进制、无容器、无数据目录）。硬件：Debian 13 trixie／内核 6.12.96／AMD Ryzen 5 5600（12 线程）／15G RAM（可用 14G）／**RTX 4070 12G**（勘时闲置：util 0%、显存 1MiB、35℃）；单盘 NVMe 450G（已用 159G，**余 268G**）。在线服务：**ollama 原生（:11434，systemd）8 模型——`bge-m3:latest` 在列（＝F-04 之 ✅实测锚点，8 周前入库）**，另有 qwen2.5:7b/14b、qwen3:8b、Hy-MT2-7B/1.8b（翻译）、minicpm5:2b、ornith-1.5:9b；容器：speaches TTS(:8000)、**weaviate 1.38.8(:8085/:50051**，数据 `/opt/mydocker/weaviate/data`，备份 `/myback/weaviate`）、perplexica/vane(:3000)、portainer-agent(:9001)；已停：cosyvoice（镜像 34.9G）、dify-tei-embedding／dify-tei-reranker（TEI 1.9）、open-webui、voicebox、garage36。NAS 通路：NFS autofs `/mnt/wd61nfsworkcenter`（api-key／dify／ragsystem／workbook）＋ fstab CIFS×3（`//61/zkyone/projects`→`/mnt/wd60projects`、`//61/zkyone/obsidian_study`→`/mnt/wd60obsidian`、`//61/llm-wiki`→`/mnt/wd60llm-wiki`，凭据在 `/home/zky/`）。`/opt`＝containerd／mydocker／ollama-models。勘时开机仅 2 分钟（刚重启，容器随起）。**用户已裁决（2026-09-23）：本机新建全功能实例 `pg36`——2026-09-24 已建成，见下行与 `docs/pg36.md` §13；32 升级案同日搁置** | 实勘（2026-09-23）；pg36 建成（2026-09-24） |
| 36 之 pg36 实例（香如故数据底座） | 容器 `pg36`＝自建镜像 `pg36-full:18-pgdg`（`postgres:18-bookworm@3725f4e2…`＋PGDG 扩展集 21 包：**PG 18.6＋PostGIS 3.6.4＋pgvector 0.8.6** 等，全表在 36 `/opt/mydocker/postgres/README.md`＋镜像 label），**2026-09-24 建成、装后核查全过**——执行记录唯一展开＝`docs/pg36.md` §13。`0.0.0.0:5432`（scram；端口登记归另派 agent）；数据 `/opt/mydocker/postgres/data/postgres`→容器 `/var/lib/postgresql`（PGDATA `…/18/docker`，700/999:999，本地 NVMe，余 267G）；网络 `postgres_default`；凭据在 36 `/opt/mydocker/postgres/.env`（600，POSTGRES_USER/DB＝postgres，**明文未出 36**）；restart unless-stopped／json-file 50m×5／healthcheck `pg_isready`／shm 128mb；§4 参数生效（shared_buffers 1GB／work_mem 16MB／maintenance 256MB／ecs 4GB／preload pg_stat_statements）；空闲占用 84MiB；**时区挂载例外**：`/etc/timezone` 行经用户裁决略去（宿主既有缺陷＝bugs 账 B-02，修复后加回）；备份＝另派 agent（homelab `backups/` ③数据库类；36 未挂 61 备份共享、通路归其定夺）；CBDB/CHGIS 装数未做（F-13 另议） | 已建成（2026-09-24） |
| 主机 35 实勘（主机名 `lx02`） | 2026-09-24 用户令"你上35主机上看看，我想pg在35上也装一个"，**全程只读**（三轮 ssh 勘察，未装未改未起停）。**定性＝家庭基础设施宿主（Gitea 代码服务＋Dify 全家），四台 docker 机中硬件最弱**。硬件：Debian 12 bookworm／内核 6.1.0-52／Intel i3-4000M（2核4线程@2.4GHz，旧移动平台）／7.5G RAM（勘时已用 3.4G、可用 4.1G，load 0.11，开机 2 小时）／单 SATA SSD 120G（Samsung 850 EVO，`/` 余 **88G**；docker root＝`/var/lib/docker`：镜像 11.5G＋容器 0.8G＋**构建缓存 19.8G 可回收**——标准 §15 维护域，未动）／GPU＝核显＋GF117M 无驱动（无关）。在线容器 16：**gitea 1.27.1（:17080 http／:17022 ssh，healthy——本项目远程仓所在主机**；其 DB 配置未在 .env/compose 环境变量暴露，涉及时另查）、**Dify 1.16.1 全家**（api/web/worker×2/websocket/plugin-daemon/sandbox/agent-backend/agent-local-sandbox/ssrf-proxy×2/redis/nginx，常驻共约 3.7G）、**dify-db-postgres（postgres:15-alpine——5432 声明未绑定宿主、仅内网 `dify_dify-net`）**、portainer-agent(:9001)。端口在用：22/8080/9001/17022/17080。`/opt/mydocker`＝dify/gitea/portainer-agent（**postgres 目录空闲**）。NAS 通路：NFS autofs `/mnt/wd61nfsworkcenter`（同 36；**未挂 workmetadata**）。Docker 29.7.1＋compose v5.4.0。**PG 冲突排查＝零冲突**（宿主 5432／pg35 名／pg35-full 镜像名／postgres 网络名全空闲）。**用户意向：35 亦装 PG——挂账 F-14，定位（备份实例？）与规模待裁决，未成案** | 实勘（2026-09-24） |
| 第三实例选型三机实勘（32 `lx03`／33 `lx01`／35 `lx02`） | 2026-09-24 用户令"你看一下32，33，35哪个更适合？"，**全程只读**（各一轮 ssh；**33 系本项目首勘**）。**33（lx01）**：Debian 12／i3-4000M 2核4线程@2.4GHz（与 35 同款）／7.5G RAM 可用 4.8G／单 SATA SSD 128G（长城）`/` 余 **71G（三机最小）**／无 PG、5432 空闲／**12 个网页检索与翻译系容器**（home-llm-translator／corpus-admin／cloudflared／crawl4ai／jina-reader／libretranslate／gpt-researcher／meilisearch／searxng×2／nginx／portainer-agent）服务密度高／仅 NFS workcenter／Docker 29.8.0＋compose v5.5.1／pg33 名与 postgres 目录空闲。**32 复勘**：i7-6567U（2C4T@3.3GHz，三机最强单核）／7.3G RAM **可用 5.5G（三机最多）**／`/` 余 **196G**＋**本地大盘 sdb1→`/mnt/nas-mirror` 余 829G**；pg32=**PG 18.4** healthy 空闲 72.9MiB、load 0.11；**端口核查：5432 已被 pg32 占用**（0.0.0.0 绑定——第二实例须让口，如 5433）；在线 7 容器（graphrag/chainlit/calibre/n8n32/portainer/nginx32〔**unhealthy 观察项**，只报未动〕/pg32）；通路＝NFS workcenter＋nas-mirror 本地大盘。**35**：见上行主机 35 实勘（SATA 余 88G／可用 4.1G／Gitea+Dify 命脉）。**三机比较结论落 F-14（推荐 32、次选 33、末选 35；待用户裁决择机）** | 实勘（2026-09-24） |
| 32 之 pg32b 实例（备份/恢复演练台） | 容器 `pg32b`＝镜像 `pg32b-full:18-pgdg`＝**36 `pg36-full:18-pgdg` 同字节拷贝**（ID `06ad5ef6a527…` 两端全同，save/load 管道移植后 retag、未重建——与 pg36 全同构：PG **18.6**＋PostGIS **3.6.4** 等 21 包，label 随 `pg36.*` 冠名如实），**2026-09-24 建成、核查九项全过**——执行记录唯一展开＝`docs/pg32b.md` §9。`0.0.0.0:5433`（5432 系 pg32 让不得；scram；端口登记归另派 agent）；数据 `/opt/mydocker/pg32b/data/postgres`→容器 `/var/lib/postgresql`（PGDATA `…/18/docker`，700/UID999）；网络 `pg32b_default`（独立，不入 `postgres_pg_net`）；凭据在 32 `/opt/mydocker/pg32b/.env`（600，**明文未出 32**）；restart unless-stopped／json-file 50m×5／healthcheck pg_isready／shm 128mb；参数缩配 512MB/8MB/128MB/2GB/50conn＋preload pg_stat_statements；**时区标准 §9 全规格三挂载实挂核验**（32 无 B-02，与 pg36 相反相成）；空闲 79MiB；与 pg32 共存零接触；备份调度/落盘＝另派 agent；**装载器补装层（09-24 用户令"那就装上吧"，执行记录＝pg32b.md §11）**：镜像＝基座锚 tag `pg32b-base`（06ad5ef6…）＋`gdal-bin` 3.13.2 层→`pg32b-full` 新 ID `d562e436…`（+42MB），ogr2ogr 驱动三件套实测（Shapefile 含 .shp.zip 直读／CSV／PostGIS rw），compose 已带 build 段＋.dockerignore（.env 不入上下文）；**36 未同建（用户前令"不要考虑pg36"）——同构联动候另令**；注：36 于 09-24 22:22 起不可达（ping 全丢，非本批所致——本批 36 零写），pg36 运行态待其恢复核验；**首批装数（09-24 夜开工令"同意＋考虑到32主机的压力"→09-25 00:24 验收七项全过）：实例内建成 `cbdb` 库——84 表（public 81＋chgis 3）／总行 5,686,842（CBDB 5,623,075 三方对账零差异）／索引 321（官方 2024-02 版 308 条 DDL 迁移＋FK 补 6＋postgis 1＋chgis 6）／1,543MB；compose＋`cpu_shares: 512`（压力让路）；施工 36 分钟 pg32 生产零感知（canary 0.092→0.089s、峰值 loadavg 1.87＜阈 4.0）；桥验证 join 7,125＋ST_Within 跨腿三点全过；执行记录唯一展开＝`docs/cbdb-load.md` §13＋`docs/pg32b.md` §12** | 已建成（2026-09-24）；装载器补装（同日）；**首批装数 cbdb 库（09-25）** |
| 构建主机与构建方式 | 待项目定型 | 待裁决 |
| 生产部署目录 / 端口 / 数据文件 | 待项目定型 | 待裁决 |

要点：

- 文档、源码、测试只存在于权威工作区；
- 部署模式定型后，运维操作细节另立文档并登记入 `docs/index.md`，本表只留事实行与指针（R-04）。

## §3 与其他文档的接缝

- 版本与发版纪律＝待项目定型后开设（rules.md 预留条款位 R-07+），届时发版流程若要求"部署快照刷新"，义务指向本文件 §2；
- 本文件出现的任何"待裁决"字样被用户指令落定后：更新本表 ＋ 记 `docs/log.md` 一行 ＋ 记 `docs/features.md`/`docs/improvements.md` 相应条目（如涉及）。
