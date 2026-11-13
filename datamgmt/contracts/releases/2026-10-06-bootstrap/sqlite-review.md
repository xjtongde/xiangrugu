# CBDB SQLite 结构与逻辑对象待审

2026-11-08最终：新p01具名真实尝试在1800秒监督截止时未完成，timeout后取消，无完整批及新增期望，仍68/78。未发生心跳拒收，资源与PG健康；该次授权已使用，不重试或下一表，后续耗时定位先限人工夹具。完整合同/冻结/导入仍未通过，见[终态证据](../../../../docs/superpowers/evidence/2026-11-08-real-p01-attempt/README.md)。

2026-11-08：POSTED_TO_ADDR_DATA/8列的新attempt关闭任务卡及固定控制输入准备通过，未真实读取或新增期望；覆盖仍68/78，冻结/导入未通过。旧attempt授权不复用，新的具名读取确认待取得，见[任务卡及元数据证据](../../../../docs/superpowers/evidence/2026-11-08-p01-retry-review/README.md)。

2026-11-07：控制心跳的人工超时边界误拒收已复现并修复，完整开发/安装候选回归和自然边界验证通过，见[本轮证据](../../../../docs/superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md)。未再次读取真实源，值期望覆盖仍68/78，未冻结或导入；25日真实失败因缺帧级收据仍不能确认同因，新真实尝试须另获授权。

2026-10-25真实单表p01（POSTED_TO_ADDR_DATA/8列）获一次授权后尝试，在约1637.6秒因宿主invalid_heartbeat触发取消，worker停于object_read_sort、无完整批及新增期望。当前源值期望仍68/78，完整合同/冻结/导入未通过；控制帧根因未确认，未启动重试或下一表，见[本次失败证据](../../../../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md)。以下日期条目保留历史时点。

2026-10-14 I-07人工调度已验证：100毫秒重型校验调度/每次轻量取消截止/阶段强制复核/父监督独立人工发布摘要，26定向、1098开发、新test1075通过23跳过。相同人工2万行47万字段84.4→14.45秒；真实模式仍逐次校验、68/78与large关闭保持。初次取消137缺监督报告保留，后续运行中取消/截止无最终批。证据：docs/superpowers/evidence/2026-10-14-guard-opt/README.md。


2026-10-14人工函数定位：10表235列/2万行47万字段普通84.4秒、剖析168.7秒，独立摘要一致；控制器guard约32.3万次、累计136.4秒（剖析CLI约82%，嵌套不能相加）。报告RED1失败转1通过，产品代码/资源门未改；I-07重型校验调度设计待审。仍68/78、真实large关闭、Task8未完。证据：docs/superpowers/evidence/2026-10-14-large-profile/README.md。


2026-10-14高唯一行大组人工批：10表235列/20万行470万字段完整匹配独立摘要，约811秒/峰值72.8MiB、临时23.1MiB，换出0。新增夹具RED10失败1通过转11通过，新开发1072/安装候选1049通过23跳过；产品代码和116构建输入未变，复用固定镜像。覆盖仍68/78，真实large关闭，Task8未完。证据：docs/superpowers/evidence/2026-10-14-large-unique/README.md。


2026-10-13大组代表性人工批：10表235列（156整数/79文本）两档均完整匹配独立摘要；大档100000行/2350000字段约419.3秒、峰值61.7MiB，交换换出0。B-20心跳超时半帧丢弃人工复现后修复，开发1072/新test1049通过23跳过。仍68/78、真实large关闭、Task8未完；全组1800秒可行性未证明。证据：docs/superpowers/evidence/2026-10-13-large-representative/README.md。


2026-10-13大组人工接线：4项先失败转28通过，受限完整开发1070通过，新test1047通过/23元数据跳过；新runtime离线准备10/235、人工完整批及磁盘三场景验证通过。large真实模式仍代码关闭，覆盖68/78，无源读取/PG/冻结/导入，Task8未完。证据：docs/superpowers/evidence/2026-10-13-large-artificial-control/README.md。


2026-10-13磁盘人工验证：用户明确空间足够且须控制测试资源后，自有磁盘排序三场景通过；临时峰值157.1MiB/容器内存峰值201.8MiB，约52.4秒，交换换出0、PG未变。采用应用总账及单文件上限，非文件系统配额或硬I/O隔离；未接通真实large，覆盖68/78不变。证据：docs/superpowers/evidence/2026-10-13-large-disk-artificial/README.md。


2026-10-13大组准备：已核实68已覆盖+10大组/235列完整分割，3项人工关闭门通过；旧1GiB磁盘临时区/7200秒与现行64MiB/1800秒冲突，入口仍关闭。无真实大组读取/新增期望/PG/冻结/导入；证据：docs/superpowers/evidence/2026-10-13-sqlite-large-readiness/README.md。


