# 香如故容器化数据接入模块 Implementation Plan

> 状态：Task 1–5 已实现并验证，Task 6 草案经选择器修复后模型通过、完整精确匹配，但导入门仍阻断；Git 提交待单独授权｜as_of 2026-10-07
> 依据：`rules.md`、`datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md`、`datamgmt/config/roots.yaml`
> 范围：只规划实现，不授权 Git 提交/推送、镜像拉取/构建、主机挂载、服务启停、数据库写入或正式导入。

**Goal:** 把唯一权威源 `usedata` 经可审计、可复现、可独立验证的容器化流水线导入 `pg32b` 的新数据库 `xiangrugu`，并把该能力保留为香如故项目中可反复使用的低频模块。

**Architecture:** 自有代码、依赖和工具全部固化进香如故自建镜像；开发、测试和生产运行同一套镜像构建链，生产不挂载源码。源经来源核实、复制和独立校验后保存到 `/opt/mydocker/xiangrugu/data/imports/usedata/<snapshot_id>`，容器从 `/data/imports/usedata/<snapshot_id>` 只读使用；项目生产数据持久化在 `/opt/mydocker/xiangrugu/data/persistent`，运行证据在 `/opt/mydocker/xiangrugu/data/var`。容器只通过 PostgreSQL 标准协议连接外部 `pg32b`，不修改 PostgreSQL 镜像，也不向任何第三方镜像注入自有代码。

**Tech Stack:** Python 3.11、pytest、psycopg 3、PyYAML、Pydantic；PostgreSQL 18/PostGIS 3.6 原版镜像仅在 Task 7 起用于隔离测试。表格使用 `xlrd`、`openpyxl`、`odfpy`；GDAL/OGR、MDBTools、Jackcess 等随对应适配器任务加入同一自有镜像，不在 Task 1 预装，且不引入 LibreOffice。Docker/Compose 负责构建和运行；具体镜像 digest、系统包版本及 Python 哈希锁在执行时从官方来源核实并写入锁文件。

---

## 0. 执行边界与完成定义

- 本计划覆盖 `datamgmt/` 数据接入模块及项目开发环境。现阶段常驻开发容器运行真实 watcher/测试进程；候选镜像运行一次性命令，未来常驻应用入口建成后复用同一开发目标和镜像内模块。
- 不用 `sleep infinity` 伪装常驻服务，不把导入目录当成项目长期生产数据，不把旧 `cbdb` 当作来源或验收基线。
- 第三方镜像保持原样，只按公开标准接口使用。测试数据库镜像仅用于隔离集成测试，正式目标始终是外部 `pg32b`。
- 每个任务遵循 RED → GREEN → REFACTOR：先写失败测试并确认失败原因，再做最小实现，再运行任务级和累计回归。
- 每个任务末尾列出的 `git commit` 都是建议检查点，必须再次获得用户明确授权后才可执行；本计划获批不等于授权提交。
- 任何 Docker 拉取/构建、SSH、宿主机目录或挂载变更、容器启停、数据库创建/写入，也都在执行时单独说明影响并等待授权。
- 模块完成必须同时满足：全量成员有处置、源字节可追溯、双路径验证一致、失败不污染正式库、同源/配置/提交/镜像可重复得到同一结果、两次隔离演练结果一致。

## 1. 阶段与授权门

路径约定：任务 2–17 的 `Files` 中，裸列的实现文件均位于 `datamgmt/src/xiangrugu_datamgmt/`，裸列的测试路径均以 `datamgmt/` 为根；`config/`、`sql/`、`docs/` 也均指 `datamgmt/` 下的同名目录。未按此约定列出的路径均从仓库根解析。

| 阶段 | 任务 | 退出条件 | 新授权 |
|---|---:|---|---|
| A 容器与合同基础 | 1–6 | 镜像链可复现；只读扫描完成；首版合同经人工复核冻结 | 构建镜像、读取并复制 `usedata`（实际执行另授权） |
| B 通用内核 | 7–9 | 标准协议、审计状态机、独立比较器通过隔离测试 | 启停隔离测试数据库 |
| C 格式适配器 | 10–15 | 每类成员都能导入或形成明确拒绝/隔离处置 | 如需真实样本，仅只读访问已验证快照 |
| D 发布与验收 | 16–18 | 原子发布、全量处置、两次演练一致、证据包完整 | 创建/写入候选库；正式构建和发布另授权 |

## Task 1：建立自有镜像、包骨架和可复现工具链

2026-10-07 验证完成：初始开发环境契约 RED 为 3 个失败；watcher 测试期间变更漏检的回归先 RED 后 GREEN。最终镜像契约 11 项通过，开发 watcher 单元测试 5 项通过。源码注释的受控同步使运行序号从 1 增至 2、退出码为 0，容器 ID 和启动时间不变；注释随后恢复。镜像均使用非 root 用户，runtime 无 pytest，开发源码只读、无网络且无 imports 挂载。Task 1 的实现及验证事项已完成，以下提交项仍不执行。

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `docker-compose.yml`
- Create: `datamgmt/pyproject.toml`
- Create: `datamgmt/requirements.in`
- Create: `datamgmt/requirements.lock`
- Create: `datamgmt/requirements-dev.in`
- Create: `datamgmt/requirements-dev.lock`
- Create: `datamgmt/config/toolchain.lock.yaml`
- Create: `datamgmt/src/xiangrugu_datamgmt/__init__.py`
- Create: `datamgmt/src/xiangrugu_datamgmt/__main__.py`
- Create: `scripts/sync-dev.ps1`
- Create: `scripts/build-task1.sh`
- Create: `datamgmt/src/xiangrugu_datamgmt/devwatch.py`
- Test: `datamgmt/tests/unit/test_devwatch.py`
- Test: `datamgmt/tests/unit/test_package_contract.py`
- Test: `datamgmt/tests/container/test_image_contract.py`
- Test: `datamgmt/tests/container/test_dev_environment.py`

