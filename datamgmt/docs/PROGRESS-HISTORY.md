# 既往进度摘录

本文件保存本次整理前散落于入口文档的历史记录，原有完成、失败、授权和下一步表述均属于记录当时。当前阶段及待办以 [IMPORT-PACKAGE-TODO.md](IMPORT-PACKAGE-TODO.md) 为准；本次迁移未重新运行历史测试，也不重新授予权限。各节保留来源及条目顺序，Markdown 链接已按归档位置换算。


部分历史引用文件仅存在于 Windows 未提交工作树，尚未进入本次 Gitea 文档分支；这些引用以“历史路径”保留，不制作失效链接。本次没有上传历史证据文件，也没有把历史执行结果重新验收。

## 来源 docs/index.md

# index.md —— 文档索引

2026-11-13 正式请求读取器已接入。安装候选在 1338.41 秒完成 465,284 行同源人工整批，黄金与双摘要一致，回退 0 次。真实覆盖 68/78。见[本轮证据](../../docs/superpowers/evidence/2026-11-13-request-reader-integration/README.md)及[交接入口](../../HANDOFF.md)。

2026-11-13 p01人工对照。逐次读取原型使用同一465,284行SQLite，在原1800秒预算下1655.93秒完成，黄金及双文件摘要核验通过。前两段的检查次数与基线相同，合计节省约280秒。原型限人工候选，真实覆盖68/78。见人工证据（历史路径 `../../docs/superpowers/evidence/2026-11-13-p01-openat-probe/README.md`）。

2026-11-12 p01人工吞吐定位。465,284行、4整数4文本在半核、768MiB及1800秒下于归并阶段超时。逐次请求重读与只读挂载检查合计1343.33秒，占观测工作时间74.75%。75份原件核验，两个候选回收，真实覆盖68/78，Task8未完。见人工诊断（历史路径 `../../docs/superpowers/evidence/2026-11-12-p01-throughput/README.md`）。

2026-11-09最终：新runtime的p01唯一真实attempt c约1800.26秒timeout，worker随后cancelled/object_read_sort，无完整批/新增期望，仍68/78、Task8未完。峰值约124.5MiB、swap/pswpout0、PG健康，无心跳拒收；59原件核验、3候选回收、scratch空。授权已用，不重试/下一表；后续先人工验证足量吞吐。见[本次终态](../../docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)。

2026-11-09获批执行：茶香针对新任务卡确认后，唯一真实只读attempt real-p01-20261109-c已启动，原半核/768MiB/1800秒及停止门保持。首次metadata安装收据路径错误B-23已保留失败并修正独立metadata-2；无额外真实读取。终态前仍68/78、Task8未完，不重试/下一表/接PG。见执行进度（历史路径 `../../docs/superpowers/evidence/2026-11-09-real-p01-attempt/progress.md`）。

2026-11-09：新runtime的p01一次真实只读任务卡real-p01-20261109-c已准备；安装API关闭审阅/完整父10表235列及投影8列、6安装模块、资源/28原件/确切回收核验通过，缺授权退出2且无候选/request。未挂快照/读源，仍68/78、Task8未完，等待针对新卡具名授权。见[任务卡与边界](../../docs/superpowers/evidence/2026-11-09-p01-read-review/README.md)。

