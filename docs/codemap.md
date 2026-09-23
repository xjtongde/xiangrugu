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
| 数据 NAS 挂载 | `//192.168.3.61/workmetadata` → **`/mnt/wd61workmetadata`（唯一正路径，2026-09-23 用户令）**。旧 `/mnt/wd` 软链同日按令**已删**（N-01 纪要内旧路径不回改，勘正注见 memos；历史 log 行保原样）。权限实测：初测挂载内 admin（`.smbkey`）整卷只读、guest 匿名可写；**2026-09-23 用户采 B 案于 NAS 端给 admin 开写**，复测 root/zky/子目录三写全通（注：服务端改 ACL 后须重挂——cifs 旧树连接缓存旧权限）。WSL 无 systemd，条目内 `x-systemd.*` 两选项休眠，开机由 WSL init 走 mount -a 生效。卷上另见项目外用户自存目录（爱因斯坦/霍金），项目不碰 | 已定（2026-09-23 路径定型） |
| 哈佛全量仓 `/mnt/wd61workmetadata/harvard-full/` | 2026-09-23 用户令"全部拿过来"：Harvard Dataverse 的 CHGIS 树＋CBDB 树全量已发布件——**370 文件 / 10.64 GiB 逐件尺寸核验吻合**（MD5 抽检；65 个数据集目录，形如 `doi_10_7910/DVN/*`）。**构成实账（2026-09-23 按数据集标题六分法核算，用户"必须搞清楚"令）**：CBDB 历年发布档案 3.51G（6 集——同一库 2017→2025 **九个版本堆叠**，与家中旧库同源，净新增≈0.9G 的 2025 MDB 快照）＋ 历史地图影像栅格 2.72G（12 集，黑龙江全省舆图/柯兹洛夫蒙藏图/俄藏北京地图等**扫描件大图**，全新增量）＋ CHGIS 历代向量 1.93G（10 集，V2/V3/V4/V5 **旧版本**＋V6 时序面包——家中已有 V6 核心表，旧版为演变考据储备）＋ LoGaRT **软件**权重 1.86G（是工具模型，非语料）＋ Hartwell/TGAZ 等专题 0.19G ＋ 其他 35 个小集 0.43G（书院/全元文索引/传教士著作/日本GIS/DCW/BGIS…）。**要算"真正的净新增内容"约 3.5G；其余 7G 是版本堆、扫描件和软件**——10G 不等于 10G 的新知识。含 CBDB 历年发布序列（2017→2025：最新 2025-05 为 ACCESS/MDB 包、解包 5GB；2024-02 SQLite 877.9MB 等）、CHGIS V2–V6 历代 shapefile 全套（政区面/点、DEM、GNS 地名、海岸线、铁路、图幅索引）、Hartwell 宋辽金 GIS、TGAZ、日本历史 GIS、俄藏中国地图、黑龙江舆图、LoGaRT-BERT、传教士著作、全元文索引、2957 书院等。货单随货（仓内四件）：`README_provenance.md`（出生纸：来源/验证法/复拉方法/许可）、`datasets.tsv`（65 数据集总账：DOI/树别/件数/字节/标题/目录）、`harvard_dl.tsv`（370 件逐行含 fid 可复拉）、`harvard_manifest.txt`（树形货单，标题字段不全、认件以 datasets.tsv 为准）；拉取管线与流水存档 `ops/harvard/`（git 外）。许可注意：CHGIS 系学术用禁商用禁再分发，CBDB 系 CC 类——**未逐件摘抄，启用哪件核哪件**（联动 N-01 落盘纪律）。**对账勘正（2026-09-23，三次修正·读官方自述后定骨）**：① **家中两件旧货都系哈佛官方**——`chgis-v6`＝Dataverse 官方件（VERIFICATION.md 当时已记 DOI 出处，本次复核家中两 zip 与新仓同款 **MD5 全同**）；`cbdb-project`＝**CBDB 官方 HuggingFace 仓 `cbdb/cbdb-sqlite` 的最新滚动发布**（org 名即"China Biographical Database Project (CBDB)"、档案链回哈佛官网、许可 CC BY-NC-SA；家中 JSON 与 HF 根 `latest.json` 逐字节同、sqlite 实算 SHA256 `bde1bb8e…` 与官方记载全同，构建日 2026-09-19）——**前记"线上库自导出/非官方打包"系误判，作废**；② **CBDB 官方实为两速通道**：HF＝快车道（月度滚动，家中即最新 0919 版，zip 139MB→库 586MB）；Dataverse＝档案/引用慢车道（bi 2025-05 系 ACCESS 快照，比家中**旧一年**，SQLite 停更在 2024-02）——新仓 CBDB 件价值＝可引用 DOI 档案＋版本序列＋MDB 制式（含家中 sqlite 所无的 `ADDR_XY`、ZZZ 预连接宽表族、说明书中英文 PDF），**不是"更多的数据"**；③ 遗留疑点挂查：`POSTED_TO_ADDR_DATA` 在两种官方制式行数悬殊（家中 sqlite 46.5 万 vs bi2025 MDB 185.3 万，mdb-count 复核非统计假象）——口径差待查（可能制式/归并规则不同），启用仕宦地点分析前必须查清；④ chinese-poetry/poetry-source 系社区产物与哈佛无干，本批零增量。原语料四库不动 | 已定（2026-09-23） |
| 构建主机与构建方式 | 待项目定型 | 待裁决 |
| 生产部署目录 / 端口 / 数据文件 | 待项目定型 | 待裁决 |

要点：

- 文档、源码、测试只存在于权威工作区；
- 部署模式定型后，运维操作细节另立文档并登记入 `docs/index.md`，本表只留事实行与指针（R-04）。

## §3 与其他文档的接缝

- 版本与发版纪律＝待项目定型后开设（rules.md 预留条款位 R-07+），届时发版流程若要求"部署快照刷新"，义务指向本文件 §2；
- 本文件出现的任何"待裁决"字样被用户指令落定后：更新本表 ＋ 记 `docs/log.md` 一行 ＋ 记 `docs/features.md`/`docs/improvements.md` 相应条目（如涉及）。