2026-10-13中组前台完成：固定快照单次只读10表156列整批证书核验通过，新增354363行/5430382字段，约1492.4秒/峰值146.2MiB，交换与宿主换出0；累计68/78，剩大组10表235列未查询。仍DRAFT、无PG/冻结/导入，Task8未完成；证据：docs/superpowers/evidence/2026-10-13-medium-foreground/README.md。以下为各批历史发生时点，不代表当前覆盖数。


2026-10-13启动停点：本轮后台控制器未维持会话，真实读取尚未开始；21分钟前台人工验证通过，58/78不变，无PG/冻结/导入。新证据：docs/superpowers/evidence/2026-10-13-medium-controller-run/README.md；失败后重新调度另记授权。


2026-10-13人工留证收尾：控制外层静态触发/信号、停止和退出已完成TDD及独立候选验证；旧真实取消发送方仍未知，覆盖58/78、Task8未完成。证据与权限false的下一次中组方案：docs/superpowers/evidence/2026-10-13-controller-evidence/README.md。


2026-10-13最新：已授权中组单次只读重试约1179.5秒以cancelled停止；第9对象ADDR_CODES、8对象仅内部完成，无整批/新增期望，覆盖仍58/78。SIGTERM事件已留证，外层触发未知，I-06待人工改进；无PG/冻结/导入。证据：docs/superpowers/evidence/2026-10-13-medium-retry/README.md。


2026-10-12收尾：末对象取消/超时诊断计数窗口已修复并经人工候选验证；58/78和旧中组根因未知保持，无真实重读/PG/冻结/导入。新证据及非执行重试审阅：docs/superpowers/evidence/2026-10-12-task-tail/README.md。


2026-10-12本轮：B-18人工失败诊断与监督原因关联已验证；原中组根因未知，58/78覆盖不变，无真实重读/PG/冻结/导入，Task8未完成。统一证据：docs/superpowers/evidence/2026-10-12-task-failure/README.md。


2026-10-12中组最新：37项先失败后通过、995开发通过，新test972通过/23跳过；中组准备10表156列及人工正/负例已验证。实际中组约955.93秒失败，通用内部失败与cancelled原因未充分留存，无完整批/新期望，覆盖仍58/78；未接PG/冻结/导入，Task8未完成。证据：docs/superpowers/evidence/2026-10-12-sqlite-medium/README.md。

2026-10-12最新进度：有界缓存策略20项通过、958开发通过、新候选935通过/23跳过；固定快照完整复核及55表326列期望整批生成，约81.2秒/峰值119.5MiB，9次换出与内存停顿0。累计58/78表，另20表未查询；仍DRAFT、未接PG/冻结/导入，Task8未完成。证据：docs/superpowers/evidence/2026-10-12-read-cache-policy/README.md。


2026-10-11茶香已明确批准固定快照一次全成员复核与55小表326列源期望生成；控制/监督/发布接线现已实现外部源模式与request摘要门，26项失败转最终93相关/936开发通过，一次新成果复核0问题。test候选构建持续换出775/828/1140触发取消，未产出新镜像、未开始runtime构建或读取真实源。授权保留，因资源风险停止后续负载，不称候选/真实就绪或Task8完成。见[本轮接线与构建停点](../../../../docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md)。以下记录保留原发生时点。


2026-10-11新增runtime实际草案拒绝证据：3项负向检查通过，原草案与错误摘要在下游读取前拒绝；缺口报告列出执行字段转换、外部证书/清单选择与控制接线。随后茶香明确授权接通并人工验证只读真实控制器，复核固定快照2026-10-07-bootstrap一次、仅生成55小表326列源期望，保留原限制/停止门；不读NAS或另20表、不接PG、不冻结/导入。授权尚未执行，见[草案门与待接线范围](../../../../docs/superpowers/evidence/2026-10-11-sqlite-draft-gates/README.md)。


2026-10-11停点后茶香明确要求继续，按原限制恢复一次人工候选：test完整回归885通过/23跳过，runtime已实际生成选定元数据的55表326列全DRAFT草案；50次宿主诊断采样换出均723，原停止阈值不变、两个容器回收。上轮换出原因仍未知，不宣称资源问题修复、Task8或真实执行完成，真实读取与PG关闭。见[本轮恢复证据](../../../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md)。以下停点记录保留其发生时的结论。


2026-10-11停点后只读调查：三次空闲换出计数723/723/723稳定，当前交换页主要记在Docker/containerd服务，缺少事发逐服务基线，不能认定事件根因；未恢复候选、未修改阈值/设置/服务，无新项目测试。见[只读调查](../../../../docs/superpowers/evidence/2026-10-11-host-swap-investigation/README.md)，原候选未完成和真实关闭结论保持。


