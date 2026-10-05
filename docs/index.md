# index.md —— 文档索引

> 状态：现行｜as_of 2026-10-06

## 现行文档

| 文档 | 职责 |
|---|---|
| `AGENTS.md` | 项目目标、成功标准、入口阅读顺序 |
| `rules.md` | 操作、记账、单一源和忠实导入纪律 |
| `docs/import-plan.md` | 导入合同、技术方案、阶段和验收门槛 |
| `datamgmt/README.md` | 数据管理模块现状、目录职责和实现缺口 |
| `datamgmt/config/roots.yaml` | 唯一源根、路径政策、目标实例与数据库 |
| `datamgmt/PITFALLS.md` | 导入设计必须拦截的历史失败模式 |
| `datamgmt/recon/usedata_ledger_findings.md` | 当前盘点草案的人读摘要；机器证据在同目录 |
| `docs/cbdb.md` | CBDB 结构知识和已确认的源生异常 |
| `docs/codemap.md` | 模块与部署拓扑查询件 |
| `docs/holdings.md` | 已持有资料及许可边界 |
| `docs/bugs.md` | 我方缺陷账 |
| `docs/improvements.md` | 工程改进账 |
| `docs/features.md` | 新能力账 |
| `docs/log.md` | 文档结构变动日志 |

`demo/` 是已纳入 Git 的非权威演示资产，不在导入执行链上。

## 权威顺序

1. 用户当前明确指令；
2. `AGENTS.md` 的项目目标；
3. `rules.md`；
4. `docs/import-plan.md` 与 `datamgmt/config/roots.yaml`；
5. 机器证据、模块文档及专职账；
6. 其他说明和 Gitea Wiki。

冲突时不得自行拼接两种说法，应报告冲突并按上列顺序裁定。

## 阅读顺序

新会话先读 `AGENTS.md`、`rules.md`、本索引和 `docs/import-plan.md`；准备开发时再读 `datamgmt/README.md` 与 `datamgmt/PITFALLS.md`。其余按需读取。

历史内容可从 Git 恢复。2026-09-30 大清理前的集中回收点为 `75ecd77`；本轮删除内容可从变更前提交 `5627da7` 恢复。
