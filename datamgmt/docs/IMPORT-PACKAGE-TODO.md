# 全量导入包与映射进度

更新日期：2026-11-21。当前阶段为数据整理与映射，第 1–2/6 块（CBDB、普通表格）已获 Codex 验收，第 3/6 块空间矢量团队核验全 PASS、**Codex 独立验收仍待接**，第 4/6 块 Access/MDB 与 SQL **Codex 整理验收通过**（收口补正提交 5d0c9e3），第 5/6 块栅格及其他成员首盒进行中、第 6 块合并与落盘待执行。交付在本 release 的 [import-package/cbdb/](../contracts/releases/2026-10-06-bootstrap/import-package/cbdb/SUMMARY.md)、[import-package/tabular/](../contracts/releases/2026-10-06-bootstrap/import-package/tabular/SUMMARY.md)、[import-package/spatial/](../contracts/releases/2026-10-06-bootstrap/import-package/spatial/SUMMARY.md)、[import-package/mdb-sql/](../contracts/releases/2026-10-06-bootstrap/import-package/mdb-sql/SUMMARY.md) 与 [import-package/raster-other/](../contracts/releases/2026-10-06-bootstrap/import-package/raster-other/SUMMARY.md)；CBDB 10 表/235 列源侧值验证单列未决，不计入映射完成，ready_for_import=False 保持。

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
| 2 | TSV/CSV/Excel、独立 DBF 等普通表格 | 已验收（Codex 2026-11-20，提交 5478271） | 文件/工作表/记录对象、编码、字段、空值及目标映射 | 编码或表格语义的未决项 |
| 3 | Shapefile、MapInfo、KML 等空间矢量 | 团队核验全 PASS，Codex 独立验收待接 | 组件组、属性、几何、CRS 原声明及目标映射 | 组件缺失、坐标声明和异常保留 |
| 4 | Access/MDB、SQL 数据 | **Codex 整理验收通过**（收口补正 5d0c9e3；96 提案批准面留导入阶段） | 内部对象及字段清单、读取/隔离方法、目标映射及不兼容项 | 不能无损读取或表达的具体对象 |
| 5 | 栅格、其他格式和非业务成员 | 首盒进行中（候选 2522 逐件处置，栅格 43/43 读通） | 栅格对象与入库方式；说明/图片/校验文件用途；未知件明细 | 剩余格式的处置决定 |
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

#### 第 2 块收尾记录（2026-11-19 round 3，列身份整表分配，终态 PARTIAL）

- 配方修复：列身份改**整张表一次分配**（identity.py allocate_columns 真函数：重复 slug 由 `__c{ordinal}` 后缀消歧，identity 含序号+源名天然唯一）；155 提案对象全量重分配，源列名/序号/全列保留不丢不并；批准 5 件权威映射不动。
- 三处定点修复实证：两份 ChinaW.Master.Beta.csv 176 列全保留、4 组重复源名（' 1820 "'×5/' prefectural level'×2/' county level'×2/' 1893 "'×7）column_id 由共享变互异、目标名消歧；china_chron.txt 首行按数据保留（header_row=null、676 记录），两模块实查无现行无表头规则⇒稳定序号名 col_001…col_020 经同一整表配方分配（提案态披露）。
- 全量唯一性：uniqueness_review 155 表/3560 列 column_id 违例 0、target_column 违例 0（脚本 assert 硬闸+lead 独立复算 0）；跨表同 schema 碰撞留第 6 块。
- **lead 方言裁定（a03 ROUND 4 注记）**：两份 ChinaW.Master.Beta.csv 旧 naive split(',') 176 列系伪影（引号内含逗号表头被错切）；引号感知 csv.reader=**159 列×2、零重复源名**（GB2312 探测/gb18030 严格解码、2403 数据行，lead/a03 SSH 独立基线一致）——与已确认文本读取语义（DOUBLE_QUOTE/doublequote）及 R-08 一致，**引号感知为正**，裁定披露入件（dialect_resolution 176→159 对照+证据 sha），提案态可逆待茶香讨论确认。字段总数 3594→**3560**。逗号 txt 107 件全量审计 naive==strict 无同类伪影；2 件个别 ragged 数据行（v3/v4_time_cnty_pts_utf）入 quote_artifact_audit 留块 6 值合同复核。CountryFilesFormat.ods 行数三值并列（39 table-row/37 含内容/38 数据行）。
- SUMMARY 五类陈旧文案清除，计数与机器件逐项一致；确定性重跑字节一致。
- **XLS 14 件环境核查（lead）**：项目锁定件（requirements.lock/requirements-dev.lock/pyproject）无 xlrd/openpyxl/odfpy/chardet；32 112 枚自有 xiangrugu 镜像同一哈希锁定 Dockerfile 谱系，最新两枚实测四模块全缺；宿主/容器/转换工具全缺。**确需安装或构建，报茶香决定**：建议 xlrd==2.0.1（PyPI 稳定版，2.x 专支持 .xls BIFF 恰合所需），哈希入 datamgmt/requirements.lock 后按 R-09 重建自有镜像（docker build -t xiangrugu:runtime-tabular-reader-<date>-a），只读挂载快照清点 14 件（14,177,280B≈13.5MiB）工作表/字段/源类型；备选：批准派生纯 stdlib BIFF 解析器（工作量大）。本轮不装不建，gap 14 逐件含 environment_audit 保留。
- **第 2 块终态 PARTIAL**：1640=organized 160（批准 5+提案 155/3560 字段）+block3 846+block5 620+pending 14（XLS）；XLS 补齐并验收后方可转 PASS。
- 名级修复追加（a03 ROUND 5 ③FAIL 揪出）：上轮审计仅比列数漏检名级伪影（缺陷如实入件）；名级全量三方比对（139 件=txt132+csv7，BOM 嗅探+严格解码+csv.reader 引号感知+行尾安全，逐元素比对）clean 128/diff 11，11 件全重导：Tibet_twns_2009_utf8.csv 13 净名（旧 12 列字面引号包裹+\r）、MingGarrisons/hist_sites/tan_GBK_names1/2/nima_feat_desig 末列 \r 清除、**ChinaWBeta.Field.Definitions.txt ×2 UTF-16LE+BOM 重判为 TAB 7 列数据字典表⇒organized 提案**（先例 v4/v6_data_dictionary 对齐；双副本 17580B sha 同保留镜像块6；旧 latin-1 NUL 碎片失真消除）。字段 3560 不变、唯一性双 0、闭合不变；a03 ROUND 6 复扫。