2026-10-11用户继续确认元数据准备器方案，现已实现外部身份/精确55表326列/预算校验和全DRAFT模板，31人工/908开发通过，完成marker缺陷已复现修正。候选完整回归以swap_pressure停止（242/618/723页），未继续runtime模板生成；仓库55表正式bundle未实际由候选生成。见[停点证据](../../../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation/README.md)。既有3/78表源期望不变，真实控制硬关闭，无PG/晋级/冻结/导入。

2026-10-11新增[当前准备补充](../../../../docs/superpowers/evidence/2026-10-11-sqlite-small-readiness/README.md)，绑定当前21项输入与上一轮人工候选，保留原准备时点摘要/证据；55表/326列不变，无新项目测试或真实读取。下一步仅元数据任务准备器方案待确认，不生成批准请求或开启真实执行。

2026-10-10用户继续批准整程截止接线，现已只用人工文件验证1800秒候选/1830秒宿主/1880秒SSH及晚发布停止。14失败转85相关通过、877开发通过、独立候选854通过/23跳过；实际限制、人工只读与短超时见[本轮证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-lifecycle-deadline/README.md)。下文为各轮历史时点，待审清单绑定准备时点输入，不代表当前代码摘要。仍3/78完整源期望、75未读，真实控制硬关闭，无PG/晋级/冻结/导入。

2026-10-10继续形成[真实小组待审范围与预算](sqlite-value-small-execution-review.md)，只用现有仓库元数据列明55表/326列及来源绑定；55个结构摘要已复算，历史行数不是期望。本轮未读取快照/源值、运行新测试或候选、修改代码或超时。当前人工外层300秒与小组批级1800秒在全快照校验后的计时边界需接线确认；方案提出整个候选生命周期1800秒上限，未激活真实模式，不解除读取或导入门。

2026-10-10用户在停止报告后再次要求继续；只读观察后按原资源限制恢复一次人工候选，完整回归840通过/23跳过，新控制器只读成功与四项创建前拒绝已验证，详见[恢复验证证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-task-control-resume/README.md)。上一轮swap_pressure记录保留；本轮单区间换出7页，未达到连续两段增长门，来源未知，不说宿主无交换。代码未改、镜像未重建、核心未重复复核；真实仍3/78表期望、75表未读，未接库/晋级/冻结/导入。

2026-10-10本轮人工控制层已实现外部三摘要与实际镜像身份门，根配置遵守P-17；14新检查、863开发回归通过。两独立候选构建成功，但test完整回归宿主pswpout62/66/69连续正增，按swap_pressure停止并移除，后续人工控制执行未运行；遇资源风险按用户边界停止，不重试或放宽阈值。详见[本轮控制层停点](../../../../docs/superpowers/evidence/2026-10-10-sqlite-task-control/README.md)。真实仍3/78表期望，75表未读，未接库/晋级/冻结/导入。

> 状态：DRAFT_FOR_REVIEW｜as_of 2026-10-09｜未冻结、未导入

## 当前进度：按既定原则继续，不逐字段重复询问

2026-10-10继续批准正式只读入口准备，但运行仍只人工文件；请求批准/逐表预算/关联文档及只读挂载校验已人工验证，证据统一见[只读入口准备](../../../../docs/superpowers/evidence/2026-10-10-sqlite-readonly-entry/README.md)。不把API的project_snapshot分支当真实读取批准；尚缺可信真实控制器、真实小组范围/预算及执行窗口。真实仍3/78表期望，剩余75表未读；未接数据库、冻结或导入。

2026-10-10本轮获人工衔接、同步32、自有独立test/runtime候选及专用容器执行/取消/清理授权，新增人工包装层、10秒宿主采样、容器租约与SSH控制心跳、终端新采样握手及最终暂存/fsync/no-clobber发布。代码、TDD、实际限制/停止检查和仅新成果一次复核统一见[本轮人工执行证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-batch-runner/README.md)。上一批已复核核心未重复审查；原资源草案非执行位保留历史时点，不作为真实读取授权。SQLite仍只有3/78表完整源期望，其余75表未读；真实范围消费、只读快照接入及大表临时区仍待另批，不是完整Task8或可以导入的版本。

2026-10-10茶香随后“继续”批准先改代码并用人工数据核验，已实现批级两次摘要/整批完成核心和资源压力判断/有限候选取消核心，52新增检查、101定向及775完整开发检查通过。一次只读复核的3项Important和1项Minor均以人工失败检查复现后修正；证据及未接通边界统一见[人工批级资源证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-batch-resources/README.md)。尚未构建新候选、接入真实scope/快照/监控/发布包装层或激活限制，没有真实75表读取、PG/服务/镜像别名/Git操作；不宣称完整Task8或真实运行已受保护。预算草案的非执行位仍保留生成时点，不能作为读取授权。

