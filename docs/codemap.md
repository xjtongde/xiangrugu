# codemap.md —— 代码地图与部署位置

> **状态：现行**｜as_of 2026-09-30
> 本文件是**查询件**，**不入必读链**（见 `docs/index.md` §三）。

## 1 目录树（工作区 `/root/xiangrugu/`＝项目唯一权威源）

```text
/root/xiangrugu/
├── .gitignore              忽略 `.agents/`（用户令"Skill不进git"）、`.secrets/`、**`ops/`**
├── AGENTS.md               AI 助手入口（§1 项目目标**待用户定义**）
├── rules.md                纪律总纲 R-01～R-07（R-08+ 预留）
├── datamgmt/               ★数据管理模块（**入 git**）
│   ├── README.md           模块入口：职责边界、五条纪律、五阶段表
│   ├── PITFALLS.md         防坑条目录 P-01…P-24（一切设计决定之依据）
│   ├── config/roots.yaml   ★数据源根与目标库（机器可读权威）
│   ├── config/             sources.yaml／decoding.yaml／g4_assertions.yaml（阶段二，候口令）
│   └── truth/ importer/ verifier/ tests/ maintenance/ recon/   空壳占位（候开工口令）
├── docs/                   文档（`index.md` 为登记处）
├── demo/                   ⚠ **未入 git**——演示三页＋build 脚本（2026-09-30 用户令留下；缺口＝I-05）
├── memos/memos.md          用户交录纪要（**非实施指导**）
└── ops/harvard/load-b2/    ⚠ **git 不跟踪**——旧装载脚本 23 支 `b2*.py`＋`src_paths.tsv`（1,770 行台账）＋recon/manifest
                            ↑ **L3 原始证据层，勿删**：`roots.yaml` 之相对键来源、`PITFALLS.md` 全部实证之出处
```

## 2 模块职责

| 路径 | 职责 | 权威文档 |
|---|---|---|
| `datamgmt/config/roots.yaml` | 数据源根、只读声明、校验账、双根共键换算、路径政策、目标库事实 | 自身（**冲突时压过任何人读摘要**） |
| `datamgmt/PITFALLS.md` | 旧库建设所踩坑之唯一登记处 | 自身（实证指向 `ops/` 与 `docs/bugs.md`） |
| `datamgmt/README.md` | 模块定位、纪律、阶段表 | 自身 |
| `datamgmt/{truth,importer,verifier,tests,maintenance,recon}/` | 真值读取／装载／验证／测试／维护／工作账——**现为空壳**，候开工口令（R-01） | `docs/import-plan.md` §4–§7 |
| `demo/` | 人物／网络／漫游三页演示＋build 脚本 | I-05（候裁：是否入 git） |

## 3 主机与实例

| 主机 | 硬件（as_of） | 实例 |
|---|---|---|
| **192.168.3.32** | i7-6567U；RAM 可用 5.5G；`/` 余 196G（09-24）；时区两文件正常（**无 B-02**） | `pg32` 生产 **5432**；**`pg32b` 5433**（`cbdb` 库宿主）；另有 nginx32（unhealthy 观察项）／n8n／chainlit／graphrag |
| **192.168.3.36**（主机名 `one`）<br>⚠ **本项目已不再依赖**（2026-09-30 用户令） | AI/GPU 主力机；**2026-09-30 实测完全不可达**（`ping` 100% 丢包／`ssh` 与 `5432` 皆 No route to host）；`/etc/timezone` 系空目录（**B-02**，已降为非阻塞） | **`pg36` 5432**——~~数据底座／彩排靶机~~ **已作废**；仅存关联＝`pg32b` 之镜像系其同字节拷贝。详见 `docs/pg36.md`（**状态：历史**） |
| 192.168.3.35 | — | Gitea **17080**（含 wiki 仓） |

⚠ **共实例告警**：`pg32b` 与生产 `pg32` **同在 32 主机** → 任何装载/验证须 `nice`／`ionice` 且 **loadavg<4.0 门禁**（`roots.yaml` 已载）。
⚠ **DB 严禁跑 NAS**（部署标准 §2.1–2.2）；NAS 仅作备份目的地。

## 4 存储路径

| 路径 | 角色 |
|---|---|
| `/mnt/wd61workmetadata` | NAS 唯一正路径（`//192.168.3.61/workmetadata`，2026-09-23 用户令） |
| `/mnt/wd61workmetadata/usedata/` | ★**权威数据源**（只读，190 件）→ 权威＝`datamgmt/config/roots.yaml` |
| `/mnt/wd61workmetadata/xiangrugudata/` | **下载区**（只读原件，7 树／16,803 件，账面 09-28） |
| `/mnt/nas-mirror/` | **项目禁用**（2026-09-27 用户裁；旧脚本 15 处仍硬编码，**该路径实测仍存在→误用不报错**） |
| `/tmp/` | **禁作工作账落点**（P-12；`/tmp/pg32b-load2` 实测已不存在） |
| `.secrets/gitea_account` | 600 权限，git 外；仅令牌不能之事（铸/撤令牌等） |

## 5 Git 与代码托管

- **远程**：Gitea `http://192.168.3.35:17080/deepseekharness/xiangrugu`（私有，默认分支 `main`）；`origin` 已设。
- **凭据**：`credential.helper=store --file=/root/.git-credentials`（用户 2026-09-22 裁**长期留用**）；工单令牌 `xiangrugu-issues`（id=7，scopes `write:issue`）；真账密收编 `.secrets/gitea_account`（用户令"这个 key 你以后用"）。
- **外围知识层**＝Gitea wiki 仓（2026-09-25 用户定性"非必要材料，用学习与了解"）——**非权威**，冲突以 `docs/index.md` §二为准。
- ⚠ `.gitignore` 吃掉 `ops/` 致旧装载脚本不入仓、NAS 又无副本 → **重建能力单点（P-16）**；故 `datamgmt/` 一律入仓。
