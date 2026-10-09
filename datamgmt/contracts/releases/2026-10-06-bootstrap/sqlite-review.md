# CBDB SQLite 结构与逻辑对象待审

> 状态：DRAFT_FOR_REVIEW｜as_of 2026-10-09｜未冻结、未导入

## 最新角色批准与三表类型观察

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
ALTNAME_CODES的c_notes仅NULL；ALTNAME_DATA为空，均不足以建立实际值类型合同。
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
