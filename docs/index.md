# index.md —— 文档索引

当前接手先读 [六块整理进度](../datamgmt/docs/IMPORT-PACKAGE-TODO.md)。本索引只维护文档职责与权威顺序，历史进度已迁入 [历史摘录](../datamgmt/docs/PROGRESS-HISTORY.md)。

仓库文件链接使用相对路径。Windows 11 本机专用笔记不入仓，也不是接手依赖；跨 clone 文档对齐及各自提交身份按 `rules.md` R-10/R-11 执行。

## 当前入口

| 文档 | 职责 |
|---|---|
| [六块整理进度](../datamgmt/docs/IMPORT-PACKAGE-TODO.md) | 当前阶段、六块任务、交付、验收状态和讨论结论 |
| [设计](../datamgmt/docs/DESIGN.md) | 数据保真、合同、完整性及全量发布门 |
| [操作生命周期](../datamgmt/docs/OPERATIONS.md) | 操作顺序和当前授权边界 |
| [工程实施计划](../datamgmt/docs/IMPLEMENTATION-PLAN.md) | 原 Task 1–18 的依赖及逐任务历史 |
| [模块资产](../datamgmt/README.md) | 已有代码、原型及能力缺口 |
| [历史摘录](../datamgmt/docs/PROGRESS-HISTORY.md) | 原入口的历史进度，保留当时语义 |

## 历史证据与文档职责索引

下列带日期的状态、预算和下一步属于各记录当时；当前派工从六块整理进度进入。历史机器证据不重写，旧结论与新证据之间以新增更正说明衔接。

其余 SQLite 75 表的逐表历史预算依据见 `datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-remaining-budget.draft.json`，后续修订见同目录 `sqlite-value-resource-revision.draft.json`。原草案保留生成时点，实际覆盖由所选收据证明，SQLite 专题事实见 `sqlite-review.md`，全项目当前进度以六块整理进度为准。

