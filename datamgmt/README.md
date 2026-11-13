# datamgmt —— 香如故数据接入模块

2026-11-13 正式请求读取器接入与人工候选验证完成。开发 1347 项通过，安装 1324 项通过及 23 项跳过，465,284 行人工整批用时 1338.41 秒。真实覆盖 68/78，Task8 尚未完成。见[本轮证据](../docs/superpowers/evidence/2026-11-13-request-reader-integration/README.md)。

2026-11-13 p01人工原型对照完成。与11月12日基线使用相同SQLite文件，逐次请求校验的原型在1655.93秒产出完整人工批，黄金及双文件摘要通过。前两段同样次数的检查合计节省约280秒。正式产品集成和真实可行性仍待验证，真实覆盖68/78，Task8未完。见[证据](../docs/superpowers/evidence/2026-11-13-p01-openat-probe/README.md)。

2026-11-12 p01人工吞吐定位完成。模拟465,284行和4整数4文本，在半核、768MiB及1800秒下于归并阶段超时。逐次请求重读和只读挂载检查占人工观测工作时间74.75%，计时开销未独立校准。真实覆盖68/78，Task8未完。见[证据与测量范围](../docs/superpowers/evidence/2026-11-12-p01-throughput/README.md)。

2026-11-09最终：新runtime获批的p01一次真实尝试1800.26秒timeout，无完整批/新增源期望，仍68/78、Task8未完。无心跳拒收、PG/交换健康；59原件、3候选回收及scratch空核验通过。读取器人工改善未使真实任务在原预算内完成，需先在人工数据上验证足量吞吐；不重试、不提高预算、不接PG。见[本轮终态](../docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)。

2026-11-09：已用新runtime为real-p01-20261109-c准备p01关闭任务卡，完整父10/235投影8列、安装6模块及缺授权拒绝门通过。没有真实快照挂载/读取，没有execution request/approval，仍68/78、Task8未完；原1800秒可能再次超时，读取须针对新卡另获具名授权。见[本次任务卡](../docs/superpowers/evidence/2026-11-09-p01-read-review/README.md)。