2026-10-10茶香要求考虑主机承受力，并同意继续修订预算。只读实测32为i7-6567U两核四线程、7,513MiB内存，项目位于SSD；当前空闲采样不代表长任务安全。[资源修订草案](sqlite-value-resource-revision.draft.json)保留旧75表逐项依据，替代其执行建议：三批仍各做完整快照复核，SQLite文件完整摘要改为每批前后各一次，预计摘要逻辑读取11,045,877,744字节而非原95,499,827,184字节，另有业务读取和排序I/O；不复用快照扫描摘要冒充原子校验。建议半个逻辑CPU/768MiB、串行、10秒采样及内存/磁盘/压力/服务异常停止门；大表临时区最多1GiB磁盘目录。整批终校验前各表结果仅暂存，原独立读取API默认校验保持；方案及故障检查须确认后才实现。当前只改非执行文档/预算，不授权新代码、真实读取、数据库或服务操作，不宣称Task8完成；旧预算和检查记录保留历史时点。

2026-10-10三表核对后，用户要求继续准备其余范围；只读已有统计形成[其余75表预算工作表](sqlite-value-remaining-budget.draft.json)，逐项绑定统计证据摘要，覆盖717列/既有5,619,215行/119,323,771字段值。建议55小表、10中表、10大表串行，1核/768MiB不变，最大表规范流参考218,438,759字节、排序临时字节保守参考655,316,034字节，因此大表临时区建议改为最多1GiB磁盘目录；这些是旧统计推导，不是新源期望。工作表不授予实现或真实读取权限，下一批范围/预算须用户明确同意；本轮无源值/数据库读取、镜像构建、服务或Git操作。

2026-10-10随后获三表源侧期望生成/真实只读核对授权，先完整复核项目快照，再读取3/78表全部行值：ADMIN_CAT_TYPES 0行、SOCIAL_INSTITUTION_ADDR 3,859行、SOCIAL_INSTITUTION_ALTNAME_CODES 1行。19列、42,453字段值的完整数量/值摘要唯一存于[源侧期望草案](sqlite-value-canary.expected.draft.json)，执行范围在[批准范围](sqlite-value-canary.approved.json)，资源/人工检查/候选镜像/一次评审与证据保存故障修复统一见[三表证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-expectations/README.md)。其余75表独立值期望仍未生成，不回写前批78表结构准备文件中的空期待；未接数据库、冻结合同、解除BLOCKED或导入。下文“真实源期望仍空”等表述保留各前批时点，不能替代本段当前范围。

随后用户批准独立只读流式接口的小范围实施：新增sqlite_values.py，以人工SQLite文件验证，41定向/705开发全套通过；最终候选682通过/23仓库元数据跳过，运行镜像包含新模块。一次评审指出后置摘要取消/超时窗口，两项先失败检查复现后修正。实现/机器证据统一见[读取接口证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-values/README.md)。这只是下述主线的读取接入前提：真实源期望仍空，没有数据库访问、服务/别名晋级、冻结或导入；原值合同准备投影保留生成时点，不回写历史字段。

2026-10-10茶香要求“你就按我们前面的原则 继续你的工作，现在我也不知道情况了”。此前已说明78表/736列命名、184列禁止空值/552列允许空值提案；本轮将其记录为按既定设计及源显式声明继续处理本子批次的政策确认，不扩大为全版本冻结或导入授权。

- 表/列名称和空值政策已按既定规则登记；[确认记录](sqlite-target-mapping-decisions.draft.json)绑定原提案精确摘要，历史提案不覆盖。
- 78表/736列已经与现有无序逐值比较组件的列描述衔接；[值合同准备](sqlite-value-contract-preparation.draft.json)记录每表列描述与结构摘要。
- 32现有开发容器检查全部78个结构模型、名称重算、字段身份/顺序/类型/空值、列描述字节及header；三个已有输入与命名/身份/编码源码摘要核对一致。未重读真实源或数据库。
- 随后对落盘文件重新检查：78个结构摘要/header、736个原生类型接受检查、552个NULL接受及184个NULL拒绝检查全部通过；[机器检查记录](sqlite-value-contract-preparation.check.json)绑定落盘文件摘要。合成值只是接口消费检查，不是源业务值答案。
- `schema_hash` 仅证明列描述，不是业务值摘要。既有5,623,075行只作为观察引用；各表 `expected_count`、`expected_sha256` 仍留空，不能假充独立源期望或冻结合同。

