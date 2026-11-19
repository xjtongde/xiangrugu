# 全量导入包与映射进度

更新日期：2026-11-19。当前阶段为数据整理与映射，第 1–2/6 块（CBDB、普通表格）整理完成待 Codex 验收，第 3–6 块待执行。交付在本 release 的 [import-package/cbdb/](../contracts/releases/2026-10-06-bootstrap/import-package/cbdb/SUMMARY.md) 与 [import-package/tabular/](../contracts/releases/2026-10-06-bootstrap/import-package/tabular/SUMMARY.md)；CBDB 10 表/235 列源侧值验证、表格 176 件待证据单列未决，不计入映射完成，ready_for_import=False 保持。

本文件是当前阶段、六块待办、交付和讨论结论的唯一进度入口。设计约束见 [DESIGN.md](DESIGN.md)，执行权限见 [OPERATIONS.md](OPERATIONS.md)，原 Task 1–18 工程依赖见 [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md)，既往运行记录见 [PROGRESS-HISTORY.md](PROGRESS-HISTORY.md)。其他入口只链接本文件，不复制当前进度。

## 目标与范围

覆盖 NAS `192.168.3.61/workmetadata/usedata` 下的全部来源，包括 `chgis-v6`、`harvard`、`harvard-full`、嵌套归档、说明及校验文件。整理建立来源、对象、处置、目标和读取规则，不改原件、不清洗、不静默舍弃。最终在 32 形成可执行导入包，再写入 `pg32b:5433/xiangrugu` 并独立回读验收。

## 已核实的起点

| 事项 | 现状与证据边界 |
|---|---|
| 权威源 | 32 的 `/mnt/wd61workmetadata/usedata`；本会话只读确认目录存在、约 2.4 GiB，未在本次文档整理中重新计算全量摘要 |
| 已有快照 | `/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap`，约 2.4 GiB；历史已验收，当前与 NAS 是否一致须执行时核验，大小相同不构成一致性证据 |
| 清点基线 | `2026-10-06-bootstrap/inventory.json` 与 review 记录列出 189 外层文件、8,004 成员（含目录和嵌套成员）；该历史枚举有阻断 issue，须在第 6 块核销，不能宣称全量清点无缺项 |
| 全量合同 | manifest/sources/decoding/assertions 及分组候选已存在，仍为草案；7,914 BLOCKED 是 metadata 候选的历史账面值，不能直接作为当前未解决对象数量 |
| CBDB | SQLite 78 表、736 列已有类型及名称/空值政策；68/78 是该文件的源侧值验证覆盖，既非导入表数，也非整个 usedata 完成比例 |
| 其他来源 | 5 件文本、83 列有局部确认；空间清单有 705 个 Shapefile 候选组、146 个 MapInfo 候选关系；候选组数不等于已确认的导入对象数 |
| 目标实例 | 本会话只读实查 pg32b 运行于 5433，已有 cbdb、cbdb_reh 和 postgres；xiangrugu 尚未创建。数据盘约 173 GiB 可用，执行前重新核对 |
| 控制链 | 38 已接收文档分支 99817df（Codex 原作者保留）；入口工作树摘要 668900d4… 未提交改动保留；离线同代集成因人工 roots 与生产 pin 不一致 BLOCKED，产品运行验收未完成；保留成果，暂停 GO/FIFO 微修，不能计入数据整理或导入完成 |

分组事实和用户确认从 [首版合同目录](../contracts/releases/2026-10-06-bootstrap/) 追溯。既有决定直接合并，新汇总不重开已关闭的历史审查。源值期望的剩余验证与导入包映射分别登记，不因一个表尚无值摘要就隐去其已完成的结构映射。

## 六块待办

本文件描述已确认的后续工作。本轮文档通过 Gitea 文档分支 `codex/docs-six-blocks-20261119` 交付，由 DSH 通过 Git 接收；Codex 不直接改写 38/32 项目目录。工作树接收状态以各端核对回报为准。文档整理未创建导入包、数据库或新运行证据，DSH 接手先读本轮文档，不能继续按旧交接启动 p01。

