# codemap.md —— 模块与部署地图

> 状态：现行查询件｜as_of 2026-10-06

## 工作区

| 位置 | 职责 |
|---|---|
| Windows `C:\Users\zkyxy\Documents\codex-xiangrugu` | 唯一 Git 修改入口；不运行项目代码 |
| 32 `/opt/mydocker/xiangrugu/deploy` | Windows 工作树的受控运行镜像；不直接编辑 |
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
  ├─ xiangrugu_sample      开发小样，计划
  ├─ xiangrugu_rehearsal   全量彩排，计划
  ├─ xiangrugu             正式目标，计划
  └─ cbdb                  现有观察库，无权威，后续另行授权删除

另有 cbdb_reh              旧彩排库，无权威，处置待用户指令

同宿主 pg32:5432           生产实例，禁止触碰
```

同宿主的 `xiangrugu-dev` 是整个项目的常驻开发容器，不是常驻导入服务。它从 `/opt/mydocker/xiangrugu/deploy` 读取同步后的工作树并提供 watcher/测试反馈；数据导入命令仍按需启动。

2026-10-08 CRS工具对应dev/test/runtime镜像已验证；授权救急回退镜像核验后仅更新dev，真实watcher284及完整292测试通过，B-14部署阻断解除。真实摘要、备份边界及接续统一见首版release/spatial-review.md最新节，不能因标签变化而省略容器实际状态核查。

连接参数、路径政策和资源门槛的唯一机器可读来源是 `datamgmt/config/roots.yaml`。2026-10-06 只读核查确认 `pg32b` 正在运行、`xiangrugu` 尚不存在；计划库名不代表已创建。

## 托管

- Gitea 仓库：`git@gitea:deepseekharness/xiangrugu`，默认分支 `main`；
- Gitea Wiki 是外围知识层，不参与运行或验收；
- 凭据位置和密钥内容不在项目文档中展开。