- [x] 先写测试：包可导入、`python -m xiangrugu_datamgmt --help` 返回 0；镜像内存在代码和工具，运行用户非 root；生产服务不挂载源码，`xiangrugu-dev` 只读挂载固定 `deploy` 到 `/workspace`，第三方测试库服务没有自有代码卷。
- [x] 获得授权后核实 `python:3.11.16-slim-bookworm` 官方标签并解析 `linux/amd64` 完整 digest；Task 1 不拉取 PostGIS，测试数据库镜像留到 Task 7 再锁定。
- [x] 构建测试目标并运行指定测试，确认因包、Dockerfile 或锁文件尚不存在而 RED，而非测试自身错误。
- [x] 实现最小多阶段 `dev`/`test`/`runtime` 镜像：共同固化项目包、psycopg、PyYAML、Pydantic、证书/时区；开发/测试依赖只进入相应目标，全部以非 root 用户运行。格式工具由 Task 10–15 按失败测试逐项加入，禁止预装 LibreOffice。
- [x] 实现 Windows PowerShell 同步入口：只把当前 Git 工作树中已跟踪及未忽略的新文件覆盖同步到 32 主机固定 `deploy`；不得上传 `.git`、`.secrets`、`.env`、运行数据或 `usedata`，也不得在未获删除授权时自动清理远端文件。
- [x] `xiangrugu-dev` 常驻运行真实文件监视/测试进程，源只读挂到 `/workspace`，持久数据分别挂到 `/data/persistent`、`/data/var`；不连接数据库、不挂 `usedata`、不使用伪保活命令。
- [x] 运行 `docker build --target test -t xiangrugu:test .` 和 `docker run --rm xiangrugu:test python -m pytest datamgmt/tests/unit/test_package_contract.py datamgmt/tests/container/test_image_contract.py -q`，确认 GREEN。
- [x] 用 `docker image inspect` 和 Compose 配置展开结果复核 OCI 标签、非 root 用户、生产无源码 bind mount、开发挂载源只读、无密钥入层；把复核逻辑纳入测试。启动 `xiangrugu-dev` 后验证 watcher 存活、初始测试已执行、同步一个无害哨兵变化能触发新一轮测试且无容器重建。
- [ ] 经单独授权后提交：`git commit -m "build(datamgmt): establish reproducible container toolchain"`。

## Task 2：实现配置模型与项目源快照校验

2026-10-07 验证完成：缺少 config/snapshots 模块时得到 RED；不可读目录静默跳过缺陷另以 RED 复现后修正。32 开发容器累计单元测试 30 项通过，新测试镜像累计单元和镜像契约 37 项通过。复制测试全部使用容器临时目录的合成字节，未读取真实 usedata。开发容器持续运行，新 dev/test/runtime 镜像已经构建；开发容器无需替换，仍通过只读工作树获得源码。当前只提供配置及快照 Python API，实际源接入与完整 CLI 留在后续授权阶段。

**Files:** `config.py`、`snapshots.py`、`tests/unit/test_config.py`、`tests/unit/test_snapshots.py`；修改 `config/roots.yaml`、`docker-compose.yml` 和镜像契约测试。

- [x] 为 `RuntimeConfig`、`SourceRoot`、`TargetConfig` 写失败测试：默认快照路径、环境变量覆盖、YAML 禁止口令、正式目标固定为 `xiangrugu`。
- [x] 使用合成小样测试来源核实、逐文件复制、独立摘要校验及完成证书：错误来源、缺件/多件、摘要不同、越界符号链接、源复制期间变化、目标已存在、空间不足、复制中断及有效快照。
- [x] 实现严格配置解析；敏感项只接受运行时 secret/file 或环境变量，日志输出脱敏。
- [x] 将候选操作服务的数据卷改为普通只读项目快照卷，移除旧 `rslave` 动态源传播配置；开发容器保持现状。实际快照接入和数据操作尚未授权。
- [x] 实现版本化快照和完成证书；导入前、每批前及发布前复核快照。输出不写源或快照，不要求特殊挂载，不修改全局 CIFS。
- [x] 在 32 的测试镜像运行本任务及累计单元测试；本任务只用合成样本，真实源读取/复制另授权。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): validate config and source snapshots"`。

## Task 3：定义领域模型、稳定标识和数据库命名

2026-10-07 完成：模块缺失时 RED；验证结果不能同时 CONFORMS 和有差异的约束另以 RED 复现后实现。32 开发容器累计单元测试 58 项通过，新测试镜像累计单元及镜像契约 65 项通过。黄金向量由 32 上独立规范 JSON/hashlib 计算并固定保存。自有 dev/test/runtime 镜像均已重建，开发容器仍以同一身份运行；未访问真实源，未连接数据库。

**Files:** `model.py`、`identity.py`、`naming.py`、`tests/unit/test_identity.py`、`tests/unit/test_naming.py`。

- [x] 写失败测试，固定 `SourceMember`、`Disposition`、`ImportRun`、`Artifact`、`ValidationResult` 的必填字段与不可变字段。
- [x] 写稳定 ID 测试：ID 由源版本、规范相对路径、归档成员路径和源字节摘要决定；Unicode、大小写和路径分隔差异不会碰撞或静默合并。
- [x] 写命名测试：schema/table/column 名可逆、长度受限、保留字安全、碰撞确定性解决，并保留原名映射。
- [x] 做最小实现，禁止使用 Python 进程随机哈希和扫描顺序生成名称。
- [x] 运行本任务及累计单元测试，保存固定 golden vectors。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): define stable identities and naming"`。

## Task 4：实现只读清点与不可变源清单

2026-10-07 验证完成：初始 21 项测试 RED；补充预算耗尽后的虚假空摘要、临时缓存越界、普通文件不需临时磁盘副本、校验账资源限制及超限清单排序回归，逐项 RED → GREEN。最终本任务 43 项、累计单元 101 项、镜像累计 108 项通过。扫描前后合成源树权限/mtime/摘要不变；缓存生产默认 `/data/var`，测试显式 `/tmp`。重复 ZIP 物理成员保留序号并阻断，未知格式不丢弃，NUL 校验账无豁免。当前仅支持标准单卷 ZIP Stored/Deflate；ZIP64 和其他压缩方法明确阻断，需后续实际源发现后补齐受限读取，不会被视为完整清点。真实源未访问、未复制；以下提交项仍不执行。

**Files:** `inventory.py`、`signatures.py`、`archive.py`、`tests/unit/test_inventory.py`、`tests/fixtures/inventory/`。

