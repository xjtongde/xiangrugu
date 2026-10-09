# 制表文本的完整候选审阅

> 状态：五件读取、83列/五个行号映射、schema及规范值口径/源侧期望已批准；表名与完整合同未完成，处置保留 BLOCKED｜as_of 2026-10-09

## 最新五件规范值批准（非执行）

用户对上批明确提问“五件规范值口径与摘要期望，不包含表名、冻结或导入”答复“同意”。新增[text-value-contract-decisions.draft.json](text-value-contract-decisions.draft.json)，绑定原提案完整SHA-256 c86be708b7469c095ae7bd35f4751dc17d9045f353da799cda651d6af38a2189及五件原始源/对象/schema/完整流期望；批准仅为五件有序XRGVALUE-v1源侧规范值口径和期望。

[text-value-contract-approved.draft.json](text-value-contract-approved.draft.json)另存非执行批准投影，保留原提案全部数据和历史源证据身份，只增加决定引用/摘要并把value_contract_approved设为true。排除头部、一基数据行号、空串保留及不去重口径与原提案一致；规范值哈希不代替将来逐行逐列G4比较。原提案、原schema批准投影的null期望、正式合同及原证据均不覆盖。

仍不批准表名、完整目标映射、全版本分配或完整版本值合同，不冻结、不导入、不连接数据库，不重新读取源/快照。五件处置继续BLOCKED，整体BLOCKED=7,914，current不存在。导入前通知及共同决定pg32b旧数据处置的门不变。32元数据定向12与累计单元488项通过；完整dev测试仍有5项因test专属/app文件未复制而失败，没有新镜像构建或全套通过声明。批准范围TDD、机器证据及限制见[执行账批准记录](../../../../docs/superpowers/plans/2026-10-09-text-value-contract-progress.md#随后五件规范值批准记录)。以下保留提案准备时点的事实。

## 前批五件规范值合同提案（批准前）

2026-10-09用户“同意”批准整理草案与测试，不是批准规范值合同本身。新增[text-value-contract-proposal.draft.json](text-value-contract-proposal.draft.json)，只绑定既有五件源侧证据，不重新读取源/快照或数据库。

提案每件绑定原始源路径/大小/SHA-256、source_object_id、已批准schema、规范schema摘要和XRGVALUE-v1完整流期望；88个值列（83源text列与五个派生bigint行号）通过固定证据文件SHA-256及JSON Pointer引用，保留原顺序/名称/非空，不维护另一份列映射。表名不进入本草案；原批准投影的expected_sha256仍null。

建议审阅范围仅为五件的有序规范值口径及期望：排除头部、行号从1起始、空串不变NULL、保留重复行；共47,607条数据、392,573源字段及47,607派生行号字段，规范值字段共440,180。五个完整流摘要逐项见机器草案expected.sha256，不混用原始文件摘要或含头部历史字符串摘要。哈希只用于绑定/定位，不能代替将来的逐值G4比较。

草案value_contract_approved=false；表名/整体目标/全版本分配/完整值合同、冻结、导入及数据库验证均未放行。正式合同与旧证据保持原样，current不存在，BLOCKED=7,914不变。源证据原始生成时间及镜像ID原样保留，本批不声明新的G0/G4或全快照复核。测试、诊断与审阅记录见[执行账](../../../../docs/superpowers/plans/2026-10-09-text-value-contract-progress.md)。下节保留源证据生成时点的事实。

## 最新五件源侧规范值期望

2026-10-08用户“同意”批准既有文本读取器与XRGVALUE-v1衔接、合成TDD及只读复核五件精确项目快照文本。新增[非执行期望](../../../../docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json)（SHA-256 47c2401197e557be356941842d099a27db867e707682a3ef536cee2430d7ac38）绑定原始文件摘要、批准投影/读取决定、对象与列身份、规范格式及镜像ID/Git dirty状态；含每件源侧完整流摘要、计数、schema摘要和明确字段映射，不含业务值。

五件计数按“排除首条头部后的数据记录”：

| 规则 | 数据记录 | 源字段数（不含行号） |
|---|---:|---:|
| m008002 | 2,957 | 159,678 |
| m008003 | 40,199 | 200,995 |
| m008004 | 1,033 | 11,363 |
| m004812 | 29 | 203 |
| m006642 | 3,389 | 20,334 |
| 合计 | 47,607 | 392,573 |

83源列全部严格UTF-8字符串、nullable=false，空串不变NULL；五个末列行号合计47,607个bigint字段，从1起始、排除头部、保留重复业务行。前两件UTF-8-SIG是文件起始BOM策略，不是逐列codec，列仍为UTF-8；本批修复衔接中错误的codec相等检查，不修改源或批准决定。

五件原始大小/SHA-256均与证书成员及读取决定吻合；读出头部/映射/数据数与批准投影一致。独立标准库CSV逐字段与字节状态机一致，含头部历史字符串摘要未变；手写v1帧参考与新源规范流的数量/长度/摘要一致。完成后重新读取所选五件，摘要仍匹配，证书字节未变。只读本项目快照，不访问原NAS；未重读完整2.5GB快照，明确full_snapshot_verified_this_run=false，不将所选五件观察推广全量。

新期望独立存放，原text-schema-approved.draft.yaml（含expected_sha256=null）、所有旧提案及sources/decoding/assertions保持原样；不写current，不把本结果当G4数据库验收、表名批准或冻结合同。全版本命名/完整值合同和真实数据库适配器仍缺，BLOCKED=7,914、ready_for_import=false不变。实现/失败裁定/镜像验证及回传核对统一见[执行账](../../../../docs/superpowers/plans/2026-10-08-text-source-values-progress.md)。以下schema/列批准各节是前批记录。

## 最新五件schema批准

用户“同意”仅批准上批明确提问的五件schema：书院、全元文索引、传教士著述、上海演讲目录归harv，GB表归chgis。`text-schema-decisions.draft.yaml`绑定完整schema提案与列批准投影的SHA-256及五件对象身份；公开发布元数据只用于归属审阅，不替代usedata权威字节，不引入线上数据值。以下schema提案段是批准前历史。

固定runtime校验五个ObjectTarget组件模型、精确对象身份及83列/五个行号元数据未变，新增`text-schema-approved.draft.yaml`非执行投影；GB的schema提案由harv更新为本批获批的chgis，其余四件保留harv。每件明确schema_approved=true，但table_names_approved/target_mapping_approved/ready_for_import/contract_frozen仍false，expected_sha256仍null；全版本命名、规范值和正式合同未完成，不放行DDL或IMPORT。列批准及旧schema提案文件均不覆盖。

`validation-text-schema-approved.json`与`artifact-hashes-text-schema-approved.json`绑定四项产物断言，回传后累计87项核对通过。正式四份合同摘要未变，current不存在，本批不重新读源/快照、不访问数据库、不改代码依赖镜像或服务。32完整292项回归通过，dev/pg32/pg32b的ID与启动时间未变，HEAD未变且未提交推送。真实导入前通知和pg32b旧数据处置确认门保留，详见OPERATIONS对应章节。Task6未完成，BLOCKED=7,914不变。

## 最新五件列映射批准

后续schema审阅提案另存 `text-schema-proposal.draft.yaml`，2026-10-08通过公开Harvard Dataverse API核查五个数据集版本及匹配文件元数据，不下载数据件。建议前四件harv、GB表chgis：GB发布说明明确CHGIS编制；书院混合来源、全元文“为CBDB准备”均不使这些文本成为DESIGN §6的CBDB SQLite来源；上海会议演讲目录建议保留为其他Harvard文本，该分类是待用户批准的解释。公开文件名/大小与既有提案吻合但没有在线/快照逐字节同一性证明，公开MD5不是usedata权威SHA-256或G4基线；不继承任何线上值、校勘或目标名。schema/table仍未批准，旧投影不覆盖。导入前通知及pg32b旧数据处置确认门统一见OPERATIONS“首次真实导入前的用户确认门”。

用户“同意”批准既有 `text-objects-five.draft.yaml` 的83个源列名称映射、全部目标类型text及nullable=false，并批准五表各自的 `__src_rownum bigint`。空字符串保留，不推断数字、日期或NULL；行号为排除头部后一基数据记录顺序，不附带主键或唯一约束批准。决定另存 `text-column-decisions.draft.yaml`，以原提案完整SHA-256和五个对象身份/规则/列数/记录数绑定范围；旧提案不覆盖。

固定自有runtime只读已有合同证据，重新分配83个列名并核验引用、身份绑定及83个ColumnEncoding组件模型，五个行号范围和无源列名碰撞通过。`text-columns-approved.draft.yaml`保留全部原对象/源观察/目标提案，仅添加明确列级批准标记；schema/table/整体target_mapping均保持未批准，expected_sha256仍为null。它是非执行sidecar，不是完整ReleaseContract Schema验证、DDL、冻结或IMPORT入口；全版本命名和规范值合同尚未完成。

`validation-text-columns-approved.json`及`artifact-hashes-text-columns-approved.json`绑定决定/投影/报告，三项新断言及累计83项历史产物断言回传核对通过；正式四份合同摘要不变，current仍不存在。一次性脚本先因误用NameMap.target_name退出、未产出；核对源码后只修正为target并重跑通过，不修改产品API。本批没有源/快照重新读取或G0/G4验收，不读NAS、不连接数据库、不改代码依赖镜像或重启服务。32主机完整292项测试通过，dev/pg32/pg32b容器ID与启动时间不变；Task6未完成，BLOCKED=7,914不变。以下为前批历史证据。

## 最新批准与五件对象提案

用户对下述两件精确解释答复“同意，继续”；批准保存于 `additional-text-reading-decisions.draft.yaml`，只覆盖 m004812/m006642 的原路径、大小、SHA-256 和读取解释。严格 UTF-8、无起始 BOM、LF/TAB、双引号语法及 doublequote=true；上海索引启用反斜杠转义，GB 表不启用。原三件决定文件保持不变，业务类型、目标映射、冻结与导入不在这次批准范围。

固定 runtime 按新决定重读两件源，独立字节路径与标准库 csv 逐字段比较：上海 210、GB 表 20,340 个字段（含头部）零差异，数量及辅助值摘要与前批成功候选一致。报告 `additional-independent-text-reading.json` 绑定决定与候选证据的文件摘要。两路径共享 UTF-8 解码器，分列一致不等于编码唯一性或数据库 G4 验收。

`text-objects-five.draft.yaml` 合并保留旧三件提案，新增两件/13 列，合计 5 对象/83 个源列；旧 `text-objects.draft.yaml` 不覆盖。新增对象采用完整文件 basename，carrier=tsv，namespace 暂取原父路径，所有身份和名称由现有 API 生成；五件范围顺序反转分配一致，旧三件目标名未变。新增对象的 `harv` 只是 Harvard 来源的暂定分组提案，不据目录断言数据领域；最终 schema（尤其 GB 表是否属于 chgis）还须依据来源说明审阅。

新增 13 列保留原头部与序号、列身份、严格 UTF-8、空串统计、最大字符/字节数及名称引用形式；类型暂提 text，nullable=false 只表示本次读取没有 NULL，不解释业务缺失。派生 `__src_rownum` 从 1 起始，不计入 83 个源列。expected_count 使用批准解释下的数据条数，expected_sha256 仍为 null；全版本名称分配、类型/schema/目标批准、正式值规范未完成，五件目标名均不可冻结。

`validation-text-objects-five.json` 是 83 个编码与 5 个目标的现有组件模型校验，不是完整 sidecar 的 JSON Schema 或 frozen 合同验证；未知 codec/public schema 负向检查拒绝。BLOCKED 规则仍不携带业务 targets，正式 metadata 合同摘要未变。全快照前后验证通过，新增文件由 `artifact-hashes-text-five.json` 绑定并回传核对；262 项回归通过。没有代码、依赖或镜像变化，没有读取 NAS、连接数据库或重启既有容器。

Ruling：复用通用读取 API，五件合并提案不冒充全版本分配；如果 schema/类型/命名提案后续被否决，只修订新版本提案，不改已批准源读取值。Task 6 未完成，BLOCKED=7,914 不变。

## 前批两件文本候选：批准前证据

用户令继续后，在固定自有 runtime 对空间审阅发现的两件外层 TAB 进行完整候选比较；新增 `additional-text-candidates.json` 和 `additional-text-escape-observations.json`，不覆盖前三件证据，不扩大其读取批准范围。

| 规则/原文件 | 源字节 | 双引号语法候选的完整结果 | 待批准读取提案 |
|---|---|---|---|
| m004812，`harvard-full/doi_10_7910/DVN/MI56KU/2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab` | 3,727 字节；SHA-256 `cdc6d3e5d6d85e139305efe9c617c756f0eb668c19ce34efc4eca4f6cc8c2728` | 不启用反斜杠时标准库在第 22 物理行失败，独立字节路径拒绝偏移 2732；启用后 30 条含头部记录、7 列、29 条数据 | 严格 UTF-8、TAB 分列、双引号语法、doublequote=true、反斜杠转义 |
| m006642，`harvard-full/doi_10_7910/DVN/SK7KGK/GB_91_HZ_040201_UTF8.tab` | 137,961 字节；SHA-256 `58ef3cb445ef4b0e70a8716aad3463915320c64ee7fa257ea88eb0c93fe1cec0` | 双引号语法完成 3,390 条含头部记录、6 列、3,389 条数据；反斜杠策略在本件无值差异 | 严格 UTF-8、TAB 分列、双引号语法、doublequote=true、不启用反斜杠转义 |

两件都无起始 BOM、NUL、CR 或空物理行，均以 LF 终止；保持所有值为字符串、空字符串不变，不推断数字/日期/NULL，不裁列或去重。上海索引的两个反斜杠原字节偏移为 2730、3491，分别在第 22、28 物理行的第 6 物理 TAB 列，下一字节均为双引号。字节邻接事实不是发布方方言声明，但解释了候选差异。

字面保留双引号也能得到相同行列数，却分别与成功引号语法候选产生 203、6,778 个字段差异。因此不能以行列数正确或 UTF-8 可解码证明读取解释唯一正确；以上只是待用户批准的提案。原失败候选只记录成功前缀，不给出整件值摘要或把前缀数当总行数。

在成功候选解释下，既有独立字节状态机与标准库 csv 路径直接从源字节逐记录逐字段比较，上海 210、GB 表 20,340 个字段（含头部）零差异；GB 表同时比较无/有反斜杠两候选。两路径共享 Python UTF-8 解码器，证明的是分列实现一致，不是编码唯一性、正式 G4 或目标库验收。辅助摘要仍采用有序紧凑 ASCII JSON 行数组加 LF，不能作为正式库值断言。

全快照读取前后均与既有完成证书一致；没有重新读取 NAS。两份 `artifact-hashes-additional-text*.json` 绑定新增报告，回传 Windows 后核对 SHA-256。复用固定镜像和 API，无产品代码、依赖或镜像变化；262 项回归通过。Ruling：不将候选成功自动视作读取批准；若解释被否决，本批数量/值结果仅为该解释的历史观察，需重新核验。两件仍 BLOCKED，未建立新对象/类型/目标映射，不改 sources/decoding、不冻结或操作数据库。

## 前批三件对象及列级提案

新增 `text-objects.draft.yaml`（JSON 形式的 YAML 子集）只供合同准备，不是 ReleaseContract 或自动执行入口。每件 TSV 作为一个无内部表名的逻辑表，以**完整外层文件 basename（含 .tab）**作为对象名约定；原路径、完整原名、大小/摘要、读取批准规则及源对象身份均保留。该约定不把文件名当作发布方声明的内部表名，也不合并跨载体对象。

三个 source_object_id 使用既有 v1 身份 API，carrier 明确为 `tsv`。目标 namespace 暂提议为原父路径 `harvard/tab`，schema 提议为 DESIGN §6 的 `harv`，表名由既有命名 API 分配，不手写短名。三件范围内顺序无关且不碰撞；完整 release 的对象还未齐备，**全版本批次碰撞分配尚未完成，目标名不可冻结**。完整原名/身份/目标名映射见机器提案，其他来源的同名对象出现后须重新进行全量分配。

70 个源列全部按原序号登记：ACADEMY 54、元代索引 5、传教士著述 11。每列保存原头部名、稳定列身份、目标名与引用形式、严格 UTF-8、空串数以及最大读出字符/UTF-8 字节数；文件起始 BOM 的解释与列值解码分开记录。列名映射只是目标标识符处理，不改变源头部证据或业务值。

没有擅自从数字/日期样式字符串反推源类型；70 列的目标类型均为**未批准的 text 提案**。空字符串保留为字符串而非 NULL，列不补值、裁列或去重；nullable=false 也只是“此严格读取结果没有 NULL”的目标约束提案，不解释业务缺失含义。另每表拟增加 `__src_rownum bigint`，为不含头部的数据记录从 1 起始的派生顺序标记，不计入 70 个源列；已检查不与源列目标名碰撞。

proposed_target 的 expected_count 引用已独立复核的源数据记录数；expected_sha256 留为 null。早期有序字符串摘要含头部，格式已留证，但不能无声明地变成未来目标库 G4 规范摘要。通用值比较/规范化合同、正式逐列类型审阅及目标映射批准仍待完成。

`validation-text-objects.json` 证明 70 个 ColumnEncoding 与 3 个 ObjectTarget 分别由现有模型校验，顺序反转命名一致、三件目标不碰撞；在内存中构造非法 codec、public schema 均被拒绝。这不是独立 JSON Schema 校验，也不是验证整个 sidecar 是 frozen 合同。原 metadata 合同摘要保持不变，处置仍 8,004 唯一匹配、BLOCKED=7,914、incomplete_inventory 阻断、ready_for_import=false。BLOCKED 规则不能携带业务 targets，因此没有放宽模型或把这些提案塞入已阻断规则。

本批复用现有自有 runtime 和身份/命名/模型/源读取 API；没有改产品代码、依赖或镜像。重新读取三件源与之前逐字段证据的头部、数量及辅助摘要一致，源摘要和全快照前后核验通过。`artifact-hashes-text-objects.json` 绑定对象提案及验证报告，回传 Windows 后逐份核验通过；旧证据不覆盖。后续继续按成员组件关系补齐其他对象；本提案没有冻结、导入或数据库操作授权。

## 当前批准与独立读取结果

用户在上述提案后答复“同意，继续”，批准三件的 BOM/双引号解释，并仅对 ACADEMY 启用反斜杠转义。精确路径、原字节大小/摘要及解释另存 `text-reading-decisions.draft.yaml`；批准范围是源读取，不是冻结、目标映射或导入。正式 sources/decoding 和 metadata 合同均未改。

新增通用 `source_text.read_utf8_tsv` 直接以字节状态机分列，不调用 csv、旧 truth 读取器或 importer；分别严格 UTF-8 解码字段，保留空字符串、源顺序、重复记录、重复/空列名及位置。文件起始 BOM 只在显式策略允许时作为签名，内部 U+FEFF 保留。该 API 仅支持明确的 LF/UTF-8/TAB 方言，不声称覆盖混合编码、CRLF、Excel 或任意 CSV；未知或坏语法、宽度不一致与预算超限明确拒绝，没有自动探测或回退。

API 在整件检查通过前不返回成功结果；输入预算 16 MiB、100,000 条含头部记录、512 列、每个读出字段 1 MiB 字节，完整结果受输入及预算限制驻留内存，不冒充流式装载器。错误保留原始零基字节偏移，已知时提供一基逻辑记录/列位置；不输出业务值到错误消息。

31 项手工推导期望的合成测试先因 API 缺失失败，再全部通过；重建 dev/test/runtime 后，全套 262 项及镜像契约通过。新 runtime 为 `sha256:f67768cf44dfbdd183766d5828404a8905932912b720a3cd8f7098f1feb38b00`，Git HEAD 不变、source_status=dirty。代码进入自有镜像；真实核验没有挂载源码，不重启既有长期容器。旧 runtime 的下列观察保留为历史证据。

`independent-text-reading.json` 绑定批准决定文件、最新 metadata 合同和清单摘要。新的独立字节路径与标准库 csv 路径均直接读取同一只读源字节，按已批准解释逐记录逐字段比较，不仅比较摘要：

| 规则 | 数据记录（不含头部） | 列数 | 比较字段（含头部） | 差异 |
|---|---:|---:|---:|---:|
| m008002 | 2,957 | 54 | 159,732 | 0 |
| m008003 | 40,199 | 5 | 201,000 | 0 |
| m008004 | 1,033 | 11 | 11,374 | 0 |

报告逐列保留字段名、序号、严格 UTF-8 和空串等观察；按源顺序的字符串摘要作为辅助证据，三件均与此前对应候选摘要一致。读取前后的原字节摘要及全快照独立校验通过。`artifact-hashes-independent-text-reading.json` 绑定报告和决定文件，回传 Windows 后逐份摘要核验通过，旧报告不覆盖。

这是两种分列实现的独立源复核，UTF-8 解码仍使用 Python 解码器；不是目标库逐值验收，也不宣称对源语义的全知证明。后续逻辑对象及目标名称/类型提案见上文，仍未冻结；通用比较器、加载器或数据库证书尚未建立。三件与整个最新候选的处置均不改变。发现未获批准的解释差异仍须 BLOCKED。

## 早期候选观察的范围与证据

早期候选批次只读已验收项目快照 `2026-10-07-bootstrap` 的三件精确外层成员，不读取原 NAS、不写源、不打开数据库。使用固定自有 runtime `sha256:64f006e4361d14f704ef83ef5ff45e732a1368442f44791412187ad027c7dea4` 中的 Python 标准库；当时未新增产品读取器、依赖或镜像，后续实现及新 digest 见上文。

`full-text-candidate-observations.json` 比较严格 UTF-8 / UTF-8-SIG 与双引号转义 / 引号普通字符四种组合，保留各列观察、失败位置和资源限制。`text-escape-candidate-observations.json` 在查明转义字节后，单独检查明确的反斜杠转义候选，并绑定前一报告摘要。两份报告及对应 `artifact-hashes-full-text-candidates.json`、`artifact-hashes-text-escape-candidates.json` 已回传 Windows 校验；它们是诊断证据，不是可执行合同或独立 G4 真值。

全文报告绑定原清单摘要 `fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db`、最新 metadata 候选的规范合同摘要 `0b98f0078dd3d2756984881610df67a5a937fa1b93005ecf99fba66f6626422c`。快照前后独立核验与原完成证书一致，清单摘要为 `03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699`；三件完整大小和原字节摘要均与合同一致。

## 已确认观察

以下数量是候选解析观测值，不是冻结合同断言。记录数包括第一条头部；“数据记录”仅在第一条被批准为头部时成立，不能把物理行数直接当作业务行数。

| 精确规则与 harvard/tab/ 下原名 | 原字节大小 | UTF-8 BOM | 候选列数 | 含头部记录 | 条件数据记录 |
|---|---:|---|---:|---:|---:|
| m008002 / ACADEMY_Data.tab | 714,962 B | 有 | 54 | 2,958 | 2,957 |
| m008003 / Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab | 2,619,410 B | 有 | 5 | 40,200 | 40,199 |
| m008004 / writings of the 19c missionaries in China.tab | 193,811 B | 无 | 11 | 1,034 | 1,033 |

三件全文严格 UTF-8 解码成功；NUL 为 0，换行均为 LF，文件以 LF 结束，无 CRLF 或孤立 CR。完整成功的候选中没有宽度不匹配、空白记录或跨物理行记录。成功候选的头部没有重复或空字段名。上述事实只覆盖这三件精确摘要，不能推广到其他文本、包内同名件或列级编码合同。

### 引号解释不能由计数决定

只启用双引号转义、不启用反斜杠转义时，ACADEMY 在第 214 物理行报告 `'\t' expected after '"'`，只解析了 213 条前缀记录；报告将总数、条件数据数和值摘要置为 null，没有把前缀数量冒充全文数量。

字节检查发现 ACADEMY 恰有 12 个反斜杠，全部是 `\"` 字节对，分别位于第 214、281、283、400、453、528 物理行的第 53 个原始 TAB 分段字段，各两处。没有字面 `\t` 或 `\n` 字节对；另两件没有反斜杠。具体字节位置见转义报告。本观察不裁定源数据“错误”，也不改这些字节。

单独设置 `escapechar` 为反斜杠、`quotechar` 为双引号、`doublequote=true`、`strict=true`、`skipinitialspace=false`、`newline=""` 后，三件均完整解析且宽度一致。另两件在无反斜杠转义时也能完整解析，但“引号是语法”和“引号是普通字符”得到的值摘要不同，即使行列数相同。禁止自动尝试宽松模式直到成功并把成功当作格式证明。

Python CSV 各参数的语法含义见 [Python 3.11 官方 CSV 文档](https://docs.python.org/3.11/library/csv.html)。官方参数说明并不证明这些源件采用哪一种方言；源件实际导出方言仍须来源证明或明确审阅。通用 Dataverse ingest 文档也不能直接证明下载 TAB 的导出语义。

### BOM 与候选值摘要

`utf-8` 保留头部首字符 U+FEFF，`utf-8-sig` 将文件起始 BOM 解释为编码签名；这会改变前两件候选头部和值摘要。不能静默移除头部字符并称为源名原样保留。原字节、BOM 位置、原头部和读出字段名须可分别追溯。

报告的值摘要采用源顺序、字符串字段数组的 ASCII 紧凑 JSON 加 LF，并包含头部；不做类型推断、去重或清洗。它用于比较候选解释，不是数据库值摘要，也不是由独立读取器证明的预期值，不能直接填入正式 expected_values_sha256。

## 上轮语义提案（本轮已批准读取解释）

以下提案已获本轮用户确认，精确读取批准记录见上文；尚未写入 sources/decoding 对象合同，不改变任何处置：

1. 三件以第一条逻辑记录为头部、TAB 为字段分隔符、双引号为包围符、成对双引号为引号转义；ACADEMY 另明确允许反斜杠转义，其他两件不启用反斜杠转义，不自动回退到字面引号模式。
2. 前两件把文件起始 UTF-8 BOM 解释为编码签名，使用 UTF-8-SIG；第三件使用严格 UTF-8。保留原始字节与含 BOM 的原头部证据，逐列填写并验证解码合同，不使用替换字符。
3. 现阶段全部字段保留为字符串；空字符串不自动变 NULL，不裁剪空白、不推断数字/日期、不去重。原记录顺序及源列序号保留，类型与目标映射另行审阅。

用户确认只批准上述读取解释，不等于批准冻结或导入。本轮已按 TDD 建立受限源读取能力并逐字段复核这三件；后续仍须审阅逻辑对象及目标映射，不能把早期标准库诊断输出单独当作独立验收器。若发现无法证明的解释差异，继续 BLOCKED 并留证，而非修源或静默清洗。

Task 6 仍未完成，最新候选 BLOCKED=7,914、ready_for_import=false。校验账严格异常、参考件保存验证器及独立 JSON Schema 验证缺口均未解除；未创建 current、未冻结、未提交或推送。
