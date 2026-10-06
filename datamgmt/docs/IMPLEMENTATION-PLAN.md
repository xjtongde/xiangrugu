# 香如故容器化数据接入模块 Implementation Plan

> 状态：规格与计划已批准，Task 1 待执行｜as_of 2026-10-06
> 依据：`rules.md`、`datamgmt/docs/DESIGN.md`、`datamgmt/docs/OPERATIONS.md`、`datamgmt/config/roots.yaml`
> 范围：只规划实现，不授权 Git 提交/推送、镜像拉取/构建、主机挂载、服务启停、数据库写入或正式导入。

**Goal:** 把唯一权威源 `usedata` 经可审计、可复现、可独立验证的容器化流水线导入 `pg32b` 的新数据库 `xiangrugu`，并把该能力保留为香如故项目中可反复使用的低频模块。

**Architecture:** 自有代码、依赖和工具全部固化进香如故自建镜像；开发、测试和生产运行同一套镜像构建链，生产不挂载源码。源数据只在导入窗口临时只读挂载到 `/opt/mydocker/xiangrugu/data/imports/usedata`，容器内固定为 `/data/imports/usedata`；项目生产数据持久化在 `/opt/mydocker/xiangrugu/data/persistent`，运行证据在 `/opt/mydocker/xiangrugu/data/var`。容器只通过 PostgreSQL 标准协议连接外部 `pg32b`，不修改 PostgreSQL 镜像，也不向任何第三方镜像注入自有代码。

**Tech Stack:** Python 3.11、pytest、psycopg 3、PyYAML、Pydantic；PostgreSQL 18/PostGIS 3.6 原版镜像仅在 Task 7 起用于隔离测试。表格使用 `xlrd`、`openpyxl`、`odfpy`；GDAL/OGR、MDBTools、Jackcess 等随对应适配器任务加入同一自有镜像，不在 Task 1 预装，且不引入 LibreOffice。Docker/Compose 负责构建和运行；具体镜像 digest、系统包版本及 Python 哈希锁在执行时从官方来源核实并写入锁文件。

---

## 0. 执行边界与完成定义

- 本计划只覆盖 `datamgmt/` 数据接入模块及其在项目镜像中的封装，不虚构尚未定义的常驻业务服务。现阶段可用候选镜像运行一次性命令；未来常驻应用入口建成后，直接复用镜像内同一模块。
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
| A 容器与合同基础 | 1–6 | 镜像链可复现；只读扫描完成；首版合同经人工复核冻结 | 构建镜像、临时挂载并读取 `usedata` |
| B 通用内核 | 7–9 | 标准协议、审计状态机、独立比较器通过隔离测试 | 启停隔离测试数据库 |
| C 格式适配器 | 10–15 | 每类成员都能导入或形成明确拒绝/隔离处置 | 如需真实样本，仅只读访问已挂载源 |
| D 发布与验收 | 16–18 | 原子发布、全量处置、两次演练一致、证据包完整 | 创建/写入候选库；正式构建和发布另授权 |

## Task 1：建立自有镜像、包骨架和可复现工具链

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `docker-compose.yml`
- Create: `datamgmt/pyproject.toml`
- Create: `datamgmt/requirements.in`
- Create: `datamgmt/requirements.lock`
- Create: `datamgmt/config/toolchain.lock.yaml`
- Create: `datamgmt/src/xiangrugu_datamgmt/__init__.py`
- Create: `datamgmt/src/xiangrugu_datamgmt/__main__.py`
- Test: `datamgmt/tests/unit/test_package_contract.py`
- Test: `datamgmt/tests/container/test_image_contract.py`

- [ ] 先写测试：包可导入、`python -m xiangrugu_datamgmt --help` 返回 0；镜像内存在代码和工具，运行用户非 root，Compose 不挂载源码，第三方测试库服务没有自有代码卷。
- [ ] 获得授权后核实 `python:3.11.16-slim-bookworm` 官方标签并解析 `linux/amd64` 完整 digest；Task 1 不拉取 PostGIS，测试数据库镜像留到 Task 7 再锁定。
- [ ] 构建测试目标并运行指定测试，确认因包、Dockerfile 或锁文件尚不存在而 RED，而非测试自身错误。
- [ ] 实现最小多阶段 `test`/`runtime` 镜像：只固化项目包、psycopg、PyYAML、Pydantic、证书/时区和测试依赖；以非 root 用户运行。格式工具由 Task 10–15 按失败测试逐项加入，禁止预装 LibreOffice。
- [ ] 运行 `docker build --target test -t xiangrugu:test .` 和 `docker run --rm xiangrugu:test python -m pytest datamgmt/tests/unit/test_package_contract.py datamgmt/tests/container/test_image_contract.py -q`，确认 GREEN。
- [ ] 用 `docker image inspect` 和 Compose 配置展开结果复核 OCI 标签、非 root 用户、无源码 bind mount、无密钥入层；把复核逻辑纳入测试。
- [ ] 经单独授权后提交：`git commit -m "build(datamgmt): establish reproducible container toolchain"`。