- [x] 写失败测试，覆盖普通/空文件、符号链接、大小写冲突、未知/伪装扩展、ZIP 和嵌套归档、压缩炸弹限制、不可读成员，以及校验账 NUL 尾部、坏行、重复项、路径越界和摘要格式错误。
- [x] 定义 `InventoryBuilder.scan(root) -> InventoryManifest`；记录 SHA-256、大小、媒体签名、容器链和读取错误。
- [x] 实现流式读取及单成员大小、总解压量、嵌套深度和成员数限制；绝不向源目录写临时文件。
- [x] 以规范排序序列化清单并计算自身摘要；校验账先保存原始文件摘要再解析，任何格式异常进入机器证据，不得静默跳过；相同源字节重复扫描必须字节级一致。
- [x] 运行夹具测试及“扫描前后源树元数据/摘要不变”回归测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): build immutable readonly inventory"`。

## Task 5：实现发布合同与全量处置判定

2026-10-07 验证完成：初始 53 项 RED，补测非法文本编码、镜像主成员、目标冲突和校验绕过；最终本任务 72 项、累计单元 173 项、镜像内全套 180 项通过（警告视为错误）。自有 dev/test/runtime 均已重建，Schema 进入镜像；只读、无网络 runtime 合同/Schema smoke 通过，常驻开发容器身份及启动时间未变。精确匹配、失效断言、完整覆盖和 BLOCKED 门已实现；审批引用、镜像相等性证据及验证器名称只是声明，未执行实际独立验证或数据库操作。真实首版合同、NUL 特例及真实源核实/复制尚未开始；以下提交项仍不执行。

**Files:** `contracts.py`、`disposition.py`、`config/contract.schema.json`、`tests/unit/test_contracts.py`、`tests/unit/test_disposition.py`。

- [x] 写失败测试：每个清单成员必须且只能匹配一条规则；零匹配、多匹配、模糊规则、失效断言和无理由忽略均拒绝。
- [x] 使用 DESIGN §5 规定的处置枚举 `IMPORT`、`MIRROR`、`NON_TABULAR`、`BLOCKED`，不提供默认 `ignore`；不得引入含义不同的第二套枚举。
- [x] 实现合同 Schema 和确定性匹配；合同包含源版本、编码、格式族、目标、验证器、预期计数/摘要及例外理由。
- [x] 实现 `DispositionLedger.coverage()`；只有覆盖率 100%、重复匹配 0、未解释成员 0 才能过门。
- [x] 运行恶意/边界规则测试与累计单元测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): enforce complete disposition contracts"`。

## Task 6：生成并冻结首版 `usedata` 合同

2026-10-09随后批准SQLite78表/76索引角色、完成三表28列只读类型统计；单元554、最终候选547通过/15仓库产物跳过，runtime smoke通过。
完整机器证据与未批准类型/值/目标映射边界见release/sqlite-review.md最新节；Task6/Task10未完成，不扩大读取或导入。

2026-10-09 CBDB SQLite单件只读结构切片：TDD新增31项，dev单元519及候选515通过/12仓库产物跳过；
源快照前后摘要一致，78表/736字段/76主键索引，非执行逻辑对象提案和待审边界见release/sqlite-review.md。
本批只连接源SQLite读取结构，不查询业务行、不读NAS/连接PG、不替换常驻/冻结/导入/提交；
Task6未完成，不能冒充Task10适配器。详细执行证据见docs/superpowers/plans/2026-10-09-sqlite-structure-progress.md。

2026-10-09随后用户“同意”仅批准五件规范值口径与源侧摘要期望，决定绑定原提案，非执行批准投影另存；原提案/合同保持不变，表名/全版本合同/冻结/导入仍未批准。元数据12及累计单元488通过，完整dev套件环境限制及证据续接同一执行账“随后五件规范值批准记录”；本Task仍未完成。

2026-10-09用户“同意”批准整理五件文本规范值合同提案及元数据测试；既有源期望绑定为非执行待审sidecar，原投影/合同不覆盖，不读取源或数据库，不批准表名、不冻结导入。本批TDD、完整测试的dev环境限制及审阅见[执行账](../../docs/superpowers/plans/2026-10-09-text-value-contract-progress.md)，提案内容统一见release/text-review.md最新节；本Task仍未完成。

2026-10-08独立JSON Schema批：用户“同意”授权锁定验证器及原始文档校验；
最终候选484项通过，未改Schema或正式合同、未读源/接库/冻结/替换长期容器/提交。
详细证据见docs/superpowers/plans/2026-10-08-json-schema-progress.md。
旧dev缺依赖导致watcher收集失败（B-15）；随后单独批准仅dev晋级，
回退镜像导出及可运行验证后重建，真实watcher476项通过，B-15恢复；Task6仍未完成。

2026-10-08五件源侧值期望批：用户“同意”批准已有文本读取/规范流衔接及只读五件项目快照；TDD后修复文件BOM与列codec边界，最终候选全套及runtime smoke通过，五件新非执行源期望生成并独立参考核验。细节只展开于release/text-review.md最新节，实施/失败证据见docs/superpowers/plans/2026-10-08-text-source-values-progress.md。不改正式合同或旧批准投影，不读NAS、接库、冻结、替换长期容器、提交推送；表名/完整值合同未完成，BLOCKED不变，本Task仍未完成。

2026-10-08 五件schema批准：用户“同意”批准上批明确归属提案；决定绑定提案/列投影摘要及五个身份，固定runtime核验5个目标组件模型、83列/5行号证据不变后新增非执行批准投影。4项新/累计87产物断言及292回归通过。Ruling：不扩大到表名、全版本命名、规范值、冻结或导入，正式合同/current及BLOCKED不变；真实导入前先通知并确认pg32b旧数据处置。本批无源/快照复读、代码依赖镜像/服务、数据库或Git操作，细节见release/text-review.md最新节，Task6未完成。

2026-10-08 五件文本列批准：用户“同意”批准83列现有名称/text/nullable=false及五个__src_rownum bigint；决定绑定完整旧提案摘要，批准投影另存。固定runtime核验83编码/列名和5行号范围，三项新/累计83产物断言及292回归通过。Ruling：不扩大到schema/表名、主键、冻结或导入，源值及正式合同不变；本批无源/快照复读、代码依赖镜像/服务、数据库或Git操作。一次性脚本字段误用查明后修正，不改产品API；细节见release/text-review.md最新节，BLOCKED不变，Task6未完成。