#### 第 2 块 XLS 补齐记录（2026-11-19 round 4，茶香授权，读取面 COMPLETE 待 Codex 验收）

- 授权：锁定 xlrd==2.0.2（PyPI 官方 wheel sha256 ea762c3d29f4cca48d82df517b6d89fbce4db3107f9d78713e48cd321d5c9aa9 逐字）+32 独立 runtime 候选镜像+只读检查 14 件 XLS；不宿主装依赖、不替换服务/镜像别名、不写库、不改源件。
- 锁件提交 **a163f00ede2f9cc4592b636970cc243f6210cf30**（requirements.lock+requirements.in，追加式谱系）；构建上下文=lead git archive 该提交经 SSH 解包至 32 /opt/mydocker/xiangrugu/build-candidates/runtime-tabular-xls-20261119-a/（不触 deploy）。
- 镜像（a02 构建，lead 独立 docker inspect/run 实证）：**Id=sha256:6144346a501c7ba1299e28862a303007fddd6a9e8030c6b6e7c1ca52921b6cd3**，tag xiangrugu:runtime-tabular-xls-20261119-a（独立标签，未跑 build-task1.sh 全脚本防别名覆盖）；labels revision=a163f00/created=2026-11-19T18:06:48Z/source.status=clean/version=0.1.0；容器内 **xlrd 2.0.2**（--require-hashes 全过）；别名三枚 Id 未动（runtime c15019fe…/dev 89f1a097…/test 474da53d…，lead 留证 .xls-block2-20261119/lead-baseline.txt）。
- 只读检查：快照 :ro 挂载、on_demand=True，**14/14 全可读、sha 对账 14/14 匹配**；逐件 sheets/nrows/ncols+逐列 XL_CELL 类型分布入 xls_probe_out.json；ChinaW.Master.Beta.xls ChinaW 2404×159 与引号感知 CSV 159 列同构互证；china_chron.xls Nian_hao_strip3 678×20；MingGarrisons Sheet1 773×14+Sheet2 376×11；零维 sheet 记结构事实不建对象；datemode 注记；**公式语义逐件 cached_value_semantics 标注**（xlrd 仅缓存结果、原文不可得、逐格不可判）；嵌套链解析器七版迭代过程如实披露（chain 末元素含目录前缀+relative_path 双重路径语义）。
- 映射提案：**+14 xls 对象/505 字段**（15 非空 sheet 整表 allocate_columns）；target_type 按源单元格类型分布提案（全 NUMBER⇒double precision、混合/文本⇒text；CHW xls 8 number/151 text），observed_cell_types 逐列留证，nullable 由 EMPTY/BLANK 观测驱动；确认态全 PROPOSED_NOT_AUTHORIZED，basis=镜像 Id+xlrd 版本+证据 sha；empty_string=preserve_not_null、行序 preserve+__src_rownum 沿用。
- **新闭合：1640 = organized 174（批准 5+提案 169）+ block3 846 + block5 620 + pending 0**；uniqueness_review **169 表/4065 列双 0 违例**；gaps 归零（剩余缺口仅批准面）；pending_review 14/14；确定性重跑字节一致。**读取面 PARTIAL⇒COMPLETE；批准面仍 PROPOSED_NOT_AUTHORIZED，ready_for_import=False**。待 Codex 独立验收后收口第 2 块，再进入第 3 块空间矢量。

#### 第 2 块工作表映射收尾记录（2026-11-19 round 5，复用已提交读取证据）

