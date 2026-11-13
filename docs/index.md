# index.md —— 文档索引

2026-11-13 正式请求读取器已接入。安装候选在 1338.41 秒完成 465,284 行同源人工整批，黄金与双摘要一致，回退 0 次。真实覆盖 68/78。见[本轮证据](superpowers/evidence/2026-11-13-request-reader-integration/README.md)及[交接入口](../HANDOFF.md)。

2026-11-13 p01人工对照。逐次读取原型使用同一465,284行SQLite，在原1800秒预算下1655.93秒完成，黄金及双文件摘要核验通过。前两段的检查次数与基线相同，合计节省约280秒。原型限人工候选，真实覆盖68/78。见[人工证据](superpowers/evidence/2026-11-13-p01-openat-probe/README.md)。

2026-11-12 p01人工吞吐定位。465,284行、4整数4文本在半核、768MiB及1800秒下于归并阶段超时。逐次请求重读与只读挂载检查合计1343.33秒，占观测工作时间74.75%。75份原件核验，两个候选回收，真实覆盖68/78，Task8未完。见[人工诊断](superpowers/evidence/2026-11-12-p01-throughput/README.md)。

2026-11-09最终：新runtime的p01唯一真实attempt c约1800.26秒timeout，worker随后cancelled/object_read_sort，无完整批/新增期望，仍68/78、Task8未完。峰值约124.5MiB、swap/pswpout0、PG健康，无心跳拒收；59原件核验、3候选回收、scratch空。授权已用，不重试/下一表；后续先人工验证足量吞吐。见[本次终态](superpowers/evidence/2026-11-09-real-p01-attempt/README.md)。

2026-11-09获批执行：茶香针对新任务卡确认后，唯一真实只读attempt real-p01-20261109-c已启动，原半核/768MiB/1800秒及停止门保持。首次metadata安装收据路径错误B-23已保留失败并修正独立metadata-2；无额外真实读取。终态前仍68/78、Task8未完，不重试/下一表/接PG。见[执行进度](superpowers/evidence/2026-11-09-real-p01-attempt/progress.md)。

2026-11-09：新runtime的p01一次真实只读任务卡real-p01-20261109-c已准备；安装API关闭审阅/完整父10表235列及投影8列、6安装模块、资源/28原件/确切回收核验通过，缺授权退出2且无候选/request。未挂快照/读源，仍68/78、Task8未完，等待针对新卡具名授权。见[任务卡与边界](superpowers/evidence/2026-11-09-p01-read-review/README.md)。

2026-11-08正式集成收尾：保持逐次检查的读取器已集成，开发1339通过、安装1316通过/23跳过，人工严格分支黄金/取消/请求变化拒绝均通过；同源80k单次整程493.14→404.63秒，小样本未改善，不证明真实1800秒可行。937原件核验、24候选回收、44人工临时路径清理；真实仍68/78、Task8未完。见[本轮证据](superpowers/evidence/2026-11-08-metadata-reader-integration/README.md)。此前暂停停点已续接完成。

2026-11-08暂停：用户要求休息、明天继续。正式读取器已集成，开发1339通过、安装1316通过/23跳过；人工80k新旧对照均结束，24候选逐ID确认不存在，PG基线健康。总证据核验、文档和人工临时清理尚待完成，真实仍68/78、Task8未完。明天先读[暂停续接](superpowers/evidence/2026-11-08-metadata-reader-integration/PAUSED-20261108.md)，不重做已完测试或复核，不自动重试真实读取。

2026-11-08后续：严格项目路径的人工剖析完成，1000行/8列普通与原型六批均匹配黄金；原版剖析guard累计约占CLI82.75%（非真实占比）。只复用词法组件、保持逐次检查的实验原型，两组普通整程均值10.16→8.16秒，观察下降19.7%，尚未产品集成或证明真实吞吐。诊断19项通过、唯一入口复核问题修正，334原件/13候选/16临时路径收尾；真实仍68/78。见[本轮证据](superpowers/evidence/2026-11-08-project-path-profile/README.md)。

2026-11-08：p01本次唯一真实尝试约1800.18秒由监督timeout停止，worker随后cancelled/object_read_sort；无完整批/新增期望，仍68/78。本次无invalid_heartbeat，峰值约120.2MiB、交换及宿主换出0、PG健康；3候选回收、scratch为空，60原件摘要核验。授权已用，不重试或下一表；后续先用人工夹具测量校验/排序耗时（I-07）。见[最终失败证据](superpowers/evidence/2026-11-08-real-p01-attempt/README.md)。