2026-10-08 SRID批准批：用户“继续”批准精确两组SRID4326且原X/Y不变；新决定绑定诊断/几何投影摘要，固定runtime核验2身份/4声明及PROJ目录后另存批准投影。Ruling：保留PRJ/QPJ轴序差异，不把EPSG轴序变成交换坐标授权；只更新非执行sidecar，不改变BLOCKED规则或旧证据。3项产物断言及292回归通过，正式合同摘要/current不变，详见release/spatial-review.md最新节。无新源读取、代码依赖镜像/服务、数据库、冻结或Git变更，表名/规范值及生产读取器未完成，Task6未完成。

2026-10-08 dev恢复批：用户“继续”批准替代export/import救急备份；tar及非root回退镜像保留，原包/启动配置/pip核验通过。完整292测试后仅compose替换dev，真实watcher284通过，pg32/pg32b前后状态一致。Ruling：救急副本不冒充原构建可复现镜像；root-owned tar不放宽权限，宿主算摘要再非root留证。8件证据/7断言回传，详情见release/spatial-review.md最新节；B-14部署阻断解除，防漏自动化未实现。无代码依赖构建、源读取、数据库、冻结或Git变更，SRID仍待批准，Task6未完成。

2026-10-08 dev备份批：用户“继续”批准已明确提出的container commit救急回退步骤。实际exit1，旧平台manifest内容摘要缺失，备份标签未生成；dev恢复运行/未暂停，容器ID与本轮基线一致，pg32/pg32b未变。Ruling：执行原提案失败边界，停止，不自行export/import或替换；下一批替代根文件系统备份须另获授权。日志/验证/两项断言回传核对，细节见release/spatial-review.md最新节；无代码依赖构建、源读取、数据库、冻结或Git变更，Task6未完成。

2026-10-08离线CRS工具批：用户“同意”批准依赖/code/tests及32构建、自有dev替换范围。27初始RED、歧义标志1RED/28通过后最终292GREEN与镜像契约/受限离线复测通过；锁定pyproj/wheel及实际PROJ/EPSG目录。既有PRJ/QPJ均4326候选、轴序不同，无新源读取或赋SRID。Ruling：我方未先固定旧镜像tag，旧摘要无法寻址，回退条件未满足，未执行dev替换，B-14及新备份授权待处理；不得报常驻开发环境已更新。详情/证据统一见release/spatial-review.md最新节。正式合同/BLOCKED不变，无数据库、冻结、提交推送，Task6未完成。

2026-10-08 Point批准：用户“同意。继续”批准两组二维geom映射，决定绑定精确提案，批准投影另存；2映射/4既有PRJ-QPJ声明核验通过。runtime实测pyproj/osgeo、projinfo/gdalsrsinfo不可用；CRS离线诊断、锁依赖、自有镜像构建/仅替换dev方案待授权，详情统一见release/spatial-review.md。Ruling：工具缺口不表示源CRS未知，不赋0/4326；无新源/快照读取，诊断不冒充G5。262回归及3产物断言通过；BLOCKED不变，无代码依赖镜像/服务、数据库、冻结或Git变更，Task6未完成。

2026-10-08 属性批准：用户“同意，继续”批准两组24列名称/非空、14字符text和各一物理行号映射，决定绑定精确提案，批准投影另存。既有报告118坐标对字节及序号复核后，新增二维Point映射提案。Ruling：不把几何类型提案与CRS/SRID混批；未指定SRID不是默认0授权，QPJ声明不代替PRJ解析；本轮无新源/快照读取，诊断不冒充生产读取器/G5。262回归与4产物断言核对通过，细节见release/spatial-review.md；BLOCKED不变，无代码依赖镜像、数据库、冻结或Git变更，Task6未完成。

2026-10-08 schema批准：用户“同意，继续”仅批准两组归入chgis，决定绑定精确原提案及对象身份。固定runtime核验2个目标组件模型和24列身份/名称，新增属性映射整体提案；Ruling：批准不扩大到表名、属性/派生列、几何/SRID或导入，本轮只处理既有证据，不声称新做源/快照校验。首次诊断入口被CLI拒绝且未产出，核对Dockerfile后仅修正一次性入口；262回归及3产物摘要核对通过。细节见release/spatial-review.md；BLOCKED不变，无代码依赖镜像、数据库、冻结或Git操作，Task6未完成。

2026-10-08 组件绑定批准：用户“同意。继续”批准两组各六件及SHP身份锚定，决定另存；12组件重新核对，同包README/HTML原字节及来源说明留证，全快照前后与262项回归通过。Ruling：CHGIS来源支持将暂定harv修订为chgis提案，但schema/目标映射未批准；修订步骤仅处理既有证据，不冒充再次源复核。来源限制原样记录，不推断许可；其他成员仍BLOCKED。细节统一见release/spatial-review.md；无代码依赖镜像变更、数据库、冻结或Git提交推送，Task6未完成。

2026-10-08 空间对象提案：用户令继续，固定runtime复用身份/命名/模型API登记两组12组件24属性列，包含新读两件QPJ；外包16中央成员匹配，其他4件留BLOCKED。七件对象范围顺序无关、原五件TSV名称未变，2目标/14编码模型通过。Ruling：SHP锚定身份和组件/目标仅提案，QPJ声明不直接赋SRID，harv暂分组待来源审阅，不放宽BLOCKED targets模型或全版本命名门。全快照前后及262项回归通过，证据回传核对；细节见release/spatial-review.md，无代码依赖镜像变更、数据库、冻结或Git提交推送，Task6未完成。

2026-10-07 N字段批准记录：用户“继续，同意。”批准两件精确DBF五个N列外围0x20读取及numeric(19,5)/bigint类型，决定另存。固定runtime重读590个N值，以Decimal/int对手工整数系数/Fraction逐值精确一致，全部无舍入适配批准类型；826个C值重核、尾空间保留。Ruling：不扩大到空白NULL、日期、空间绑定/目标映射或SRID，不冒充生产读取器。全快照前后及262项回归通过，证据回传核对；细节见release/spatial-review.md，无代码依赖镜像变更、数据库、冻结或Git提交推送，BLOCKED=7,914，Task6未完成。

