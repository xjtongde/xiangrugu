# SQLite角色与三表类型执行账 — plan: IMPLEMENTATION-PLAN.md Task6限定切片

用户“同意”批准78表逻辑对象、76主键索引附属元数据角色的非执行记录，
及 ADDR_CODES / SOCIAL_INSTITUTION_ALTNAME_CODES / SOCIAL_INSTITUTION_ALTNAME_DATA
三表28列只读类型统计。按TDD扩展探针、构建候选、自有代码镜像内运行。
不输出文本/BLOB明细、不改源、不访问NAS或PostgreSQL、不替换dev、不冻结/导入/提交推送。
实际导入前仍须通知用户并商定pg32b旧数据处置。

接口：原提案/源结构观察 → 仅角色批准与精确28列权限 → 源侧SQLite API统计。
统计不是原始页解析、完整值合同、主键唯一性或数据库验证；Task10尚未实现。

Ruling: 在用户指定Windows脏工作树原地修改、同步到32测试，不建分支/worktree或提交；
不在Windows执行项目代码。代价是以文件/镜像摘要绑定当前脏树，发布仍需另批Git定版。
Ruling: 类型使用SQLite API typeof观测，不宣称原始页存储类型；
TEXT长度分Unicode码点与API UTF-8字节，整数极值十进制字符串、REAL极值float.hex，
避免JSON精度损失；不读取其他表。代价是后续独立原始读取与目标值验证不能省略。

步骤：

1. 已有结构提案绑定角色决定/批准投影；原提案不覆盖，正式BLOCKED不变。
2. 23项合成诊断先全失败（模块缺失）；首轮22通过/1失败，小VM预算在1000步回调前结束，
   调整回调粒度为min(1000,max_vm_steps)，累计单元542通过。
3. 三个角色元数据测试与七个镜像探针测试先10失败（批准文件/脚本未创建），实现后累计552单元通过；首候选545通过/15仓库产物跳过，runtime smoke通过。
4. 单次独立代码评审；候选镜像完整测试及runtime smoke。
5. 资源与容器基线、只读单件/证书/权限卷、三表流式统计、前后摘要与回收。
6. 回传证据、R-06对齐、只报告本切片，不冻结/导入。

预算：单worker，模块180秒、3表64列、总50万行/800万cell、单cell2MiB/
值128MiB/输出1MiB/VM2000万；文件1GiB。超预算抛错，不输出部分成功。
外层容器1CPU/768MiB/64PID、无网络/非root/只读rootfs，nice19/ionice3与主机超时回收。
一次工具编排因完整大JSON回传被截断而解析失败，未写文件或访问源；
改为PowerShell只投影角色所需元数据，无日期精度/源值转换。
以下续接阶段出口与机器证据；此前各计数为对应阶段时点。

## 单次独立评审及一轮修正

sqlite_type_review只读审查，无Critical；VM预算边界为Important，rule_id绑定为Minor。
Ruling: rule_id虽不影响源件选择，但成功证据可误标规则归属，按Important处理；与VM问题一起在同一轮修正，不扩大源读取范围。
新增两项回归：规则号不匹配及抵达VM回调预算边界必须失败。VM测试替身先两次因contextmanager代理错误失败，修正测试后确认真实RED（未抛异常）；规则绑定同样RED。
实现后554单元通过。VM提前保留一次回调间隔并在边界中断；机器证据明确近似计数，不宣称精确VM指令上限。
SQLite官方接口只给近似间隔，硬资源边界仍由时间/容器资源限制承担；官方参考：https://www.sqlite.org/c3ref/progress_handler.html。
SQLITE_LIMIT_LENGTH同时限制整行和单值，2MiB限制可能保守拒绝整行，失败码不证明某个cell超限：https://www.sqlite.org/limits.html。
仅评审一次、修正一次，不做循环重审；上述两项均修复，无延期Minor。
一次构建工具编排在JS模板插值阶段失败，未执行远端命令；改用无JS插值的脚本后继续。

## 阶段出口与证据

最终候选test：xiangrugu:test-sqlite-types-final-20261009-b1，
sha256:6ef1b6df7cec36b919f3326ddaa85c6762020e18526e5d4fbc6a8d6a0d5b9e57；完整547通过/15仓库产物跳过。
runtime：xiangrugu:runtime-sqlite-types-final-20261009-b1，
sha256:bdbb8421352288e33dfcc9d2cb4a1cba19a13a39b44d4209922bd87199dfaea3；非root包与CLI smoke通过。
devwatch最后554通过/exit0，未替换常驻容器；旧test/runtime别名保留。

最终运行目录：/opt/mydocker/xiangrugu/data/var/sqlite-types-final-20261009-b1。
磁盘可用191,937,884,160 bytes，MemAvailable5,616,560KiB，SwapFree999,420KiB；load<4门禁通过。
2026-10-09T10:02:59Z～10:03:04Z完成三表统计，单源件仅只读卷、权限/证书仅只读卷，运行目录可写；
宿主240秒超时/10秒强制回收，临时容器已移除，前后stat/摘要及无sidecars核验通过。
dev/pg32/pg32b容器身份、镜像与启动时刻完全一致。未访问NAS、连接PG、扩大75表范围或输出TEXT/BLOB原值。

[源侧统计](../evidence/2026-10-09-sqlite-types/sqlite-types-observation.draft.json)本地/远端SHA一致；
[核验](../evidence/2026-10-09-sqlite-types/verification.json)绑定脏树代码摘要、镜像、角色权限及服务/文件基线。
[JUnit](../evidence/2026-10-09-sqlite-types/candidate-tests.xml)本地加末尾LF，远端/本地摘要分别记录，不冒称字节同一。
一次后置只读SSH命令因PowerShell引号误解析失败，未改变镜像或容器；改用base64 Linux脚本后复核通过。
角色批准与统计最新事实只在release/sqlite-review.md展开，原结构提案/正式合同保持不变。
R-06索引/日志/README/Task6/member-review/cbdb入口已续接；本切片完成，不宣称Task6、Task9/10或导入完成。
最终对齐复核：镜像内三个自有代码文件与Windows摘要一致，源观察本地/远端摘要一致；
再跑dev单元554通过（5.74秒），服务基线/别名仍不变，git diff --check通过（仅既有换行提示）。
五份受保护正式/候选合同及原结构提案摘要与前批一致，current.yaml仍不存在；新证据锚点均存在，日志新行140字符。
HEAD仍1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05，未提交推送。运行统计基于SQLite3.40.1 API，不推断其他表或未来版本。