当前主线仍是：补齐独立源值读取及完整流期望 → 数据库写入与独立核对 → 隔离演练 → 通知用户并确认旧库处置后正式导入。下一步集中独立源读取接入；B-16保守保留路线不在此扩展。没有完整值合同、真实适配器或各闸门证据时不解除BLOCKED。
本轮只有非执行元数据和文档变化，无产品代码/依赖/镜像构建、服务替换、源/数据库或Git写入；没有重跑全套测试，不复用历史测试数字作为本轮结论。

## 最新准备：目标名称与空值规则提案

2026-10-10用户令按原计划继续，复用32现有命名API及已有结构/类型元数据形成78表/736列的非执行提案。建议和验证边界统一见[目标映射审阅](sqlite-target-mapping-review.md)，逐项清单为[机器提案](sqlite-target-mapping-proposal.draft.json)。名称与空值规则仍待用户确认，不回写正式合同、不冻结或导入；下节保留前批实现时点。

## 最新阶段：合成无序比较组件已实现

2026-10-10用户“同意”批准四任务及当前会话实施/一次独立评审；完成纯合成无损编码、受限外部排序及完整行字节/重复次数比较。运行结果、评审修复、候选镜像与已知限制统一见[执行账](../../../../docs/superpowers/plans/2026-10-09-sqlite-unordered-value-progress.md)及其证据入口。
没有真实SQLite/PG适配器或本轮源/库访问，目标名称/空值约束/独立值合同未批准；正式合同和BLOCKED保持不变，未晋级、冻结或导入。下文是前批历史时点，不代表当前实现状态。

## 历史阶段：书面设计确认，执行计划待审

用户“继续”确认整行内容/重复次数书面设计后，形成[四任务待审执行计划](../../../../docs/superpowers/plans/2026-10-09-sqlite-unordered-value-comparison.md)。
先合成值编码检查，再受限排序，再实际行字节/次数比较，最后候选镜像验证；不实现真实SQLite/库读取器，不替换常驻dev或现行镜像别名。
本轮仅编写文档及只读环境核实，没有新增产品代码/测试执行/镜像构建，执行计划与实施方式仍待确认。下节为书面设计编写时点。

## 最新准备：整行内容与重复次数核对设计

用户确认对话方案后，已形成[待审书面设计](../../../../docs/superpowers/specs/2026-10-09-sqlite-unordered-value-comparison-design.md)。
统一无序比较全部字段及完整行重复次数，精确保留整数、有限二进制浮点、文本、NULL与空串；不依赖声明主键或虚构源行号。
首实现切片仅用人工合成数据验证编码、外部排序、实际字节/次数比较及失败回收；书面设计和实施计划尚未批准，没有产品实现、真实源重读或数据库访问。
该规格不批准目标名称/空值约束，不回写正式值合同，不解除BLOCKED或导入门；原类型确认范围保持不变。

## 最新确认：736字段保存类型及保留原值规则

用户在描述性说明后明确“同意”：全部78表/736列保存类型及整数/浮点/文本、NULL与空串的保留规则已确认。
[确认记录](sqlite-type-decisions.draft.json)绑定原结构、全量观察和36字段提案的精确摘要；[逐字段确认清单](sqlite-types-approved.draft.json)另存，不回写历史观察或提案。
394字段完整保存有符号64位整数、4字段保存原二进制64位浮点数、338字段保存不额外限制长度的文本。
其中700字段依据实际非NULL存储类，36字段仅依据源定义；清单如实区分，不将批准类型冒充实际非NULL证据。
不裁剪文本、不替换坏字符、不推日期、不填空值、不执行源默认表达式、不转换坐标，NULL和空文本保持不同。
本次仅保存类型/标量保留原则确认，不批准目标表名/列名、是否禁止空值等约束、独立逐值验证合同、冻结或导入。
目标nullable全部保持未定；原3空表主键字段的源端禁止空值声明仍留证，不自动执行建表约束。
新增4项确认消费检查先失败后通过，572单元通过；在dev运行全部580项得到575通过/5项环境目录检查失败（找不到/app/docker-compose.yml或/app/scripts/sync-dev.ps1），不能称全套通过。
该5项为此前已知的dev与候选测试镜像布局差异，本次没有修改代码/镜像/容器布局；详细测试名与命令另存本轮核验记录。未重建或晋级镜像，未访问真实源或数据库，未提交推送。
下一步仍需整理SQLite规范值读取/验证方案及目标名称与约束；不是可以导入的完整版本合同。

## 前批预算恢复：78表完整类型观察（以下批准位是历史时点）

