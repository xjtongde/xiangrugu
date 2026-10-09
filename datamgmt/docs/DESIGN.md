# datamgmt 最终设计规格

> 状态：主体容器架构及 32 主机常驻开发环境修订已批准｜as_of 2026-10-07
>
> 本文件是香如故数据接入模块的架构、数据合同、验证和发布规则的唯一权威来源。实现不得静默偏离。

## 1. 定位与目标

`datamgmt/` 是香如故项目长期保留的数据接入与版本发布模块，不是一次性迁移脚本。首次建库、源数据换版、新增来源、验证、彩排、发布和回滚都使用同一模块。

香如故是长期运行的自有容器项目，`datamgmt` 只是其中按需调用的低频模块。项目常态功能、数据接入命令和测试都在香如故自有镜像中运行；导入完成后，常态功能不依赖 `usedata` 持续在线。

唯一权威输入为 `/mnt/wd61workmetadata/usedata`。目标为 32 主机 `pg32b:5433` 实例中新建的 `xiangrugu` 数据库。

现有 `cbdb` 仅供观察，`cbdb_reh` 是旧彩排库；两者都没有权威性，不得参与清单、映射、期望值或验收。其删除或其他处置必须另获用户明确授权。

本模块不负责业务 API、页面、搜索、向量、知识图谱或数据校勘。上层应用只能消费已经发布的数据版本。

## 2. 完成定义

一个数据版本只有同时满足以下条件才可发布：

1. `usedata` 每个文件和容器成员都有唯一记录；
2. 每个成员的处置是 `IMPORT`、`MIRROR`、`NON_TABULAR` 或 `BLOCKED`，且有理由和证据；
3. `BLOCKED=0`、`PARTIAL=0`、未登记成员为 0；
4. 所有 `IMPORT` 对象通过结构、数量、值、空间/栅格和溯源验证；
5. 中断后重跑及成功后重跑不产生重复、漂移或半成品；
6. 两次从零全量彩排均为 `CONFORMS`，证书一致；
7. 仅凭源件、版本合同和指定 Git 提交即可重建；
8. 正式库未通过前不向普通读取角色开放。

“命令成功”“脚本存在”“抽样正确”都不构成完成。

## 3. 模块结构

目标结构如下；尚不存在的目录和文件由后续实施计划逐项建立，不在设计阶段造空壳。

```text
datamgmt/
├── README.md
├── pyproject.toml
├── docs/
│   ├── DESIGN.md
│   ├── OPERATIONS.md
│   └── PITFALLS.md
├── config/
│   ├── roots.yaml
│   └── policies.yaml
├── contracts/
│   ├── current.yaml
│   └── releases/<release_id>/
│       ├── manifest.yaml
│       ├── sources.yaml
│       ├── decoding.yaml
│       └── assertions.yaml
├── src/xiangrugu_datamgmt/
│   ├── cli.py
│   ├── model.py
│   ├── inventory/
│   ├── readers/
│   ├── loaders/
│   ├── verifier/
│   ├── orchestration/
│   ├── audit/
│   └── release/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   ├── fault_injection/
│   └── regression/
└── certificates/<release_id>/
```

源码、测试、合同和最终证书进入 Git。运行状态、staging、缓存和日志只写镜像外的 `/data/var`，不得写入仓库或镜像可写层。现有 `recon/` 属于首版盘点工作区；有效证据迁入首个 release 合同后退役，不能长期成为第二套合同。

## 4. 数据版本与合同

每次首次导入、换版或新增来源都创建不可变 `release_id`：

```text
YYYY-MM-DD-<purpose>
```

同名 release 不得覆盖。`contracts/current.yaml` 只在版本正式发布后切换。

每个 release 必须包含：

- `manifest.yaml`：全部源成员、成员链、大小、摘要、载体和处置；
- `sources.yaml`：全部逻辑对象、目标映射、字段、类型和验证策略；
- `decoding.yaml`：逐文本列的编码、判定依据和不可解码策略；
- `assertions.yaml`：源生语义哨兵，不负责修正源值。