## Task 2：实现配置模型与临时只读源挂载守卫

**Files:** `config.py`、`mounts.py`、`tests/unit/test_config.py`、`tests/unit/test_mounts.py`；修改 `config/roots.yaml`。

- [ ] 为 `RuntimeConfig`、`SourceRoot`、`TargetConfig` 写失败测试，覆盖默认容器路径、环境变量覆盖、禁止口令写进 YAML、目标库名固定为 `xiangrugu`。
- [ ] 为 `inspect_mount(path, mountinfo)` 和 `require_readonly_source_mount(path)` 写失败测试，覆盖上游 CIFS 为 `rw`、项目入口未独立 bind、普通目录、项目 bind 仍可写、错误源、正确 `ro` bind 和运行中卸载。
- [ ] 实现严格配置解析；敏感项只接受运行时 secret/file 或环境变量，日志输出必须脱敏。
- [ ] 解析 `/proc/self/mountinfo`，在扫描前、每批前和发布前验证 `/data/imports/usedata` 指向预期源身份且为独立 `ro` bind；不得要求或修改全局 CIFS 挂载，Windows 测试只用固定样本。
- [ ] 在测试镜像运行本任务及累计单元测试，确认 GREEN。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): enforce config and readonly source mount"`。

## Task 3：定义领域模型、稳定标识和数据库命名

**Files:** `model.py`、`identity.py`、`naming.py`、`tests/unit/test_identity.py`、`tests/unit/test_naming.py`。

- [ ] 写失败测试，固定 `SourceMember`、`Disposition`、`ImportRun`、`Artifact`、`ValidationResult` 的必填字段与不可变字段。
- [ ] 写稳定 ID 测试：ID 由源版本、规范相对路径、归档成员路径和源字节摘要决定；Unicode、大小写和路径分隔差异不会碰撞或静默合并。
- [ ] 写命名测试：schema/table/column 名可逆、长度受限、保留字安全、碰撞确定性解决，并保留原名映射。
- [ ] 做最小实现，禁止使用 Python 进程随机哈希和扫描顺序生成名称。
- [ ] 运行本任务及累计单元测试，保存固定 golden vectors。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): define stable identities and naming"`。

## Task 4：实现只读清点与不可变源清单

**Files:** `inventory.py`、`signatures.py`、`archive.py`、`tests/unit/test_inventory.py`、`tests/fixtures/inventory/`。

- [ ] 写失败测试，覆盖普通/空文件、符号链接、大小写冲突、未知/伪装扩展、ZIP 和嵌套归档、压缩炸弹限制、不可读成员，以及校验账 NUL 尾部、坏行、重复项、路径越界和摘要格式错误。
- [ ] 定义 `InventoryBuilder.scan(root) -> InventoryManifest`；记录 SHA-256、大小、媒体签名、容器链和读取错误。
- [ ] 实现流式读取及单成员大小、总解压量、嵌套深度和成员数限制；绝不向源目录写临时文件。
- [ ] 以规范排序序列化清单并计算自身摘要；校验账先保存原始文件摘要再解析，任何格式异常进入机器证据，不得静默跳过；相同源字节重复扫描必须字节级一致。
- [ ] 运行夹具测试及“扫描前后源树元数据/摘要不变”回归测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): build immutable readonly inventory"`。

## Task 5：实现发布合同与全量处置判定

**Files:** `contracts.py`、`disposition.py`、`config/contract.schema.json`、`tests/unit/test_contracts.py`、`tests/unit/test_disposition.py`。

- [ ] 写失败测试：每个清单成员必须且只能匹配一条规则；零匹配、多匹配、模糊规则、失效断言和无理由忽略均拒绝。
- [ ] 定义处置枚举 `import`、`reference`、`quarantine`、`reject`，不提供默认 `ignore`。
- [ ] 实现合同 Schema 和确定性匹配；合同包含源版本、编码、格式族、目标、验证器、预期计数/摘要及例外理由。
- [ ] 实现 `DispositionLedger.coverage()`；只有覆盖率 100%、重复匹配 0、未解释成员 0 才能过门。
- [ ] 运行恶意/边界规则测试与累计单元测试。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): enforce complete disposition contracts"`。

## Task 6：生成并冻结首版 `usedata` 合同

**Files:** 新建 `contracts/releases/2026-10-06-bootstrap/` 下的 `manifest.yaml`、`sources.yaml`、`decoding.yaml`、`assertions.yaml`、`review.md`。