2026-11-08正式集成收尾：保持逐次检查的读取器已集成，开发1339通过、安装1316通过/23跳过，人工严格分支黄金/取消/请求变化拒绝均通过；同源80k单次整程493.14→404.63秒，小样本未改善，不证明真实1800秒可行。937原件核验、24候选回收、44人工临时路径清理；真实仍68/78、Task8未完。见[本轮证据](../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。此前暂停停点已续接完成。

2026-11-08暂停：用户要求休息、明天继续。正式读取器已集成，开发1339通过、安装1316通过/23跳过；人工80k新旧对照均结束，24候选逐ID确认不存在，PG基线健康。总证据核验、文档和人工临时清理尚待完成，真实仍68/78、Task8未完。明天先读暂停续接（历史路径 `../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/PAUSED-20261108.md`），不重做已完测试或复核，不自动重试真实读取。

2026-11-08后续：严格项目路径的人工剖析完成，1000行/8列普通与原型六批均匹配黄金；原版剖析guard累计约占CLI82.75%（非真实占比）。只复用词法组件、保持逐次检查的实验原型，两组普通整程均值10.16→8.16秒，观察下降19.7%，尚未产品集成或证明真实吞吐。诊断19项通过、唯一入口复核问题修正，334原件/13候选/16临时路径收尾；真实仍68/78。见本轮证据（历史路径 `../../docs/superpowers/evidence/2026-11-08-project-path-profile/README.md`）。

2026-11-08：p01本次唯一真实尝试约1800.18秒由监督timeout停止，worker随后cancelled/object_read_sort；无完整批/新增期望，仍68/78。本次无invalid_heartbeat，峰值约120.2MiB、交换及宿主换出0、PG健康；3候选回收、scratch为空，60原件摘要核验。授权已用，不重试或下一表；后续先用人工夹具测量校验/排序耗时（I-07）。见最终失败证据（历史路径 `../../docs/superpowers/evidence/2026-11-08-real-p01-attempt/README.md`）。

2026-11-08：用户针对新任务卡明确确认后，p01唯一真实尝试已启动；控制端固定request=a50b80f8…5f946c及approval/roots原始pin。metadata首次因专用空目录属主失败，修正10001并保留原件后metadata-2成功，未额外读取源。原半核/768MiB/禁交换及1800秒保持，终态前仍68/78，不重试或下一表。见本次运行（历史路径 `../../docs/superpowers/evidence/2026-11-08-real-p01-attempt/progress.md`）。

2026-11-08：p01新attempt real-p01-20261108-b的关闭任务卡、固定控制包及元数据候选核验已完成，缺授权时拒绝启动已验证；尚未读取真实源，仍68/78。范围为POSTED_TO_ADDR_DATA/8列及全快照摘要，原资源门不变，只一次且失败停止，等待具名确认。见本次任务卡与证据（历史路径 `../../docs/superpowers/evidence/2026-11-08-p01-retry-review/README.md`）。

2026-11-07：B-21人工复现确认完整tick换行在Bash读取超时边界可能被误拼入下一帧；最小修复经RED→GREEN、开发1325通过、安装候选1302通过/23跳过、自然边界100/100验证，候选及人工临时文件已清理。25日真实失败仍缺帧级证据，不能确认同因；真实仍68/78、Task8未完，未重试或接PG。见本轮证据（历史路径 `../../docs/superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md`）。以下保留历史停点。

2026-10-25首表真实尝试已停止：约1637.6秒时宿主invalid_heartbeat触发取消，worker停于object_read_sort，无完整批/新增期望，仍68/78。内存峰值约120.3MiB、无swap/OOM，PG基线健康、容器回收；B-21待人工心跳复现，未确认错误帧成因。见失败证据（历史路径 `../../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md`），本次授权不自动重试或下一表。

2026-10-25已获首表一次真实尝试授权，POSTED_TO_ADDR_DATA/8列及全快照摘要复核已启动；外部原始请求固定为4becb3ce…fff24f35，仍按1800秒/0.5CPU/768MiB运行，不重试或下一表。终态未判前覆盖保持68/78；见本次尝试（历史路径 `../../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md`）。数据库、冻结和导入未授权。

2026-10-25首个真实单表任务的关闭权限材料已准备：POSTED_TO_ADDR_DATA/8列，b镜像纯元数据校验完整父10/235后投影成功，审阅无缺项；未挂真实快照/NAS、未读源/接PG，仍68/78。下一步等待针对一次尝试及全快照摘要复核的具名授权，详见任务卡（历史路径 `../../docs/superpowers/evidence/2026-10-25-first-real-partition-review/README.md`）。

2026-10-25真实单表协议及人工候选验证：完整父链/双层门/23角色离线核验已实现，唯一复核两项Important经RED→GREEN修复；开发1314通过，新test安装版1291通过/23跳过，runtime离线四场景通过。真实覆盖仍68/78、Task8未完，真实读取及PG另行授权。实现、限制和收尾证据统一见本轮记录（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md`）。以下日期条目保留历史时点。

2026-10-25用户要求暂停、明天续接：真实单表协议已完成人工候选验证；唯一复核两项资源语义问题已修复，26新定向及289元数据检查通过，修复后完整回归途中取消。b镜像/安装回归/修复后离线集成及最终清理待做，真实仍68/78、Task8未完。见暂停交接（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/PAUSED-20261025.md`）。

2026-10-17真实单表设计经继续确认后形成实施计划，待计划审阅；四任务覆盖关闭审阅包、双层控制门、独立真实覆盖和人工协议候选。沿用主代理串行及末尾一次复核，未实施/读源/接PG，68/78与Task8保持。见docs/superpowers/plans/2026-10-17-real-partition-control.md。


2026-10-16真实large单表接线设计草案已形成，待审阅：完整父范围/严格单表身份、独立真实离线覆盖、逐次guard及原资源门保持。仅设计，未改产品代码、未实施/读源/接PG；确认后先写实施计划，68/78与Task8不变。见docs/superpowers/specs/2026-10-16-real-partition-control-design.draft.md。


2026-10-16人工阶段后就绪核对：10表235列及2713份历史证据摘要复验一致；历史规范流均低于256MiB，但真实时间/临时峰值未证明，十次逻辑摘要量约36.82GB。真实large执行与真实覆盖汇总仍关闭，下一阶段需审定实现范围和执行身份；未读源/主动跑项目测试/构建，68/78、Task8未变。见docs/superpowers/evidence/2026-10-16-large-readiness-review/README.md。


2026-10-16宽文本人工SQLite受控路径验证通过：4094行完整发布且独立摘要/完整快照/双哈希/发布pin吻合，4095行sort/budget拒绝且无完整批；4定向检查通过。产品输入未变，无新完整回归。仅人工单对象，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-sqlite-artificial/README.md。


2026-10-16宽流人工边界通过：64KiB文本含重复，4094行完整匹配独立摘要，4095行budget拒绝且输出0行；临时峰值511.9MiB、容器内存峰值567.5MiB，清理完成。4定向检查通过，123产品输入未变、复用候选，无新完整回归。仅排序组件，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-stream-artificial/README.md。


2026-10-16人工夹具测试目录适配完成：默认目录1通过2跳过，受限目录3通过；完整开发1181通过，新test安装版1158通过23跳过。仅改一项测试输入，生成器/输出根门/服务不变；devwatch剩余87失败未修。真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-fixture-test-scope/README.md。


2026-10-15人工单表闭环已验证：10表235列/1万行23.5万字段十个手工摘要吻合，取消/新attempt重试及离线九项缺覆盖、十项完成、重复/冲突拒绝通过。47核验/2夹具、1180开发、新test1157通过23跳过；3重要复核修复、123输入/919原件/28容器清理。真实仍68/78，large关闭、Task8未完。见docs/superpowers/evidence/2026-10-15-partition-coverage/README.md。


2026-10-15：人工单表执行与覆盖核验计划形成，限定固定人工夹具、明确pin的离线核验，十任务串行及取消重试/九项缺覆盖诊断/十项证明。准备草案不通用放行，真实large关闭。计划待审，无新产品实现/测试/构建/源读/PG，68/78及Task8保持。 见docs/superpowers/plans/2026-10-15-artificial-partition-coverage.md。


2026-10-15单表草案准备已实现：完整large父范围10/235先校验，再投影一表；六文档摘要链及发布前输入/生成/stage复核，权限关闭。64定向、1131开发、新test1108通过23跳过，新runtime纯人工CLI核对通过；119输入/两独立镜像/138原件、7容器清理。真实large关闭、人工执行与覆盖汇总未实现，68/78、Task8未完。证据：docs/superpowers/evidence/2026-10-15-partition-preparation/README.md。


2026-10-14：用户继续确认拆批设计后，形成large-partition-preparation实施计划，限完整父校验后的单表关闭权限草案；定义六文档摘要链、十分区/五失败门TDD及新候选验证。计划待审阅，尚未改产品/运行新项目测试或构建；真实large关闭，68/78、Task8未完。 计划：docs/superpowers/plans/2026-10-14-large-partition-preparation.md。


2026-10-14单表拆批设计：确认large完整10/235约束位于准备器，底层允许子集但真实large仍在读源前拒绝。新增完整父范围/十个单表子范围/独立覆盖核验草案，9项输入绑定及10/235元数据核对通过；F-14待审未实现，无新项目测试/构建/源读/PG，68/78与Task8不变。见docs/superpowers/evidence/2026-10-14-partition-design/README.md。


2026-10-14扩大人工调度验证：10表235列/20万行470万字段，十个手工摘要、两次源摘要及完整快照通过；相同源字节810.90→114.32秒，峰值73.2MiB/临时23.1MiB，交换0。117产品输入不变，复用候选，无新完整回归/构建。保留首次devwatch重叠准备，干净重跑；3容器/2人工fixture清理。真实仍逐次校验、68/78，Task8未完。证据：docs/superpowers/evidence/2026-10-14-guard-scale/README.md。


2026-10-14 I-07人工调度已验证：100毫秒重型校验调度/每次轻量取消截止/阶段强制复核/父监督独立人工发布摘要，26定向、1098开发、新test1075通过23跳过。相同人工2万行47万字段84.4→14.45秒；真实模式仍逐次校验、68/78与large关闭保持。初次取消137缺监督报告保留，后续运行中取消/截止无最终批。证据：docs/superpowers/evidence/2026-10-14-guard-opt/README.md。


2026-10-14人工函数定位：10表235列/2万行47万字段普通84.4秒、剖析168.7秒，独立摘要一致；控制器guard约32.3万次、累计136.4秒（剖析CLI约82%，嵌套不能相加）。报告RED1失败转1通过，产品代码/资源门未改；I-07重型校验调度设计待审。仍68/78、真实large关闭、Task8未完。证据：docs/superpowers/evidence/2026-10-14-large-profile/README.md。


2026-10-14高唯一行大组人工批：10表235列/20万行470万字段完整匹配独立摘要，约811秒/峰值72.8MiB、临时23.1MiB，换出0。新增夹具RED10失败1通过转11通过，新开发1072/安装候选1049通过23跳过；产品代码和116构建输入未变，复用固定镜像。覆盖仍68/78，真实large关闭，Task8未完。证据：docs/superpowers/evidence/2026-10-14-large-unique/README.md。


2026-10-14大组下一步仅元数据核算：按行/字段两种敏感性比较，单表拆分也不保证1800秒；优先研究ALTNAME_DATA/ASSOC_DATA/ENTRY_DATA，4表历史最大值临时上界超1GiB。新增高唯一行人工方案待确认，未运行新测试/镜像/真实读源，68/78与原限制不变。见docs/superpowers/evidence/2026-10-14-large-next-scope/README.md。


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


> 状态：现行｜as_of 2026-10-11


## 来源 datamgmt/README.md

# datamgmt —— 香如故数据接入模块

2026-11-13 正式请求读取器接入与人工候选验证完成。开发 1347 项通过，安装 1324 项通过及 23 项跳过，465,284 行人工整批用时 1338.41 秒。真实覆盖 68/78，Task8 尚未完成。见[本轮证据](../../docs/superpowers/evidence/2026-11-13-request-reader-integration/README.md)。

2026-11-13 p01人工原型对照完成。与11月12日基线使用相同SQLite文件，逐次请求校验的原型在1655.93秒产出完整人工批，黄金及双文件摘要通过。前两段同样次数的检查合计节省约280秒。正式产品集成和真实可行性仍待验证，真实覆盖68/78，Task8未完。见证据（历史路径 `../../docs/superpowers/evidence/2026-11-13-p01-openat-probe/README.md`）。

2026-11-12 p01人工吞吐定位完成。模拟465,284行和4整数4文本，在半核、768MiB及1800秒下于归并阶段超时。逐次请求重读和只读挂载检查占人工观测工作时间74.75%，计时开销未独立校准。真实覆盖68/78，Task8未完。见证据与测量范围（历史路径 `../../docs/superpowers/evidence/2026-11-12-p01-throughput/README.md`）。

2026-11-09最终：新runtime获批的p01一次真实尝试1800.26秒timeout，无完整批/新增源期望，仍68/78、Task8未完。无心跳拒收、PG/交换健康；59原件、3候选回收及scratch空核验通过。读取器人工改善未使真实任务在原预算内完成，需先在人工数据上验证足量吞吐；不重试、不提高预算、不接PG。见[本轮终态](../../docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)。

2026-11-09：已用新runtime为real-p01-20261109-c准备p01关闭任务卡，完整父10/235投影8列、安装6模块及缺授权拒绝门通过。没有真实快照挂载/读取，没有execution request/approval，仍68/78、Task8未完；原1800秒可能再次超时，读取须针对新卡另获具名授权。见[本次任务卡](../../docs/superpowers/evidence/2026-11-09-p01-read-review/README.md)。

2026-11-08正式集成：read_metadata只缓存32条词法Path链、合并同次stat，逐次新鲜检查不变。开发1339通过、安装1316通过/23跳过；固定80k人工黄金/归并、取消和请求变化拒绝通过，单次整程493.14→404.63秒，小样本整程未改善。937原件核验、24候选/44临时路径收尾。真实仍68/78、Task8未完，真实1800秒可行性未证，不自动重试；见[证据与限制](../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。以下保留历史时点。

2026-11-08后续：人工等价严格分支确认重复元数据检查为小夹具剖析主要成本；保持逐次检查的词法路径读取原型，两组普通整程观察平均下降19.7%，19项诊断及六批黄金核验通过。仅实验进程覆盖一处函数，产品未集成、无新项目完整回归，真实仍68/78/Task8未完。下一步正式兼容性实现和较大人工验证；见证据与限制（历史路径 `../../docs/superpowers/evidence/2026-11-08-project-path-profile/README.md`）。

2026-11-08最终：获批的p01唯一真实尝试触及1800秒监督截止，随后取消，未形成完整批或新期望；仍68/78、Task8未完。本次无心跳拒收，资源/PG健康、3候选回收及scratch空已核验。耗时分布待人工剖析（I-07），不自动重读、不提高预算；见本次终态（历史路径 `../../docs/superpowers/evidence/2026-11-08-real-p01-attempt/README.md`）。

2026-11-08：新attempt real-p01-20261108-b的p01关闭审阅已用安装API校验完整10/235父链并投影8列；控制包及缺授权拒绝启动核验完成，未挂真实快照或读取源。仍68/78、Task8未完，本次真实读取待具名批准。见任务卡（历史路径 `../../docs/superpowers/evidence/2026-11-08-p01-retry-review/README.md`）。

2026-11-07：B-21心跳超时边界已人工复现并最小修复，开发1325通过、安装候选1302通过/23跳过、自然边界100/100。仅人工验证；25日真实失败不能确认同因，真实仍68/78、Task8未完，新的真实尝试须另获具名授权。见证据（历史路径 `../../docs/superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md`）。

2026-10-25后续真实p01一次尝试未成功：外层invalid_heartbeat取消，约1637.6秒、无完整批或新期望，仍68/78。控制帧根因待人工复现（B-21），资源与PG健康、确切容器已回收；本次不重试真实数据。见失败停点（历史路径 `../../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md`）。

2026-10-25后续：首个真实单表POSTED_TO_ADDR_DATA/8列的关闭审阅已用b版安装API准备并复验，无缺项；只读已有仓库metadata，真实数据未读，覆盖68/78。首表任务卡及一次尝试授权边界见关闭审阅（历史路径 `../../docs/superpowers/evidence/2026-10-25-first-real-partition-review/README.md`）。

2026-10-25：严格project_snapshot单表元数据链、控制端/底层独立门及23角色离线覆盖已实现并完成人工候选验证；唯一复核两项资源语义问题已修复。公开审阅件始终不可执行，真实执行仍需具名授权，真实覆盖68/78、Task8未完成。最新测试、独立镜像和资源限制见本轮证据（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md`）。以下为各批历史记录。

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


2026-10-11茶香已明确批准固定快照一次全成员复核与55小表326列源期望生成；控制/监督/发布接线现已实现外部源模式与request摘要门，26项失败转最终93相关/936开发通过，一次新成果复核0问题。test候选构建持续换出775/828/1140触发取消，未产出新镜像、未开始runtime构建或读取真实源。授权保留，因资源风险停止后续负载，不称候选/真实就绪或Task8完成。见本轮接线与构建停点（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md`）。以下记录保留原发生时点。


2026-10-11停点后茶香明确要求继续，按原限制恢复一次人工候选：test完整回归885通过/23跳过，runtime已实际生成选定元数据的55表326列全DRAFT草案；50次宿主诊断采样换出均723，原停止阈值不变、两个容器回收。上轮换出原因仍未知，不宣称资源问题修复、Task8或真实执行完成，真实读取与PG关闭。见本轮恢复证据（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md`）。以下停点记录保留其发生时的结论。


2026-10-11实现仅仓库元数据的任务准备器：31项人工检查/908开发通过；一次新增复核的完成marker持久化缺陷已失败复现并修正。独立候选完整回归因宿主242/618/723连续换出以swap_pressure停止，未重试，runtime仓库55表模板生成未运行。见本轮停点证据（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation/README.md`）。准备件全DRAFT、授权false，真实75表/数据库/Task8不变。

2026-10-11仅补齐55表准备材料的当前绑定与下一步方案（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-small-readiness/README.md`）：21项当前摘要、四项代码预期变化、原55表/326列范围及候选参考已核对；原证据保留，不计新测试。拟增加只读仓库元数据的任务准备器，方案待确认，真实入口仍关闭。

2026-10-10整程截止已在人工链路接通并验证：14项先失败、85项相关通过、877项开发回归通过，独立候选854通过/23跳过；受控候选/宿主/SSH为1800/1830/1880秒，短超时实际停止。证据见本轮截止验证（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-lifecycle-deadline/README.md`）。下述各轮保留历史时点；真实75表、数据库、Task8及B-16/B-17仍未完成。

2026-10-10继续整理仅元数据的真实小组待审准备：精确55表/326列及逐表预算、来源摘要均已核对，历史统计不生成源期望。人工300秒外层与草案1800秒源批计时的范围差异已列明，整个生命周期截止及真实包装接线待确认，仍只允许人工实现验证。见[小组审阅](../contracts/releases/2026-10-06-bootstrap/sqlite-value-small-execution-review.md)；本轮不改代码、不运行新候选/项目测试、不读真实源或数据库。

2026-10-10用户在资源停止后明确要求继续；只读观察换出稳定后，按原阈值恢复一次人工验证。新候选完整回归840通过/23跳过；新控制器人工只读成功及三个错误摘要/错误镜像revision创建前拒绝已实际验证。宿主另有单区间7页换出，来源未确认，不宣称风险修复。当前证据见人工控制层恢复验证（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-task-control-resume/README.md`）；下面上一轮停点与开发结果保留历史时点，真实75表、数据库和Task8仍未完成。

2026-10-10继续接通仅人工任务控制层：外部请求/批准/roots摘要与实际镜像身份核对，移除入口业务根硬编码；14新检查、863开发回归通过。独立候选完整回归因宿主62/66/69页连续换出以swap_pressure停止，未重试；后续runtime控制层实际验证尚未运行。证据见任务控制与资源停点（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-task-control/README.md`）。真实75表、数据库及Task8仍未完成。

> 状态：Task 1–5 已实现；Task 6 合同准备中，SQLite78表/736列类型与子批次命名/空值政策已登记，独立源值期望已覆盖58/78表，剩余20表，导入门仍阻断｜as_of 2026-10-12

本模块长期负责首次建库、数据换版、新增来源、独立验证、彩排、发布和回滚。它是香如故长期运行自有容器中的低频模块，不是独立常驻导入服务。唯一权威源是 `usedata`，运行输入为复制并独立校验后的项目快照，目标是外部 `pg32b/xiangrugu`。

2026-10-10继续获仅人工文件验证的正式只读入口准备授权，新增readonly_batch.py，校验完整请求的批准摘要、关联文档、逐表预算和快照/元数据只读挂载；小组上限55表及64MiB排序空间，拒绝中/大组。实际人工候选及一次新增成果复核处置见只读入口证据（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-readonly-entry/README.md`）。project_snapshot仅API分支，尚无可信真实任务控制器/正式发布接线；真实75表未读，Task8和真实执行就绪仍未完成。

2026-10-10本轮继续接通人工批级执行、宿主采样及容器租约监督，完成后必须取得新宿主采样才发布最终人工结果；实际候选限制及取消证据统一见人工执行与监控证据（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-batch-runner/README.md`）。入口自行生成固定人工数据，拒绝真实读取授权；剩余75表期望未生成，Task8整体、真实范围/只读卷/大表临时区消费未完成。常驻watcher默认/tmp与排序器/data/var约束冲突另记B-17，手工全套通过不等于watcher恢复。

随后获三表源侧期望衔接/真实只读核对授权，已完成全快照摘要复核及3/78表完整源值期望（3,860行/42,453字段值），18定向/723开发通过，候选700通过/23仓库元数据跳过。唯一结果、一次评审保存失败修复和资源/镜像/运行证据见三表期望证据（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-expectations/README.md`）。未接数据库、冻结合同或导入，剩余75表源值期望未生成；下文缺口和测试数字保留历史时点。

用户要求按既定原则继续处理技术细节；当前SQLite命名/空值政策确认、736列逐值描述核验及尚缺的独立源值期望统一见[SQLite当前进度](../contracts/releases/2026-10-06-bootstrap/sqlite-review.md)。下文各批次的“待审”、调查范围和测试数字保留历史时点，不作为当前未批准或新验收声明。

随后批准并实现SQLite独立流式原生值读取接口，人工文件41项及开发完整705项通过，候选与一次评审修复见读取接口证据（历史路径 `../../docs/superpowers/evidence/2026-10-10-sqlite-values/README.md`）。没有真实源重读、源侧值期望生成或数据库接入，不是Task10完整适配器；镜像别名与服务不变。

2026-10-10已实现整行内容/重复次数无序标量比较的纯合成组件，含无损编码、受限外部排序、独立输入实际字节比较与失败报告；最终候选和一次评审证据统一见执行账（历史路径 `../../docs/superpowers/plans/2026-10-09-sqlite-unordered-value-progress.md`）。未提供真实SQLite/PG适配器、未替换常驻服务，不等于完整Task9或导入验收，BLOCKED不变。

随后授权修复配置检查路径：开发时读/workspace所属项目，候选时读/app所属项目；镜像代码检查仍固定/app，前批5项路径失败已消除。B-16回收补丁因并发替换误删风险被否决并撤掉，仍待重新设计；最新验证及边界统一见修复证据（历史路径 `../../docs/superpowers/evidence/2026-10-10-cleanup-layout/README.md`），下文各批次数量保留历史时点。


## 来源 datamgmt/docs/IMPLEMENTATION-PLAN.md

# 香如故容器化数据接入模块 Implementation Plan

2026-11-13 正式请求读取器通过回归、人工请求变化与取消验证，安装候选 1338.41 秒完成同源人工整批。下一步准备新 runtime 下的 p01 关闭权限任务卡，真实覆盖 68/78。见[交接入口](../../HANDOFF.md)。

2026-11-13 逐次请求重读人工原型。465,284行同源人工批在1655.93秒完成，黄金及双摘要核验通过。先验证正式接入的兼容性和保护条件，再以受限候选复核结果。真实覆盖68/78，Task8未完。见人工对照（历史路径 `../../docs/superpowers/evidence/2026-11-13-p01-openat-probe/README.md`）。

2026-11-12 p01规模人工诊断。读取、编码与分桶508.70秒，块排序467.38秒，归并至截止820.53秒。两项逐次请求检查合计1343.33秒，占人工观测工作时间74.75%。后续人工对照聚焦这两项检查，保留原有新鲜性和安全门。真实覆盖68/78，Task8未完。见人工证据（历史路径 `../../docs/superpowers/evidence/2026-11-12-p01-throughput/README.md`）。

2026-11-09真实停点：p01新attempt c在新runtime上1800.26秒timeout，无完整批/新增期望；59原件核验、3候选回收、scratch空、PG健康/交换0，仍68/78、Task8未完。人工80k改善不能证明真实原预算可行；本次授权已用，不重试或下一表，后续先足量人工吞吐定位。见[最终证据](../../docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)。

2026-11-09下一步已具体化：新runtime的新attempt real-p01-20261109-c关闭任务卡及纯元数据安装核验完成；原表/快照/预算不变，实际拒绝未授权执行且无request/候选。等待具名批准一次真实只读及全快照摘要复核，不自动重试，不接PG。真实仍68/78、Task8未完；见[任务卡](../../docs/superpowers/evidence/2026-11-09-p01-read-review/README.md)。

2026-11-08读取器正式集成人工验证完成：开发1339通过、安装1316通过/23跳过，80k人工完整黄金/多chunk归并及实际取消/变化拒绝均通过；保持逐次检查，单次80k493.14→404.63秒，小样本未改善，真实吞吐未证明。937原件核验及24候选/44人工临时路径收尾完成。真实仍68/78，Task8未完；下一步新真实任务卡另获具名授权，不自动重试，不接PG。见[本轮证据](../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。

2026-11-08人工性能阶段：严格分支1000行/8列剖析及保持逐次检查的元数据读取实验原型完成，六人工批黄金一致、诊断19项通过，两组普通整程均值观察下降19.7%。原型未产品集成，真实吞吐/完整兼容性及较大多轮归并待验证，无新项目完整回归。真实仍68/78，Task8未完；见下一阶段边界（历史路径 `../../docs/superpowers/evidence/2026-11-08-project-path-profile/README.md`）。

2026-11-08最终：p01本次真实尝试1800.18秒timeout，worker停于object_read_sort，无完整批/新覆盖；68/78及Task8未完保持。本次未发生invalid_heartbeat，资源/PG健康，候选及临时值流回收。暂停真实推进，先在人工夹具测量严格真实模式等价路径的耗时，真实校验调度改变仍须方案审定；不重试、不放宽预算。见证据（历史路径 `../../docs/superpowers/evidence/2026-11-08-real-p01-attempt/README.md`）。

2026-11-08：新的p01一次只读尝试已形成关闭任务卡和执行包装，安装API元数据校验、控制摘要及缺授权拒绝验证通过；准备阶段未读真实源，68/78与Task8未完保持。真实读取等待针对新attempt的明确确认，任何PG操作/冻结/导入仍关闭。见本次准备（历史路径 `../../docs/superpowers/evidence/2026-11-08-p01-retry-review/README.md`）。

2026-11-07：B-21人工心跳故障路径已复现并修复，开发1325通过、安装1302通过/23跳过及自然边界100/100完成。此为控制链修复验证，非真实容量/1800秒可行性或Task8验收；25日历史根因未确认，真实仍68/78，未重试或接PG。见证据（历史路径 `../../docs/superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md`）。

2026-10-25后续真实p01一次尝试已因外层invalid_heartbeat取消，约1637.6秒、无完整批/新增期望，仍68/78；B-21根因待人工复现，不能归为SQLite数据或1800秒超时。容器/值流清理、PG健康、swap0；本次不重试。见真实停点（历史路径 `../../docs/superpowers/evidence/2026-10-25-real-p01-attempt/README.md`）。

2026-10-25：真实单表协议接线的四任务实施及人工候选验证已推进至收尾，唯一复核两项Important修复后开发1314通过、安装版1291通过/23跳过，runtime离线四场景通过。全部为人工数据，真实仍68/78；真实容量/读取、数据库状态机、全载体执行和Task8整体未完成。最新证据见本轮记录（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md`），以下保留各批历史发生时点。

2026-10-17真实单表设计经继续确认后形成实施计划，待计划审阅；四任务覆盖关闭审阅包、双层控制门、独立真实覆盖和人工协议候选。沿用主代理串行及末尾一次复核，未实施/读源/接PG，68/78与Task8保持。见docs/superpowers/plans/2026-10-17-real-partition-control.md。


2026-10-16真实large单表接线设计草案已形成，待审阅：完整父范围/严格单表身份、独立真实离线覆盖、逐次guard及原资源门保持。仅设计，未改产品代码、未实施/读源/接PG；确认后先写实施计划，68/78与Task8不变。见docs/superpowers/specs/2026-10-16-real-partition-control-design.draft.md。


2026-10-16人工阶段后就绪核对：10表235列及2713份历史证据摘要复验一致；历史规范流均低于256MiB，但真实时间/临时峰值未证明，十次逻辑摘要量约36.82GB。真实large执行与真实覆盖汇总仍关闭，下一阶段需审定实现范围和执行身份；未读源/主动跑项目测试/构建，68/78、Task8未变。见docs/superpowers/evidence/2026-10-16-large-readiness-review/README.md。


2026-10-16宽文本人工SQLite受控路径验证通过：4094行完整发布且独立摘要/完整快照/双哈希/发布pin吻合，4095行sort/budget拒绝且无完整批；4定向检查通过。产品输入未变，无新完整回归。仅人工单对象，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-sqlite-artificial/README.md。


2026-10-16宽流人工边界通过：64KiB文本含重复，4094行完整匹配独立摘要，4095行budget拒绝且输出0行；临时峰值511.9MiB、容器内存峰值567.5MiB，清理完成。4定向检查通过，123产品输入未变、复用候选，无新完整回归。仅排序组件，真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-wide-stream-artificial/README.md。


2026-10-16人工夹具测试目录适配完成：默认目录1通过2跳过，受限目录3通过；完整开发1181通过，新test安装版1158通过23跳过。仅改一项测试输入，生成器/输出根门/服务不变；devwatch剩余87失败未修。真实仍68/78、large关闭、Task8未完。见docs/superpowers/evidence/2026-10-16-fixture-test-scope/README.md。


2026-10-15人工单表闭环已验证：10表235列/1万行23.5万字段十个手工摘要吻合，取消/新attempt重试及离线九项缺覆盖、十项完成、重复/冲突拒绝通过。47核验/2夹具、1180开发、新test1157通过23跳过；3重要复核修复、123输入/919原件/28容器清理。真实仍68/78，large关闭、Task8未完。见docs/superpowers/evidence/2026-10-15-partition-coverage/README.md。


2026-10-15单表草案准备已实现：完整large父范围10/235先校验，再投影一表；六文档摘要链及发布前输入/生成/stage复核，权限关闭。64定向、1131开发、新test1108通过23跳过，新runtime纯人工CLI核对通过；119输入/两独立镜像/138原件、7容器清理。真实large关闭、人工执行与覆盖汇总未实现，68/78、Task8未完。证据：docs/superpowers/evidence/2026-10-15-partition-preparation/README.md。


2026-10-14 I-07人工调度已验证：100毫秒重型校验调度/每次轻量取消截止/阶段强制复核/父监督独立人工发布摘要，26定向、1098开发、新test1075通过23跳过。相同人工2万行47万字段84.4→14.45秒；真实模式仍逐次校验、68/78与large关闭保持。初次取消137缺监督报告保留，后续运行中取消/截止无最终批。证据：docs/superpowers/evidence/2026-10-14-guard-opt/README.md。


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


2026-10-11茶香已明确批准固定快照一次全成员复核与55小表326列源期望生成；控制/监督/发布接线现已实现外部源模式与request摘要门，26项失败转最终93相关/936开发通过，一次新成果复核0问题。test候选构建持续换出775/828/1140触发取消，未产出新镜像、未开始runtime构建或读取真实源。授权保留，因资源风险停止后续负载，不称候选/真实就绪或Task8完成。见本轮接线与构建停点（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md`）。以下记录保留原发生时点。


2026-10-11新增runtime实际草案拒绝证据：3项负向检查通过，原草案与错误摘要在下游读取前拒绝；缺口报告列出执行字段转换、外部证书/清单选择与控制接线。随后茶香明确授权接通并人工验证只读真实控制器，复核固定快照2026-10-07-bootstrap一次、仅生成55小表326列源期望，保留原限制/停止门；不读NAS或另20表、不接PG、不冻结/导入。授权尚未执行，见草案门与待接线范围（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-draft-gates/README.md`）。


2026-10-11停点后茶香明确要求继续，按原限制恢复一次人工候选：test完整回归885通过/23跳过，runtime已实际生成选定元数据的55表326列全DRAFT草案；50次宿主诊断采样换出均723，原停止阈值不变、两个容器回收。上轮换出原因仍未知，不宣称资源问题修复、Task8或真实执行完成，真实读取与PG关闭。见本轮恢复证据（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md`）。以下停点记录保留其发生时的结论。


2026-10-11停点后只读调查：三次空闲换出计数723/723/723稳定，当前交换页主要记在Docker/containerd服务，缺少事发逐服务基线，不能认定事件根因；未恢复候选、未修改阈值/设置/服务，无新项目测试。见只读调查（历史路径 `../../docs/superpowers/evidence/2026-10-11-host-swap-investigation/README.md`），原候选未完成和真实关闭结论保持。


> 状态：Task 1–5 已实现并验证，Task 6 草案经选择器修复后模型通过、完整精确匹配，但导入门仍阻断；Git 提交待单独授权｜as_of 2026-10-07
> 依据：`rules.md`、`datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md`、`datamgmt/config/roots.yaml`
> 范围：只规划实现，不授权 Git 提交/推送、镜像拉取/构建、主机挂载、服务启停、数据库写入或正式导入。


## 来源 datamgmt/docs/OPERATIONS.md

# datamgmt 操作生命周期

2026-11-08：保持逐次检查的元数据读取器已进入独立候选并完成人工验证，运行/复核/资源及精确清理收据见[本轮证据](../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。两个新镜像没有晋级现行别名，人工结果不计真实覆盖，不代表真实1800秒可行；下一次真实读取另行具名授权。

2026-10-25：单表协议的人工执行、取消后新attempt、宽流边界及离线覆盖入口见本轮证据脚本与收据（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md`）。公开project_partition CLI只生成不可执行审阅件；审批JSON不是人类授权，真实读取仍须具名批准，任何PG写入及pg32b旧数据处置另行确认。project_partition_coverage只消费明确选定metadata和收据，不读取SQLite，不按“最新目录”选择attempt；人工结果的外部标记不能删除或计入真实覆盖。以下保留既有历史操作记录。

2026-10-12中组最新：37项先失败后通过、995开发通过，新test972通过/23跳过；中组准备10表156列及人工正/负例已验证。实际中组约955.93秒失败，通用内部失败与cancelled原因未充分留存，无完整批/新期望，覆盖仍58/78；未接PG/冻结/导入，Task8未完成。证据：docs/superpowers/evidence/2026-10-12-sqlite-medium/README.md。

2026-10-12最新进度：有界缓存策略20项通过、958开发通过、新候选935通过/23跳过；固定快照完整复核及55表326列期望整批生成，约81.2秒/峰值119.5MiB，9次换出与内存停顿0。累计58/78表，另20表未查询；仍DRAFT、未接PG/冻结/导入，Task8未完成。证据：docs/superpowers/evidence/2026-10-12-read-cache-policy/README.md。


2026-10-11茶香已明确批准固定快照一次全成员复核与55小表326列源期望生成；控制/监督/发布接线现已实现外部源模式与request摘要门，26项失败转最终93相关/936开发通过，一次新成果复核0问题。test候选构建持续换出775/828/1140触发取消，未产出新镜像、未开始runtime构建或读取真实源。授权保留，因资源风险停止后续负载，不称候选/真实就绪或Task8完成。见本轮接线与构建停点（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-project-control/README.md`）。以下记录保留原发生时点。


2026-10-11停点后茶香明确要求继续，按原限制恢复一次人工候选：test完整回归885通过/23跳过，runtime已实际生成选定元数据的55表326列全DRAFT草案；50次宿主诊断采样换出均723，原停止阈值不变、两个容器回收。上轮换出原因仍未知，不宣称资源问题修复、Task8或真实执行完成，真实读取与PG关闭。见本轮恢复证据（历史路径 `../../docs/superpowers/evidence/2026-10-11-sqlite-task-preparation-resume/README.md`）。以下停点记录保留其发生时的结论。


2026-10-11停点后只读调查：三次空闲换出计数723/723/723稳定，当前交换页主要记在Docker/containerd服务，缺少事发逐服务基线，不能认定事件根因；未恢复候选、未修改阈值/设置/服务，无新项目测试。见只读调查（历史路径 `../../docs/superpowers/evidence/2026-10-11-host-swap-investigation/README.md`），原候选未完成和真实关闭结论保持。


## 来源 datamgmt/docs/DESIGN.md

# datamgmt 最终设计规格

2026-11-08读取器合同补充：有界32条缓存仅保存纯词法Path对象及祖先元组；每次保留整链符号链接检查、叶子stat和有界重读，只合并同次类型/大小重复stat。不缓存文件系统状态、fd、字节或授权结论，不改变guard频率、阶段/发布前重核及取消截止；不新增TOCTOU原子性保证。兼容性及人工候选验证见[正式集成证据](../../docs/superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。

2026-10-25新增严格project_snapshot单表协议：完整10表/235列父链先校验，再投影一个分区；控制端和底层独立验证实际镜像、审批、源身份及原件pin，阶段/发布前重核；独立23角色离线入口不读SQLite或数据库。权限与资源设计见已实施设计（历史路径 `../../docs/superpowers/specs/2026-10-16-real-partition-control-design.draft.md`），人工验证及当前限制见证据入口（历史路径 `../../docs/superpowers/evidence/2026-10-24-real-partition-control/README.md`）。真实仍68/78、Task8未完，真实任务另行具名授权。以下是历史时点记录。

2026-10-15人工单表闭环已验证：10表235列/1万行23.5万字段十个手工摘要吻合，取消/新attempt重试及离线九项缺覆盖、十项完成、重复/冲突拒绝通过。47核验/2夹具、1180开发、新test1157通过23跳过；3重要复核修复、123输入/919原件/28容器清理。真实仍68/78，large关闭、Task8未完。见docs/superpowers/evidence/2026-10-15-partition-coverage/README.md。


2026-10-15单表草案准备已实现：完整large父范围10/235先校验，再投影一表；六文档摘要链及发布前输入/生成/stage复核，权限关闭。64定向、1131开发、新test1108通过23跳过，新runtime纯人工CLI核对通过；119输入/两独立镜像/138原件、7容器清理。真实large关闭、人工执行与覆盖汇总未实现，68/78、Task8未完。证据：docs/superpowers/evidence/2026-10-15-partition-preparation/README.md。


2026-10-14 I-07人工调度已验证：100毫秒重型校验调度/每次轻量取消截止/阶段强制复核/父监督独立人工发布摘要，26定向、1098开发、新test1075通过23跳过。相同人工2万行47万字段84.4→14.45秒；真实模式仍逐次校验、68/78与large关闭保持。初次取消137缺监督报告保留，后续运行中取消/截止无最终批。证据：docs/superpowers/evidence/2026-10-14-guard-opt/README.md。


2026-10-14高唯一行大组人工批：10表235列/20万行470万字段完整匹配独立摘要，约811秒/峰值72.8MiB、临时23.1MiB，换出0。新增夹具RED10失败1通过转11通过，新开发1072/安装候选1049通过23跳过；产品代码和116构建输入未变，复用固定镜像。覆盖仍68/78，真实large关闭，Task8未完。证据：docs/superpowers/evidence/2026-10-14-large-unique/README.md。


2026-10-13大组代表性人工批：10表235列（156整数/79文本）两档均完整匹配独立摘要；大档100000行/2350000字段约419.3秒、峰值61.7MiB，交换换出0。B-20心跳超时半帧丢弃人工复现后修复，开发1072/新test1049通过23跳过。仍68/78、真实large关闭、Task8未完；全组1800秒可行性未证明。证据：docs/superpowers/evidence/2026-10-13-large-representative/README.md。


2026-10-13大组人工接线：4项先失败转28通过，受限完整开发1070通过，新test1047通过/23元数据跳过；新runtime离线准备10/235、人工完整批及磁盘三场景验证通过。large真实模式仍代码关闭，覆盖68/78，无源读取/PG/冻结/导入，Task8未完。证据：docs/superpowers/evidence/2026-10-13-large-artificial-control/README.md。


2026-10-13中组前台完成：固定快照单次只读10表156列整批证书核验通过，新增354363行/5430382字段，约1492.4秒/峰值146.2MiB，交换与宿主换出0；累计68/78，剩大组10表235列未查询。仍DRAFT、无PG/冻结/导入，Task8未完成；证据：docs/superpowers/evidence/2026-10-13-medium-foreground/README.md。以下为各批历史发生时点，不代表当前覆盖数。


2026-10-13人工留证收尾：控制外层静态触发/信号、停止和退出已完成TDD及独立候选验证；旧真实取消发送方仍未知，覆盖58/78、Task8未完成。证据与权限false的下一次中组方案：docs/superpowers/evidence/2026-10-13-controller-evidence/README.md。


2026-10-13最新：已授权中组单次只读重试约1179.5秒以cancelled停止；第9对象ADDR_CODES、8对象仅内部完成，无整批/新增期望，覆盖仍58/78。SIGTERM事件已留证，外层触发未知，I-06待人工改进；无PG/冻结/导入。证据：docs/superpowers/evidence/2026-10-13-medium-retry/README.md。


2026-10-12收尾：末对象取消/超时诊断计数窗口已修复并经人工候选验证；58/78和旧中组根因未知保持，无真实重读/PG/冻结/导入。新证据及非执行重试审阅：docs/superpowers/evidence/2026-10-12-task-tail/README.md。


2026-10-12本轮：B-18人工失败诊断与监督原因关联已验证；原中组根因未知，58/78覆盖不变，无真实重读/PG/冻结/导入，Task8未完成。统一证据：docs/superpowers/evidence/2026-10-12-task-failure/README.md。


2026-10-12中组最新：37项先失败后通过、995开发通过，新test972通过/23跳过；中组准备10表156列及人工正/负例已验证。实际中组约955.93秒失败，通用内部失败与cancelled原因未充分留存，无完整批/新期望，覆盖仍58/78；未接PG/冻结/导入，Task8未完成。证据：docs/superpowers/evidence/2026-10-12-sqlite-medium/README.md。


## 来源 HANDOFF.md

# 香如故数据接入交接

截至 2026-11-13，正式请求读取器已经接入并通过安装候选人工验证。开发回归 1347 项通过，安装版 1324 项通过、23 项跳过。465,284 行人工整批用 1338.41 秒完成，独立黄金摘要和两次 SQLite 文件摘要一致。 [本轮证据](../../docs/superpowers/evidence/2026-11-13-request-reader-integration/README.md)

真实源值期望已覆盖 **68/78 表**，余 10 表 235 列，Task8 未完成。11 月 9 日 p01 尝试在原 1800 秒预算内超时，未形成完整批。 [真实运行停点](../../docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)

1. 先读 [AGENTS.md](../../AGENTS.md)、[rules.md](../../rules.md)、[项目索引](../../docs/index.md)、[数据接入模块](../README.md) 和 [阶段计划](../docs/IMPLEMENTATION-PLAN.md)。Windows 是项目编辑入口，项目构建、测试和执行都在 32 上串行进行。
2. 下一步用已验证的新 runtime 准备 p01 `POSTED_TO_ADDR_DATA` 八列的关闭权限任务卡。绑定固定快照及控制输入，核验候选身份和主机状态，保持半核、768MiB、无交换、1800 秒候选截止。
3. 任务卡经茶香明确授权后方可执行一次真实只读及全快照摘要核验。以上次授权已用完为准。只有完整批和独立核验通过后才能增加真实源值期望。数据库写入前另行通知茶香并确认 pg32b 旧数据的处置。

交接基线为 `8fbc8c97fcf1d818caddf6ab556fa82d986643ed`。阅读和同步时以项目授权为准。历史日志中的授权收据仅说明对应历史操作，当前权限以本次用户指令为准。