合同由源侧盘点生成、机器校验并经用户审阅。运行时不得从旧数据库反推合同。

## 5. 成员处置与镜像规则

| 条件 | 处置 |
|---|---|
| 内容不同，即使名称或语义相似 | 全部 `IMPORT` |
| 文件或逻辑对象字节完全相同 | 一个 `IMPORT`，其余 `MIRROR` |
| 许可、README、校验文件、缩略图等非业务成员 | `NON_TABULAR` |
| 当前无法无损读取或装载 | `BLOCKED` |

不得按格式优先级选一个载体而丢弃其余载体。跨载体同名但内容不同的对象全部导入并以来源身份区分。

`v4_chgis_dbase.mdb` 的两个相同副本按镜像处理，内容不同的副本独立导入。`Thumbs.db` 明确登记为 `NON_TABULAR`。未知扩展名不能静默跳过。

## 6. 目标数据库与命名

正式数据库使用：

| schema | 职责 |
|---|---|
| `cbdb` | CBDB SQLite 来源对象 |
| `chgis` | CHGIS 及相关空间、MDB、SQL 对象 |
| `harv` | Harvard 其他数据集 |
| `audit` | 来源、映射、运行、闸门、证书和发布历史 |

业务数据不落 `public`。

每个逻辑对象以“源相对路径、容器成员链、对象原名、载体类型”的规范字节计算稳定 `source_object_id`。目标表名为 `<dataset_slug>__<object_slug>`；规范化后重名、超过 PostgreSQL 63 字节或存在跨载体碰撞时，追加该身份 SHA-256 的前 8 位。

标识符规范化规则固定为：Unicode NFKC；ASCII 字母转小写；ASCII 数字保留；其他码点编码为 `_u<hex>_`；非字母开头加 `t_`；超长时截断后追加身份哈希。列名使用同一规则，重复列按源顺序加后缀。原始名称、路径和完整映射原样保存于 `audit.name_map`。

Task 3 的 v1 身份规范采用 UTF-8 紧凑 JSON 数组再计算 SHA-256：成员为 `["xiangrugu.source-member.v1", release_id, relative_path, archive_chain, sha256]`；逻辑对象为 `["xiangrugu.source-object.v1", relative_path, archive_chain, object_name, carrier]`。身份不做 Unicode 或大小写折叠；只接受规范 POSIX 相对路径，非规范、越界和反斜杠路径明确拒绝，不自动替换后合并。列身份另含源列序号，以保留重复列。

表名以完整批次分配，所有同名规范化候选都加身份前 8 位，与扫描先后无关；重复列按 1 起始源序号附加 `__c<ordinal>`。短哈希仍发生碰撞时明确拒绝，须合同逐案处置，不静默复用名称。名称可逆依赖保存的原名映射，而非对截断后的标识符猜测还原。SQL 使用时必须统一引用标识符，不能直接拼接未引用名称；Task 3 不建立连接或执行 SQL。

## 7. 数据保真规则

导入层禁止改字、业务去重、补值、推断日期、推断未知哨兵、自动投影、修改几何、过滤异常值或装后用 `UPDATE`/`DELETE` 修补。

类型只能选择无损表示：整数优先 `bigint`，超界用 `numeric`；精确小数用 `numeric(p,s)`；只有源本身为浮点时才用 `double precision`；文本按列级合同解码；二进制用 `bytea`；没有明确源类型的日期样式字符串仍为 `text`；混合类型列无法无损统一时使用文本或结构化表示，并保存原始类型。

无法解码的字节不得被替换字符掩盖，必须保留原始字节、位置和错误。CSV、Excel 等行序有意义的对象增加保留字段 `__src_rownum`。重复行不得去重。

DBF 逻辑删除记录不进入业务表，但其数量、位置和原始摘要进入 `audit`，证明没有被静默忽略。

