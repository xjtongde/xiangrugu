# datamgmt —— 香如故数据接入模块

> 状态：Task 1–5 已实现，Task 6 草案精确匹配完整，五件文本源侧期望及CBDB三表类型统计已建立，但导入门仍阻断；阶段存档见下节｜as_of 2026-10-09

本模块长期负责首次建库、数据换版、新增来源、独立验证、彩排、发布和回滚。它是香如故长期运行自有容器中的低频模块，不是独立常驻导入服务。唯一权威源是 `usedata`，运行输入为复制并独立校验后的项目快照，目标是外部 `pg32b/xiangrugu`。

## 必读入口

| 文档 | 职责 |
|---|---|
| `docs/DESIGN.md` | 唯一权威设计：模块边界、合同、保真、验证、版本与发布 |
| `docs/IMPLEMENTATION-PLAN.md` | 已批准规格对应的可执行开发计划；实际写入、构建、部署和提交仍逐项授权 |
| `docs/OPERATIONS.md` | 首次构建、后续更新、失败处理和计划 CLI |
| `docs/PITFALLS.md` | P-01～P-25 强制拦截规则 |
| `config/roots.yaml` | 当前源根、目标实例和安全边界 |

## 当前已有资产

| 路径 | 现状 |
|---|---|
| `config/g4_assertions.yaml` | 旧目标命名下的哨兵原型，阶段 0 必须迁入 release 合同并重建 SQL |
| `truth/` | SQLite、DBF/Shapefile、MapInfo、文本、XLS 等部分源读取能力 |
| `importer/load.py` | 部分载体的 staging 装载原型 |
| `verifier/` | 完整性及部分验证原型 |
| `maintenance/` | 盘点、编码调查和旧配置生成脚本 |
| `recon/` | 首版盘点证据与草案，迁入首个 release 后退役 |
| `contracts/releases/2026-10-06-bootstrap/` | 已验收快照的清点证据和候选合同；最新 metadata 审阅草案 BLOCKED=7,914，历史证据不覆盖，仍禁止导入；入口 review.md、逐组工作表 member-review.md；旧 recon 尚未退役 |
| `tests/` | Task 1–5 包、开发环境、快照、身份、清点和合同合成测试已建立；数据库导入相关测试待后续任务 |
| `src/xiangrugu_datamgmt/config.py` | roots 配置解析、环境覆盖、口令脱敏，不建立数据库连接 |
| `src/xiangrugu_datamgmt/snapshots.py`、`snapshot_transfer.py` | 路径及流式复制、独立摘要校验和完成证书；首个真实快照已验收，结果见 OPERATIONS |
| `src/xiangrugu_datamgmt/model.py` | 成员、处置、运行、产物和验证结果的不可变记录 |
| `src/xiangrugu_datamgmt/identity.py` | 版本化规范输入的稳定 SHA-256 身份；固定黄金向量在 tests/fixtures |
| `src/xiangrugu_datamgmt/naming.py` | 确定性目标名称分配、原名映射及标识符引用；不执行 SQL |
| `src/xiangrugu_datamgmt/inventory.py` | 只读清点、不可变清单及摘要、校验账原始摘要与严格异常证据 |
| `src/xiangrugu_datamgmt/signatures.py`、`archive.py` | 字节签名、ZIP 中央目录预检查及资源限制；不用扩展名推断嵌套归档 |
| `src/xiangrugu_datamgmt/contracts.py`、`config/contract.schema.json` | 不可变版本合同、严格 JSON/YAML 装载、列级编码及逻辑对象断言；Schema 进入自有镜像 |
| `src/xiangrugu_datamgmt/disposition.py` | 精确成员规则、全量处置账、失效断言/目标碰撞/镜像主成员校验及覆盖门 |
| `src/xiangrugu_datamgmt/checksum_candidates.py` | 两类校验账候选的只读预览；精确摘要、NUL 尾部及显式路径绑定，不启用运行例外；真实结果见 release/review.md |
| `src/xiangrugu_datamgmt/source_text.py` | 受限 UTF-8/LF TSV 独立字节读取，不复用 csv/importer；显式 BOM/转义、保留空串与顺序，坏语法/宽度/预算拒绝；三件逐字段源复核见 release/text-review.md，不是数据库验收 |
| `src/xiangrugu_datamgmt/crs_diagnostic.py` | 通用离线WKT诊断：原bytes、轴序、全部authority候选/置信度和预算；锁定pyproj/PROJ目录，不自动赋SRID或转换，不是生产空间读取器 |

