# 首版 usedata 合同草案审阅

> 状态：DRAFT_BLOCKED，修复后模型通过，导入门未通过；未冻结、未批准｜as_of 2026-10-07

最新审阅候选为 `sources-metadata-review.draft.yaml`：在不改源位置或原字节断言的前提下，将三本校验账和 DESIGN 明确规定的一件 Thumbs.db 登记为 NON_TABULAR，BLOCKED=7,914、conforms=false。原 `sources.yaml` 及下列初稿数字是历史基线，未覆盖；逐件依据、物理分组口径和接续顺序见 `member-review.md`。候选不是自动执行入口，不启用校验账例外。

## 本轮结论

2026-10-08随后用户单独授权仅dev晋级，旧镜像导出/可运行确认后已重建，
真实watcher476项及pip check通过，B-15恢复；完整部署和自动重测证据
统一见JSON Schema执行账dev晋级节。未读取源/快照、操作数据库或导入，
BLOCKED=7,914及冻结门不变。以下保留上批候选尚未部署时的事实。

2026-10-08 独立JSON Schema校验完成：锁定jsonschema 4.26.0及必要依赖，
静态Schema自校验、与模型导出相等，以及两份原始sources文档的独立结构/模型校验通过，
摘要不变；sources.yaml仍BLOCKED=7,918，metadata候选仍BLOCKED=7,914。
最终候选484项、三目标pip check及runtime smoke通过。未访问真实源/快照或数据库，
未冻结、未替换长期容器、未提交推送；ready_for_import/conforms=false。
证据入口为docs/superpowers/plans/2026-10-08-json-schema-progress.md。
旧dev缺新增依赖，watcher收集失败（B-15），不等于开发环境晋级完成。
下列初稿“未执行Schema”结论保留为历史时点，不覆盖旧证据。

2026-10-08 两组SRID4326已逐案批准，原X/Y保持、PRJ/QPJ轴序差异留证；决定绑定精确诊断/几何投影，批准投影与核验集中见spatial-review.md最新节。2对象/4声明及292回归通过，无新源读取，正式合同/BLOCKED不变；表名/规范值、生产读取器、冻结未完成。以下为前批历史。

2026-10-08 授权export/import救急回退已核验，tar/镜像留存；仅dev更新，完整292及真实watcher284测试通过，pg32/pg32b前后状态一致，B-14部署阻断解除。事实与边界统一见spatial-review.md最新节；SRID/冻结未批准，正式合同及BLOCKED不变。以下为前批历史。

2026-10-08 离线CRS工具及三镜像/292测试已验证，既有声明匹配4326但PRJ/QPJ轴序不同；SRID未批准。旧dev回退镜像不可寻址，未替换常驻容器，B-14待备份授权；事实与接续统一见spatial-review.md最新节。正式合同/处置未改变，无新源读取或冻结。以下为前批记录。

2026-10-08 两组二维Point/geom映射已批准，决定及批准投影见 `spatial-review.md` 最新节；SRID仍未批准。runtime实测缺少CRS工具，离线pyproj核验方案已列为待授权操作，尚未安装或重建镜像。本轮无新源读取，正式合同/BLOCKED不变。以下为前批记录。

2026-10-08 两组24属性列及派生物理行号整体映射已批准；决定、批准投影及二维Point几何提案统一见 `spatial-review.md` 最新节。本轮只核验既有证据及118个坐标对报告字节，没有新源/快照校验；几何/CRS、表名及完整合同未完成，正式BLOCKED不变。以下为前批记录。

2026-10-08 两组chgis归属已按用户“同意，继续”批准，schema决定及24属性列整体提案见 `spatial-review.md` 最新节。仅处理既有证据、重核身份/映射与组件模型，未重新读取快照；正式合同和BLOCKED不变。属性/派生行号及几何/表名仍待批准。以下为前批记录。

2026-10-08 最新12组件绑定已批准并复核，同包README/HTML来源说明已留证；依据CHGIS来源将schema修订为chgis提案，尚未批准目标映射。决定、来源字节及新提案统一见 `spatial-review.md` 最新节；不改变正式合同或BLOCKED。以下为前批记录，不表示当前批准状态。