用户已明确批准前批失败ASSOC_DATA及后续63表的协调预算调整；不重读11成功表，不覆盖原权限或统计。
新增sqlite-recovery-budget.approved.json及sqlite-recovery-read-scopes/64件，CLI按权限SHA绑定消费；默认ProfileLimits仍不变。
2026-10-09T11:40:16Z～11:48:03Z恢复64表/650列全部完整：5,345,479行、115,961,834cell、523,376,869累计值bytes。
与前批11表及原三表合并，覆盖78唯一表/736列，5,623,075行、119,366,224cell；已成功14表未重读，旧失败与权限记录不覆盖。
预算/测试/候选镜像和逐表证据统一见[执行账](../../../../docs/superpowers/plans/2026-10-09-sqlite-remaining-types-progress.md)及[机器汇总](../../../../docs/superpowers/evidence/2026-10-09-sqlite-remaining-types/sqlite-recovery-20261009-b1/summary.json)。
64件统计本地/远端SHA全等，全部完整列/行计数、源前后SHA和权限/预算摘要核对通过；非root、无网络、只读rootfs及5件精确数据/权限卷隔离通过。
568单元通过，候选557通过/19仓库产物跳过，runtime非root/默认预算/--help通过；全部64临时容器回收，源无sidecar，dev/pg32/pg32b及test/runtime别名未变。

全量API观察与未批准类型候选另存[736列审阅投影](sqlite-type-observations.draft.json)，不是正式合同：

| 非NULL观察 | 列数 | 待审口径 |
|---|---:|---|
| INTEGER | 375 | bigint，不推业务含义 |
| REAL | 4 | double precision，原binary64/坐标不转换 |
| TEXT | 321 | text，不设臆测长度上限、不裁剪或转日期 |
| 无非NULL值 | 36 | 14列位于3空表、22列全NULL，仍未决 |

REAL仅ADDR_CODES.x_coord/y_coord及SOCIAL_INSTITUTION_ADDR.inst_xcoord/inst_ycoord。
409列出现NULL，93文本列出现空串，必须分别保留；未发现混合非NULL存储类、BLOB、非法UTF-8、TEXT嵌入NUL或非有限REAL。
空表是SOCIAL_INSTITUTION_ALTNAME_DATA、ADMIN_CAT_CODE_TYPE_REL、ADMIN_CAT_TYPES；36未决列逐项列在投影，不按表名或其他表猜类型。
最大文本码点长度是BIOG_MAIN.c_notes的3,338；API UTF-8字节不等于原始页编码，不把源声明长度直接变成目标截断上限。
没有观察到NULL不能证明NOT NULL约束；本批不批准类型、nullable约束、值合同或目标映射，也不提供独立生产SQLite逐值验证。
沿用前批一次静态评审，不重复派发re-review；新增预算CLI由本执行者检查并TDD，未获第二次独立评审。
Deferred minor：单表权限未显式继承source_ddl_execution_approved=false；实际authorizer仍拒绝DDL，本批不顺手补改历史权限。
不连接数据库，不冻结或导入；任何导入前仍先通知用户并共同确认pg32b旧数据处置。

## 36个无实际类型证据字段：源定义核对及待审建议