2026-10-07 数值/点观察：用户令继续，固定runtime只读核验两组canary的590个N字段候选、C/N空间字节及各59个Point；索引/顺序坐标字节一致、全点有限且bbox匹配，N均普通十进制候选，两条精确构造一致。Ruling：去N空间/Decimal仅在候选中，不自动批准类型、C去空间、NULL、日期或SRID，不等同生产验证器/G4/G5。细节及待批准提案见release/spatial-review.md。全快照前后及262项回归通过，证据另存回传核对，无代码依赖镜像变更、数据库、冻结或Git提交推送，BLOCKED=7,914，Task6未完成。

2026-10-07 DBF 字符列批准记录：用户“同意，继续”批准1884route两件精确DBF各7字符列 cp1251/UTF-8；决定另存。固定 runtime 两条源字节分区路径比较1,416个字段切片、826个字符值零差异，保留全部固定宽度空格/NUL，不解析其他类型。Ruling：诊断路径不是经黄金夹具验证的生产读取器，编码批准不包括填充/NULL/目标/空间；正式逻辑值未决，处置仍BLOCKED。全快照前后及262项回归通过，报告回传核对，详细证据见release/spatial-review.md。无代码依赖镜像变更、数据库、冻结或Git提交推送，Task6未完成。

2026-10-07 空间 canary 观察：用户令继续，在固定 runtime 只读检查 1884route 同包两组的 10 件核心/声明成员；各 59 条 SHP/SHX/DBF 物理记录、12 字段，索引偏移/长度匹配，CPG 分别1251/UTF-8，与全字符列严格候选相容。原始字段、删除标记、PRJ、错码位置另存证据，细节见 release/spatial-review.md。Ruling：诊断不是新增产品读取器或正式验证器；几何相同但 DBF 不同不判整对象 MIRROR，不自动批准编码/填充/数值/CRS。全快照前后及262项回归通过，证据另存回传核对，无代码依赖镜像变更、数据库、冻结或 Git 提交推送，BLOCKED=7,914，Task 6 未完成。

2026-10-07 新增文本批准记录：用户答复“同意，继续”批准 m004812/m006642 的精确读取提案；决定另存，不覆盖前三件。固定 runtime 重新源复核 20,550 字段零差异，五件/83 列对象合并提案使用既有身份/命名/模型 API；全快照前后及 262 项回归通过。Ruling：读取批准不等于类型/schema/目标批准，harv 只为新增 Harvard 文本的暂定分组；全版本分配和值规范未齐备，不放宽 BLOCKED 模型、不冻结。新证据回传核对，源、代码依赖镜像、数据库与 Git 不变，Task 6 未完成。

2026-10-07 新增文本候选核验：用户令继续，固定 runtime 对 m004812/m006642 全文比较字面引号、双引号及反斜杠解释，成功候选与独立字节路径逐字段一致；上海两个反斜杠均邻接引号，无转义候选失败。完整证据及待批准解释见 release/text-review.md。Ruling：复用现有 API、不改行为，候选成功不自动扩大前三件读取批准；解释未获批则保持 BLOCKED，数量和值仅为候选观察。全快照前后核验及 262 项回归通过，无代码依赖镜像变更、源修改、冻结、数据库或 Git 提交推送，Task 6 未完成。

2026-10-07 空间未决字节核验记录：用户令继续，固定 runtime 只读核验 9 个物理归档及 4 件 TAB/1 件 CPG，逐层摘要和全部中央目录匹配清单；对应归档中无 1 DBF/3 PRJ 同后缀成员。两件 Native TAB 声明 WindowsSimpChinese/23 字段，未检出受限 File 行；另两件外层 TAB 呈制表头部，CPG 原文 UTF-8。Ruling：观察不批准大小写绑定、DAT 编码、补件/CRS 或扩展三件文本读取合同；新增文本另审阅。全快照前后校验通过，报告另存回传核对，不覆盖旧清单级证据。无代码依赖镜像变更、源修改、冻结、数据库或 Git 提交推送；BLOCKED=7,914，Task 6 未完成。

2026-10-07 空间组件审阅记录：用户令继续按完整容器关系整理组件。本批在固定自有 runtime 处理既有清单，生成 705 个 Shapefile 与 146 个 TAB/MapInfo 关系候选；同基名 DBF 未找到 1 组、PRJ 未找到 3 组，大小写差异 2 处、未配对 CPG 1 件逐件留证。Ruling：后缀仅作入口，casefold 只报歧义，不跨物理容器拼组，不读首个同名件，不从其他版本补件；本批未重新读取快照字节，不声称通过源未变/格式门。详细证据见 release/spatial-review.md，原合同不变、BLOCKED=7,914；无代码依赖镜像变更、冻结、数据库或 Git 提交推送，Task 6 未完成。

2026-10-07 文本对象审阅记录：用户令继续整理逻辑对象、列级合同和目标映射。本批复用既有 runtime/API，登记三件/70 列非执行 draft，对象身份、原头部/序号、UTF-8、text 与源行号提案、目标名称映射留证；70 编码模型/3 目标模型、三件命名及非法 codec/public schema 负向检查通过。Ruling：BLOCKED 规则禁止业务 targets，不放宽模型；全版本对象未齐备，三件目标名仅预分配，expected_sha256 留 null，目标/类型未批准。源与此前独立证据一致，全快照前后核验通过；原合同及证据不覆盖，BLOCKED=7,914。无代码依赖镜像变更，无冻结、数据库、提交推送，Task 6 未完成。

2026-10-07 独立文本读取授权记录：用户对三件精确 BOM/双引号解释及仅 ACADEMY 反斜杠转义答复“同意，继续”。新增通用受限 source_text 字节读取，31 项手工期望用例 RED→GREEN；重建自有 dev/test/runtime 后，262 项全套及镜像契约通过。三件源与标准库路径逐字段比较 372,106 字段（含头部），零差异；全快照前后校验通过，报告和批准决定另存回传校验，详细范围见 release/text-review.md。Ruling：这是 Task 6 合同准备所需的源读取，不提前实现 Task 11 的装载或全格式适配，不新增依赖、不复用旧猜测/清洗行为、不改变正式合同处置。读取批准不等于冻结/导入；BLOCKED=7,914，未连接数据库、重启既有容器、提交或推送。Task 6 未完成。

2026-10-07 文本审阅进度：用户令继续，复用固定自有镜像只读核验三件文本的全文及显式转义候选。发现 ACADEMY 双引号独用在第 214 物理行失败，12 个反斜杠均为转义引号候选；其他两件相同行列数的不同引号解释仍产生不同值摘要。全文观察、BOM 和待确认语义集中于 release/text-review.md；新增报告另存回传校验。Ruling：不新增产品代码、依赖或镜像，不改任何正式对象/编码/值断言；三件仍 BLOCKED，需用户确认读取解释后才能建立后续独立读取期望。未冻结、写库、提交或推送，Task 6 未完成。