2026-10-08 最新两组空间对象/12组件/24属性列及目标映射提案见 `spatial-review.md` 最新节与 `spatial-objects-canary.draft.yaml`。QPJ原文新增留证，包内其余4成员不遗漏；组件绑定及目标/空间合同未批准，不改变正式合同或BLOCKED。

最新两件DBF五个N字段读取/类型已获批准并完成590值精确源复核，同时重核826个C值，决定与证据集中于 `spatial-review.md` 最新节。对象绑定/映射、正式独立读取器、空间合同及冻结仍未批准或完成，处置不变。

两组 canary 的最新全 N 字段/填充候选与 Point 原坐标观察见 `spatial-review.md` 最新节及 `dbf-numeric-point-observations.json`；590个N字段候选及每组59个点全量留证，不自动批准数值类型、去填充、CRS或空间合同，原BLOCKED保留。

最新两件 DBF 的14个字符列编码已获用户批准，固定宽度原字节及字符串双路径复核见 `spatial-review.md` 最新节与 `approved-dbf-character-reading.json`；不剥填充、不批准数值/几何/CRS或 MIRROR，处置保持 BLOCKED。前批 `shapefile-canary-observations.json` 保留，不回写。

新增两件制表文本的读取解释已获批准并重新逐字段源复核，五件/83 列合并对象提案及完整证据集中于 `text-review.md` 最新节。原候选和三件对象证据保留；不改变正式合同或 BLOCKED，目标映射与冻结未批准。

后续空间未决位置字节核验见 `spatial-review.md` 最新节及 `spatial-exception-observations.json`：9 个物理归档摘要/中央目录匹配，1 DBF/3 PRJ 在对应归档中确实无同后缀成员；两件 Native TAB 的字符集/字段声明及两件新增制表文本头部、CPG 原文已留证。仅观察，不自动绑定大小写组件、扩展读取批准或更改处置；快照前后核验通过。

最新空间组件清单级关系候选见 `spatial-review.md` 和 `spatial-component-candidates.json`：705 个 Shapefile 候选组、146 个 TAB/MapInfo 关系组；核心组件/PRJ未找到、大小写差异及未配对件按精确位置留证。仅凭清单，不声称已经读取源字节、证明格式、批准绑定或通过源未变门；原合同与 BLOCKED 数量不变。

最新三件文本的逻辑对象、70 个列级声明及目标名称/类型提案另存 `text-objects.draft.yaml`，详见 `text-review.md`；只使用既有 API，不放宽 BLOCKED 规则的 targets 限制。现有模型校验和三件范围命名检查通过，但完整 release 命名、正式规范值摘要、类型/映射批准仍未完成，处置及导入门不变。

后续三件制表文本全文候选及最新独立源复核见 `text-review.md`：读取解释已获用户批准，新字节路径与标准库路径逐字段比较差异为零。两份早期观察及新复核证据各自保留；没有冻结逻辑对象或目标库验收，不改变最新 metadata 合同或 BLOCKED 数量。原头部与清点证据不覆盖。

已在固定 digest 的自有镜像内只读清点已验收项目快照，并保留全部物理成员。初稿被模型拒绝；经另行授权修复字面选择器后，模型已通过，8,004 个成员全部精确匹配，但 BLOCKED=7,918、conforms=false，仍禁止导入。原生成文件与摘要保留不覆盖，新结果见 `validation-after-selector-fix.json` 和 `disposition-ledger-after-selector-fix.json`。