| 文档 | 职责 |
|---|---|
| `docs/superpowers/evidence/2026-10-13-controller-evidence/README.md`、`medium-next-review.draft.json` | I-06人工停止留证TDD/一次复核/1043开发与候选验证、241原件及新中组非执行待审；旧真实根因未知，58/78不变 |
| `docs/superpowers/evidence/2026-10-13-medium-retry/README.md` | 已明确授权中组一次只读重试的第9对象取消/8内部完成、41原件及外层触发未知；无新完整期望，58/78保持，I-06待人工留证改进 |
| `docs/superpowers/evidence/2026-10-12-task-tail/README.md`、`medium-retry-review.draft.json` | 末对象失败诊断计数TDD/候选收尾；原中组10表156列一次重试非执行审阅，权限false，无新真实读取 |
| `docs/superpowers/evidence/2026-10-12-task-failure/README.md` | B-18人工静态错误/阶段/监督关联、先失败后修复与候选证据；无真实重读，原中组根因未知，58/78保持 |
| `docs/superpowers/evidence/2026-10-12-sqlite-next-groups/README.md`、release/`sqlite-value-next-groups.review.draft.json` | 仅元数据核实剩余中组10表156列/大组10表235列；中组实施与精确只读方案待新授权，无新源读/测试 |
| `docs/superpowers/evidence/2026-10-12-sqlite-medium/README.md` | 中组入口995开发/972通过23跳过候选及人工证据；真实10表批失败无新增期望，B-18诊断缺口，累计58/78 |
| `docs/superpowers/evidence/2026-10-12-read-cache-policy/README.md`、release/`sqlite-value-small.expected.draft.json` | 本轮有界缓存接线、958开发/935通过23跳过候选、55表326列期望与全快照成功；累计58/78，仍源侧DRAFT |
| `docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md` | 已批准55表只读控制/监督/发布接线，93相关/936开发通过；test构建775/828/1140持续换出取消，无新候选/真实源读取，授权保留 |
| `docs/superpowers/evidence/2026-10-11-sqlite-draft-gates/README.md` | runtime草案3项拒绝验证/非执行字段缺口；随后55小表与一次固定快照复核明确授权，接线与真实执行尚未开展 |
| `docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md` | 停点后明确继续的候选恢复：885通过/23跳过，runtime生成55表326列元数据草案；50次换出723稳定、原限制保持，真实关闭 |
| `docs/superpowers/evidence/2026-10-11-host-swap-investigation/README.md` | 候选停止后只读调查：空闲723/723/723页稳定，当前交换主要记在Docker/containerd服务；事件根因未知，未恢复负载或修改停止门 |
| `docs/superpowers/evidence/2026-10-11-sqlite-task-preparation/README.md` | 元数据准备器31人工/908开发通过，完成marker修正；候选242/618/723页持续换出停止，runtime未运行，全DRAFT且真实关闭 |
| `docs/superpowers/evidence/2026-10-11-sqlite-small-readiness/README.md`、release/`sqlite-value-small-readiness-refresh.draft.json` | 当前21项输入/四项代码预期变化与55表范围、候选参考的非执行补充；任务准备器方案待确认，无新项目测试或真实授权 |
| `docs/superpowers/evidence/2026-10-10-sqlite-lifecycle-deadline/README.md` | 人工整程1800/1830/1880秒接线，14失败转85通过、877开发、候选854通过/23跳过；只读控制/短超时及限制证据，真实模式关闭 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-small-execution-review.md`、`sqlite-value-small-execution-review.draft.json` | 55表/326列非执行范围/逐表预算与输入摘要；整程截止已接入人工验证，清单绑定准备时点输入，仍不是读取授权 |
| `docs/superpowers/evidence/2026-10-10-sqlite-task-control-resume/README.md` | 用户继续后的人工控制恢复验证：候选840通过/23跳过，外部摘要及实际镜像创建前拒绝、只读控制成功；保留宿主单区间换出与前轮停止记录 |
| `docs/superpowers/evidence/2026-10-10-sqlite-task-control/README.md` | 本轮人工任务外部摘要与镜像身份门、P-17修正、863开发回归和候选swap_pressure停点；当时后续控制层实际验证未运行，恢复结果见上一行 |
| `docs/superpowers/evidence/2026-10-10-sqlite-readonly-entry/README.md` | 正式只读入口准备：请求/批准/关联文档和逐表预算绑定、完整成员预检、实际人工只读挂载及可写拒绝候选证据；未实现真实控制器或读取75表 |
| `docs/superpowers/evidence/2026-10-10-sqlite-batch-runner/README.md` | 本轮人工包装、宿主采样/租约/SSH控制心跳、终端新采样发布及受限候选/取消/一次新成果复核证据；非完整Task8或真实75表读取就绪 |
| `docs/superpowers/evidence/2026-10-10-sqlite-batch-resources/README.md` | 人工数据批级两次摘要/资源停止核心、一次复核修正及775开发检查证据；未接通真实监控/执行包装层、未构建候选或读取75表 |
| `docs/superpowers/evidence/2026-10-10-sqlite-expectations/README.md`、release/`sqlite-value-canary.approved.json`、`sqlite-value-canary.expected.draft.json` | 三表源侧期望衔接与真实只读核对的范围/唯一答案；全快照复核、一次评审修复及候选证据；3/78表，非PG验收或导入授权 |
| `docs/superpowers/evidence/2026-10-10-sqlite-values/README.md` | 已批准的小范围SQLite独立原生值读取接口、41人工检查/705开发回归、候选镜像与一次评审修复证据；不含真实读取/PG/导入 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-target-mapping-review.md`、`sqlite-target-mapping-proposal.draft.json`、`sqlite-target-mapping-decisions.draft.json` | 78表/736列命名与源显式空值规则提案及随后按既定原则继续的子批次政策确认；不批准全版本冻结或导入 |
| `datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-contract-preparation.draft.json` | 78表/736列无序逐值核对结构描述与结构摘要；32既有API核验，独立源记录数/值摘要仍空，非完整值合同 |
| `docs/superpowers/specs/2026-10-10-scratch-cleanup-safety-design.md` | B-16保守保留与管理层隔离回收的待审路线比较；仅方案，不算修复或Task8实施授权 |
| `docs/superpowers/evidence/2026-10-10-cleanup-layout/README.md` | 5项配置路径失败修复及B-16回收补丁被否决/撤回的检查、评审和候选证据；B-16仍未解决 |
| `docs/superpowers/plans/2026-10-09-sqlite-unordered-value-progress.md` | 已批准四任务合成实现、先失败后实现、一次评审与候选验证交接账；未晋级或导入 |
| `docs/superpowers/evidence/2026-10-09-sqlite-unordered-values/README.md` | 原始测试/构建/退出状态、构建输入摘要与合成范围验证证据入口 |
| `docs/superpowers/plans/2026-10-09-sqlite-unordered-value-comparison.md` | 已批准并完成合成范围的无序标量比较四任务计划；不含真实源/数据库访问或替换服务 |
| `docs/superpowers/specs/2026-10-09-sqlite-unordered-value-comparison-design.md` | 已确认并实现合成切片的SQLite整行内容/重复次数核对设计；不批准真实适配器、合同冻结或导入 |
| datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-type-decisions.draft.json、sqlite-types-approved.draft.json | 736字段保存类型与标量原值保留规则的用户确认/逐项清单；不批准名称、空值约束、独立值合同或导入 |
| datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-unobserved-type-proposal.draft.json | 36个空表/全NULL字段的原类型及空值约束定义、逐列待审建议；仅源声明依据，不冒充值域证据或批准 |
| datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-type-observations.draft.json | 全78表/736列观察到的API存储类、700列待审类型候选及36空表/全NULL列未决清单，非执行合同 |
| docs/superpowers/plans/2026-10-09-sqlite-remaining-types-progress.md | 75表连续执行、前批11成功/预算出口及随后64表预算恢复授权/TDD/候选与执行账 |
| docs/superpowers/plans/2026-10-09-sqlite-remaining-types.md | 待审的SQLite其余75表/708列分批统计方案及精确scope清单，尚未批准源值读取；单表串行、失败停止 |
| docs/superpowers/plans/2026-10-09-sqlite-types-progress.md | SQLite仅对象角色批准、三表28列类型统计/TDD、候选镜像与单次评审账；类型/值/目标映射未批，不导入 |
| docs/superpowers/plans/2026-10-09-sqlite-structure-progress.md | CBDB 单件 SQLite 结构切片 TDD、候选镜像/单次评审及运行证据；不是 Task10 或导入授权 |
| datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-review.md | CBDB完整结构、78表/76索引角色批准及78表类型观察；类型/值/目标映射合同仍待审 |
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

新会话先读 `AGENTS.md`、`rules.md`、本索引、`datamgmt/docs/IMPORT-PACKAGE-TODO.md` 和 `datamgmt/README.md`；准备数据接入开发时再读 `datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md` 与 `datamgmt/docs/PITFALLS.md`。其余按需读取。

历史内容可从 Git 恢复。2026-09-30 大清理前的集中回收点为 `75ecd77`；本轮删除内容可从变更前提交 `5627da7` 恢复。
