# codemap.md —— 模块与部署地图

> 状态：现行查询件｜as_of 2026-10-06

## 工作区

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
/mnt/wd61workmetadata/usedata  (唯一只读源)
                 │
                 ▼
192.168.3.32 / pg32b:5433
  ├─ xiangrugu_sample      开发小样，计划
  ├─ xiangrugu_rehearsal   全量彩排，计划
  ├─ xiangrugu             正式目标，计划
  └─ cbdb                  现有观察库，无权威，后续另行授权删除

另有 cbdb_reh              旧彩排库，无权威，处置待用户指令

同宿主 pg32:5432           生产实例，禁止触碰
```

连接参数、路径政策和资源门槛的唯一机器可读来源是 `datamgmt/config/roots.yaml`。2026-10-06 只读核查确认 `pg32b` 正在运行、`xiangrugu` 尚不存在；计划库名不代表已创建。

## 托管

- Gitea 仓库：`git@gitea:deepseekharness/xiangrugu`，默认分支 `main`；
- Gitea Wiki 是外围知识层，不参与运行或验收；
- 凭据位置和密钥内容不在项目文档中展开。