| 项目 | 本轮机器证据 |
|---|---|
| release_id | `2026-10-06-bootstrap`（按执行计划） |
| snapshot_id | `2026-10-07-bootstrap`（不等同于 release_id） |
| 范围 | 189 个外层文件、43 个外层子目录，以及可枚举的全部嵌套归档成员 |
| 清单成员 | 8,004：文件 7,918、目录 86；嵌套深度 0/1/2 分别 232/3,879/3,893 |
| 清点完整门 | `complete=false`；三个阻断 issue |
| 校验账断言 | 191 条，190 条匹配；按各校验账声明的目录基准解析 |
| 草案规则 | 8,004 条精确候选规则；文件暂为 BLOCKED，结构目录为 NON_TABULAR |
| 合同模型 | 初稿拒绝 13 个字面名；修复后模型通过，精确匹配 8,004/8,004，零未匹配/多匹配/失效断言；导入门不通过 |
| JSON Schema | 初稿时未执行独立校验；2026-10-08新增锁定验证器与原始文档核验，最新报告见上述执行账；不等于导入门通过 |
| 对象/编码/值断言 | 未独立建立，不猜测目标、字段、编码或计数；保持 BLOCKED |
| 镜像/去重 | 仅保存同 SHA-256/大小候选，未证明实际字节全等，未指定 IMPORT 主成员或 MIRROR |

`sources.yaml` 是 JSON 形式的 YAML 1.2 子集候选文档，包含所有规则；修复后可通过模型，但仍是未批准的 BLOCKED 草案。`manifest.yaml` 保存完整原始清单和候选处置；`decoding.yaml` 显式保存未决规则，不给未知列填写猜测编码；`assertions.yaml` 保存初稿时的原始校验账断言及冲突，不伪造语义哨兵。初稿的理由和失败报告是历史观察，当前修复状态由新增报告说明，不覆盖旧证据。

## 两条精确候选的预览核验

2026-10-07 用户令继续执行此前列明的两条候选写入、TDD、镜像重建及快照核验，不授权冻结或运行豁免。新增 `checksum-candidates.draft.yaml` 是非执行提案，不改初稿 `sources.yaml`/`manifest.yaml`/`assertions.yaml`，不向原合同填写审批或例外。候选校验 API 不包含源布局硬编码，不打开源文件、不改变清单，也没有运行激活入口。

- B2 原账完整大小/摘要锁定；172 条有效记录全部匹配，偏移 21,945 之后恰为 126 个 NUL，原字节和异常全部保留。
- 发布账原始大小/摘要锁定；第 4 行原名及声明路径保留，明确绑定的目标唯一，大小和摘要相符；没有名称搜索、重命名、复制补路径或隐式回退。
- `checksum-candidates-preview.json` 记录两条预览通过，但 `runtime_applied=false`、`ready_for_import=false`；严格清点仍有 3 个阻断、191 条断言中 190 条匹配，8,004 成员唯一匹配、BLOCKED=7,918、conforms=false。
- `artifact-hashes-checksum-preview.json` 是本轮新增文件的摘要；回传 Windows 后逐份校验通过，原 artifact-hashes 两份记录逐份复核不变。快照核验前后与已验收证书一致，未再读取原 NAS。

初始 20 项测试因 API 缺失而失败后通过；补充精确尾部/目标唯一性边界，超大尾部计数的分配溢出单独 RED→GREEN。最终新增 28 项、累计 224 单元/231 镜像全套和镜像契约通过。候选核验 runtime digest 为 `sha256:64f006e4361d14f704ef83ef5ff45e732a1368442f44791412187ad027c7dea4`，Git HEAD 不变、source_status=dirty。

实际例外的冻结合同集成尚未实现，现有 `exception_not_implemented` 拦截未改。对象、编码、独立期望和最终处置仍未建立；本轮预览没有解除这些阻断。JSON Schema 独立验证仍未运行，未安装新依赖。

按代码审阅技能安排 `checksum_preview_review` 独立只读静态复核本轮 API、28 项测试和候选配置，未发现 Critical/Important/Minor。该审阅未独立运行测试、访问快照或远端，不为这些行为作结论；其余脏工作树、整个 Task 6、冻结/运行例外/导入均在审阅范围外。运行验证由本轮主 Agent 执行并在上述机器报告留证；静态审阅不构成用户审批。

## 初稿三项阻断及修复进度

2026-10-07 用户随后授权修复：字面方括号选择器已按四项 RED→GREEN 回归修复，仍按完整位置元组精确匹配，不执行 glob，`*?` 仍拒绝。NUL 数量已获授权更正 DESIGN/roots/PLAN 为 126，不改源件。校验账仍严格报告 NUL/坏行、缺失路径仍阻断，兼容例外未启用。下面保留初稿发现经过，不表示这两项自有缺陷仍未修复。