用户要求改用描述性语言并继续工作。本轮只读取仓库已保存的源定义和统计，不重新读取实际数据、不连接数据库、不把继续工作视为类型方案批准。
逐项身份/原表名/原列名/序号匹配后，36列源声明中19列为整数类、17列为文本类；建议分别使用能完整保存整数的bigint和不额外限制长度的text。
详细原声明、字段身份、空表/全NULL原因、源端是否禁止空值及候选见[36字段待审方案](sqlite-unobserved-type-proposal.draft.json)。
这是依据源定义提出的候选，不声称这些列出现过非NULL值；前一观察投影中的36列未决状态保留，批准另行记录。
其中只有ADMIN_CAT_CODE_TYPE_REL的c_admin_cat_code/c_admin_cat_type_code、ADMIN_CAT_TYPES的c_admin_cat_type_code在源定义明确禁止空值，并属于主键；三列所在表当前都为空。
其余33列没有显式禁止空值；不因此补值、生成默认值或擅自添加目标约束，也不执行源默认表达式。
SQLite声明属于类型倾向，不保证以后新增值的实际类型；VARCHAR(255)等括号长度也不是SQLite执行的截断规则。依据[SQLite官方类型规则](https://www.sqlite.org/datatype3.html#determination_of_column_affinity)。
因此该建议仅绑定当前固定源版本，新版本必须重新核查；不因字段名含date/year便转日期，不把未知值换成0或空串。
类型/是否允许空值的目标约束/值合同/目标映射仍未批准，正式合同和数据库均未改变。

## 前批剩余75表调查：预算出口停止（历史）

用户已批准75表计划连续执行，权限另存sqlite-remaining-type-read-decisions.draft.json及sqlite-type-read-scopes/75件；
原规划scope保持PROPOSED_NOT_AUTHORIZED，不覆盖旧角色/三表权限。实际2026-10-09T11:18:02Z～11:19:07Z依序执行。
前11表/58列完整统计，247,438行、2,921,874cell；这些成功表未发现混合非NULL存储类，不能推断未读表。

| 已完整统计表 | 行数 |
|---|---:|
| ADDR_BELONGS_DATA | 37,177 |
| ADMIN_CAT_CODES | 213 |
| ADMIN_CAT_CODE_TYPE_REL | 0 |
| ADMIN_CAT_TYPES | 0 |
| ALTNAME_CODES | 21 |
| ALTNAME_DATA | 208,828 |
| APPOINTMENT_CODES | 116 |
| APPOINTMENT_CODE_TYPE_REL | 109 |
| APPOINTMENT_TYPES | 13 |
| ASSOC_CODES | 498 |
| ASSOC_CODE_TYPE_REL | 463 |

第12表ASSOC_DATA的42列调查触发vm_limit（近似VM预算2,000万），容器exit1，未生成部分成功profile。
后续63表未启动，当前剩余范围是1表失败+63表未读；加原三表，累计14/78表有完整类型统计，不是75表调查完成。
没有自动重试、拆列/截行、加预算或越过失败表。失败表完整行数/值域仍未知，其原始值不输出明细。

[机器汇总/逐表统计/12容器隔离及JUnit/失败日志](../../../../docs/superpowers/evidence/2026-10-09-sqlite-remaining-types/sqlite-remaining-20261009-b1/summary.json)；
[执行账](../../../../docs/superpowers/plans/2026-10-09-sqlite-remaining-types-progress.md)。558单元通过，候选547通过/19仓库产物跳过、runtime smoke通过。
成功11表源前后摘要一致；失败表未完成探针后验摘要，另外主机完整文件SHA后核验与批准身份一致。
逐表宿主stat、无sidecar与三个常驻容器基线保持一致，临时容器全部回收；不访问NAS/PG，不替换服务或晋级别名。
下一步需对剩余64表批准更高计算预算及显式预算消费；已成功11表不重读，不放宽原值/源件/数据库边界。
正式BLOCKED=7,914、类型/值/目标映射批准位及current.yaml仍不变。任何导入前仍先通知用户并确认pg32b旧数据处置。

以下三表及规划描述保留对应历史时点。

## 最新角色批准与三表类型观察

阶段提交8fbc8c9后，剩余75表/708列的[分批调查计划](../../../../docs/superpowers/plans/2026-10-09-sqlite-remaining-types.md)已整理供审阅，scope仍PROPOSED_NOT_AUTHORIZED；未新增源值读取，以下三表观察不变。

用户已批准78表作为逻辑表对象、76主键索引作为附属源结构元数据；
[角色决定](sqlite-role-decisions.draft.json)与[非执行批准投影](sqlite-roles-approved.draft.json)另存，原结构提案不覆盖。
仅角色批准，不批准源DDL执行、类型/值合同、目标映射或导入；正式BLOCKED=7,914不变。

2026-10-09T10:02:59Z～10:03:04Z，只读同一项目快照成员，完整检查指定三表28列：

| 表 | 列数 | 完整读取行数 |
|---|---:|---:|
| ADDR_CODES | 16 | 30,157 |
| SOCIAL_INSTITUTION_ALTNAME_CODES | 4 | 1 |
| SOCIAL_INSTITUTION_ALTNAME_DATA | 8 | 0 |

累计30,158行、482,516个cell。只输出storage class/NULL数量、数值极值和长度，
不输出TEXT/BLOB原值；各列未出现混合非NULL存储类、BLOB、非法UTF-8或嵌入NUL。
ADDR_CODES的x/y分别15,555个REAL与14,602个NULL；c_notes/c_alt_names有长度0的TEXT，
不能把空串当NULL。其c_notes最大113码点/331个API UTF-8字节，不等于声明长度255的验证。
SOCIAL_INSTITUTION_ALTNAME_CODES的c_notes仅NULL；SOCIAL_INSTITUTION_ALTNAME_DATA为空，均不足以建立实际值类型合同。
INTEGER原声明宽度不是值域保证；日期相关列本次是TEXT，不自动转换时间类型。
统计不是原始页存储语义、完整值摘要、有序值验证或主键唯一性证明。

- [三表完整统计](../../../../docs/superpowers/evidence/2026-10-09-sqlite-types/sqlite-types-observation.draft.json)，SHA-256：8298fbbc97c2272c6e79f0dd4aac3cd4930bc6c9fbe3991148d84c4311059635。
- [测试及隔离/身份核验](../../../../docs/superpowers/evidence/2026-10-09-sqlite-types/verification.json)，候选完整547通过/15仓库产物跳过，dev单元554通过；runtime smoke通过。
- [执行账及单次评审修正](../../../../docs/superpowers/plans/2026-10-09-sqlite-types-progress.md)。

前后源SHA及宿主stat一致，无sidecar；仅单源件/证书/角色权限只读卷，无源码挂载，
非root/无网络/只读rootfs/1CPU/768MiB/64PID，外层240秒超时。VM是保守近似回调预算，非精确指令计数。
未访问NAS或PostgreSQL，dev/pg32/pg32b身份及启动时刻未变；test/runtime别名未晋级。
下一步须另行批准其余75表的类型调查范围及预算，再提出类型和值合同，不能自动扩大读取。
任何实际导入前仍须先通知用户并共同确认pg32b旧数据处置。

以下保留先前结构批次时点，未查询业务行的描述仅适用于该历史批次。

## 本批来源与观察口径

只读项目快照 2026-10-07-bootstrap 的
harvard/cbdb/cbdb_20260919.sqlite3（m007906，586,485,760 bytes）。
前后 SHA-256 均为 bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400；
证书/manifest 身份和选定成员吻合，宿主机文件身份及无 sidecar 前后核对通过。
不访问 NAS，不读取其他快照成员；本轮不是全快照复验或数据库值验收。

结构观察时间 2026-10-09T09:06:15Z～09:06:19Z。分母是该件完整 sqlite_schema：

| 指标 | 结果与口径 |
|---|---|
| 表 | 78，全量目录包括内部名称，不按 sqlite_ 前缀过滤 |
| 字段 | 736，所有表 table_xinfo 返回项；无生成/隐藏字段 |
| 索引 | 76，均为 origin=pk 的主键自动索引，原目录 sql=NULL |
| 主键 | 76 张表有声明主键，其中 27 张复合主键；仅结构，不证明实际值唯一/非空 |
| 视图 / 触发器 | 0 / 0，完整目录枚举 |
| 外键 | 0 条 foreign_key_list 元数据；不推断业务关系 |
| 业务行 | 未查询、未计数、未验证值 |

观察到九种原声明：INTEGER(11)、smallint(6)、varchar(255)、TEXT、REAL、
varchar(191)、varchar(1)、tinyint(4)、varchar(128)。声明长度和类型名称不能证明
SQLite 实际存储值域、文本长度或 NULL 语义，故不自动映射到 PostgreSQL。

## 机器证据与提案

- [完整原结构证据](../../../../docs/superpowers/evidence/2026-10-09-sqlite-structure/sqlite-structure-observation.draft.json)
  SHA-256：f29f8e138192ccf05ccc53e6175ae246fb6da19f1a90184e72000d61e2291b40。
- [78 个逻辑对象非执行提案](sqlite-object-contract-proposal.draft.json)
  SHA-256：5a1d1308080a4d16459be74f2de71f89ad0c54e75dd61e6f7bdf6e36218487d8。
  逐表稳定对象身份、736 个原字段顺序/声明/默认值/主键位次及索引关系保留；
  76 个索引另有附属结构元数据候选，均未批准执行其 DDL。
- [实施、TDD、镜像与单次评审](../../../../docs/superpowers/plans/2026-10-09-sqlite-structure-progress.md)。

提案仅供下一轮审阅：源表候选是逻辑表对象，索引候选是源结构元数据。
cbdb schema 来自 DESIGN §6，不构成本批新增目标映射批准。目标表/列名与类型、
可空语义、值/数量/顺序合同、生产适配器及独立验证均待完成。
所有相关批准位为 false，m007906 及正式合同仍 BLOCKED；current.yaml 未建立。

## 运行与下一步

探针来自独立候选 test 镜像，未挂载源码；只给该 SQLite 文件和证书只读卷，
仅运行证据目录可写。非 root、无网络、1 CPU、768 MiB、64 PID、nice 19 / ionice 3；
180 秒宿主超时与容器回收，模块内 120 秒及目录/元数据/输出预算。
本件无视图/虚拟表；通用探针遇到它们仅留 DDL/pending，不执行它们查询字段。

下一轮先审阅对象角色及类型/值调查方案，不把本次结构观察当成导入批准。
任何实际导入（含样本/彩排/staging）之前，先通知用户并共同确认 pg32b 旧数据处置。

## 2026-10-12 本轮源侧期望出口

新55表草案见sqlite-value-small.expected.draft.json，来源/外部摘要索引见sqlite-value-small.expected-index.draft.json；与原3表无交集，共58/78表。全部成员与前后摘要通过，未查询剩余20表、未接PG/冻结/导入。完整验证语义不变的缓存实现修订见sqlite-read-cache-amendment.draft.json。旧轮记录按发生时点保留，不把本轮结果倒写成旧轮成功。