- MingGarrisonsSheet_29jan08.xls（V4_Data_Archive.zip!KML/ming_garrisons_KML.zip）横拼对象（25 字段=Sheet1 14+Sheet2 11）**拆为两个独立导入对象**：Sheet1（sid 0e2674e1…，14 字段源序，nrows 773/data 772）、Sheet2（sid 04e26d04…，11 字段，nrows 376/data 375）；身份输入 convention `<member>#<sheet>` 经 identity.py 真函数、候选表名经 naming.py 真函数，逐对象 worksheet_split.convention 披露；**禁止横拼/按行号合并**；归档成员仍登记一个源文件。
- 同类扫描（方法修正披露：上轮用错键 nrows/rows 全漏，本轮正确键 columns/data_records_observed）：**多非空 sheet 合并仅此一处**；xlsx 13 各单命名 sheet、ods 按 table:table 逐表成对象、其余 XLS 各 1 非空 sheet；零残留。
- 补名：csv/txt 平面件 null worksheet 统一 'TABLE' 标签（138 件）；76ed534c…（RUXK8/Ming_Garrisons.zip!MingGarrisonsSheet_29jan08.**csv**）经授权镜像只读回测兄弟簿（sheet_names=[Sheet1,Sheet2,Sheet3]），11 列表头与 Sheet2 逐列同构（11 列/375 行）⇒worksheet 标 'Sheet2' 带比对注记（提案态解释性标签，待复核）；与嵌套件 Sheet2 对象双成员保留镜像块 6。null 标签终值 0。过程缺陷披露：常量 hoist 遗漏致修复初版两轮静默失效，经机器件复核抓到——标签类修复必须断言终值。
- 空 sheet：零维 Sheet2/Sheet3 共 5 处保留 members 清点结构事实，不建对象。
- 消歧明细：uniqueness_review.disambiguation_detail **5 对象 23 处全 XLS 面**（xlrd 首行空表头 ''×n：1999_gb_pop_uce extra4、KML/Gazetteers.Beta extra7、ming_garrisons Sheet1 extra3、gbk/Gazetteers.Beta extra7、THDL_ADMareas extra2），__c{ordinal} 消歧；csv/txt 面 ChinaW 修正后 0；违例双 0。
- SUMMARY 陈旧段修复（lead 指定文本、a02 编辑周期应用、lead 终验）：「读不了 14」清零、提案分解含 xls 每表一对象口径、169→170 同步。
- **对象级终值：proposed 170/4065 字段（拆分净增减 0）、170 表唯一性双 0、候选表名跨对象碰撞 0、sid 全局唯一**；成员级闭合 1640=174+846+620+0 不变；确定性重跑字节一致；未重建镜像/未写库/未改源件。a03 ROUND 8 独立核对。

### 第 3 块空间矢量

- [ ] 将已有候选组落实到确切归档链与组件身份；缺件、大小写差异、孤立组件均有处置。
- [ ] 合并已确认的编码、属性类型、Point/几何及 SRID 规则，保留原坐标和声明，不自动投影或修几何。
- [ ] 完成属性与几何的目标映射、异常原字节保留及独立核验方法。
- [ ] 对全部空间成员覆盖核对，验收并讨论未决项。

### 第 4 块 MDB 与 SQL

- [x] 清点所有内部表、字段、对象和重复副本关系。
- [x] 给出 MDB 的读取和独立验证路径；SQL 采用受限解析或隔离恢复，禁止直接执行源 SQL 到目标库。
- [ ] 明确精度、二进制、编码及目标类型，不能无损表达的项目单列。
- [ ] 输出完整映射与读取依赖，验收并讨论。

#### 第 4 块完成记录（2026-11-21，首盒+续盒，待更正复核收口）

- 核心成员 **7** = MDB ×5 + SQL ×2；完整链 sha 绑定 inventory 精确对账。
- 已枚举对象 **96** = SQL 表 **34**（全量 CREATE TABLE 解析，异常 0）**311 列** + MDB 表实例 **62**（5/5 读通，全 JET4）**500 字段实例**；行数合计 **876,453**，schema/count/export 错误 **0**，读不出项 **0**。
- 映射提案 **96** 全部 `PROPOSED_NOT_AUTHORIZED`、`ready_for_import=false`；sid **101** 全局唯一；SQL 34 提案 byte-identical 保留；生成器真双跑 exit 0/0 字节一致。
- geom 字节忠实提取 **1/1**：raw 33B（sha `9379a445…`）→ decoded 25B（sha `cfe2b8d4…`），MySQL 4B LE SRID=0 + WKB LE Point，consumed==len 闭合；首个无法验证项 null。
- 缺口 **6** = MDB 读取器缺口 ×5 **RESOLVED**（茶香授权候选镜像 `runtime-mdbtools-20261120-a`，仅入镜像不装宿主）+ SQL 编码记录 ×1（`encoding_loss_risk`：含 geom 提取结果与待定导入合同）。
- 四产物 sha：members `9a859420…` / object-mapping `b56889f1…` / evidence-gaps `a6ed3537…` / SUMMARY `22873f9e…`（本轮 32 双跑 exit 0/0、stderr 0/0 字节重生成，三 JSON 字节==基线）。
- **V4 的 13 个同名目标各对应三个来源实例（direct + 两 zip 镜像）**，命名与镜像处置登记第 6 块。
- 工具面：镜像 `74e022830b3b…`，mdbtools=`1.0.0+dfsg-1.1`（4 deb 离线闭包），仅候选镜像，宿主零安装。

### 第 5 块栅格及其他成员