**Files:** 新建 `contracts/releases/2026-10-06-bootstrap/` 下的 `manifest.yaml`、`sources.yaml`、`decoding.yaml`、`assertions.yaml`、`review.md`。

2026-10-07 执行记录：用户已授权源字节读取、复制、独立校验和必要目录权限。前置真实快照 `2026-10-07-bootstrap` 已验收，完整记录见 OPERATIONS 的“32 主机流式快照桥”。Ruling：为遵守 DESIGN §13.3，不给直接路径 API 增设原源挂载；补受限标准流传输桥，所有复制/摘要/校验代码进入自有镜像，宿主只做标准 tar 传输和身份检查。新增 20 项测试按 RED→GREEN 验证，累计单元 193 项、镜像全套 200 项通过。作者自审；未另派 Agent。快照号不自动等于 release_id，后续合同仍须独立清点、覆盖检查和用户书面复核。本 Task 仍未完成。

2026-10-07 清点授权记录：用户同意只读清点快照并生成合同草案。已在固定 runtime digest 使用既有 API 完成 canary、全量枚举及快照前后核验，候选文件和证据已回传 Windows；状态 DRAFT_MODEL_REJECTED，不修改 current、不冻结。三项阻断、原名字面选择器最小对照复现与待裁定事实见首版 release/review.md；本轮未改代码/安装依赖，现有镜像全套 200 项仍通过但未覆盖新发现的真实名缺陷。Ruling：不因模型拒绝而删除/改名 13 个源成员，不启用校验账兼容或重解释路径；完整候选保留，正式覆盖门未运行。Task 6 未完成，旧 recon 不退役。

2026-10-07 修复授权记录：用户同意按 TDD 修复字面名称选择器、更正 NUL 文档计数并重建自有镜像。四项新回归先失败，最小修复后单元 196 项、镜像全套 203 项及契约通过。Ruling：仅把 `[]` 视为原名字面字符，仍拒绝 `*?`，不引入 glob、路径重解释或兼容例外。新镜像对原草案模型校验成功，8,004 成员精确匹配；13 个字面原名保留，BLOCKED=7,918、conforms=false。原生成文件不覆盖，新账及验证报告另存；作者自审未另派 Agent。NUL 数量事实纠正不等于批准兼容解析，缺失路径继续 BLOCKED。Task 6 未完成。

2026-10-07 候选核验授权记录：用户令继续执行两条精确校验账候选；新增 draft 提案与只读预览 API，初始 20 项 RED→GREEN，超大 NUL 声明的分配溢出另以 RED→GREEN 修正；累计 224 单元、231 镜像全套及契约通过。固定 runtime 对已验收快照的两条候选通过，前后快照与原证据摘要均一致；报告另存，详细范围与 digest 见 release/review.md。Ruling：不改原声明、原件或严格清单，不启用运行例外、不冻结、不提交/推送、不访问数据库；BLOCKED 和导入门保持阻断。Task 6 未完成。

- [x] 先用合成清单确认空合同和臆造规则必然失败。Task 5 合成回归已覆盖；2026-10-07 对最新候选另做内存空合同/臆造成员/metadata 大小漂移检查，证据见 `metadata-candidate-negative-checks.json`，未改真实候选或源。
- [ ] 经另行授权核实真实源身份、大小和磁盘预算，复制为项目快照并独立校验；在候选镜像内清点已验收快照，记录源/副本清单摘要、完成证书、Git 提交和镜像 digest。
- [ ] 对所有成员按签名和容器关系分组，逐组指定处置、编码、表/层/成员预期及独立验证方法；不确定项只能 `BLOCKED` 并明确原因，不另设 `quarantine`/`reject` 处置枚举。
- [ ] 把 `SHA256SUMS-b2` 原始摘要 `900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb` 及尾部 126 NUL 异常写入合同（2026-10-07 同摘要逐字节复核并获用户授权更正原计数）；只对这个精确摘要批准兼容解析，源件不得改写。再运行 Schema、100% 覆盖、碰撞、编码抽样和源未变检查。
- [ ] 用户书面复核后才把 release 改为 frozen；冻结前禁止写针对真实源布局的特例加载器。
- [ ] 经单独授权后提交：`git commit -m "docs(datamgmt): freeze bootstrap usedata contract"`。

2026-10-07 分组审阅记录：用户令继续逐组明确对象、编码和处置。本批按 DESIGN §5 将三本校验账及一件精确 Thumbs.db 登记在独立 draft 修订，8,004 唯一匹配、BLOCKED=7,914；严格异常仍阻断，参考件实际保存验证尚未实现。核验三件首批 .tab 的头部，记录为制表文本候选而非按后缀套 MapInfo，不推断全文/逐列编码。无代码或依赖变更，231 镜像测试通过；Ruling：原合同及旧证据不覆盖，新增证据逐份校验回传，续接工作表为 release/member-review.md。作者自审；未另派 Agent、未冻结、未提交、未打开任何数据库。Task 6 未完成。

## Task 7：实现 PostgreSQL 标准协议传输层和审计表

**Files:** `postgres.py`、`audit_schema.py`、`sql/audit.sql`、`tests/unit/test_postgres.py`、`tests/integration/test_audit_schema.py`。

- [ ] 写单元测试确认 DSN 参数化、标识符安全、事务边界、COPY 流式接口和日志脱敏；禁止拼 shell、调用 `docker exec` 或依赖目标主机路径。
- [ ] 写集成测试定义 run、source_member、disposition、artifact、object_map、validation、event、publish 八类审计记录及约束。
- [ ] 通过 psycopg 3 实现 `PostgresTransport`、事务、COPY 和只读查询接口。
- [ ] 在原样第三方测试库镜像上运行迁移两次证明幂等；故障注入后确认完整回滚。
- [ ] 运行本任务测试和累计回归。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): add postgres transport and audit schema"`。

## Task 8：实现运行状态机、资源预算和可取消执行器

**Files:** `run.py`、`resources.py`、`process.py`、对应三个 `tests/unit/test_*.py`。