### 1. NUL 数量与现行文档冲突

`SHA256SUMS-b2` 原始 SHA-256 仍是 `900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb`，大小 22,071 字节。逐字节独立核验：172 个换行之后恰有 **126 个 NUL**，总 NUL 和尾部连续 NUL 数量均为 126。DESIGN §13.3、roots.yaml 和 IMPLEMENTATION-PLAN Task 6 记载的 1,101 与该精确摘要的实际字节不符。

本轮不擅自修改现行设计/配置事实，也不启用兼容解析。见 `checksum-anomalies.json` 的计数、摘要和尾部字节直方图，以及 `inventory.json` 中 `checksum_nul`、`checksum_line`。冻结前须批准纠正事实记录，并单独审阅精确摘要兼容规则；不改源件。

### 2. 发布方校验账引用的路径不存在

`harvard/chgis/SHA256SUMS.txt` 第 4 条声明 `China_Periods_ReignDates.zip`，按该账目录应位于 `harvard/chgis/China_Periods_ReignDates.zip`，实际不存在。`chgis-v6/China_Periods_ReignDates.zip` 存在，大小 155,774 字节，摘要与该条期望 `7452ae6cf8d7dedbd0b06ea4e0e8343be9bac4075069ca8eb89e8ff0451c355e` 相同。

这只能证明存在同摘要候选，不能自动重解释原账路径或把原账改为通过。用户须逐案决定允许怎样绑定来源位置；源件和校验账保持原样。

### 3. 自有选择器实现误拒绝合法原名

13 个 XLSX 包内的字面成员名为 `[Content_Types].xml`。清点器已读出它们的完整原名、容器链、物理序号、大小和摘要；`MemberSelector.exact_paths` 在 `contracts.py` 直接拒绝任何含 `*?[]` 的字符串，而 `DispositionLedger.evaluate` 实际使用精确位置元组匹配，没有进行 glob 展开。这把字面方括号与通配规则混淆。

见 `selector-validation-errors.json`。不得删除这 13 个成员、重命名、改链或用默认规则绕过。修复必须另获代码修改授权，先以合成 XLSX 字面名和明确的匹配方式区分做失败测试，再按 TDD 实现与累计验证。

## 证据与溯源

- `spatial-exception-observations.json`、`artifact-hashes-spatial-exceptions.json`：未决归档逐层精确身份/摘要与中央目录，4 件 TAB 及 CPG 原字节观察，全快照前后校验；不是几何/属性值验收、字符集合同或绑定批准。

- `spatial-review.md`、`spatial-component-candidates.json`、`artifact-hashes-spatial-components.json`：物理容器＋精确目录/stem 的空间关系候选、逐件原字节断言与未决位置；casefold 仅提示，不自动合并，不跨容器拼件；不是内容验证或冻结合同。

- `text-objects.draft.yaml`、`validation-text-objects.json`、`artifact-hashes-text-objects.json`：三件/70 列的非执行对象及目标提案、现有单项模型/三件命名/负向验证和摘要；全版本命名未完成，expected_sha256=null，原 BLOCKED 合同不变。

- `text-review.md`、`text-reading-decisions.draft.yaml`：三件全文历史观察、已批准的精确读取解释及最新独立源复核；不是 frozen 执行合同或导入授权。
- `independent-text-reading.json`、`artifact-hashes-independent-text-reading.json`：新 runtime 的源逐字段比较及报告/决定摘要，三件零差异、全快照前后校验通过；没有数据库证书，BLOCKED 保留。
- `full-text-candidate-observations.json`、`text-escape-candidate-observations.json`：全文四种组合及另行明确的反斜杠转义观察；严格失败保留前缀口径，没有独立值真值或自动放行。
- `artifact-hashes-full-text-candidates.json`、`artifact-hashes-text-escape-candidates.json`：新增报告摘要；原证据不覆盖。