## 8. 空间、栅格、SQL 与 MDB

Shapefile/MapInfo 的主文件和伴随文件共同构成一个对象。坐标、维度、部件和环原样保存，禁止 `ST_Transform`。`.prj` 原文、摘要和解析结果进入 `audit`；CRS 能无歧义映射时设置 SRID，否则使用 SRID 0 并保留源声明。

PostGIS 无法表示的退化几何不得丢弃：业务几何可为 NULL，但必须在 `audit.geometry_exception` 保存源记录身份、原始几何字节、摘要和原因。

地理栅格必须验证尺寸、波段、像素类型、NoData、仿射参数、CRS 和每波段内容。普通说明图登记为 `NON_TABULAR`，不冒充地理栅格。

SQL 文件不得直接对目标库执行。必须先在受限解析或隔离恢复环境中枚举结构和值，再通过统一装载接口进入 staging；源 SQL 不得创建角色、修改权限、安装扩展、执行外部程序或操作本次运行范围之外的对象。

MDB 的装载器和验证器采用独立读取路径，避免同一解析错误同时生成结果和答案。

## 9. audit 数据模型

至少包含：

| 表 | 职责 |
|---|---|
| `audit.source_member` | 文件及容器成员的身份、大小、摘要和处置 |
| `audit.source_object` | 表、sheet、图层、栅格等逻辑对象 |
| `audit.name_map` | 原始名称与 PostgreSQL 名称映射 |
| `audit.import_run` | 运行 ID、release、Git 提交、配置摘要和状态 |
| `audit.object_result` | 每对象装载数量、耗时和结果 |
| `audit.gate_result` | 每道验证闸门的结构化结果 |
| `audit.geometry_exception` | 无法直接进入 PostGIS 的源几何 |
| `audit.release` | 已发布版本及 `CONFORMS` 证书 |

审计表是验收证据，不是可随意裁剪的运行日志。

## 10. 流水线与发布

统一流程为：

```text
inventory → diff → contract check → staging import
→ independent verify → rehearsal → publish → certificate
```

每次运行使用唯一 `run_id`。staging 名称必须包含 `run_id`。单对象发布中的旧对象处理、staging 改名和审计记录必须位于同一事务；失败整体回滚，不允许手工续跑修补 SQL。

首次构建使用 `xiangrugu_sample`、`xiangrugu_rehearsal` 和 `xiangrugu` 三个数据库。后续更新默认完整重建，不做行级原地增量：在正式库中建立 `build_<run_id>_cbdb/chgis/harv` 影子 schema，完整验证后在一个事务中把当前 schema 改名为 `retired_<release>_*`，再把影子 schema 改为稳定名称。用于 PostgreSQL 标识符的 run/release token 必须按本文件的标识符规则规范化，不能直接拼接带连字符的原始 `release_id`。

`audit` 不参与换名，持续保存版本历史。默认保留上一版 retired schema 作为快速回滚点；删除旧 schema 必须另获授权。

正式库未通过前不向普通读取角色开放。发布完成后才更新 `contracts/current.yaml` 和只读权限。

## 11. 独立验证与测试

验证器不得调用 importer 的值解析实现，也不得把 importer 中间产物当作期望值。

| 闸门 | 证明内容 |
|---|---|
| G0 | 导入前后源摘要一致 |
| G1 | 全部成员和内部对象都有处置 |
| G2 | schema、表、列、类型及名称映射符合合同 |
| G3 | 源与目标记录数按同一口径完全一致 |
| G4 | 每个值逐行逐列完全一致 |
| G5 | 几何、CRS、栅格及异常记录一致 |
| G6 | 中断重跑和重复运行不重复、不漂移 |
| G7 | 两次从零全量彩排证书一致 |

无主键及重复行数据先按规范行字节分区，再在分区内排序并比较实际字节及重复次数；哈希只负责分区和定位，不能代替值级相等。