2026-11-08：用户针对新任务卡明确确认后，p01唯一真实尝试已启动；控制端固定request=a50b80f8…5f946c及approval/roots原始pin。metadata首次因专用空目录属主失败，修正10001并保留原件后metadata-2成功，未额外读取源。原半核/768MiB/禁交换及1800秒保持，终态前仍68/78，不重试或下一表。见[本次运行](superpowers/evidence/2026-11-08-real-p01-attempt/progress.md)。

2026-11-08：p01新attempt real-p01-20261108-b的关闭任务卡、固定控制包及元数据候选核验已完成，缺授权时拒绝启动已验证；尚未读取真实源，仍68/78。范围为POSTED_TO_ADDR_DATA/8列及全快照摘要，原资源门不变，只一次且失败停止，等待具名确认。见[本次任务卡与证据](superpowers/evidence/2026-11-08-p01-retry-review/README.md)。

2026-11-07：B-21人工复现确认完整tick换行在Bash读取超时边界可能被误拼入下一帧；最小修复经RED→GREEN、开发1325通过、安装候选1302通过/23跳过、自然边界100/100验证，候选及人工临时文件已清理。25日真实失败仍缺帧级证据，不能确认同因；真实仍68/78、Task8未完，未重试或接PG。见[本轮证据](superpowers/evidence/2026-11-07-heartbeat-diagnosis/README.md)。以下保留历史停点。

2026-10-25首表真实尝试已停止：约1637.6秒时宿主invalid_heartbeat触发取消，worker停于object_read_sort，无完整批/新增期望，仍68/78。内存峰值约120.3MiB、无swap/OOM，PG基线健康、容器回收；B-21待人工心跳复现，未确认错误帧成因。见[失败证据](superpowers/evidence/2026-10-25-real-p01-attempt/README.md)，本次授权不自动重试或下一表。

2026-10-25已获首表一次真实尝试授权，POSTED_TO_ADDR_DATA/8列及全快照摘要复核已启动；外部原始请求固定为4becb3ce…fff24f35，仍按1800秒/0.5CPU/768MiB运行，不重试或下一表。终态未判前覆盖保持68/78；见[本次尝试](superpowers/evidence/2026-10-25-real-p01-attempt/README.md)。数据库、冻结和导入未授权。

2026-10-25首个真实单表任务的关闭权限材料已准备：POSTED_TO_ADDR_DATA/8列，b镜像纯元数据校验完整父10/235后投影成功，审阅无缺项；未挂真实快照/NAS、未读源/接PG，仍68/78。下一步等待针对一次尝试及全快照摘要复核的具名授权，详见[任务卡](superpowers/evidence/2026-10-25-first-real-partition-review/README.md)。

2026-10-25真实单表协议及人工候选验证：完整父链/双层门/23角色离线核验已实现，唯一复核两项Important经RED→GREEN修复；开发1314通过，新test安装版1291通过/23跳过，runtime离线四场景通过。真实覆盖仍68/78、Task8未完，真实读取及PG另行授权。实现、限制和收尾证据统一见[本轮记录](superpowers/evidence/2026-10-24-real-partition-control/README.md)。以下日期条目保留历史时点。

2026-10-25用户要求暂停、明天续接：真实单表协议已完成人工候选验证；唯一复核两项资源语义问题已修复，26新定向及289元数据检查通过，修复后完整回归途中取消。b镜像/安装回归/修复后离线集成及最终清理待做，真实仍68/78、Task8未完。见[暂停交接](superpowers/evidence/2026-10-24-real-partition-control/PAUSED-20261025.md)。

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

## 现行文档

其余SQLite75表的逐表历史预算依据见`datamgmt/contracts/releases/2026-10-06-bootstrap/sqlite-value-remaining-budget.draft.json`；其执行建议已由同目录`sqlite-value-resource-revision.draft.json`修订为批级摘要与更保守的硬件预算。原草案非执行位保留生成时点，随后人工代码/候选验证授权另记，不授权真实75表读取；当前进度以`sqlite-review.md`为准。

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

新会话先读 `AGENTS.md`、`rules.md`、本索引和 `datamgmt/README.md`；准备数据接入开发时再读 `datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md` 与 `datamgmt/docs/PITFALLS.md`。其余按需读取。

历史内容可从 Git 恢复。2026-09-30 大清理前的集中回收点为 `75ecd77`；本轮删除内容可从变更前提交 `5627da7` 恢复。