## 已确认的实现缺口

2026-10-09用户授权将10月6日后累计开发成果阶段提交至Gitea；
此次仅存档代码、锁、测试、合同草案与证据，不冻结合同，不晋级镜像或替换服务，不导入。
历史证据中的旧Git提交/dirty状态和各批次“未提交”保留原时点；阶段提交本身不回写历史镜像标签。

2026-10-09随后批准CBDB SQLite的78表/76索引对象角色，并完成三表28列只读类型统计。
新增sqlite_profile.py及镜像内inspect-sqlite-types.py；dev单元554通过，最终候选547通过/15仓库产物跳过、runtime smoke通过。
最新统计、空表限制、批准范围与机器证据统一见release/sqlite-review.md最新节；类型/值/目标映射仍待审。
不读其余75表，不访问NAS/PG，不替换dev或晋级别名，不冻结/导入/提交；以下结构段保留历史时点。

2026-10-09 CBDB SQLite 单件结构切片完成：78 表、736 字段、76 主键自动索引；
新增 sqlite_diagnostic.py 与镜像内开发证据探针，31 项合成测试通过，
候选完整 515 通过/12 仓库产物测试跳过，dev 单元 519 通过。
结构证据及78逻辑对象非执行提案统一见 release/sqlite-review.md；
不查询业务行、不读 NAS/连接 PostgreSQL、不替换 dev、不冻结或导入。
Task6仍未完成，Task10载体适配器/值验证尚未实现，正式BLOCKED不变。

2026-10-09随后用户批准上述五件规范值口径和源侧完整流期望，决定与非执行批准投影另存；表名、完整版本值合同及冻结/导入仍未放行。当前事实统一见release/text-review.md最新批准节，元数据定向12/累计单元488通过；下面保留提案准备时点说明。

2026-10-09新增五件文本非执行规范值合同提案及元数据消费测试，绑定既有源证据/批准列与schema；当前待审范围统一见release/text-review.md最新节。原投影及正式合同不变，没有新源/数据库读取，不批准表名、不冻结或导入。测试在32既有dev执行，不涉及产品源码、依赖或镜像变化。

独立JSON Schema校验已加入：原始文档先经锁定jsonschema验证，再走既有模型语义门；
最终候选484项通过，实施与原始合同核验见JSON Schema执行账。
2026-10-08随后获单独授权仅dev晋级，旧镜像导出留存且可运行后重建；
真实watcher476项及pip check通过，B-15恢复。完整事实和自动重测证据统一见JSON Schema执行账。
test/runtime别名未晋级，导入/数据库/冻结边界不变。

下列各段保留各历史批次的测试/部署时点；当前dev状态以本节首段及执行账dev晋级节为准。

五件文本已有源侧规范值期望，不含数据库验证；新增text_values.py负责批准读取/列映射到规范流的受限纯衔接，scripts/prepare-text-source-values.py负责镜像内开发证据探针。当前状态和新证据统一见release/text-review.md最新节，原批准投影及正式合同未改。

纯合成text/bigint/显式NULL有序值比较切片已实现：canonical.py固定无损字节/结构/行流编码，validate.py独立输入逐cell比较及有界脱敏报告；完整候选393项及runtime smoke通过。运行证据、评审修复及镜像身份统一见[执行账](../docs/superpowers/plans/2026-10-08-text-value-progress.md)。不提供真实源/数据库适配器，不等于Task6或完整Task9完成；现有常驻容器未换镜像，正式BLOCKED不变。