测试必须覆盖单元、每载体黄金夹具、端到端集成、故障注入、重入和全库回归。故障注入至少包括漏行、多行、改单值、错码、漏列、表头污染、几何变化、错 SRID、镜像误判、成员遗漏、发布中断和远端孤儿进程。

## 12. 资源与操作安全

`pg32b` 与生产 `pg32` 同宿主。`nice`/`ionice` 不能单独构成保护。实现必须支持单 worker 默认并发、批大小、连接上限、磁盘/内存/负载门槛、I/O 监控、自动暂停、远端进程组、取消和回收。

先运行 canary，再逐步扩量。修改容器限制、数据库参数、服务状态、数据库、权限或正式数据，每次都需要用户明确授权。

## 13. 容器、代码与持久目录

### 13.1 自有镜像

香如故遵守 `rules.md` R-09：源码、锁定的 Python 依赖、数据接入 CLI 和必需系统工具进入自有镜像。开发、自动测试、彩排和生产使用同一 Dockerfile 的 `dev`、`test`、`runtime` 明确构建目标。Windows 工作区只负责 Git 修改，不运行项目代码；32 主机是唯一执行环境。

开发期的明确例外是：Windows 当前工作树通过受控同步进入 32 主机 `/opt/mydocker/xiangrugu/deploy`，再只读挂载到 `xiangrugu-dev:/workspace`，由真实的文件监视/测试进程热加载；不得以 `sleep infinity`、`tail -f /dev/null` 等伪进程保活。该挂载不覆盖镜像内 `/app`，开发镜像仍须包含一份自有代码和锁定依赖。远端 `deploy` 只是运行镜像，不是第二个编辑源，不得在其中直接形成未回传 Git 的修改。

候选测试、彩排和生产一律从同步前的 Git 工作树重新构建镜像，不执行 `/workspace` 中的挂载源码；生产环境不得挂载任何源码。任何代码变化在晋级前都必须重建 `test`/`runtime` 并通过镜像契约。

镜像必须：

- 使用固定基础镜像版本；发布时记录完整 digest；
- 先复制依赖锁文件建立缓存层，再复制源码；
- 以非 root 用户运行项目进程；
- 不包含 `.env`、密钥、源数据、运行账或生产数据；
- 写入 OCI 标签，至少包含 Git commit、构建时间和项目版本；
- 通过镜像内测试后才允许替换长期运行容器。

第三方数据库和服务保持原版。我方代码不得进入 `pg32b` 或其他第三方镜像；香如故容器只通过 PostgreSQL 标准协议和第三方公开接口集成。安装经真实载体证明必需的 GDAL、MDBTools 等公开发行工具到香如故自有镜像，不等于修改其源码；版本和来源仍须锁定并留证。工具按适配器任务逐步加入，禁止预装尚无必要性证据的重型软件；当前表格集合使用 `xlrd`、`openpyxl`、`odfpy`，不引入 LibreOffice。

### 13.2 长期容器与持久数据

部署根固定为宿主机 `/opt/mydocker/xiangrugu`，遵循现有容器目录规范。运行时至少包含：

```text
/opt/mydocker/xiangrugu/
├── docker-compose.yml
├── .env                    # 不进 Git
├── deploy/                 # Windows Git 工作树的受控运行镜像；开发容器只读挂到 /workspace
└── data/                   # 镜像外长期持久目录
    ├── persistent/         # 项目生产数据
    ├── var/                # 运行状态、staging、缓存和日志
    └── imports/
        └── usedata/        # 按 snapshot_id 保存已验证字节快照
```

`xiangrugu-dev` 是项目从首个 `datamgmt` 模块开始即存在的常驻开发容器；其前台进程监视 `/workspace` 并执行开发反馈，后续真实业务服务出现后由同一开发目标启动并热重载。数据导入 CLI 仍按需执行，不因开发容器常驻而变成常驻导入服务。