| 块 | 范围 | 状态 | 本块交付 | 完成后的讨论 |
|---|---|---|---|---|
| 1 | CBDB SQLite、JSON 及配套成员 | 已验收（入库缺口另列） | 78 表/736 列映射、全部 CBDB 成员处置、未决项及确认依据 | 对象关系、类型和命名的剩余决定 |
| 2 | TSV/CSV/Excel、独立 DBF 等普通表格 | 整理完成待验收 | 文件/工作表/记录对象、编码、字段、空值及目标映射 | 编码或表格语义的未决项 |
| 3 | Shapefile、MapInfo、KML 等空间矢量 | 待执行 | 组件组、属性、几何、CRS 原声明及目标映射 | 组件缺失、坐标声明和异常保留 |
| 4 | Access/MDB、SQL 数据 | 待执行 | 内部对象及字段清单、读取/隔离方法、目标映射及不兼容项 | 不能无损读取或表达的具体对象 |
| 5 | 栅格、其他格式和非业务成员 | 待执行 | 栅格对象与入库方式；说明/图片/校验文件用途；未知件明细 | 剩余格式的处置决定 |
| 6 | 全量合并、重复关系及 32 落盘 | 待执行 | 全部成员覆盖、唯一目标命名、包清单、执行顺序、完整性报告及绝对路径 | 全量包验收、导入准备与实际执行安排 |

### 第 1 块 CBDB

- [x] 逐项归集全部 CBDB 成员，包含 JSON 与 SQLite 的关系；只在有证据时判定镜像，不按格式优先级丢弃不同内容。
- [x] 合并 `sqlite-target-mapping-proposal.draft.json`、`sqlite-target-mapping-decisions.draft.json` 及 `sqlite-review.md` 中的既有确认。
- [x] 对齐 78 表、736 列的身份、字段顺序、类型、空值、schema 与表列名；核对无重复目标名。
- [x] 输出每个对象的装载方法、独立回读方法和依赖能力；缺装载器如实标注，映射完成不能冒充程序已实现。
- [x] 列出源侧期望未覆盖的 10 表和后续验证安排，与已完成映射分别计数。
- [ ] Codex 验收新汇总，与茶香讨论后记录结论及第 2 块启动状态。

#### 第 1 块完成记录（2026-11-19，DSH 整理，待 Codex 验收）

- 交付：`import-package/cbdb/`（本 release 下）members.json、table-mapping.json（78）、field-mapping.json（736）、remaining-value-verification.json（10 表/235 列）、SUMMARY.md、build_cbdb_package.py（确定性合并脚本，重跑字节一致）。
- 成员：inventory 8004 中 CBDB 路径恰 3（目录容器、385B 出版方元数据 JSON、586,485,760B 主源 sqlite3 m007906）；JSON 经 32 只读取证为元数据描述关系，非重复载体，分别处置。
- 确认态：类型子批 type_mapping_approved=true（700 观测+36 declaration-only，后者 PROPOSED_NOT_AUTHORIZED 未升级）；命名/空值按 decisions 用户继续确认（184 禁止空/552 允许空）；proposal 顶层 flags 逐字保持 False/BLOCKED，ready_for_import=False。
- 独立核对：a03 七项全 PASS（覆盖/字段顺序全量/目标名三层唯一/basis sha 重算/配套处置/剩余 10 表三方吻合/旧文件零改动），三处口径注记见 `.cbdb-block1-20261119/a03-cross-evidence.txt`。
- Codex 验收结论：**第 1 块 Codex 已验收：3 成员、78 表、736 字段，剩余入库缺口另列**（2026-11-19 茶香转发；剩余缺口=PG 装载器/大组 10 表值验证授权/全版本命名/约束执行/36 declaration-only 列，见上未决项）。
- 未决项：①PG 生产装载器未实现（importer/load.py 仅 staging 原型且须修订，禁直跑）②大组 10 表读取需另行授权+预算修订（1GiB scratch>64MiB 执行域）③全版本命名分配未完成（naming_scope 子批）④约束执行未批准⑤36 declaration-only 列类型待授权。

### 第 2 块普通表格

- [x] 合并已确认的 5 件文本/83 列规则，清点全部其他表格及工作表。
- [x] 明确编码、分隔/引号规则、空串/NULL、单元格类型、行序与源行号。
- [x] 独立 DBF 归本块；空间组件中的 DBF 由第 3 块负责，交叉引用不重复装载。
- [ ] 形成对象和列映射、成员覆盖、已确认/未决明细，验收并讨论。

#### 第 2 块完成记录（2026-11-19，DSH 整理，待 Codex 验收）