- [ ] 先用合成清单确认空合同和臆造规则必然失败。
- [ ] 经授权把真实 `usedata` 通过项目专用 `ro` bind 挂到固定入口，并在候选镜像内清点；记录上游 `rw` CIFS 事实、项目 `ro` 视图、源身份、清单摘要、Git 提交和镜像 digest。
- [ ] 对所有成员按签名和容器关系分组，逐组指定处置、编码、表/层/成员预期及独立验证方法；不确定项只能 `quarantine` 或 `reject`。
- [ ] 把 `SHA256SUMS-b2` 原始摘要 `900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb` 及尾部 1,101 NUL 异常写入合同；只对这个精确摘要批准兼容解析，源件不得改写。再运行 Schema、100% 覆盖、碰撞、编码抽样和源未变检查。
- [ ] 用户书面复核后才把 release 改为 frozen；冻结前禁止写针对真实源布局的特例加载器。
- [ ] 经单独授权后提交：`git commit -m "docs(datamgmt): freeze bootstrap usedata contract"`。

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
- [ ] 每批前调用挂载守卫；挂载消失、源摘要变化或预算越界立即停止且不得发布。
- [ ] 运行故障注入和累计回归，确认无遗留子进程和孤立临时文件。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): control runs resources and processes"`。

## Task 9：实现独立规范化比较器

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

- [ ] 写失败测试：只加载到 run 专属影子 schema；验证未过、清单变化、挂载消失、有未处置成员时不得发布。
- [ ] 发布前核验合同 frozen、全量覆盖、必需验证、证据包、目标实例身份为 `pg32b`、库名为 `xiangrugu`，显式拒绝 `pg32`。
- [ ] 在单事务中切换逻辑入口并写 publish 记录，避免跨事务 rename 串造成半发布。
- [ ] 实现失败 run 清理、已发布版本保留和“回退入口而不伪造源重导”的恢复流程。
- [ ] 注入断线、磁盘不足、约束失败和发布中断，确认旧版本始终可用。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): publish validated imports atomically"`。

## Task 17：完成统一 CLI、证据包与容器运维接口

**Files:** 修改 `__main__.py`；新建 `cli.py`、`evidence.py`、`tests/cli/test_cli.py`；修改 `docker-compose.yml`、`docs/OPERATIONS.md`。

- [ ] 写失败测试固定 `inventory`、`contract check`、`plan`、`run`、`validate`、`publish`、`status`、`evidence verify` 命令、退出码和 JSON 输出；破坏性命令必须显式确认参数。
- [ ] 实现证据包：源清单、合同、配置摘要、Git 提交、镜像 digest、工具链锁、对象映射、验证结果、事件和发布记录，并生成总摘要。
- [ ] Compose 只提供候选操作/测试 profile：代码来自镜像，长期数据挂载到 `/data/persistent` 和 `/data/var`，导入入口挂载到 `/data/imports/usedata`；不挂源码或 Docker socket。
- [ ] 运行手册写明 Linux shell 的挂载、核验、执行、卸载和恢复；未来常驻应用镜像直接包含此包，不另建修改过的第三方容器。
- [ ] 运行 CLI 端到端夹具和累计全套测试，确认 JSON 无秘密、错误可定位、命令可重入。
- [ ] 经单独授权后提交：`git commit -m "feat(datamgmt): expose audited container operations"`。

## Task 18：完成双演练、全量验收与旧原型退役判定

**Files:** `tests/e2e/test_rehearsal.py`、`docs/ACCEPTANCE.md`、`config/acceptance.schema.json`；修改 `docs/PITFALLS.md` 和仓库根 `docs/log.md`。

- [ ] 写端到端失败测试，把全量处置、独立验证、可复现、源未修改、不触碰 `pg32`、失败不污染正式库变成机器断言。
- [ ] 在两个全新隔离候选库执行相同源版本、合同、Git 提交和镜像 digest；比较对象清单、DDL 摘要、规范数据摘要和证据包，只允许运行 ID/时间字段等声明差异。
- [ ] 做取消/恢复和源挂载消失演练，确认无发布、无遗漏、无残留活动子进程。
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
- [ ] `usedata` 是临时只读输入；长期数据和运行证据位于项目宿主机目录。
- [ ] 首版合同在真实格式适配器开发前冻结；所有成员必须有处置。
- [ ] `cbdb` 只作观察，不能参与断言或验收。
- [ ] 正式库、正式导入、镜像提升、部署、Git 提交/推送和删除均保留独立授权门。

---

计划通过后采用已选择的 **Native（当前会话逐任务执行）** 方式推进：每次只进入一个任务，先说明写入、构建、服务和数据库影响并等待授权；测试与复核通过后再申请提交授权。
