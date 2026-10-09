# SQLite 结构盘点执行账 — plan: datamgmt/docs/IMPLEMENTATION-PLAN.md Task 6 限定切片

## 授权、边界及接口核查

用户“同意”批准上一轮明确提出的 CBDB SQLite 结构盘点批：只读一个项目快照成员、
前后摘要、表/视图/字段/索引/约束证据，按 TDD 完善受限探针并构建候选 test/runtime。
不读业务行，不执行视图/触发器，不访问 NAS，不连接 PostgreSQL；
不替换 dev、不冻结、不导入、不提交或推送。实际导入前先通知用户并商定 pg32b 旧数据处置。

Task 6 接受源结构观察；Task 10 需要值读取/装载/独立验证。前者不能证明后者完成。
Ruling: 本批是结构观察切片，不实现 Task 10 适配器或值合同；误判成本是错误放行，
故输出固定非执行且仍为 BLOCKED。

Ruling: 维持用户指定 Windows 当前脏工作树作为唯一编辑权威，不创建 worktree、不切分支、
不安装 Windows 依赖、不提交；所有测试经受控同步在 32 执行。代价是依赖逐文件摘要识别本批。

Ruling: 不解析或执行视图/虚拟表字段，完整保存其目录及原 DDL 并标为待审；
普通表使用 table_xinfo，包括生成/隐藏列；原约束 SQL、外键及索引元数据保留。
误判成本是后续仍须专门批准安全字段/值观察，不把声明类型当作存储值类型。

