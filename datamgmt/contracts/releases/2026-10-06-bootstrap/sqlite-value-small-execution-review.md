# SQLite小组真实执行准备审阅

状态：待审、不可执行。2026-10-10用户要求继续，人工控制层已验证，本轮只从Windows仓库内已有合同、历史统计和代码整理后续精确范围；未打开NAS或真实快照、未读取真实SQLite值。没有改产品代码、运行项目Python或Docker负载、构建候选或连接数据库。HEAD仍为8fbc8c97fcf1d818caddf6ab556fa82d986643ed，既有未提交成果保留。

[机器待审清单](sqlite-value-small-execution-review.draft.json)完整列出55表、326列的对象身份、源列顺序、类型/空值保留描述、结构摘要、逐表读/排序预算与历史统计来源。它排除已有期望的3表和剩余10个中表、10个大表；沿用原剩余预算中的小组顺序。12,260行/76,392单元只是历史完整统计参考，expected_count/expected_sha256仍为空，不冒充新源侧答案。

## 范围与预算

后续如果另获读取授权，只消费项目配置指向的版本化快照中同一SQLite成员，不访问NAS。成员身份来自既有预算：snapshot_id=2026-10-07-bootstrap、relative_path=harvard/cbdb/cbdb_20260919.sqlite3、586,485,760字节；成员摘要与所有材料摘要见机器清单。本轮未复核实际快照或文件是否仍存在、只读或静止；证书/清单、执行请求/批准、实际执行候选摘要和无写入者窗口仍待正式选择。

每表上限沿用小组预算：4,000行、50,000单元、64列、单元1MiB、读取原生值8MiB、读取VM步数20,000,000、读取300秒；排序流8MiB、块2MiB、临时字节64MiB、300秒、单worker。每项都在机器清单展开，包括当前排序器要求的max_differences=100。历史参考没有超过这些上限，但这不是未来峰值或耗时保证。

受限候选继续半个逻辑CPU、768MiB、memory-swap同值（候选swap不可用）、pids128、无网络、根和输入只读、64MiB scratch tmpfs与32MiB /tmp tmpfs；只运行一项，压力和服务异常阈值完全沿用资源修订草案。既有宿主换出来源仍未知；容器swap=0不能保证宿主无交换。

## 需要先解决的执行接线

当前人工控制器硬拒绝project_snapshot；宿主包装仅消费固定人工fixture。当前候选外层300秒、宿主330秒、SSH传输380秒，不能拿它作为真实小组1800秒执行器。

待审接线采用既有小组1800秒预算作为**整个候选生命周期**上限，覆盖元数据预检、全快照校验、SQLite批前后摘要、逐表读取/排序、暂存与末端新宿主采样发布。候选1800秒、宿主强制停止兜底1830秒、SSH等待1880秒，保留原30秒/80秒清理余量关系；不是实测耗时预测，也没有在本轮激活。源批级计时目前在全快照验证之后启动，其内部1800秒不能作为额外延长时段，始终受外层总截止约束。

租约25秒、10秒宿主采样、2秒SSH心跳/15秒控制失联保持原设计。全快照验证目前没有内部取消回调，因此外层必须能在校验阶段取消并有限TERM/KILL回收精确进程组；完整源结果不等于发布。截止或末端新采样失败必须保留失败证据且无final，不增加预算或自动重试。

后续接线先用人工文件做失败测试与完整回归，包括：请求/预算身份与外层截止绑定；预检/全快照校验/读取/排序/暂存/等待新采样各阶段取消；候选/宿主/SSH截止一致；实际资源限制与服务身份检查；真实模式仍受独立授权门约束。人工故障使用缩短的截止验证，不以30分钟空等待冒充真实负载验证。后续代码与候选镜像将形成新一批成果；不重复审已完成核心。

小组计划的摘要逻辑读取为3,681,959,248字节：一次完整快照2,508,987,728字节，加SQLite两次共1,172,971,520字节；业务查询/排序I/O另计，不是实际SSD流量或本轮执行结果，未采用旧95GB方式。

## 本轮核对与门槛

机器核对确认：原75表集合等于78表结构准备减去既有3表；小组55对象身份/名字唯一；每列ordinal/column_key/类型与原映射一致，共326列；全部历史统计参考在预算内；原预算6项依赖摘要和小组每个引用统计文件摘要匹配。原始验证与跨机一致性见[准备证据](../../../../docs/superpowers/evidence/2026-10-10-sqlite-small-review-preparation/README.md)。这些是文档/元数据核对，不是新一轮产品测试。