- [x] 逐件区分地理栅格、说明图片与其他格式，未知件不得归入“其他”后省略。
- [x] 地理栅格保存尺寸、波段、像素、NoData、仿射、CRS 及每波段验证规则。
- [x] 说明、许可、校验账和辅助材料保留原件、摘要、用途和明确处置。
- [ ] 全部剩余成员有归属，验收并讨论。

#### 第 5 块首盒记录（2026-11-21，基线 5d0c9e3，待独立核与验收）

- 归属对账闭合：inventory **8004** = 前四块已归属 **6103**（块1=3/块2=174/块3=5294/块4=11/交接面 620+1）+ 本块候选 **2522**（块2交接 620 + Thumbs.db 1 + 无归属扫描 1901；文件 2437 + 目录 85）；unresolved 0；跨块引用 4 件逐条登记不重复认领。
- 逐件处置（unknown 0）：documentation_license **1445** / structural_container **615** / ordinary_image **299** / sidecar_companion **116**（世界文件 26+栅格伴随 48+GIS 侧车 42）/ geo_raster **43** / checksum_ledger **3** / cache **1**；sha256 全量流式重算 2437/2437==声明，失配 0。
- 栅格面 **43/43 读通**（现有镜像 f1675321e33e osgeo 绑定；镜像无 gdalinfo CLI、python3-gdal 半装态如实披露，未装依赖）：尺寸/波段/像素类型/NoData/仿射/**源 CRS WKT 逐字**（内部声明 19 件，LOCAL_CS 不推导 EPSG）/世界文件六参数 verbatim 绑定 23 件（同容器同目录同 stem，跨容器不借用）；逐波段 checksum ≤20MB 实跑 26 件，17 大件登记方法留导入阶段；NoData 113 波段源均未声明如实 null（探测脚本 GetNoDataValue(True) 传参缺陷经 lead 令 a02 定点修复，错误键归零，修复件 sha a8b543f2…）。
- 缺口 6 组：**pdb2.TIF(v4_dem_geotiff.zip) 无几何声明且本容器无世界文件**（同名 tifw 在另 3 容器，跨容器借用属镜像语义留块6）；WMF 12 件 tool_gap 待授权；大件 checksum 未跑；NoData 源未声明留导入合同；inventory 历史阻断 3 项显式登记留块6；LOCAL_CS 非 EPSG 不推导。
- 块5范围同 sha 镜像候选组 **377**（含 map1_.TIF/Ca1884_przh_partial.TIF 疑似异名同内容，checksum 全同），合并裁定留第 6 块；43 栅格提案全 PROPOSED_NOT_AUTHORIZED，命名/装载器（PostGIS raster vs bytea）留块6与导入阶段，ready_for_import=false。
- 交付 `import-package/raster-other/`：members.json / raster-mapping.json / evidence-gaps.json / SUMMARY.md + 确定性生成器（32 双跑 exit 0/0、stderr 0/0 字节一致）；证据 `.raster-block5-20261121/`（recon/candidates/probe_evidence/三脚本）。生成器两处缺陷（32 浅目录 parents 越界、目录件 sha 断言过严）lead 定点修复披露，修复后双跑通过。

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
- 2026-11-19：第 2 块收尾（30 分钟盒内）：列身份整表分配修复（__c{ordinal} 消歧）、三处定点修复实证、全量 3594 列唯一性违例 0、SUMMARY 陈旧文案核销；XLS 14 环境核查确证无锁定依赖/无可用自有镜像，xlrd==2.0.1 决策路径报茶香；**第 2 块终态 PARTIAL**（XLS 补齐前不转 PASS），逐件缺口保留。待 Codex 验收与茶香依赖决策。
- 2026-11-19：第 2 块 XLS 补齐（茶香授权 xlrd==2.0.2，30 分钟盒内）：锁件 a163f00、独立候选镜像 6144346a…（xlrd 2.0.2 实证、别名未动、不宿主安装）、14/14 全可读 sha 全匹配、+14 对象/505 字段提案、闭合 1640=174+846+620+0、169 表/4065 列唯一性双 0、公式缓存语义逐件标注；读取面 COMPLETE，批准面 PROPOSED_NOT_AUTHORIZED 保持。待 Codex 独立验收后收口第 2 块，再进入第 3 块空间矢量。
- 2026-11-20：**第 2 块 Codex 验收通过**（茶香转发，核对 Gitea 提交 5478271）：15 张非空 XLS 工作表各有独立映射，MingGarrisons 拆 14 列/11 列两对象；终态 **174 件已整理源成员、175 个映射对象（5 沿用既有确认+170 提案）**；正式装载和回读验收留在入库阶段。进入第 3/6 块空间矢量（基线 5478271，首个 30 分钟盒）：复用 spatial-component-candidates（705 Shapefile/146 MapInfo 候选）与 spatial-review 决定，846 交接归属+全量矢量补查，按外层文件/完整归档链/成员序号分组，2 批准对象逐字沿用，证据齐全者补提案映射（原坐标+CRS 声明保留）。
- 2026-11-20：第 3/6 块空间矢量首盒（30 分钟）：inventory sha fb5e6b33…==候选件记录值断言后复用分组；**候选组 903（shapefile 705+mapinfo 146+kml 52）/确证组 903（头级只读取证 2708+ 记录 0 错 0 sha 失配，复用块 2 授权镜像未重建）/映射对象 898（批准 2 逐字+提案 896）**；846 交接（dbf704+TAB142）逐件恰属一组断言闭合；泳道分区 approved 2+proposed 896+gap 3+text-owned-by-block2 2=903 UNASSIGNED=0；KML 52 初版零归属经 lead 终核揪出补全（52/52 提案，srid=null，ExtendedData 属性面留正式读取器合同披露）；counts 陈旧字段 844≠846 经 lead 揪出修正+断言防复发；缺件组 1（v5_time_pref_pts_utf 缺 dbf）+prj 缺 3 注记；**首个实质阻塞=casefold 孪生无主件组 2（v3_time_pref_pgn_PRC/V3_…仅 DAT/IND/MAP 无 .TAB）待茶香裁定合并/独立合同**；2 批准（Ca1884route_przh_1251/utf8，SRID4326/原 XY/PRJ+QPJ 双保留/轴序注记）JSON 子树字节级相等断言；提案面 srid 全 null 不推导扩展、Z/M 2 件 target_type_proposal=null 留正式合同；stdlib 取证无新依赖；取证四版迭代过程缺陷如实披露。a03 ROUND 9 独立核对。
- 2026-11-20：第 3/6 块缺口收尾盒（30 分钟，基线 75fda05）：**三缺口组级归零**。①孪生真相更正：mapinfo/ 与 shapefiles/ 两 copies 内层 ZIP 字节相同（sha 69b5119f…），**TAB 实存（V3_ 大写前缀，上轮"无 TAB"系 stem 大小写分裂伪影，如实披露）**；DAT 按 TAB 23 字段 schema struct 试解通过（601448=769+1989×302+EOF 精确、1989 记录删除标志 0 违例、OBJ_TYPE 全 POLYGON；置信度结构 HIGH/值 MEDIUM 分层披露，NUL/null 语义留正式 reader 合同）；**两案分立组件绑定登记**（来源路径分别保留，镜像合并留第 6 块）；**工具缺口如实报：MAP 几何 stdlib 不可解码，受影响 2 件（各 20469248B），所需 GDAL/OGR MapInfo driver 或茶香批准派生解析器证据轨，未装未伪报**。②v5_time_pref_pts_utf：README 全文无属性说明、全 inventory 同族 23 件 dbf 记录数对 shx 3409 **0 吻合**⇒无可证实伴随（同名不足配对、pgn 不充配对）；独立可读几何登记提案（Point/bbox 实测/shp 遍历 3409==shx/prj 逐字/srid=null/fields 空**零补造**）。③KML 口径：ElementTree convention 机器件定义，**52/52 重算==交付**（断言抓到比较语义缺陷即修披露）；3 轴 50 件海拔原样保留/2 轴 2 件；ExtendedData 逐件留正式读取器决策。**lead 终核揪出 3 新对象 sid/表名/链三缺经 a02 速修补齐**（identity/naming 真函数、孪生 fields 23、v5 fields 空）；carrier"漂移"经查基线文件本就 702/142（首盒报告文本误，2 件 dir 口径 ROUND 9 已核等价）非真改判。**终值：候选组 903/确证 903/映射 901=批准 2+提案 899（shapefile 702+partial 1+mapinfo_tab 142+twin_bound 2+kml 52）**；泳道 approved 2+proposed 899+text-owned 2=903 UNASSIGNED=0；om.counts 增 text_owned_by_block2/twin_bound/partial_no_dbf 字段（披露 B 修复）；sid 899 全唯一表名碰撞 0；846 归属/2 批准字节级非回归。**复现性缺陷披露（lead 终核揪出）**：a02 半截编辑致 build 脚本 L787 语法破损随 cd0406b 入仓；lead 前轮双跑因 2>&1 吞崩溃成假证（方法论已修正：验退出码）；cc76510 修复仍误且声明不实，9509f12 正解（单 }，COMPILE-OK、真 exit 0/0）；脚本含 a02 半截逻辑改，重生成对 844 件 chain/identity 富化漂移⇒om 恢复 a03 已验证态，**脚本逻辑与已验证产物对齐=次轮首要**；观察 A（SYS_ID verbatim 缺行）/B（tool_gap_report 悬空键）留次轮。剩余缺口=工具面（MAP 2 件）+v5 属性源件缺失注记+批准面 899 待茶香。a03 ROUND 10 独立复核四项 PASS。收尾超盒 76 秒（安全恢复优先，如实披露）。
- 2026-11-20：第 3/6 块复现性收尾盒（30 分钟，基线 c0d0799）：**a02 本轮三次早退（路由杂讯未执行），lead 接管生成器修复（停手令披露在案），a03 隔离复跑验证不变**。修复三处：①_ensure_common_fields 按 carrier 白名单守卫（kml/twin/partial）⇒**844 件 chain/identity 富化漂移全消**（重生成==已验证基线）；②字段正则纳 `(?:\s+Index\s+\d+)?` 后缀⇒**63 件 mapinfo_tab attribute_order 补 71 行 Index 原声明**（SYS_ID_2×24/SYS_ID×12/NAME_CH×12/Lks_id×4/Key_ID×4/LEV2_CH×4/Sea_ID×2/GEO_ID×2/NOTE_ID×2/Key_id×2/SYSTEM_ID_2/SYSTEM_ID/LEV1_CH 各 1；名集差实证全含 Index；fields 键/sid 序列/counts/groups/SUMMARY 字节零变）；③evidence-gaps.json 补 **tool_gap_report** 键（MAP×2 全 sha a7b44b35a4123c7c…/size 20469248/两案链+所需 GDAL/OGR MITAB 或批准派生解析器+本轮未装声明+方案文档引用）。孪生 SYS_ID 原声明经 tab_definition_verbatim 全文键断言在件。**真双跑 exit 0/0 字节一致（单调用验退出码，假双跑方法论修正）**。v5 保持源缺件/3409 点/原 CRS Xian_1980_GK_Zone_19/fields 空不补造。**MAP 读取方案提案落盘 MAP-READ-PLAN.md**：32 自有环境三面勘察（宿主/dev 容器/镜像）无可复用 MapInfo 几何读取器；pyproj 3.7.2+PROJ 9.5.1 在位（requirements.lock L24 锁定，CRS 面可复用）；方案 A=apt 锁定 python3-gdal=3.6.2+dfsg-1+b2（bookworm，32 apt-cache policy 实测）+deb sha256 入新 apt 锁件+自有候选镜像 runtime-spatial stage（永不覆盖别名）+ogrinfo -ro/ogr.Open(path,0) 只读+隔离 /tmp 提取+**严禁 pg32b 服务容器试验**；影响+60–80MB/PROJ 9.1.1 与 9.5.1 并存注记/孪生 TAB 无 Coordsys⇒CRS 仍 unresolved 不推导；方案 B 派生 stdlib 解析器备选高风险。**待茶香批准，本轮未安装未写库**。提交 bceb425（lead 修复+方案）；a03 ROUND 11 隔离复跑核对中。第 4 块暂不启动（茶香指令）。
- 2026-11-20：第 3/6 块 MapInfo 几何核验盒（30 分钟，基线 2df6e3d，**茶香已授权候选镜像**）：**a02 第四次早退（同型杂讯），lead 接管构建与读取（披露），a03 独立复读不变**。①锁定：基座容器 apt 下载闭包 **92 deb**（bookworm/main，python3-gdal=3.6.2+dfsg-1+b2 sha 7f80b371…）入新锁件 **datamgmt/requirements-apt.lock**（deb 实物留 32 build-candidates，a03 抽核 14/14）；②构建：datamgmt/Dockerfile.spatial-candidate，**--network none 离线构建成功**（闭包完整实证），镜像 **xiangrugu:runtime-spatial-mapinfo-20261120-a Id f1675321e33eeb95…**（labels revision=2df6e3d…/gdal/purpose；别名零触宿主零改）；③预检：/usr/bin/python3 osgeo OK、GDAL 3.6.2、**MapInfo File 驱动在位**（MITAB 注册名差异 a03 注记）；④两案读取（mapinfo/ 与 shapefiles/ 精确链，--network none/快照 :ro/无凭据无 socket/未进 pg32/pg32b）：**1989×2==DAT 互证、POLYGON 1456+MULTIPOLYGON 533、0 空几何 0 错误、extent [106.60376,124.576195,18.160896,35.726135]**、组件/内层/外层 sha 全匹配、源件前后 4dec393b… 零触、临时副本大小写统一 3 件（DAT/MAP/IND v3_→V3_）原名映射记录；⑤**CRS 裁定：TAB 无 Coordsys，MITAB Pulkovo_1942 WKT 系读取器默认猜测非源声明⇒不采纳 UNRESOLVED 保留不推断不转换**；⑥**属性坐标裁定：X_COOR 1970/1989 零、Y_COOR 1975 零含哨兵 999.999999⇒源件未填充/占位，几何为权威不补造**（质心偏差全由零值/哨兵解释）；⑦a03 ROUND 12 五项 PASS（独立 struct DAT 全量解码 1989×23 零差、extent 逐位同值、deb 抽核、纪律复核）+披露 A（环数口径：纯 POLYGON 环数 vs MULTIPOLYGON 部件数——lead 补测 533 部件 2–39 另记口径注记）/B（crs_status 标签改 UNRESOLVED_READER_DEFAULT_NOT_ADOPTED）已修正复测；⑧集成：生成器证据驱动（MIE 常量+_mie_case 助手），重生成真双跑 exit 0/0 字节一致，与 HEAD 差恰四面（groups 仅 baseline_git 引用、om 恰 2 孪生 geometry_verification、gaps tool_gap_report→**RESOLVED_FOR_TWO_PRC_MAP_OBJECTS**+resolution、SUMMARY MapInfo 专段），counts/sid/泳道零变；MAP-READ-PLAN 转已批准执行态。证据 .mapinfo-verify-20261120/（脚本/expected/evidence/geom_types/attributes×2/lead-record）+32 隔离目录保留。**镜像处置留第 6 块；其余 MapInfo TAB 对象 MAP 几何不在本轮授权范围；第 4 块未启动；本轮后交 Codex 独立验收**。
- 2026-11-20：**第 3/6 块整理验收结论（团队核验面）与剩余入库事项补记**（第 4 块盒内 lead 落账）。**结论：空间矢量整理子项全数 PASS**——首盒 a03 ROUND 9 六项 PASS（903 组/903 确证/901 映射=2 批准逐字+899 提案，846 exactly-once，sid 901 唯一，泳道分区 UNASSIGNED=0）；缺口闭合 ROUND 10 四项 PASS（三缺口组闭合，孪生/V5/KML 真相修正披露）；复现性 ROUND 11 PASS（32 隔离真双跑 exit 0/0、4/4 产物 sha==待提交 JSON、844 富化漂移全消、63 件 Index 原声明补全、tool_gap_report 补键）；MapInfo 几何核验 ROUND 12+补段 PASS（茶香授权候选镜像 f1675321e33e…，两案 1989×2==DAT 互证、POLYGON 1456+MULTIPOLYGON 533、0 空 0 错、摘要全匹配源件零触、CRS UNRESOLVED 裁定/属性坐标源零值裁定、897/897 非回归 byte-identical）。过程披露：a02 四次早退（路由杂讯），lead 接管生成器修复与 MapInfo 构建读取，a03 独立验证不变。**Codex 独立验收待接**（尚未收到验收回文）。**剩余入库事项**：①899 提案批准面（茶香/Codex）；②v5_time_pref_pts_utf 属性合同决策（源 dbf 确证不存在，几何-only 3409 点待决）；③CRS 源级未决（孪生 TAB 无 Coordsys，MITAB Pulkovo_1942 系读取器猜测不采纳，基准面待源证据或裁定）；④其余 MapInfo TAB 对象 MAP 几何读取（候选镜像已具 MITAB 能力，逐批授权）；⑤孪生镜像合并（V3 PRC×2、V4 MDB 镜像对）留第 6 块；⑥候选镜像/apt 锁转正留第 6 块；⑦PG 装载器实现+正式装载回读验收（第 6 块，32 落地）；⑧KML ExtendedData/altitude 正式读取器合同逐件决策；⑨全 release 命名碰撞分配（第 6 块）。
- 2026-11-20：**第 4/6 块 MDB 与 SQL 启动**（首个 30 分钟盒，基线 ef90b64）。范围（lead 侦察）：核心 **7 成员**=MDB×5（V3 68853b49…/V4 直接 a2cc4039…/V4 zip 包裹 04be983d…×2 镜像对/**V4 直接件与包裹件字节不同两版本分别注册**/V2 4a9bd1bc…）+SQL×2（china_chron.sql 117824B/tgaz_bak_2018.sql 122853166B）；相关处置：3 内层容器 ZIP structural、Thumbs.db Windows 缓存非数据库排除→块5、**cbdb_20260919.sqlite3 块1既有（78 表 736 列）exactly-once 不重映射**、china_chron.xls 块2既有、txt/README documentation。**MDB 工具缺口**：32 宿主与现有容器均无 mdbtools（实测），本轮不装⇒头级探针+逐件原因/所需工具；SQL 只读方言/结构/载体识别**禁执行**。a02 生成器+四件（members/object-mapping/evidence-gaps/SUMMARY）分段落地；a03 ROUND 13 独立覆盖/映射/损失原值/隔离恢复核对；lead 交付+TODO+Gitea。
- 2026-11-20：第 4/6 块首盒结果（lead 接管，**a02 第五次早退披露**）：REL/import-package/mdb-sql/ 四件+确定性生成器落盘，**32 真双跑 exit 0/0 字节一致**（定位证据补全后再双跑，差分恰增量面）。**计数：核心成员 7（MDB5+SQL2）/已枚举对象 39（SQL 表 34 全量解析异常 0+MDB 文件级 5 头探针）/已映射提案 34（PROPOSED_NOT_AUTHORIZED）/缺口 6**。SQL：china_chron=mysql 1 表 20 列 677 行 utf-8-sig BOM 0 替换；tgaz=mysql **33 表**（InnoDB32+MyISAM1）136 extended INSERT ~983236 行估算（口径注记）utf-8 **5 替换字符全定位 line 326 `geom` 表二进制几何载荷（WKB 风格原始高位字节）⇒字节忠实提取隔离恢复对象**。MDB×5 全 **JET4**（magic 00010000/Standard Jet DB/ver1/page4096 推导/hexdump128），sha 流式复验全匹配；**V4 直接件 a2cc4039≠包裹件 04be983d×2 镜像（两版本分别注册，镜像合并块6）**；逐件原因=锁定环境无目录读取器（mdbtools 宿主容器均无实测），所需工具 **mdbtools=1.0.0+dfsg-1.1 候选提案未装待批**。相关 exactly-once：sqlite3 块1（78表736列）/xls 块2/Thumbs.db 排除→块5/3ZIP structural/txt README doc。**首个阻塞=MDB 目录读取器工具缺口（5 件表/字段/值枚举）**。SQL 未执行、未装依赖、源件零触。产物 sha：members 9a859420…/om 820eff12…/gaps 016740f1…/SUMMARY bca41b50…；证据 .mdb-sql-block4-20261120/（lead-record+run1-4 日志+sha）。a03 ROUND 13 独立核对中。
- 2026-11-21：**第 4/6 块续盒（MDBTools 茶香授权，30 分钟，基线 8b58466）**：lead 锁定 **mdbtools=1.0.0+dfsg-1.1 闭包 4 deb**（requirements-apt.lock mdbtools 段增量，sha fb95bada…）→独立候选镜像 **xiangrugu:runtime-mdbtools-20261120-a Id 74e022830b3b16ab…**（--network none 离线构建，别名零触宿主零改）→mdb-tables/mdb-schema v1.0.0 预检过→5 MDB 隔离解包（完整链+序号 sha 全断言）→**5/5 读通全 JET4：内部表 62 实例（按源 sha 去重 49=4 版本；V4 直接 vs 包裹字节异但 schema/表/行数输出全同——差异在非 schema 页；逻辑族 36）、**500 列实例**（a03 首轮 380 系其解析器多词类型分词假阳性，补段自纠 500==lead 实测；SQL 面 311 列）、行数 876453、schema/count/export 错误全 0、读不出项 0**；镜像对分别登记合并留块6。**a02 本轮存活完成 geom 原始字节提取**：tgaz geom 表 INSERT 1/记录 1（三途径互证含 AUTO_INCREMENT=2；全文件 1432 行），raw 33B（\0/\\ 转义）→decoded 25B sha cfe2b8d4…，MySQL 4B LE SRID=0+WKB LE Point(115.31562,38.94772) consumed==len 闭合，**可验证 1/1 首个无法验证 null**，零替换字符 SQL 未执行（a03 独立双 sha 9379a445/cfe2b8d4 互证；y 超 PRC 面 bbox 系属性标注点非面几何，观察注记）。集成：生成器证据驱动（MDB_EV+schema 解析+类型映射+62 提案+GEOM 引用+缺口 RESOLVED），**SQL 34 提案 byte-identical 保留**，sid 101 唯一，真双跑 0/0（首跑 f-string `{{}}` TypeError 缺陷修正披露 run5-10 日志在证）。**a03 ROUND 14 四项 PASS**（62/380/876453 逐档同值、锁 4 deb 实测、非回归全绿）。**披露 C 裁定：entry/rehearsal M=2 系块轮前既有保留工作树态（mtime 11-19，锚点 668900d4 R1-R14 连续，HEAD blob 6f5987f6 为早前提交变体）——非本轮回归，本轮不提交不回转（R-10），留茶香/Codex 专项裁定正典版**。终态 sha：members 9a859420…/om **b56889f1…**/gaps **a6ed3537…**/SUMMARY **e818e3d9…**；计数成员 7/枚举 96/映射 96/缺口 6（5 RESOLVED+1 encoding 含 geom 状态）。剩余：MDB 全量值/编码规范化/NULL 目录级/二进制字节忠实合同留导入阶段；96 提案批准面；tgaz geom 导入合同；镜像/apt 锁转正+V4 合并块6。证据 .mdb-sql-block4-20261120/（mdb/ 五案+geom/+lead-record-continuation+run5-10）。
- 2026-11-21：**第 4 块收口补正**——SUMMARY 文案统一（62 表实例/500 字段实例/311 列/缺口 5 RESOLVED+1 encoding）；**历史误提交更正：84386df 含 5 个 .mdb 条目合计 296,587,264 字节、4 个唯一 blob（v4_access_zip 与 v4_shapefiles_zip 共享 blob `14d21fc9…`，v4_direct 为独立 blob `5e1dcac0…`）；当前追踪 .mdb=0；历史对象仍在祖先提交，不重写（R-10），处置留茶香裁定；旧回报 bb9b2e5「~295MB」与 cd595db「296652508B」保留原文，以本行更正为准**；Codex 已独立通过 MDB 结构覆盖与 geom 字节核对，第 4 块待本次更正复核后收口；第 3 块 Codex 验收待接，第 5 块待讨论派工。
- 2026-11-21：**第 4 块 Codex 整理验收通过**（茶香本轮派工指令记入；收口补正提交 5d0c9e3 已上 Gitea）；96 提案批准面、MDB 值/编码/NULL/二进制合同与 tgaz geom 导入合同留导入阶段裁定。**第 5/6 块首盒**（30 分钟盒，基线 5d0c9e3）：lead 对账 8004=6103 已归属+1901 无归属，候选 2522 逐件处置 unknown 0；a02 探测 sha 2437/2437 失配 0、栅格 43/43 osgeo 读通（镜像无 gdalinfo CLI 半装态披露，未装依赖）；NoData 传参缺陷 lead 令定点修复（113 波段源未声明真值态，错误键 0）；生成器两缺陷 lead 定点修复后 32 双跑 0/0 字节一致；缺口 6 组（pdb2 跨容器世界文件留块6/WMF 12 待授权/大件 checksum 方法未跑/NoData 导入合同/inventory 历史 issues 3 项留块6/LOCAL_CS 不推导）；镜像候选组 377 留块6；43 提案 PROPOSED_NOT_AUTHORIZED。a03 独立核进行中。