- 交付：`import-package/tabular/`（本 release 下）members.json、object-mapping.json、handoffs.json、evidence-gaps.json、SUMMARY.md、build_tabular_package.py（确定性合并，重跑字节一致）。
- 候选 **1636**（inventory 8004 末链名大小写不敏感过滤：csv 7/xls 14/xlsx 13/dbf 704/TAB 142/tab 5/txt 751）；处置闭合 **organized 5 + handoff-block3 846 + handoff-block5 609 + pending-evidence 176 = 1636**，无重复计数。
- 5 件文本合并：权威件 text-schema-approved.draft.yaml（5 对象/83 源字段=54+5+11+7+6/5 派生 __src_rownum bigint；schema harv×4+chgis×1）；逐列对账 mismatches=0；读取规则两 decisions yaml 12 键逐字沿用（empty_string=preserve_not_null、type_inference=false、source_order=preserve）；table_names/target_mapping/ready_for_import=false 与 BLOCKED 原样保持；表名为候选，全量碰撞留第 6 块。
- **DBF 归属实测**：704/704 全有 shp/shx 兄弟组件⇒全部交块 3，**独立 DBF=0**（lead 全扫描独立证实）；approved-dbf-*-reading 仅覆盖 1884route 两诊断件（空间组件），随块 3 交接不重复认领。TAB 142（MapInfo 定义）⇒块 3。
- 核对缺陷与修复：a03 首轮揪出 1 件静默遗漏（RAS_1900_pdb2_README.TXT，大写 .TXT 未入扩展名集+名称预剔先于登记）；a02 修复（大小写不敏感+先全量登记后分类）补录 handoff-block5，1635→1636 闭合，a03 复核。
- 未决项：①176 件待证据（csv 7/xls 14/xlsx 13 无读取批准件+工作表清单缺口；txt 142 非决定性名称模式需授权后首行抽样判表性）②块 5 交接 609 件仅名称模式判定、内容未读③PG 装载器 GAP 沿用块 1④全版本命名碰撞第 6 块。

#### 第 2 块续做记录（2026-11-19 round 2，32 快照内容核实，待 Codex 验收）

- 补录 ODS 4 件（inventory 确证），candidates 1636→**1640**；Manshu .ods/.xlsx 双载体内容比对（表头/60 键集/8 列逐字同，Y1/Y2 仅 IEEE-754 序列化差异、行序不同）⇒分别处置不认重复。
- 32 项目快照（2026-10-07-bootstrap）只读核实 180 件：sha256 对账 inventory 789/789 全匹配；嵌套件 zipfile 提取到 /tmp，快照字节零接触；**未装任何依赖**（宿主仅 chardet；xlsx/ods 走 stdlib zipfile+XML 现有能力）。
- 结果：**新增提案映射 155 对象/3594 字段**（csv 7+xlsx 13+ods 3+txt 132；逐工作表+字段，naming.py 配方先精确重现权威 5 件 5/5 后采用）；确认态一律 **PROPOSED_NOT_AUTHORIZED**（schema/表名/类型/值合同未批准，类型全 text 沿用 type_inference=false）；批准 5 件 83+5 列原样不动。
- 改判块 5 共 11 件新入（10 非表格 txt 内容证据+CountryFilesFormat.ods 字段格式说明文档）+2 irregular Notes 升级内容证据；块 5 609→**620**。**首个实质阻塞：XLS 14 件 BIFF 现有工具不可读**（宿主+容器无 xlrd/转换器），逐件入 gaps（建议授权装 xlrd 或批准派生解析器），未伪报 sheet 清单。
- 终态闭合：**1640 = organized 160（批准 5+提案 155）+ block3 846 + block5 620 + pending 14**；块 3/块 5 交接项 pending_review=true 全量（846/846、620/620）；结构异常留证（NGIA csv BOM+尾空列方言、china_chron.txt 首行即数据、ChinaW.Master.Beta.csv 12 重复表头名、CHGIS v6/V4 六对字典簿行级全同保留双成员）。
- 佐证：`.tabular-probe-20261119/`（probe_out/headers/sheet_counts/carrier_compare/ods_structure 等，sha 入 basis）；a03 三轮独立核对（ROUND 2 揪出内容版未落盘缺口+SUMMARY 公式笔误，经修复 ROUND 3 复核）。

### 第 3 块空间矢量

- [ ] 将已有候选组落实到确切归档链与组件身份；缺件、大小写差异、孤立组件均有处置。
- [ ] 合并已确认的编码、属性类型、Point/几何及 SRID 规则，保留原坐标和声明，不自动投影或修几何。
- [ ] 完成属性与几何的目标映射、异常原字节保留及独立核验方法。
- [ ] 对全部空间成员覆盖核对，验收并讨论未决项。

### 第 4 块 MDB 与 SQL

- [ ] 清点所有内部表、字段、对象和重复副本关系。
- [ ] 给出 MDB 的读取和独立验证路径；SQL 采用受限解析或隔离恢复，禁止直接执行源 SQL 到目标库。
- [ ] 明确精度、二进制、编码及目标类型，不能无损表达的项目单列。
- [ ] 输出完整映射与读取依赖，验收并讨论。