- [ ] 写失败测试固定 planned → inventory → loading → validating → ready_to_publish → published，任一步可 failed/cancelled，非法回跳拒绝。
- [ ] 写资源测试覆盖超时、磁盘预算、内存/进程限制、输出上限、子进程树取消和秘密脱敏。
- [ ] 实现只接受参数数组的可取消执行器；记录工具版本、参数摘要、输入输出摘要和退出状态。
- [ ] 每批前调用快照校验；快照缺失、源摘要变化或预算越界立即停止且不得发布。
- [ ] 运行故障注入和累计回归，确认无遗留子进程和孤立临时文件。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): control runs resources and processes"`。

## Task 9：实现独立规范化比较器

2026-10-08用户“同意”批准后，纯合成text/bigint/NULL有序切片已实施并完成候选验证；证据及授权边界见[执行账](../../docs/superpowers/plans/2026-10-08-text-value-progress.md)。本Task完整类型/真实适配器未完成，Task6和合同冻结未放行；下文待审记录为前批历史。

2026-10-08规格确认后计划批：用户“继续”回应书面规格审阅门，已编写docs/superpowers/plans/2026-10-08-text-value-comparison.md待审计划；限定纯合成text/bigint有序切片，若实施则提前服务Task6合同准备，顺序调整及代码/测试/候选镜像范围仍须计划批准。只写文档，不实现、不读源/数据库、不替换dev、不Git提交推送；完整Task9及Task6仍未完成。以下规格编写记录为前批历史。

2026-10-08仅规格编写：用户“同意。继续”批准先形成通用值比较规则书面规格，待审件为docs/superpowers/specs/2026-10-08-text-value-comparison-design.md。第一切片只定义text/bigint/显式NULL及有序比较，不覆盖本Task的全部类型、无序/Merkle或真实源/库适配器，不勾选实施项。本批没有产品代码、源/数据库读取、冻结或Git提交推送；书面规格审阅通过后才编写实施计划，实施顺序需单独确认，不把本技术细化当Task6已完成。

**Files:** `canonical.py`、`validate.py`、`tests/unit/test_canonical.py`、`tests/integration/test_validation.py`。

- [ ] 写失败测试固定 NULL、空串、NaN、Infinity、十进制、时区、Unicode、二进制、JSON、几何和栅格元数据规则。
- [ ] 定义源侧与库侧两个独立适配接口；验证器不得复用加载器中间值作为“源真值”。
- [ ] 实现有序/无序摘要、分块 Merkle 摘要、计数/字段/类型/约束断言和可定位差异报告。
- [ ] 故意制造截断、编码替换、NULL 转换、SRID 和浮点差异，确认全部拒绝。
- [ ] 运行本任务和累计回归，保存小型 golden evidence fixture。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): add independent canonical validation"`。

## Task 10：实现 SQLite 适配器

**Files:** `adapters/sqlite.py`、`verifiers/sqlite.py`、`tests/adapters/test_sqlite.py`。

- [ ] 写失败测试覆盖表、视图、无 rowid 表、复合主键、BLOB、动态类型、非法页和损坏库。
- [ ] 加载器使用 SQLite 只读 URI 流式读取并写影子 schema，不复制回源目录。
- [ ] 验证器用独立查询路径生成源侧规范摘要，与 PostgreSQL 导出摘要比较。
- [ ] 对不支持对象写明确处置，不静默跳过 sqlite_master 成员。
- [ ] 运行适配器、验证器和累计测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): import and verify sqlite sources"`。

## Task 11：实现 CSV/TSV/Excel/DBF 表格适配器

**Files:** `adapters/tabular.py`、`verifiers/tabular.py`、`tests/adapters/test_tabular.py`。

- [ ] 写失败测试覆盖 BOM、GB18030/UTF-8、混合换行、重复/空列名、嵌入换行、公式、日期系统、隐藏/空表、DBF codepage 和逻辑删除记录。
- [ ] 编码和方言只由冻结合同指定；探测只能给候选，不能自动改合同。
- [ ] 用流式 COPY 导入；`.xls`、`.xlsx`、`.ods` 分别使用锁定版本的 `xlrd`、`openpyxl`、`odfpy` 读取并保留工作表/单元格语义映射，不经 LibreOffice 转换。
- [ ] 独立验证器直接读取原格式，比较工作表/记录/字段计数和规范摘要。
- [ ] 运行格式矩阵、故障注入和累计测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): import and verify tabular sources"`。

## Task 12：实现 Shapefile 适配器

**Files:** `adapters/shapefile.py`、`verifiers/shapefile.py`、`tests/adapters/test_shapefile.py`。

- [ ] 写失败测试覆盖组件集合、缺件、多/空/无效几何、Z/M、编码、字段截断和 CRS 缺失。
- [ ] 以组件组为导入单元；组内每个源成员仍保留独立处置和摘要。
- [ ] 用 OGR 加载到 PostGIS 影子 schema，显式记录 driver、layer、CRS、geometry type；默认不自动修复几何。
- [ ] 用独立读取路径比较 feature/attribute/geometry 摘要、范围和 SRID。
- [ ] 运行地理夹具矩阵与累计测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): import and verify shapefiles"`。

## Task 13：实现 MapInfo 适配器

**Files:** `adapters/mapinfo.py`、`verifiers/mapinfo.py`、`tests/adapters/test_mapinfo.py`。

- [ ] 写失败测试覆盖 TAB/MAP/DAT/ID 完整性、MIF/MID 配对、字符集、坐标系、对象类型和损坏索引。
- [ ] 实现组件组识别；缺少必要组件必须拒绝，不能降级为“空层成功”。
- [ ] 用 OGR 导入并记录原图层、字段和坐标系映射。
- [ ] 独立验证对象数、属性/几何摘要、范围和 CRS；制造组件替换测试防止串组。
- [ ] 运行适配器测试与累计回归。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): import and verify mapinfo sources"`。

## Task 14：实现 Access/MDB 与 SQL 沙箱适配器

**Files:** `adapters/access.py`、`verifiers/access.py`、`adapters/sql_dump.py`、`tests/adapters/test_access.py`、`tests/adapters/test_sql_dump.py`。