2026-10-08两组空间对象组件、chgis、属性/物理行号、二维Point及SRID4326已逐案批准；原X/Y不交换/转换，PRJ/QPJ轴序差异保留，批准投影是非执行sidecar。离线CRS镜像及救急回退已验证，仅dev已更新，完整292及真实watcher284测试通过，B-14部署阻断解除。详情统一见release/spatial-review.md；表名、生产读取器、全版本命名及规范值合同未完成，正式BLOCKED不变。

两组 canary 的两件DBF五个N字段读取/类型已批准并精确源复核，59点原坐标观察及未决对象/空间合同见 release/spatial-review.md；不把诊断路径当生产独立读取器。

1884route 两件DBF字符编码已批准，固定宽度源字节/字符串复核通过；C尾空间保留、N读取和两组组件绑定另有逐案批准。黄金夹具及独立生产读取器、目标映射、几何/CRS合同尚未完成，不是载体适配器或数据库验收。

五件文本读取、83列名称/text/非空、五个派生行号映射及schema归属已批准，决定与非执行投影核验统一见 release/text-review.md 最新节。表名、全版本命名和值合同未完成，不改变 BLOCKED；以下三件提案段为前批历史。

空间关系候选及后续未决归档、4 件 TAB/CPG 字节观察见 `contracts/releases/2026-10-06-bootstrap/spatial-review.md`。Native 声明不等于属性值编码或几何验证；两件外层TAB已按精确文本规则独立批准，不扩展到其他TAB。全量组件绑定、编码及空间合同仍未完成，不自动合并大小写不同或跨容器同名成员。

三件首批制表文本的读取语义已获用户确认，独立源复核通过；三件/70 列的逻辑对象及类型/目标映射提案已登记，入口为 `contracts/releases/2026-10-06-bootstrap/text-review.md`。源复核不等于目标库验收；全版本命名、规范值合同、类型/映射批准和冻结均未完成，处置仍未放行。

- Python 包、最小 `--help` 入口与合同校验/处置模型已建立；完整 CLI、可通过门槛的真实首版合同和运行状态机尚未建立；
- 首版 `sources.yaml`、`decoding.yaml` 仅为阻断候选，未确认逻辑对象、列级编码和独立值期望；
- MDB、SQL dump、XLSX/CSV/ODS、栅格和多层容器尚未全部打通；
- ZIP 成员清点已实现；PRJ、ZIP 成员独立验证器和栅格头独立读取能力仍缺失；
- 发布没有实现影子 schema 和单事务切换；
- `db.py`、`rehearse.py`、`verify.py`、`load.py` 仍默认旧 `cbdb_reh`；
- `build_sources_yaml.py` 仍写死旧 `database=cbdb` 与 `public` schema；
- 部分源读取器写死源路径，XLS 依赖 `/tmp/xlsdeps`；
- Task 1 单元测试已建立；数据接入集成、故障注入、重入和全库回归测试尚未建立。

因此当前仍处于阶段 0：现有盘点只是草案，尚未形成获批的首个 release 合同。不得直接开始全量导入。

## 操作边界

香如故代码、锁定依赖和数据接入工具进入自有镜像；生产环境不挂载源码，配置、密钥与 `/opt/mydocker/xiangrugu/data` 持久目录留在镜像外。`usedata` 经来源核实后复制到 `data/imports/usedata/<snapshot_id>`，校验通过才供项目只读使用，不再建立源临时挂载。创建目录骨架、改代码、构建或替换镜像、读取/复制源、安装依赖、建库、写库、彩排、发布、回滚或删除旧对象，都必须按项目纪律逐阶段获得用户授权。

项目开发代码在 Windows Git 工作区修改并同步到 32 主机 `/opt/mydocker/xiangrugu/deploy` 执行；Windows 不运行项目代码。`xiangrugu-dev` 是整个项目的常驻开发容器，`datamgmt` 作为首个模块由它监视和测试。远端 `deploy` 不是第二个编辑源，禁止直接修改后不回传 Git。