生产长期容器连接外部 PostgreSQL，代码来自镜像，只有配置和数据从镜像外注入。容器重建、升级或迁移不得破坏 `data/`。宿主机、IP、容器名和凭据均是部署参数，不得写入业务代码或 release 合同。

### 13.3 `usedata` 项目内快照

按 2026-10-07 用户指令，唯一权威源仍是 `/mnt/wd61workmetadata/usedata`，运行输入改为复制到项目目录并独立校验后的字节快照；不再建立源的临时 bind/remount，不修改全局 CIFS。

快照保存到 `/opt/mydocker/xiangrugu/data/imports/usedata/<snapshot_id>`，操作容器从 `/data/imports/usedata/<snapshot_id>` 只读使用。副本保持与源字节相同，不进入 Git、镜像或源码同步；新版本使用新目录，不覆盖已验收版本。

复制前核实配置源路径及实际来源，记录全部成员的相对路径、类型、大小及 SHA-256。拒绝符号链接越界和未明确处理的特殊成员。复制到未完成目录，独立读取副本逐成员核对清单及摘要，再复核源复制前后清单及摘要。缺件、多件、字节不同、复制中断或源在复制期间变化时均失败，不生成完成证书，不允许导入。前后校验不等于原子源快照，复制窗口需避免并发更新。

完成证书记录来源身份、源/副本清单摘要、复制和核验时间、Git 提交与镜像 digest。导入前、每批前和发布前复核证书与快照内容；快照缺失或改变即停止。运行输出写入 `data/var`，源与快照均不得修改。

`SHA256SUMS-b2` 的 172 条有效记录之后实有 126 个 NUL 字节（2026-10-07 对同一固定原始摘要逐字节复核，更正原 1,101 计数；证据见首版 release/checksum-anomalies.json）。复制时保留原字节；清单工具留存原始摘要、报告异常，只允许冻结合同对精确摘要批准兼容解析，不能清洗或修补。

2026-10-07 用户同意先核验两条候选：上述账的完整原始摘要、大小、有效行数和精确 NUL 尾部；发布账 `harvard/chgis/SHA256SUMS.txt` 的第 4 行保留原名及声明路径，仅显式绑定 `chgis-v6/China_Periods_ReignDates.zip` 并锁定原账和目标的摘要/大小，不按名称查找回退。候选与结果见首版 release/review.md。预览不是运行豁免；实际使用仍须冻结合同的逐案批准及对应运行门实现，不能把严格清点异常改成成功。

实际读取/复制源、接入普通只读数据卷、构建镜像、替换容器及清理快照仍须明确授权。复制前统计源体积，核实磁盘余量和同机 I/O 影响；本次设计修改不授权真实源访问或复制。

## 14. 实施阶段

| 阶段 | 产物 | 出口 |
|---|---|---|
| 0 合同冻结 | 首个 release 的 manifest/sources/decoding/assertions | 100% 成员有处置，合同校验通过并获用户批准 |
| 1 基础框架 | Python 包、CLI、模型、audit、编排和测试骨架 | 配置与故障注入基础测试通过 |
| 2 载体竖切 | SQLite、文本/表格、Shapefile、MapInfo、MDB、SQL、栅格各一条闭环 | 每类通过适用闸门 |
| 3 载体全量 | 合同内全部对象 | 未实现载体、静默跳过和 BLOCKED 均为 0 |
| 4 全量彩排 | 两次独立重建证书 | 两次 `CONFORMS` 且一致 |
| 5 正式构建 | `xiangrugu` 与发布证书 | 全闸通过并开放只读访问 |
| 6 后续更新 | 新 release、影子 schema、原子切换 | 新版发布并保留上一版回滚点 |

实施必须从阶段 0 开始。任何合同级变化——来源、目标、去重、命名、保真、验证、彩排或发布规则——都必须停工、说明证据并获用户批准，不能在代码中绕过。