2026-11-08正式集成：read_metadata只缓存32条词法Path链、合并同次stat，逐次新鲜检查不变。开发1339通过、安装1316通过/23跳过；固定80k人工黄金/归并、取消和请求变化拒绝通过，单次整程493.14→404.63秒，小样本整程未改善。937原件核验、24候选/44临时路径收尾。真实仍68/78、Task8未完，真实1800秒可行性未证，不自动重试；见[证据与限制](../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。以下保留历史时点。

2026-11-08后续：人工等价严格分支确认重复元数据检查为小夹具剖析主要成本；保持逐次检查的词法路径读取原型，两组普通整程观察平均下降19.7%，19项诊断及六批黄金核验通过。仅实验进程覆盖一处函数，产品未集成、无新项目完整回归，真实仍68/78/Task8未完。下一步正式兼容性实现和较大人工验证；见[证据与限制](../docs/superpowers/evidence/2026-11-08-project-path-profile/README.md)。

2026-11-08最终：获批的p01唯一真实尝试触及1800秒监督截止，随后取消，未形成完整批或新期望；仍68/78、Task8未完。本次无心跳拒收，资源/PG健康、3候选回收及scratch空已核验。耗时分布待人工剖析（I-07），不自动重读、不提高预算；见[本次终态](../docs/superpowers/evidence/2026-11-08-real-p01-attempt/README.md)。

2026-11-08：新attempt real-p01-20261108-b的p01关闭审阅已用安装API校验完整10/235父链并投影8列；控制包及缺授权拒绝启动核验完成，未挂真实快照或读取源。仍68/78、Task8未完，本次真实读取待具名批准。见[任务卡](../docs/superpowers/evidence/2026-11-08-p01-retry-review/README.md)。

2026-11-07：B-21心跳超时边界已人工复现并最小修复，开发1325通过、安装候选1302通过/23跳过、自然边界100/100。仅人工验证；25日真实失败不能确认同因，真实仍68/78、Task8未完，新的真实尝试须另获具名授权。见[证据](../docs/superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md)。

2026-10-25后续真实p01一次尝试未成功：外层invalid_heartbeat取消，约1637.6秒、无完整批或新期望，仍68/78。控制帧根因待人工复现（B-21），资源与PG健康、确切容器已回收；本次不重试真实数据。见[失败停点](../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md)。

2026-10-25后续：首个真实单表POSTED_TO_ADDR_DATA/8列的关闭审阅已用b版安装API准备并复验，无缺项；只读已有仓库metadata，真实数据未读，覆盖68/78。首表任务卡及一次尝试授权边界见[关闭审阅](../docs/superpowers/evidence/2026-10-25-first-real-partition-review/README.md)。

2026-10-25：严格project_snapshot单表元数据链、控制端/底层独立门及23角色离线覆盖已实现并完成人工候选验证；唯一复核两项资源语义问题已修复。公开审阅件始终不可执行，真实执行仍需具名授权，真实覆盖68/78、Task8未完成。最新测试、独立镜像和资源限制见[本轮证据](../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md)。以下为各批历史记录。

2026-10-17真实单表设计经继续确认后形成实施计划，待计划审阅；四任务覆盖关闭审阅包、双层控制门、独立真实覆盖和人工协议候选。沿用主代理串行及末尾一次复核，未实施/读源/接PG，68/78与Task8保持。见docs/superpowers/plans/2026-10-17-real-partition-control.md。


2026-10-16真实large单表接线设计草案已形成，待审阅：完整父范围/严格单表身份、独立真实离线覆盖、逐次guard及原资源门保持。仅设计，未改产品代码、未实施/读源/接PG；确认后先写实施计划，68/78与Task8不变。见docs/superpowers/specs/2026-10-16-real-partition-control-design.draft.md。


2026-10-16人工阶段后就绪核对：10表235列及2713份历史证据摘要复验一致；历史规范流均低于256MiB，但真实时间/临时峰值未证明，十次逻辑摘要量约36.82GB。真实large执行与真实覆盖汇总仍关闭，下一阶段需审定实现范围和执行身份；未读源/主动跑项目测试/构建，68/78、Task8未变。见docs/superpowers/evidence/2026-10-16-large-readiness-review/README.md。


2026-10-16宽文本人工SQLite受控路径验证通过：4094行完整发布且独立摘要/完整快照/双哈希/发布pin吻合，4095行sort/budget拒绝且无完整批；4定向检查通过。产品输入未变，无新完整回归。仅人工单对象，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-sqlite-artificial/README.md。


2026-10-16宽流人工边界通过：64KiB文本含重复，4094行完整匹配独立摘要，4095行budget拒绝且输出0行；临时峰值511.9MiB、容器内存峰值567.5MiB，清理完成。4定向检查通过，123产品输入未变、复用候选，无新完整回归。仅排序组件，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-stream-artificial/README.md。


2026-10-16人工夹具测试目录适配完成：默认目录1通过2跳过，受限目录3通过；完整开发1181通过，新test安装版1158通过23跳过。仅改一项测试输入，生成器/输出根门/服务不变；devwatch剩余87失败未修。真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-fixture-test-scope/README.md。


2026-10-15人工单表闭环已验证：10表235列/1万行23.5万字段十个手工摘要吻合，取消/新attempt重试及离线九项缺覆盖、十项完成、重复/冲突拒绝通过。47核验/2夹具、1180开发、新test1157通过23跳过；3重要复核修复、123输入/919原件/28容器清理。真实仍68/78，large关闭、Task8未完。见docs/superpowers/evidence/2026-10-15-partition-coverage/README.md。


2026-10-15单表草案准备已实现：完整large父范围10/235先校验，再投影一表；六文档摘要链及发布前输入/生成/stage复核，权限关闭。64定向、1131开发、新test1108通过23跳过，新runtime纯人工CLI核对通过；119输入/两独立镜像/138原件、7容器清理。真实large关闭、人工执行与覆盖汇总未实现，68/78、Task8未完。证据：docs/superpowers/evidence/2026-10-15-partition-preparation/README.md。


2026-10-14单表拆批设计：确认large完整10/235约束位于准备器，底层允许子集但真实large仍在读源前拒绝。新增完整父范围/十个单表子范围/独立覆盖核验草案，9项输入绑定及10/235元数据核对通过；F-14待审未实现，无新项目测试/构建/源读/PG，68/78与Task8不变。见docs/superpowers/evidence/2026-10-14-partition-design/README.md。


2026-10-14扩大人工调度验证：10表235列/20万行470万字段，十个手工摘要、两次源摘要及完整快照通过；相同源字节810.90→114.32秒，峰值73.2MiB/临时23.1MiB，交换0。117产品输入不变，复用候选，无新完整回归/构建。保留首次devwatch重叠准备，干净重跑；3容器/2人工fixture清理。真实仍逐次校验、68/78，Task8未完。证据：docs/superpowers/evidence/2026-10-14-guard-scale/README.md。


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


2026-10-11茶香已明确批准固定快照一次全成员复核与55小表326列源期望生成；控制/监督/发布接线现已实现外部源模式与request摘要门，26项失败转最终93相关/936开发通过，一次新成果复核0问题。test候选构建持续换出775/828/1140触发取消，未产出新镜像、未开始runtime构建或读取真实源。授权保留，因资源风险停止后续负载，不称候选/真实就绪或Task8完成。见[本轮接线与构建停点](../docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md)。以下记录保留原发生时点。


2026-10-11停点后茶香明确要求继续，按原限制恢复一次人工候选：test完整回归885通过/23跳过，runtime已实际生成选定元数据的55表326列全DRAFT草案；50次宿主诊断采样换出均723，原停止阈值不变、两个容器回收。上轮换出原因仍未知，不宣称资源问题修复、Task8或真实执行完成，真实读取与PG关闭。见[本轮恢复证据](../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md)。以下停点记录保留其发生时的结论。


2026-10-11实现仅仓库元数据的任务准备器：31项人工检查/908开发通过；一次新增复核的完成marker持久化缺陷已失败复现并修正。独立候选完整回归因宿主242/618/723连续换出以swap_pressure停止，未重试，runtime仓库55表模板生成未运行。见[本轮停点证据](../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation/README.md)。准备件全DRAFT、授权false，真实75表/数据库/Task8不变。

2026-10-11仅补齐[55表准备材料的当前绑定与下一步方案](../docs/superpowers/evidence/2026-10-11-sqlite-small-readiness/README.md)：21项当前摘要、四项代码预期变化、原55表/326列范围及候选参考已核对；原证据保留，不计新测试。拟增加只读仓库元数据的任务准备器，方案待确认，真实入口仍关闭。

2026-10-10整程截止已在人工链路接通并验证：14项先失败、85项相关通过、877项开发回归通过，独立候选854通过/23跳过；受控候选/宿主/SSH为1800/1830/1880秒，短超时实际停止。证据见[本轮截止验证](../docs/superpowers/evidence/2026-10-10-sqlite-lifecycle-deadline/README.md)。下述各轮保留历史时点；真实75表、数据库、Task8及B-16/B-17仍未完成。

2026-10-10继续整理仅元数据的真实小组待审准备：精确55表/326列及逐表预算、来源摘要均已核对，历史统计不生成源期望。人工300秒外层与草案1800秒源批计时的范围差异已列明，整个生命周期截止及真实包装接线待确认，仍只允许人工实现验证。见[小组审阅](contracts/releases/2026-10-06-bootstrap/sqlite-value-small-execution-review.md)；本轮不改代码、不运行新候选/项目测试、不读真实源或数据库。

2026-10-10用户在资源停止后明确要求继续；只读观察换出稳定后，按原阈值恢复一次人工验证。新候选完整回归840通过/23跳过；新控制器人工只读成功及三个错误摘要/错误镜像revision创建前拒绝已实际验证。宿主另有单区间7页换出，来源未确认，不宣称风险修复。当前证据见[人工控制层恢复验证](../docs/superpowers/evidence/2026-10-10-sqlite-task-control-resume/README.md)；下面上一轮停点与开发结果保留历史时点，真实75表、数据库和Task8仍未完成。

2026-10-10继续接通仅人工任务控制层：外部请求/批准/roots摘要与实际镜像身份核对，移除入口业务根硬编码；14新检查、863开发回归通过。独立候选完整回归因宿主62/66/69页连续换出以swap_pressure停止，未重试；后续runtime控制层实际验证尚未运行。证据见[任务控制与资源停点](../docs/superpowers/evidence/2026-10-10-sqlite-task-control/README.md)。真实75表、数据库及Task8仍未完成。

> 状态：Task 1–5 已实现；Task 6 合同准备中，SQLite78表/736列类型与子批次命名/空值政策已登记，独立源值期望已覆盖58/78表，剩余20表，导入门仍阻断｜as_of 2026-10-12

本模块长期负责首次建库、数据换版、新增来源、独立验证、彩排、发布和回滚。它是香如故长期运行自有容器中的低频模块，不是独立常驻导入服务。唯一权威源是 `usedata`，运行输入为复制并独立校验后的项目快照，目标是外部 `pg32b/xiangrugu`。

2026-10-10继续获仅人工文件验证的正式只读入口准备授权，新增readonly_batch.py，校验完整请求的批准摘要、关联文档、逐表预算和快照/元数据只读挂载；小组上限55表及64MiB排序空间，拒绝中/大组。实际人工候选及一次新增成果复核处置见[只读入口证据](../docs/superpowers/evidence/2026-10-10-sqlite-readonly-entry/README.md)。project_snapshot仅API分支，尚无可信真实任务控制器/正式发布接线；真实75表未读，Task8和真实执行就绪仍未完成。

2026-10-10本轮继续接通人工批级执行、宿主采样及容器租约监督，完成后必须取得新宿主采样才发布最终人工结果；实际候选限制及取消证据统一见[人工执行与监控证据](../docs/superpowers/evidence/2026-10-10-sqlite-batch-runner/README.md)。入口自行生成固定人工数据，拒绝真实读取授权；剩余75表期望未生成，Task8整体、真实范围/只读卷/大表临时区消费未完成。常驻watcher默认/tmp与排序器/data/var约束冲突另记B-17，手工全套通过不等于watcher恢复。

随后获三表源侧期望衔接/真实只读核对授权，已完成全快照摘要复核及3/78表完整源值期望（3,860行/42,453字段值），18定向/723开发通过，候选700通过/23仓库元数据跳过。唯一结果、一次评审保存失败修复和资源/镜像/运行证据见[三表期望证据](../docs/superpowers/evidence/2026-10-10-sqlite-expectations/README.md)。未接数据库、冻结合同或导入，剩余75表源值期望未生成；下文缺口和测试数字保留历史时点。

用户要求按既定原则继续处理技术细节；当前SQLite命名/空值政策确认、736列逐值描述核验及尚缺的独立源值期望统一见[SQLite当前进度](contracts/releases/2026-10-06-bootstrap/sqlite-review.md)。下文各批次的“待审”、调查范围和测试数字保留历史时点，不作为当前未批准或新验收声明。

随后批准并实现SQLite独立流式原生值读取接口，人工文件41项及开发完整705项通过，候选与一次评审修复见[读取接口证据](../docs/superpowers/evidence/2026-10-10-sqlite-values/README.md)。没有真实源重读、源侧值期望生成或数据库接入，不是Task10完整适配器；镜像别名与服务不变。

2026-10-10已实现整行内容/重复次数无序标量比较的纯合成组件，含无损编码、受限外部排序、独立输入实际字节比较与失败报告；最终候选和一次评审证据统一见[执行账](../docs/superpowers/plans/2026-10-09-sqlite-unordered-value-progress.md)。未提供真实SQLite/PG适配器、未替换常驻服务，不等于完整Task9或导入验收，BLOCKED不变。

随后授权修复配置检查路径：开发时读/workspace所属项目，候选时读/app所属项目；镜像代码检查仍固定/app，前批5项路径失败已消除。B-16回收补丁因并发替换误删风险被否决并撤掉，仍待重新设计；最新验证及边界统一见[修复证据](../docs/superpowers/evidence/2026-10-10-cleanup-layout/README.md)，下文各批次数量保留历史时点。

## 必读入口

| 文档 | 职责 |
|---|---|
| `docs/DESIGN.md` | 唯一权威设计：模块边界、合同、保真、验证、版本与发布 |
| `docs/IMPLEMENTATION-PLAN.md` | 已批准规格对应的可执行开发计划；实际写入、构建、部署和提交仍逐项授权 |
| `docs/OPERATIONS.md` | 首次构建、后续更新、失败处理和计划 CLI |
| `docs/PITFALLS.md` | P-01～P-25 强制拦截规则 |
| `config/roots.yaml` | 当前源根、目标实例和安全边界 |

## 当前已有资产

| 路径 | 现状 |
|---|---|
| `config/g4_assertions.yaml` | 旧目标命名下的哨兵原型，阶段 0 必须迁入 release 合同并重建 SQL |
| `truth/` | SQLite、DBF/Shapefile、MapInfo、文本、XLS 等部分源读取能力 |
| `importer/load.py` | 部分载体的 staging 装载原型 |
| `verifier/` | 完整性及部分验证原型 |
| `maintenance/` | 盘点、编码调查和旧配置生成脚本 |
| `recon/` | 首版盘点证据与草案，迁入首个 release 后退役 |
| `contracts/releases/2026-10-06-bootstrap/` | 已验收快照的清点证据和候选合同；最新 metadata 审阅草案 BLOCKED=7,914，历史证据不覆盖，仍禁止导入；入口 review.md、逐组工作表 member-review.md；旧 recon 尚未退役 |
| `tests/` | Task 1–5 包、开发环境、快照、身份、清点和合同合成测试已建立；数据库导入相关测试待后续任务 |
| `src/xiangrugu_datamgmt/config.py` | roots 配置解析、环境覆盖、口令脱敏，不建立数据库连接 |
| `src/xiangrugu_datamgmt/snapshots.py`、`snapshot_transfer.py` | 路径及流式复制、独立摘要校验和完成证书；首个真实快照已验收，结果见 OPERATIONS |
| `src/xiangrugu_datamgmt/model.py` | 成员、处置、运行、产物和验证结果的不可变记录 |
| `src/xiangrugu_datamgmt/identity.py` | 版本化规范输入的稳定 SHA-256 身份；固定黄金向量在 tests/fixtures |
| `src/xiangrugu_datamgmt/naming.py` | 确定性目标名称分配、原名映射及标识符引用；不执行 SQL |
| `src/xiangrugu_datamgmt/inventory.py` | 只读清点、不可变清单及摘要、校验账原始摘要与严格异常证据 |
| `src/xiangrugu_datamgmt/signatures.py`、`archive.py` | 字节签名、ZIP 中央目录预检查及资源限制；不用扩展名推断嵌套归档 |
| `src/xiangrugu_datamgmt/contracts.py`、`config/contract.schema.json` | 不可变版本合同、严格 JSON/YAML 装载、列级编码及逻辑对象断言；Schema 进入自有镜像 |
| `src/xiangrugu_datamgmt/project_partition.py` | project_snapshot单表的关闭权限审阅、严格完整父链/分区投影、白名单请求组装和原始元数据重核；唯一公开CLI只生成不可执行审阅件，生产读取仍须另行具名授权 |
| `src/xiangrugu_datamgmt/project_partition_coverage.py` | 只读明确选定23角色收据，校验实际限额/峰值、控制pin、末端采样及回收，生成10表235列覆盖草案；不读取SQLite，不连接数据库，不赋予读取或导入权限 |
| `src/xiangrugu_datamgmt/disposition.py` | 精确成员规则、全量处置账、失效断言/目标碰撞/镜像主成员校验及覆盖门 |
| `src/xiangrugu_datamgmt/checksum_candidates.py` | 两类校验账候选的只读预览；精确摘要、NUL 尾部及显式路径绑定，不启用运行例外；真实结果见 release/review.md |
| `src/xiangrugu_datamgmt/source_text.py` | 受限 UTF-8/LF TSV 独立字节读取，不复用 csv/importer；显式 BOM/转义、保留空串与顺序，坏语法/宽度/预算拒绝；三件逐字段源复核见 release/text-review.md，不是数据库验收 |
| `src/xiangrugu_datamgmt/crs_diagnostic.py` | 通用离线WKT诊断：原bytes、轴序、全部authority候选/置信度和预算；锁定pyproj/PROJ目录，不自动赋SRID或转换，不是生产空间读取器 |

## 已确认的实现缺口

2026-10-09用户随后确认78表/736列保存类型及原值保留原则，确认记录/逐字段清单另存；394整数/4浮点/338文本，其中36列仅源定义依据。
新4检查通过、572单元通过；dev完整580项中575通过/5项既有镜像目录检查失败，不冒称全套通过。目标名称/空值约束/独立值合同仍未批准，完整事实见release/sqlite-review.md最新节。以下保留前批观察/待审时点。

2026-10-09用户随后批准剩余64表预算调整及CLI绑定消费；64表全部完成，与已有14表合并覆盖78表/736列，5,623,075行；类型/值/目标映射仍未批。
预算TDD/568单元与候选557通过/19跳过、runtime smoke通过；700列有非NULL类型证据，36列未决，最新观察/待审投影统一见release/sqlite-review.md。
不连接PG、不换服务、不冻结或导入。下段保留前批停止时点。
随后继续核对36未决字段的已存源定义：19整数声明/17文本声明，三列源端显式禁止空值；逐项建议另存，未批准，不冒称观察到实际非空值。详情仍在sqlite-review.md。

2026-10-09剩余75表调查获整批批准并连续执行：前11表完整，第12表ASSOC_DATA触发近似VM预算，后续63表未启动；
累计14/78表有完整类型统计，Task6/Task10仍未完成。最新证据/失败边界及预算恢复条件统一见release/sqlite-review.md首节。
本批558单元、候选547通过/19仓库产物跳过、runtime smoke通过；现有服务不变，无PG/NAS/冻结/导入/Git提交推送。
以下待审计划和三表段保留历史时点，不作为当前调查完成声明。

2026-10-09阶段存档后整理剩余75表/708列的待审调查方案与精确范围清单，见
../docs/superpowers/plans/2026-10-09-sqlite-remaining-types.md；本轮只读已有结构元数据，不读取新源值或数据库，尚未批准执行。

2026-10-09用户授权将10月6日后累计开发成果阶段提交至Gitea；
此次仅存档代码、锁、测试、合同草案与证据，不冻结合同，不晋级镜像或替换服务，不导入。
历史证据中的旧Git提交/dirty状态和各批次“未提交”保留原时点；阶段提交本身不回写历史镜像标签。

2026-10-09随后批准CBDB SQLite的78表/76索引对象角色，并完成三表28列只读类型统计。
新增sqlite_profile.py及镜像内inspect-sqlite-types.py；dev单元554通过，最终候选547通过/15仓库产物跳过、runtime smoke通过。
最新统计、空表限制、批准范围与机器证据统一见release/sqlite-review.md最新节；类型/值/目标映射仍待审。
不读其余75表，不访问NAS/PG，不替换dev或晋级别名，不冻结/导入/提交；以下结构段保留历史时点。

2026-10-09 CBDB SQLite 单件结构切片完成：78 表、736 字段、76 主键自动索引；
新增 sqlite_diagnostic.py 与镜像内开发证据探针，31 项合成测试通过，
候选完整 515 通过/12 仓库产物测试跳过，dev 单元 519 通过。
结构证据及78逻辑对象非执行提案统一见 release/sqlite-review.md；
不查询业务行、不读 NAS/连接 PostgreSQL、不替换 dev、不冻结或导入。
Task6仍未完成，Task10载体适配器/值验证尚未实现，正式BLOCKED不变。

2026-10-09随后用户批准上述五件规范值口径和源侧完整流期望，决定与非执行批准投影另存；表名、完整版本值合同及冻结/导入仍未放行。当前事实统一见release/text-review.md最新批准节，元数据定向12/累计单元488通过；下面保留提案准备时点说明。

2026-10-09新增五件文本非执行规范值合同提案及元数据消费测试，绑定既有源证据/批准列与schema；当前待审范围统一见release/text-review.md最新节。原投影及正式合同不变，没有新源/数据库读取，不批准表名、不冻结或导入。测试在32既有dev执行，不涉及产品源码、依赖或镜像变化。

独立JSON Schema校验已加入：原始文档先经锁定jsonschema验证，再走既有模型语义门；
最终候选484项通过，实施与原始合同核验见JSON Schema执行账。
2026-10-08随后获单独授权仅dev晋级，旧镜像导出留存且可运行后重建；
真实watcher476项及pip check通过，B-15恢复。完整事实和自动重测证据统一见JSON Schema执行账。
test/runtime别名未晋级，导入/数据库/冻结边界不变。

下列各段保留各历史批次的测试/部署时点；当前dev状态以本节首段及执行账dev晋级节为准。

五件文本已有源侧规范值期望，不含数据库验证；新增text_values.py负责批准读取/列映射到规范流的受限纯衔接，scripts/prepare-text-source-values.py负责镜像内开发证据探针。当前状态和新证据统一见release/text-review.md最新节，原批准投影及正式合同未改。

纯合成text/bigint/显式NULL有序值比较切片已实现：canonical.py固定无损字节/结构/行流编码，validate.py独立输入逐cell比较及有界脱敏报告；完整候选393项及runtime smoke通过。运行证据、评审修复及镜像身份统一见[执行账](../docs/superpowers/plans/2026-10-08-text-value-progress.md)。不提供真实源/数据库适配器，不等于Task6或完整Task9完成；现有常驻容器未换镜像，正式BLOCKED不变。

2026-10-08两组空间对象组件、chgis、属性/物理行号、二维Point及SRID4326已逐案批准；原X/Y不交换/转换，PRJ/QPJ轴序差异保留，批准投影是非执行sidecar。离线CRS镜像及救急回退已验证，仅dev已更新，完整292及真实watcher284测试通过，B-14部署阻断解除。详情统一见release/spatial-review.md；表名、生产读取器、全版本命名及规范值合同未完成，正式BLOCKED不变。

两组 canary 的两件DBF五个N字段读取/类型已批准并精确源复核，59点原坐标观察及未决对象/空间合同见 release/spatial-review.md；不把诊断路径当生产独立读取器。

1884route 两件DBF字符编码已批准，固定宽度源字节/字符串复核通过；C尾空间保留、N读取和两组组件绑定另有逐案批准。黄金夹具及独立生产读取器、目标映射、几何/CRS合同尚未完成，不是载体适配器或数据库验收。

五件文本读取、83列名称/text/非空、五个派生行号映射及schema归属已批准，决定与非执行投影核验统一见 release/text-review.md 最新节。表名、全版本命名和值合同未完成，不改变 BLOCKED；以下三件提案段为前批历史。

空间关系候选及后续未决归档、4 件 TAB/CPG 字节观察见 `contracts/releases/2026-10-06-bootstrap/spatial-review.md`。Native 声明不等于属性值编码或几何验证；两件外层TAB已按精确文本规则独立批准，不扩展到其他TAB。全量组件绑定、编码及空间合同仍未完成，不自动合并大小写不同或跨容器同名成员。

三件首批制表文本的读取语义已获用户确认，独立源复核通过；三件/70 列的逻辑对象及类型/目标映射提案已登记，入口为 `contracts/releases/2026-10-06-bootstrap/text-review.md`。源复核不等于目标库验收；全版本命名、规范值合同、类型/映射批准和冻结均未完成，处置仍未放行。

- Python 包、最小 `--help` 入口与合同校验/处置模型已建立；完整 CLI、可通过门槛的真实首版合同和运行状态机尚未建立；
- 首版 `sources.yaml`、`decoding.yaml` 仅为阻断候选，未确认逻辑对象、列级编码和独立值期望；
- MDB、SQL dump、XLSX/CSV/ODS、栅格和多层容器尚未全部打通；
- ZIP 成员清点已实现；PRJ、ZIP 成员独立验证器和栅格头独立读取能力仍缺失；
- 发布没有实现影子 schema 和单事务切换；
- `db.py`、`rehearse.py`、`verify.py`、`load.py` 仍默认旧 `cbdb_reh`；
- `build_sources_yaml.py` 仍写死旧 `database=cbdb` 与 `public` schema；
- 部分源读取器写死源路径，XLS 依赖 `/tmp/xlsdeps`；
- Task 1 单元测试已建立；数据接入集成、故障注入、重入和全库回归测试尚未建立。

因此当前仍处于阶段 0：现有盘点只是草案，尚未形成获批的首个 release 合同。不得直接开始全量导入。

## 操作边界

香如故代码、锁定依赖和数据接入工具进入自有镜像；生产环境不挂载源码，配置、密钥与 `/opt/mydocker/xiangrugu/data` 持久目录留在镜像外。`usedata` 经来源核实后复制到 `data/imports/usedata/<snapshot_id>`，校验通过才供项目只读使用，不再建立源临时挂载。创建目录骨架、改代码、构建或替换镜像、读取/复制源、安装依赖、建库、写库、彩排、发布、回滚或删除旧对象，都必须按项目纪律逐阶段获得用户授权。

项目开发代码在 Windows Git 工作区修改并同步到 32 主机 `/opt/mydocker/xiangrugu/deploy` 执行；Windows 不运行项目代码。`xiangrugu-dev` 是整个项目的常驻开发容器，`datamgmt` 作为首个模块由它监视和测试。远端 `deploy` 不是第二个编辑源，禁止直接修改后不回传 Git。