### 第 5 块栅格及其他成员

- [ ] 逐件区分地理栅格、说明图片与其他格式，未知件不得归入“其他”后省略。
- [ ] 地理栅格保存尺寸、波段、像素、NoData、仿射、CRS 及每波段验证规则。
- [ ] 说明、许可、校验账和辅助材料保留原件、摘要、用途和明确处置。
- [ ] 全部剩余成员有归属，验收并讨论。

### 第 6 块合并与落盘

- [ ] 合并前五块并重新统计；核销历史清点 issue、未知件和所有未决语义。
- [ ] 全局检查源成员覆盖、组件交叉归属、目标名称冲突及镜像主从关系；用双向检查发现漏项和多余项。
- [ ] 确定 32 的版本化导入包目录，保留现有快照，不覆盖同名包；复用一致的本地源字节，差异明确留证。
- [ ] 交付 manifest、成员处置、对象/字段映射、读取与装载方法、核验依据、依赖能力和分批执行顺序。文件名和包布局在本块确定，不能把对话中的拟议路径写成已存在。
- [ ] 独立核对包内字节与来源、完整性及可追溯性，记录 32 绝对路径和实际摘要。
- [ ] 茶香讨论并验收整理包；数据库装载能力、未完成验证和全量发布门另列，准备进入导入执行阶段。

## 每块的交付与收口规则

DSH lead 收口、a02 整理最小必要产物、a03 独立只读核对，Codex 独立验收。报告标题使用“数据整理与映射｜第 N/6 块｜PASS/PARTIAL/BLOCKED”。每块报告实际数量、已确认目标、交付路径及摘要、未决问题和本轮操作；完成一块先讨论一次再推进下一块。

PASS 必须覆盖本块全部范围及处置；未决项保留 PARTIAL/BLOCKED，不能以占位规则凑完成。每条目标映射须包含源路径/归档链/对象身份、目标库/schema/表/列、类型与空值/编码/空间规则、读取和核验方法、确认依据。原始文件字节保持不动。

## 后续数据库阶段

- [ ] 整理包完成并验收后，核实标准协议装载和独立 PG 回读能力，补齐必要实现。
- [ ] 执行前报告实际目标、对象冲突、资源影响和批次；已有授权按 OPERATIONS 执行，新增范围再确认。
- [ ] 从包中分批导入 xiangrugu，每批核对结构、数量、值与重复次数；失败事务回滚，重跑不重复，失败现场保留。
- [ ] 核销全部成员、完成适用的空间/栅格验收、可重建与双演练要求后发布。六块整理完成不等于导入或发布完成。

## 讨论与变更记录

- 2026-11-19：茶香确认六块顺序，要求每次派工标明当前阶段、完成一块讨论一次；当前先整理文档，第 1 块尚未派发。
- 2026-11-19：茶香确定目标为 pg32b/xiangrugu，并要求整理全部源数据、在 32 落盘后导入；Codex 核对，DSH 执行。旧 p01 任务卡保持关闭。
- 2026-11-19：DSH 第 1/6 块 CBDB 整理完成（30 分钟盒内，lead/a02/a03 三方核对），产物与进度经 DSH 身份提交推送 Gitea；待 Codex 独立验收后与茶香讨论，再决定第 2 块派工。未写库、未部署、未改 GO/FIFO。
- 2026-11-19：DSH 第 2/6 块普通表格整理完成（30 分钟盒内）：1636 候选四路处置闭合、5 件/83 列/5 派生逐列合并零失配、DBF 704/704 全空间交块 3（独立 DBF=0）；a03 揪出 1 件大写 .TXT 静默遗漏经修复复核闭合；176 件待证据/609 件名称模式交块 5 如实单列。产物与进度经 DSH 身份提交推送 Gitea，待 Codex 验收后讨论第 3 块。未写库、未部署、未开源字节（工作表清点待授权）。
- 2026-11-19：第 2 块续做（30 分钟盒内）：ODS 4 补录、32 快照只读核实 180 件（789/789 sha 对账）、新增提案映射 155 对象/3594 字段（PROPOSED_NOT_AUTHORIZED）、11 件内容证据改判块 5、XLS 14 件依赖缺口为首个实质阻塞；终态 1640=160+846+620+14，交接待复核标记全量。第 1 块 Codex 已验收（3 成员/78 表/736 字段，剩余入库缺口另列）。第 2 块收口后再进入第 3 块。
