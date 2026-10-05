# codemap.md —— 代码地图与部署位置

> **状态：现行**｜as_of 2026-10-05
> 本文件是**查询件**，**不入必读链**（见 `docs/index.md` §三）。

## 1 目录树（工作区 `/root/xiangrugu/`＝项目唯一权威源）

```text
/root/xiangrugu/
├── .gitignore              忽略 `.agents/`（用户令"Skill不进git"）、`.secrets/`
├── AGENTS.md               AI 助手入口（§1 项目目标**待用户定义**）
├── rules.md                纪律总纲 R-01～R-09
├── datamgmt/               ★数据管理模块（**入 git**）
│   ├── README.md           模块入口：职责边界、五条纪律（阶段表见 `import-plan.md` §10）
│   ├── PITFALLS.md         防坑条目录 P-01…P-25（一切设计决定之依据）
│   ├── config/roots.yaml   ★数据源根与目标库（机器可读权威）
│   ├── config/             g4_assertions.yaml（闸4 断言，已建）；sources.yaml／decoding.yaml＝阶段二重建（旧 868 版已删）
│   └── truth/ importer/ verifier/ maintenance/ recon/   已建（真值读取·load.py·verify.py·维护脚本·工作账底账）；tests/ 仅 .gitkeep 空壳
├── docs/                   文档（`index.md` 为登记处）
├── demo/                   ⚠ **未入 git**——演示三页＋build 脚本（2026-09-30 用户令留下；缺口＝I-05）
└── memos/memos.md          用户交录纪要（**非实施指导**）
```

## 2 模块职责

| 路径 | 职责 | 权威文档 |
|---|---|---|
| `datamgmt/config/roots.yaml` | 数据源根、只读声明、校验账、双根共键换算、路径政策、目标库事实 | 自身（**冲突时压过任何人读摘要**） |
| `datamgmt/PITFALLS.md` | 旧库建设所踩坑之唯一登记处 | 自身（历史实证脚本已 2026-10-05 删；教训以本文件＋`docs/bugs.md` 留存） |
| `datamgmt/README.md` | 模块定位、纪律（阶段表→`import-plan.md` §10） | 自身 |
| `datamgmt/{truth,importer,verifier,maintenance,recon}/` | 真值读取／装载／验证／维护／工作账——**已建**（truth 28 件、load.py、verify.py、维护 5、recon 底账 27）；tests 空壳；阶段二重建 sources.yaml | `docs/import-plan.md` §4–§7 |
| `demo/` | 人物／网络／漫游三页演示＋build 脚本 | I-05（候裁：是否入 git） |

## 3 主机与实例

| 主机 | 硬件（as_of） | 实例 |
|---|---|---|
| **192.168.3.32** | i7-6567U（2C/4T）；RAM 总 7G／可用 5G；`/` 233G 总、**余 189G**（**09-30 现算**）；时区两文件正常 | `pg32` 生产 **5432**；**`pg32b` 5433**（`cbdb` 库宿主）；另有 nginx32（unhealthy 观察项）／n8n／chainlit／graphrag |
| 192.168.3.35 | — | Gitea web **17080**／SSH **17022**（含 wiki 仓） |

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

- **远程**：Gitea `git@gitea:deepseekharness/xiangrugu`（SSH **17022**，私有，默认分支 `main`）；`origin` 已切 SSH，`~/.ssh/config` 有 `Host gitea` 块（`git` 用户＋专用密钥）。
- **凭据**：**SSH 为主**——`~/.ssh/gitea/id_ed25519`（2026-10-05 新制并登记 Gitea，无口令，供 DSH 免密走 `git@gitea`）；HTTP 回退＝`credential.helper=store --file=/root/.git-credentials`（用户 2026-09-22 裁**长期留用**）；工单令牌 `xiangrugu-issues`（id=7，scopes `write:issue`）；真账密收编 `.secrets/gitea_account`（用户令"这个 key 你以后用"）。
- **外围知识层**＝Gitea wiki 仓（2026-09-25 用户定性"非必要材料，用学习与了解"）——**非权威**，冲突以 `docs/index.md` §二为准。
- ⚠ 旧装载脚本（`ops/`）原系 P-16 重建单点——已 **2026-10-05 用户令删除**（旧方案退役，单点随删消除）；故 `datamgmt/` 一律入仓。