- `metadata-decisions.draft.yaml`、`sources-metadata-review.draft.yaml`：四条精确非业务成员提案及既有 API 组装后的最新审阅候选；其余 8,000 条规则和全局范围不变。
- `validation-metadata-review.json`、`disposition-ledger-metadata-review.json`：模型通过、8,004 唯一匹配、零未匹配/多匹配/过时断言，NON_TABULAR=90、BLOCKED=7,914；严格清点三项异常、191 条断言中 190 匹配及 incomplete_inventory 保留，导入门为 false。
- `metadata-candidate-negative-checks.json`：在内存中构造空合同、臆造成员及 Thumbs.db 大小断言漂移，分别被模型或处置 API 检出；不改真实候选和源。首次因回传文件尚未同步而失败，核实路径与同步后重跑通过；该操作错误不冒充合同拒绝证明。
- `text-header-observations.json`：三件精确外层 .tab 的源摘要、原始头部、BOM/TAB 观察，不包含业务数据行，也不是全文/逐列编码证明。
- `artifact-hashes-metadata-review.json`、`artifact-hashes-metadata-negatives.json`、`artifact-hashes-text-headers.json`：本批新增证据摘要，已回传 Windows 并逐份校验；旧证据摘要均保留。
- `inventory.json`：规范完整枚举，SHA-256 `fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db`；该摘要绑定原始清点证据，不是扩展的 `manifest.yaml` 文件摘要。
- `summary.json`：范围、时间、候选镜像 digest、Git HEAD、清点前后快照验证结果。
- `canary.json`：`chgis-v6` 小范围清点，26 成员、complete=true；只证明该 canary 范围。
- `validation.json`：真实模型拒绝和正式覆盖门未运行，不把候选规则数量冒充通过率。
- `validation-after-selector-fix.json`：新镜像模型成功、全量精确匹配及仍未通过导入门的报告；13 个原名精确匹配，快照前后验证一致。
- `disposition-ledger-after-selector-fix.json`：正式 API 生成的全量处置账；零未匹配、多匹配、失效断言，7918 个 BLOCKED；仍有 incomplete_inventory。
- `artifact-hashes-after-selector-fix.json`：新增修复证据的文件摘要，不覆盖原 artifact-hashes.json。
- `checksum-candidates.draft.yaml`、`checksum-candidates-preview.json`、`artifact-hashes-checksum-preview.json`：两条非执行候选、真实快照预览及新增摘要；不覆盖原清点/合同，不启用运行例外。
- `groups.json`：签名与容器深度；扩展名明确仅为提示，不用于静默选择或丢弃。
- `mirror-candidates.json`：哈希/大小候选，不是字节全等证明或镜像裁定。
- `artifact-hashes.json`：镜像生成的机器文件摘要；本人工审阅文件不属于其中的生成证据。

清点使用 runtime digest `sha256:0ba034861027dd4ec1c7b0cabbdd3e651783c35a4518082c0539db98e8b0a8e8`，Git HEAD `1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05`，`source_status=dirty`。未提交源码不能冒充已经提交、可发布或已完全可重建的版本。

初稿轮没有安装依赖或修改解析器。后续授权轮仅修改选择器校验和 NUL 事实文档，重建 dev/test/runtime；196 项单元、203 项镜像测试及契约通过。修复验证 runtime digest 为 `sha256:8155c7f4dedd0626bcdea5182de4fa9ed36f70d17270a239d441eb71341ba4f7`；Git HEAD 不变、source_status=dirty。两轮均未读取旧库、访问数据库、修改源或项目快照、重启既有长期容器。原 NAS 是否在快照复制后变化不在本轮观察范围；只确认项目快照验证前后与已验收证书一致。

Task 6 未完成。不得修改 `contracts/current.yaml`、填入虚构审批记录、置为 frozen，或开始 Task 7/数据库操作。

本批未改代码、依赖或镜像，复用前述固定 runtime digest 与已有合同/处置 API；本轮镜像完整回归 231 项通过。草案前后快照核验通过，原证据摘要不变；三件头部观察的完整源摘要分别与清单一致。作者按执行计划技能自审，不另派实现或逐批审阅 Agent；整个阶段完成后再做整体复核。本批未打开 SQLite、连接 PostgreSQL、执行 SQL 或重启既有容器。
