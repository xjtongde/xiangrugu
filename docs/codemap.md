# codemap.md —— 模块与部署地图

> 状态：现行查询件｜as_of 2026-11-19

## 工作区

| 位置 | 职责 |
|---|---|
| Codex 本地 clone（仓库根 `.`） | Codex 用自己的账号经 Gitea 交付文档；个人路径只在本机记录 |
| 38 的 DSH clone（仓库根 `.`） | DSH 用自己的账号经 Gitea 提交；保留现有工作树，项目构建和测试仍在 32 |
| 32 `/opt/mydocker/xiangrugu/deploy` | 经授权接收并核对 Git 版本的受控运行目录；不直接编辑 |
| 32 `/opt/mydocker/xiangrugu/deploy/docker-compose.yml` | 当前实际Compose入口；仅dev晋级与watcher证据见JSON Schema执行账dev晋级节 |
| `xiangrugu-dev:/workspace` | 常驻开发容器中的只读源码视图；所有项目进程在 32 运行 |

| 路径 | 职责 |
|---|---|
| `datamgmt/` | 长期数据接入、版本更新、独立验证与发布模块 |
| `datamgmt/docs/` | 模块权威设计、操作生命周期和防坑规则 |
| `datamgmt/config/` | 当前机器可读根配置；长期合同结构见模块设计 |
| `datamgmt/recon/` | 首版盘点草案；证据迁入首个 release 后退役 |
| `docs/` | 项目级入口、账目和查询件；不重复模块方案 |
| `demo/` | 已纳入 Git 的演示资产；非权威，不在导入链上 |

详细文件现状见 `datamgmt/README.md`，不要在本文件维护手写全树或文件数量。

## 部署拓扑

```text
/mnt/wd61workmetadata/usedata  (唯一权威源)
                 │ 核实来源 → 复制 → 独立摘要校验
                 ▼
/opt/mydocker/xiangrugu/data/imports/usedata/<snapshot_id>
                 │ 已验证快照，只读导入
                 ▼
192.168.3.32 / pg32b:5433
  ├─ xiangrugu             用户已选定的本次目标，最后实查尚未创建
  └─ cbdb                  现有观察库，保留，无权威

另有 cbdb_reh              旧彩排库，保留，无权威

同宿主 pg32:5432           生产实例，禁止触碰
```

同宿主的 `xiangrugu-dev` 是整个项目的常驻开发容器，不是常驻导入服务。它从 `/opt/mydocker/xiangrugu/deploy` 读取经核对的 Git 工作树并提供 watcher/测试反馈；数据导入命令仍按需启动。文档对齐遵循 `rules.md` R-10，不通过本机传输脚本覆盖其他 clone。

2026-10-08 CRS工具对应dev/test/runtime镜像已验证；授权救急回退镜像核验后仅更新dev，真实watcher284及完整292测试通过，B-14部署阻断解除。真实摘要、备份边界及接续统一见首版release/spatial-review.md最新节，不能因标签变化而省略容器实际状态核查。

连接参数、路径政策和资源门槛的唯一机器可读来源是 `datamgmt/config/roots.yaml`，其中 sample/rehearsal 库名是历史规划，不代表本次必须创建。最后实查状态与当前进度统一见 [六块整理进度](../datamgmt/docs/IMPORT-PACKAGE-TODO.md)。旧库保留；删除须另获授权。

## 托管

- Gitea 项目为 `deepseekharness/xiangrugu`；各自配置对应账号的 SSH remote，具体本机别名不作为共享文档依赖。DSH 交付分支为 `dsh/p01-real-prep-20261113`，实际分支头读取后再确认；
- Gitea Wiki 是外围知识层，不参与运行或验收；
- 凭据位置和密钥内容不在项目文档中展开。
