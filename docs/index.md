# index.md —— 文档索引

> 状态：现行｜as_of 2026-10-09

## 现行文档

| 文档 | 职责 |
|---|---|
| docs/superpowers/plans/2026-10-09-sqlite-types-progress.md | SQLite仅对象角色批准、三表28列类型统计/TDD、候选镜像与单次评审账；类型/值/目标映射未批，不导入 |
| docs/superpowers/plans/2026-10-09-sqlite-structure-progress.md | CBDB 单件 SQLite 结构切片 TDD、候选镜像/单次评审及运行证据；不是 Task10 或导入授权 |
| datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-review.md | CBDB完整结构、78表/76索引角色批准及三表类型统计；类型/值/目标映射合同仍待审 |
| `docs/superpowers/plans/2026-10-09-text-value-contract-progress.md` | 五件规范值提案、随后范围批准与元数据TDD账；非执行批准投影，不读取真实源或数据库、不冻结或导入 |
| docs/superpowers/plans/2026-10-08-json-schema-progress.md | 独立Schema原始文档校验及随后授权的仅dev晋级/回退与watcher证据；B-15恢复，未冻结或导入 |
| `AGENTS.md` | 项目目标、成功标准、入口阅读顺序 |
| `rules.md` | 操作、记账、单一源和忠实导入纪律 |
| `docs/import-plan.md` | 项目级兼容入口，只指向数据接入模块文档 |
| `datamgmt/README.md` | 数据接入模块入口、现有资产和实现缺口 |
| `datamgmt/docs/DESIGN.md` | 数据接入模块唯一权威设计、合同、阶段与验收门槛 |
| `datamgmt/docs/IMPLEMENTATION-PLAN.md` | 已批准方案与 32 主机常驻开发环境修订对应的执行计划；开发、构建、部署和提交按授权门推进 |
| `docs/superpowers/specs/2026-10-08-text-value-comparison-design.md` | 已确认text/bigint有序值比较规格；类型/长度前缀与独立逐值比较的技术细化，不是完整Task9或冻结合同 |
| `docs/superpowers/plans/2026-10-08-text-value-comparison.md` | 已批准并完成纯合成切片的TDD计划；执行账及验证证据从该文件续接，不含源/数据库访问或服务替换 |
| `docs/superpowers/plans/2026-10-08-text-source-values-progress.md` | 五件文本源侧规范值期望衔接的授权、实施与验证账；真实期望与状态统一见release/text-review.md，不是冻结或导入授权 |
| `datamgmt/docs/OPERATIONS.md` | 首次构建、数据更新、发布和失败处理 |
| `datamgmt/config/roots.yaml` | 唯一源根、路径政策、目标实例与数据库 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/review.md` | 真实快照清点、初稿阻断、选择器修复及校验账候选预览证据入口；模型和两条候选通过，导入门仍阻断，未冻结 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/member-review.md` | 最新 metadata 候选的逐件依据、全量物理分组口径、三件制表文本头部观察与未决审阅顺序；不是冻结或导入授权 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/text-review.md` | 五件读取/列/行号/schema批准及源侧规范值期望证据；表名及全版本合同未完成，不改变 BLOCKED |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/spatial-review.md` | 两组空间映射/SRID4326批准及离线CRS验证，原X/Y与轴序差异留证；救急回退/dev更新已核验，表名/生产读取器及完整合同未完成 |
| `datamgmt/docs/PITFALLS.md` | 数据接入必须拦截的历史失败模式 |
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
4. `datamgmt/docs/DESIGN.md` 与 `datamgmt/config/roots.yaml`；
5. 机器证据、模块文档及专职账；
6. 其他说明和 Gitea Wiki。

冲突时不得自行拼接两种说法，应报告冲突并按上列顺序裁定。

## 阅读顺序

新会话先读 `AGENTS.md`、`rules.md`、本索引和 `datamgmt/README.md`；准备数据接入开发时再读 `datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md` 与 `datamgmt/docs/PITFALLS.md`。其余按需读取。

历史内容可从 Git 恢复。2026-09-30 大清理前的集中回收点为 `75ecd77`；本轮删除内容可从变更前提交 `5627da7` 恢复。