- [ ] 写 Access 失败测试覆盖表/查询、附件/复杂类型、Unicode、OLE、自动编号、空表、密码/损坏文件及不支持对象。
- [ ] 加载路径使用 MDBTools，独立验证路径使用 Jackcess；二者不共享解析结果。
- [ ] 写 SQL dump 失败测试覆盖 DDL/DML、COPY、编码、扩展、owner、绝对路径、外部程序、网络/文件访问和事务失败。
- [ ] SQL dump 只在网络隔离、无敏感卷的一次性原样 PostgreSQL 沙箱恢复；随后按标准协议抽取，绝不直接对目标执行未知 SQL。
- [ ] 做攻击夹具测试，确认不能访问目标库、宿主机文件或外网；再跑累计回归。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): sandbox access and sql dump imports"`。

## Task 15：实现栅格与非表格证据适配器

**Files:** `adapters/raster.py`、`adapters/reference.py`、`verifiers/raster.py`、对应两个适配器测试。

- [ ] 写失败测试覆盖多波段、nodata、色表、旋转仿射、无 CRS、超大/损坏栅格，以及合同指定的 PDF/图像/文档 reference 成员。
- [ ] 栅格只按合同决定进入 PostGIS raster 还是证据目录，禁止按扩展名擅自转换。
- [ ] reference 成员不伪装成关系表；记录原字节摘要、媒体类型、元数据、位置和用途。
- [ ] 独立比较尺寸、波段、类型、nodata、地理变换、CRS、统计量/分块摘要；reference 逐字节核验。
- [ ] 运行大文件流式、资源限制和累计测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): preserve raster and reference evidence"`。

## Task 16：实现影子构建、原子发布和恢复

**Files:** `publish.py`、`recovery.py`、`tests/integration/test_publish.py`、`tests/integration/test_recovery.py`。

- [ ] 写失败测试：只加载到 run 专属影子 schema；验证未过、清单变化、快照缺失、有未处置成员时不得发布。
- [ ] 发布前核验合同 frozen、全量覆盖、必需验证、证据包、目标实例身份为 `pg32b`、库名为 `xiangrugu`，显式拒绝 `pg32`。
- [ ] 在单事务中切换逻辑入口并写 publish 记录，避免跨事务 rename 串造成半发布。
- [ ] 实现失败 run 清理、已发布版本保留和“回退入口而不伪造源重导”的恢复流程。
- [ ] 注入断线、磁盘不足、约束失败和发布中断，确认旧版本始终可用。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): publish validated imports atomically"`。

## Task 17：完成统一 CLI、证据包与容器运维接口

**Files:** 修改 `__main__.py`；新建 `cli.py`、`evidence.py`、`tests/cli/test_cli.py`；修改 `docker-compose.yml`、`docs/OPERATIONS.md`。

- [ ] 写失败测试固定 `inventory`、`contract check`、`plan`、`run`、`validate`、`publish`、`status`、`evidence verify` 命令、退出码和 JSON 输出；破坏性命令必须显式确认参数。
- [ ] 实现证据包：源清单、合同、配置摘要、Git 提交、镜像 digest、工具链锁、对象映射、验证结果、事件和发布记录，并生成总摘要。
- [ ] Compose 只提供候选操作/测试 profile：代码来自镜像，长期数据挂载到 `/data/persistent` 和 `/data/var`，已验收项目快照以只读数据卷提供到 `/data/imports/usedata`；不挂源码或 Docker socket。
- [ ] 运行手册写明 Linux shell 的来源核实、复制、核验、执行和失败恢复；未来常驻应用镜像直接包含此包，不另建修改过的第三方容器。
- [ ] 运行 CLI 端到端夹具和累计全套测试，确认 JSON 无秘密、错误可定位、命令可重入。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): expose audited container operations"`。

## Task 18：完成双演练、全量验收与旧原型退役判定

**Files:** `tests/e2e/test_rehearsal.py`、`docs/ACCEPTANCE.md`、`config/acceptance.schema.json`；修改 `docs/PITFALLS.md` 和仓库根 `docs/log.md`。

- [ ] 写端到端失败测试，把全量处置、独立验证、可复现、源未修改、不触碰 `pg32`、失败不污染正式库变成机器断言。
- [ ] 在两个全新隔离候选库执行相同源版本、合同、Git 提交和镜像 digest；比较对象清单、DDL 摘要、规范数据摘要和证据包，只允许运行 ID/时间字段等声明差异。
- [ ] 做取消/恢复和快照缺失/改变演练，确认无发布、无遗漏、无残留活动子进程。
- [ ] 生成 `ACCEPTANCE.md`，逐项链接机器证据并区分“已确认、未确认、例外”；任何红项都不得写“可正式导入”。
- [ ] 用户复核后，另行决定是否创建正式 `xiangrugu`、正式导入、提升镜像标签和部署常驻应用。
- [ ] 只有新流水线正式验收且另获授权，才退役旧原型；删除 `cbdb` 始终是独立破坏性授权。
- [ ] 经单独授权后提交：`git commit -m "test(datamgmt): prove reproducible end to end import"`。

## 2. 统一检查命令

以下命令均在获准使用 Docker 的 Linux 主机、仓库根目录执行；不在 Windows 本机安装项目依赖：

```bash
docker build --target test --tag xiangrugu:test .
docker run --rm xiangrugu:test python -m pytest datamgmt/tests/unit -q
docker compose --profile test up -d test-db
docker compose --profile test run --rm datamgmt-test python -m pytest datamgmt/tests/integration -q
docker compose --profile test down
```

最终阶段增加：

```bash
docker run --rm xiangrugu:test python -m pytest datamgmt/tests -q
docker compose config
docker image inspect xiangrugu:test
```

## 3. 计划自身验收

- [ ] 18 个任务均有明确文件、失败测试、最小实现、验证和授权边界。
- [ ] 自有代码进镜像、生产不挂源码、第三方镜像不改、PostgreSQL 走标准协议。
- [ ] `usedata` 是唯一权威源，运行输入为已验证项目快照；长期数据和运行证据位于项目宿主机目录。
- [ ] 首版合同在真实格式适配器开发前冻结；所有成员必须有处置。
- [ ] `cbdb` 只作观察，不能参与断言或验收。
- [ ] 正式库、正式导入、镜像提升、部署、Git 提交/推送和删除均保留独立授权门。

---

计划通过后采用已选择的 **Native（当前会话逐任务执行）** 方式推进：每次只进入一个任务，先说明写入、构建、服务和数据库影响并等待授权；测试与复核通过后再申请提交授权。