此清单不是readonly_batch请求、scope批准文件或APPROVED_READONLY_BATCH，所有授权/冻结/导入位均为false，不能直接提交给入口执行。下一阶段须先确认这里的精确范围、整个生命周期截止及宿主包装接线；实现仍先用人工数据验证。真实源读取另获明确授权并确认无写入者窗口，任何数据库写入前仍通知茶香并确认pg32b原数据处置。

中/大组、磁盘临时区、数据库状态机及Task8整体未完成，B-16/B-17不在本轮修复。已有人工候选成功证据和前轮swap_pressure失败证据均保持历史事实，现行镜像别名与常驻服务不变。

## 精确55表（以下行数仅历史参考）

| 顺序 | 源表 | 历史行数参考 | 列数 |
|---|---|---:|---:|
| 1 | POSSESSION_DATA | 60 | 20 |
| 2 | POSSESSION_ADDR | 62 | 3 |
| 3 | POSSESSION_ACT_CODES | 4 | 3 |
| 4 | PARENTAL_STATUS_CODES | 7 | 3 |
| 5 | OFFICE_TYPE_TREE | 2742 | 4 |
| 6 | OFFICE_CATEGORIES | 15 | 4 |
| 7 | OCCASION_CODES | 10 | 4 |
| 8 | NIAN_HAO | 682 | 7 |
| 9 | MEASURE_CODES | 7 | 3 |
| 10 | LITERARYGENRE_CODES | 12 | 4 |
| 11 | KIN_MOURNING_STEPS | 159 | 5 |
| 12 | KIN_MOURNING | 159 | 10 |
| 13 | SCHOLARLYTOPIC_CODES | 32 | 7 |
| 14 | TEXT_ROLE_CODES | 12 | 3 |
| 15 | TEXT_BIBLCAT_TYPES | 51 | 6 |
| 16 | TEXT_BIBLCAT_CODE_TYPE_REL | 144 | 2 |
| 17 | TEXT_BIBLCAT_CODES | 144 | 7 |
| 18 | STATUS_TYPES | 14 | 4 |
| 19 | STATUS_CODE_TYPE_REL | 285 | 2 |
| 20 | STATUS_CODES | 285 | 3 |
| 21 | SOCIAL_INSTITUTION_TYPES | 7 | 3 |
| 22 | SOCIAL_INSTITUTION_NAME_CODES | 2603 | 3 |
| 23 | SOCIAL_INSTITUTION_ALTNAME_DATA | 0 | 8 |
| 24 | SOCIAL_INSTITUTION_ADDR_TYPES | 2 | 4 |
| 25 | TEXT_TYPE | 126 | 6 |
| 26 | KINSHIP_CODES | 488 | 13 |
| 27 | INDEXYEAR_TYPE_CODES | 31 | 4 |
| 28 | BIOG_ADDR_CODES | 22 | 6 |
| 29 | ASSUME_OFFICE_CODES | 6 | 3 |
| 30 | ASSOC_TYPES | 45 | 7 |
| 31 | ASSOC_CODE_TYPE_REL | 463 | 2 |
| 32 | ASSOC_CODES | 498 | 8 |
| 33 | APPOINTMENT_TYPES | 13 | 3 |
| 34 | APPOINTMENT_CODE_TYPE_REL | 109 | 2 |
| 35 | APPOINTMENT_CODES | 116 | 6 |
| 36 | ALTNAME_CODES | 21 | 3 |
| 37 | ADMIN_CAT_CODE_TYPE_REL | 0 | 2 |
| 38 | ADMIN_CAT_CODES | 213 | 5 |
| 39 | BIOG_INST_CODES | 26 | 4 |
| 40 | KINREL_REDUCTION | 8 | 10 |
| 41 | BIOG_INST_DATA | 571 | 19 |
| 42 | HOUSEHOLD_STATUS_CODES | 34 | 3 |
| 43 | GANZHI_CODES | 61 | 3 |
| 44 | EXTANT_CODES | 4 | 3 |
| 45 | EVENT_CODES | 117 | 20 |
| 46 | EVENTS_DATA | 427 | 21 |
| 47 | EVENTS_ADDR | 4 | 12 |
| 48 | ETHNICITY_TRIBE_CODES | 498 | 11 |
| 49 | ENTRY_TYPES | 29 | 6 |
| 50 | ENTRY_CODE_TYPE_REL | 284 | 2 |
| 51 | ENTRY_CODES | 273 | 3 |
| 52 | DYNASTIES | 85 | 6 |
| 53 | COUNTRY_CODES | 11 | 3 |
| 54 | CHORONYM_CODES | 173 | 3 |
| 55 | YEAR_RANGE_CODES | 6 | 5 |