immutable=1 仅用于无 sidecar、调用者保证静止且容器只读的项目快照；
前后摘要不是原子性保证。官方依据：
[SQLite URI](https://www.sqlite.org/uri.html)、
[PRAGMA](https://www.sqlite.org/pragma.html)、
[Python sqlite3 authorizer](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.set_authorizer)。

## 当前执行证据

HEAD = 1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05，标题为 docs: 确定容器化数据接入执行方案。
32 已重启（2026-10-09 14:33），容器 ID/镜像仍在，启动时间以本轮重新建立基线。
磁盘可用约 193 GB，内存可用约 5.8 GB，swap 使用 0，低负载；Docker 29.7.2 / Compose 5.4.0。

预检失败记录：第一次 PowerShell 双引号拼接展开了 shell 变量，SSH shell 语法错误，
尚未执行主机操作；改为 UTF-8/base64 传输。普通 Python 标签不存在，预检提前退出；
随后完整锁定 digest 检查成功，无须拉取新基础镜像。两次均只读。
一次工具编排 JavaScript 因补丁字符串的 Markdown 反引号语法错误，未执行任何文件写入；
去除字符串内反引号后重发，不影响远端或项目源。

TDD:

- 新诊断测试先收集失败（模块缺失），随后首轮 20 通过/3 失败。
- 其中 WITHOUT ROWID 主键没有对应 sqlite_schema autoindex 条目、目录被测试辅助函数
  提前 read_bytes 均为夹具错误；修正夹具，不变更源行为。
- SQLITE_TOOBIG 未归类为输出预算错误属于我方诊断错误，按实际 sqlite_errorcode 修复。
- 补前后源变化拒绝测试，诊断 24 项及累计单元 512 项通过。
- 新证据探针 7 项先因脚本缺失失败；后续验证待续。

## 独立评审与修复

sqlite_structure_review 单次只读静态评审，未读真实源/凭据、未执行测试，无 Critical/Important。
其 Minor 是 database_connected=false 的范围歧义。复评为 Important：
机器证据明明打开了源 SQLite，却可被理解为没有连接任何数据库，影响事实可信度。
按 TDD 补精确字段测试，先 1 失败/6 通过（KeyError），再改为
source_sqlite_connected=true / postgresql_connected=false，移除歧义字段。
这是唯一修复轮，不进行重复评审。

Final: Ruling: 原 Minor 提升为 Important并修复 — 机器证据应区分源 SQLite 与目标 PostgreSQL；
误判成本是下一 agent 错读访问范围，故以精确字段消除。

评审 Declined to judge 六项逐条处理：

- 测试真实性：由本任务在 32 运行并回传报告，不以评审转述代替。
- 镜像/挂载事实：由本任务核对 digest 与一次性启动参数，不晋级别名。
- 真实成员/证书事实：由本批限定探针建立，未出结果前不作成功声明。
- Task 10 值/装载/独立验证：明确不属于本批，不放行该任务。
- 视图/虚拟表字段：待审，不把目录完整说成字段/值完整。
- 并发原子性：静止只读项目快照，无源写流程；前后哈希不声称原子保证。

首版候选全套 515 通过/12 跳过（仓库元数据产物不随 test 镜像复制，固定 /app 边界跳过）；
runtime help/package smoke 通过。修复后须重建独立候选标签并重新验证，旧候选不覆盖。
## 最终候选、真实结构及交付

最终候选标签为 xiangrugu:test-sqlite-structure-final-20261009T071000Z 和
xiangrugu:runtime-sqlite-structure-final-20261009T071000Z。
test ID = sha256:0a01e49dd0d576e0f4a03f62757f2cc4f9d27c9cb022542dbdf71afc48a0aafd；
runtime ID = sha256:40b1347027616fdc4f2a0e2ff9acc8703edfb1aea87c7b8fc6adfacc423f7524。
创建时间以 OCI 标签和机器证据为准，标签后缀只是唯一批次标识，不能当实际执行时间。
本轮 Dockerfile、依赖锁、Compose 未变更；两轮候选旧标签保留，不覆盖别名。

修复后镜像完整 515 通过/12 跳过；runtime help/package smoke 通过。
最后 dev 单元 519 通过，真实 watcher 第9轮 519 通过/returncode=0。
四件代码/测试的镜像内摘要与 Windows 当前源码一致，OCI HEAD/dirty/非root核对通过。

真实结构观察为 2026-10-09T09:06:15Z～09:06:19Z，仅 m007906，前后摘要及宿主文件身份一致，
无 sidecar；78表/736字段/76主键自动索引，无视图、触发器或显式外键。
源读取只发生在候选 test 镜像，单文件/证书只读卷、无源码挂载、无网络；
结果和未决合同统一见 release/sqlite-review.md，不在本账复制结构明细。

提案文档的78身份由 runtime 中既有 source_object_id API 独立复核，736字段逐项
对照结构证据、76索引目录全集及全部非执行批准位校验通过，不重新读取源。
提案仍未批准，不赋目标类型/表名/可空语义，不构成数据库验证。

最终 [机器核查](../evidence/2026-10-09-sqlite-structure/verification.json) 绑定
源码/合同/提案、镜像、JUnit、容器参数、源前后身份与运行日志。
源证据/probe容器JSON回传字节摘要一致；JUnit原件无尾换行，本地apply_patch加一个LF，
两件不同SHA均明确记录，不宣称字节一致。运行原件及完整构建日志留在32本批data/var目录。

dev/pg32/pg32b 的ID、镜像、启动时间、运行状态前后完全一致；一次性容器已回收，
没有删除数据或候选镜像。正式四件合同及metadata候选摘要不变，current.yaml仍不存在。
BLOCKED=7914不变，Task6/Task10未完成。

Final: Ruling: 维持未提交交付而不执行技能的提交/合并/清理菜单 — 用户明令不提交推送且
工作区是指定唯一Git入口；代价是正式发布前仍需单独批准可复现Git版本。
最终评审无遗留Minor；没有重开无关JSON Schema或旧dev完整套件缺配置的已记录问题。

Task6结构切片 complete（不是完整Task6）：31项新增/519 dev单元/515候选完整+12跳过，
runtime smoke及真实单件结构、提案参考核验通过。未冻结/导入/连接PG/替换常驻/提交推送。
R-06：新审阅/执行账入索引，R-05日志更新，README/Task6/成员工作表/CBDB指针同步；
正式合同和原五文本/空间证据不覆盖，无新增待修代码缺陷。
