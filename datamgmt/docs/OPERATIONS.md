# datamgmt 操作生命周期

> 状态：Task 1–5 API 及 Task 6 流式快照桥已实现；完整操作 CLI 尚未实现｜as_of 2026-10-07

本文件规定模块实现后的唯一操作顺序。当前命令是接口契约，不代表现有代码已经支持；在实施和测试完成前不得用于正式数据。

## 首次真实导入前的用户确认门

2026-10-08 用户要求：“导入之前通知我”，并要求届时共同确认pg32b原有数据如何处理。任何真实源数据写入（包括sample、rehearsal、staging与正式库）之前必须停下通知用户，列出具体目标数据库/对象、现存对象冲突、资源影响以及拟采取的保留或处置步骤，获明确批准才继续。仅完成合同或测试不能自动越过此门。

当前不连接或修改pg32b，不创建数据库，不删除/清空/覆盖旧数据，也不变更pg32。旧库不作为源、基线或验收依据；备份、迁移、改名或删除等操作均需具体范围另获授权。pg32b旧数据最终处置仍待用户决定，本要求不预先选择“删除”方案。

## 运行形态与目录

香如故以自有版本化镜像长期运行，项目代码进入镜像；生产环境不挂载宿主机源码。宿主机部署根为 `/opt/mydocker/xiangrugu`，长期数据在其 `data/` 子目录，容器内对应 `/data`。容器通过 PostgreSQL 标准协议连接外部 `pg32b`，不得把项目代码写入数据库镜像，也不得依赖 SSH 或 `docker exec pg32b` 作为应用传输层。

当前开发执行链固定为：

```text
Windows Git 工作区（只修改）
→ 受控同步到 32:/opt/mydocker/xiangrugu/deploy
→ xiangrugu-dev:/workspace（只读源码挂载）
→ 32 主机上的 watcher、测试和后续业务服务
```

Windows 不安装或运行项目 Python、Docker 测试和服务。后续 Agent 必须先同步，再通过 SSH 在 32 主机验证；不得直接编辑远端 `deploy` 后留下未回传 Git 的分叉。常驻开发容器运行真实 watcher，禁止 `sleep infinity` 等伪保活。当前 watcher 只提供首个模块的测试反馈；真实业务入口建立后，由同一 `dev` 目标运行并热重载。

## 项目源快照

1. 实际读取/复制另获授权，先核实 `roots.usedata.path` 来源身份、源体积和 32 主机磁盘/I/O 预算。
2. 创建新的 `snapshot_id`，记录源复制前清单及逐文件 SHA-256，复制到 `data/imports/usedata/<snapshot_id>` 的未完成目录，不覆盖已验收版本。
3. 独立读取副本核对全部成员及摘要，再复核源复制后清单与摘要。缺件、多件、字节不同或源变化即失败，禁止导入。
4. 校验通过才生成完成证书、关联 release；操作容器只读使用项目快照，运行输出写入 `data/var`。
5. 导入和发布前复核快照；副本保留在 Git/镜像外，清理另授权。无需源目录的项目临时挂载或卸载。

原 NAS 的全局 CIFS 设置保持原样。现有开发容器继续运行合成测试，不接入源或项目快照；真实复制按独立授权运行一次性自有容器。

Task 2 当前 API：`load_config(path, environ=...)` 从 roots 配置读取权威源和快照根；`create_snapshot(...)` 要求显式传入配置中的 `expected_source`、版本 ID、Git revision 和镜像 digest，执行复制及校验；`verify_snapshot(...)` 只读取副本和完成证书，不重新访问 NAS。相同版本不可覆盖，失败的未完成副本及 `.failed.json` 保留待人工处理。完成证书记录来源的规范路径和设备/inode 身份；这不等于对 NAS 管理端进行认证，真实源接入前仍须核实实际来源。

源复制前后全量摘要校验可检测两次读取间的变化，不能提供跨文件原子快照；真实复制需稳定更新窗口。磁盘空间检查支持额外保留预算，正式任务还须结合 Task 8 的运行预算。不直接运行旧导入脚本。

### 32 主机流式快照桥（Task 6 前置）

直接路径 API 需要源可见，但 DESIGN §13.3 禁止为原源建立项目临时挂载。因此 `scripts/copy-source-snapshot.sh` 只用 32 的标准 GNU tar 只读发送源字节，`snapshot_transfer.py` 在固定 digest 的自有 runtime 镜像内接收、摘要和校验。源字节不经过 Windows，不对任何容器挂入原源，不更改 CIFS。输出根从 roots 配置读取；宿主观察到的规范源路径、设备/inode 与实际 CIFS 来源也须匹配。

传输只支持未压缩 USTAR 的普通文件、目录及 UTF-8 规范相对路径；GNU/PAX 扩展头、符号链接、特殊成员、重复路径、超预算、截断及非零尾部均拒绝。硬链接由发送端 `--hard-dereference` 传为独立普通文件。当前真实源最长相对路径 83 字节，可由 USTAR 完整表达；将来不满足格式限制时停止，不截断路径。

`StreamSnapshot` 分四阶段：`prepare` 第一次读取源形成独占证据和未完成目录；`copy` 第二次读取源复制，并独立重读副本；`check` 第三次读取源，复核前后清单及副本，但不发证；每次 tar/接收管道均成功退出、宿主身份再次一致后，`finish` 再独立重读副本、改名并发证。中断/失败保留未完成目录及阶段证据；同名版本不能重用或覆盖。当前候选证书如实标记 `source_status=dirty`，Git HEAD 不代表未提交源码已经成为可发布版本。

执行前另获读取/复制、目录及权限授权，确认 imports 根为空且无符号链接后仅设置该根所有者为 10001:10001；证据根也使用此 UID/GID。不得递归修改源或其他项目目录权限。复制容器只为新快照写入挂载输出；验收后的普通操作只读挂载快照。

Linux shell（32，获授权后；已构建镜像，快照号必须全新）：

```bash
cd /opt/mydocker/xiangrugu/deploy
SNAPSHOT_ID=2026-10-07-bootstrap \
VCS_REF=1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05 \
bash scripts/copy-source-snapshot.sh
```

完成证书为 `/opt/mydocker/xiangrugu/data/var/snapshots/<snapshot_id>.json`。三次源读取需约三倍源字节 I/O，另有副本独立读取；当前默认预留 10 GiB、单容器 1 CPU/768 MiB/64 进程/无网络/只读镜像，每阶段前主机负载须低于 4。快照完成不是数据合同冻结、数据库验收或导入授权。

2026-10-07 实际验收：快照 `/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap`，189 个普通文件、43 个子目录（源统计含根为 44 目录），2,508,987,728 字节，无链接或特殊成员。清单 SHA-256 为 `03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699`；证书 `2026-10-07-bootstrap.json` 状态 VERIFIED，源设备/inode 为 71/78251103。Git revision 为 `1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05`，dirty 候选 runtime digest 为 `sha256:0ba034861027dd4ec1c7b0cabbdd3e651783c35a4518082c0539db98e8b0a8e8`。复制结束后再用该 digest 的自有容器只读挂载副本/证书，调用 `verify_snapshot` 全量独立重读通过；主机磁盘剩余 196,067,848,192 字节。常驻 dev、pg32/pg32b 的 ID 和启动时间未改变，未访问数据库。源更新窗口并非原子快照保证；该证书仅证明本轮全部观察与副本一致。

## 当前只读清点 API（Task 4）

`InventoryBuilder(...).scan(root)` 接受已独立验证且稳定的项目快照，返回不可变 `InventoryManifest`；`canonical_bytes()` 是规范 JSON，`sha256` 为这些规范字节的摘要。清单不含宿主绝对根路径或扫描时间，因此相同成员字节、相对位置和限制可重复得到相同结果。完整 CLI 尚未实现。

记录包含相对路径、ZIP 容器链、物理成员序号、大小、SHA-256、字节签名和异常。文件夹（包括空目录）有记录；未知格式保留为 `unknown`，伪装 ZIP 扩展名留下非阻断告警，处置由 Task 5 决定。不能读取、非法路径、重复成员、大小写冲突、CRC 错误或资源限制都会使 `complete=False`；未读完的成员没有摘要，不能拿部分摘要冒充完整文件摘要。物理序号仅用于区分清点证据；重复 ZIP 名称明确阻断，不改变 Task 3 身份协议后自动合并。

默认预算：单成员 8 GiB、整个扫描读取总量 64 GiB（外层文件与每层解压字节都计入）、100,000 成员、8 层归档、压缩比 1,000、ZIP 中央目录 16 MiB、累计校验账缓存 8 MiB；每本校验账最多解析 `max_members` 行。预算参数可显式调整，但实际源扫描和预算调整仍须经过授权与磁盘/I/O 核查。

归档按字节签名递归，不向源树解压。当前 ZIP 支持 Stored/Deflate；ZIP64、多卷、其他压缩方法明确产生阻断证据，需后续按实际源另补受限读取能力，不能视为扫描成功。超过成员数等预算时清单是有明确阻断的部分证据，不能用于宣称全量覆盖。ZIP 原始名称含 NUL 时保留原名并阻断，不使用 CPython 截断后的名字；重复成员按 `ZipInfo` 逐件读取。实现依据：[Python ZIP 文档](https://docs.python.org/3.11/library/zipfile.html)与 [CPython 3.11 实现](https://github.com/python/cpython/blob/3.11/Lib/zipfile.py)。

普通文件只流式计算摘要；需随机访问的归档和受限校验账使用最多 1 MiB 内存缓存，超出后写入显式 `temp_root`，默认 `/data/var`，自动关闭临时文件。缓存根必须在源树之外，磁盘不可写或不足即失败，不自动改用系统临时目录。合成测试显式使用 pytest 的 `/tmp`；真实扫描必须使用项目运行目录并由 Task 8 补齐磁盘预算。

校验账按原始字节先记录摘要，再严格读取 UTF-8 与 SHA-256 行；原始路径和行号保留，仅接受明确的 `./` 前缀语义。NUL、坏行、坏摘要、重复、越界、缺件和摘要不符均为机器异常，不忽略 NUL，不猜编码，不改源件。普通账的相对路径以账所在目录为根，归档内账限定在同一物理容器；其他路径根约定必须进入合同。Task 6 才能按精确原始摘要批准特例，当前没有真实 `SHA256SUMS-b2` 兼容豁免。

## 当前合同与处置 API（Task 5）

独立结构门：validate_contract_document(document, schema) 使用锁定jsonschema，
先检查Schema本身，再校验未经Pydantic变换的JSON域原始对象。load_contract在模型前调用该门。
静态Schema与运行时导出相等仍由测试证明；Schema定义并非独立生成，实例校验实现独立。
只允许根Draft202012、声明的非根Schema节点片段引用；禁外部检索、$id及子节点$schema。
const/default/examples里的字面数据不作Schema节点。JSON域深度128/节点100万、
实例执行200万关键字调用；这不是任意不可信正则或第三方Schema的通用安全沙箱。
结构通过不等于处置账、源未变、值验证、冻结或导入门通过。
实现/依赖依据：[jsonschema校验文档](https://python-jsonschema.readthedocs.io/en/stable/validate/)、
[离线引用文档](https://python-jsonschema.readthedocs.io/en/stable/referencing/)。
本批先仅构建候选，旧dev的watcher因缺jsonschema失败（B-15）；随后用户单独授权仅dev晋级，
已核验旧镜像导出/可运行并重建dev，真实watcher476项及pip check通过，B-15恢复。
未原地pip安装；实际Compose入口是受控deploy/docker-compose.yml。回退资产、镜像身份和
自动重测证据统一见docs/superpowers/plans/2026-10-08-json-schema-progress.md的dev晋级节。

`load_contract(path)` 只装载本地 JSON/YAML，拒绝重复键、不安全 YAML tag、超过 16 MiB 的合同和不符合模型的字段；不访问源、不连接数据库、不执行合同里的验证器名称。JSON Schema 为 `config/contract.schema.json`，由锁定版本的 Pydantic 模型导出并随自有镜像提供；生成 API 是 `contract_schema()`。Schema 用于结构校验，实际合同门必须再调用 Python 模型和处置账，不能把 Schema 通过等同于语义或导入验证通过。机制依据：[Pydantic Schema 文档](https://docs.pydantic.dev/latest/concepts/json_schema/)与[模型验证文档](https://docs.pydantic.dev/latest/concepts/validators/)。

`ReleaseContract` v1 包含 `release_id`、`source_version`、清单 SHA-256、draft/frozen 状态、复核记录、规则和例外声明。每条规则精确绑定相对路径、容器链及物理成员序号；不执行任何 glob 展开，`[]` 作为字面原名精确匹配（如 XLSX 的 `[Content_Types].xml`），当前仍拒绝 `*` 和 `?`。不折叠大小写或 Unicode，不提供默认规则、ignore、格式优先级或静默丢弃。规则声明预期成员种类、大小、原始字节摘要、签名、四种批准处置、非空理由、格式族、验证器 ID 和逻辑对象目标；文本编码明确到对象/列且只允许严格字节到文本编码，不允许 replace/ignore。冻结合同的逻辑对象计数和规范数据摘要不能为空。

`DispositionLedger.evaluate(manifest, contract).coverage()` 逐件保留记录，报告分母 total、唯一匹配 matched、零匹配 unmatched、多匹配 multiple、未解释 unexplained、BLOCKED 和错误数。`conforms` 要求非空清单、覆盖率 100%、零多匹配/未解释/BLOCKED/错误；清单摘要不符、清点异常、过时断言、失效规则及目标碰撞均阻断。空清单不是“自然 100%”。重复成员按物理序号区分，不自动合并；清点器已发现的重复名称或其他错误仍会阻断。

相同原始 SHA-256/大小的多个 IMPORT 声明会触发 `mirror_required`，必须显式指定唯一 IMPORT 主成员和 MIRROR；镜像引用只能指向 IMPORT，需相同字节断言和独立相等性证据摘要，不能引用缺失成员或镜像链。这一阶段检查合同断言的一致性，不执行证据报告、字节比较或行值验证；实际镜像相等性仍须由后续独立验证器证明，不能仅凭哈希把业务对象静默去重。

合同、处置记录和其规范 JSON 均为不可变证据；规则先后顺序不改变合同摘要或匹配结果。`ready_for_import` 只表示 frozen 合同通过上述静态合同门，不是用户授权，不是 G0–G7 验收证书，不会产生任何数据库操作。复核记录只能保留授权引用，字符串本身不能证明真实审批；Task 6 仍须用户书面复核。

例外声明保留精确原始摘要和理由，但 Task 5 不实现 NUL 兼容解析；存在例外声明会以 `exception_not_implemented` 阻断，不会借 NON_TABULAR 绕过坏校验账。真实首版合同、精确摘要例外和清点异常的逐案复核留到 Task 6；当前测试的 release 和审批记录全部为合成夹具，不代表真实版本已冻结。

### 校验账候选预览（Task 6）

`ChecksumCandidates` 与 `preview_checksum_candidates(manifest, candidates, raw_ledgers)` 仅检查未冻结的候选。调用方从已验证快照提供指定外层校验账的完整原始字节；当前不支持归档内账，不扫描名称、不修改源或严格清单。模型拒绝 frozen、未知字段、绝对路径、重复 ID 及同一本账的多条候选。候选文件是 release 内的非执行提案，不是 `sources.yaml` 的例外声明，也不切换 current。

NUL 候选核验原账摘要/大小、有效前缀每条声明及全部严格匹配结果、尾部偏移和精确 NUL 数量；任何中间 NUL、坏行、记录数偏差或不匹配均拒绝。路径绑定候选核验原账摘要/大小、指定行和原名/声明路径，要求声明位置不存在、明确目标唯一且为普通文件、目标大小/摘要相符；不会按同名或同摘要找替代件，也不能掩盖已存在但错误的声明位置。

预览结果固定 `runtime_applied=false`、`ready_for_import=false`；严格清点/处置 API 的行为未改变。真实候选、digest 和核验报告统一见首版 release/review.md。预览通过不表示所有校验账通过、合同完整、已冻结或获准导入；实际例外的冻结合同集成尚未实现，现有 `exception_not_implemented` 拦截保持有效。

### 逐组合同审阅（Task 6）

五件文本83列名称/text/非空、五个__src_rownum bigint及schema归属已逐案批准；最新决定、非执行投影及核验证据统一见首版release/text-review.md。表名、全版本命名和规范值合同仍未完成，批准sidecar不改变BLOCKED规则，不可用作DDL或IMPORT入口；本批只校验既有证据，不声明重新通过源/快照门。下面三件提案说明保留为历史。

两组空间对象组件、chgis、属性/派生行号、二维Point及SRID4326均已逐案批准；geom保持原SHP X/Y，不按EPSG声明轴序交换或转换，PRJ/QPJ差异留证，表名/规范值合同仍未完成。2026-10-08授权export/import救急备份核验后仅替换xiangrugu-dev，完整292测试及真实watcher284通过；tar/非root救急镜像留存，不包含挂载工作树或数据、不冒充原构建历史。后续构建前固定当前可寻址镜像回退标签，防漏自动化尚未实现。当前批准/镜像/诊断/B-14记录统一见首版release/spatial-review.md最新节，不在运行容器临时pip安装。所有成员仍BLOCKED，非执行sidecar不能作DDL/IMPORT入口；其他来源不能继承这两组SRID批准。

同一canary的两件精确DBF五个N字段读取/类型已有独立逐案批准，最新决定与源复核见首版 release/spatial-review.md。仅N移除外围0x20并精确读取；不扩大为C去空间、NULL或其他源数值批准，不把DATE_改为日期，不假定LAT/LONG与SHP X/Y等同。坐标原字节/顺序保留，不舍入、转换或推SRID。

1884route 两件精确 DBF 的各7字符列编码批准及固定宽度字节复核见首版 release/spatial-review.md 最新节。批准不包括剥除空格/NUL、NULL、N 值、目标映射、组件绑定或 CRS；两条诊断路径与正式独立生产读取器及 G4/G5 分开记录，不能把本批字符串摘要自动用作目标合同。

空间候选及后续未决归档/TAB/CPG 字节观察见首版 release/spatial-review.md；包含容器的物理序号属于身份，不能只按 ZIP 名字或 leaf stem 拼接。大小写只作歧义提示，不折叠/改名/取首个匹配。Native 定义声明的字符集不能直接证明 DAT 值编码，File 声明未检出时不能猜关联；CPG 不自动配给不同 stem。清单级证据与后续源字节检查分别保留，不能混用证明范围。

三件文本的对象/70 列及目标映射提案与现有模型验证结果另存，入口为首版 release/text-review.md。BLOCKED 规则按模型不得携带业务 targets，故提案独立保存而非放宽规则；三件范围预分配名称必须在完整 release 对象齐备后重算。尚未声明正式目标值摘要，不能把含头部的源观察摘要直接作为 G4 合同。

三件制表文本的历史全文候选报告、随后批准的 BOM/转义解释及独立字节路径复核见首版 release/text-review.md。新通用 source_text API 只支持受限 UTF-8/LF TSV，显式策略、固定预算，没有源布局特例或数据库访问；不共享 csv/importer 分列代码，不补裁字段、不吞空记录。真实验证比较全部字段，摘要仅作辅助；批准源读取与批准冻结/导入是不同授权门。报告和读取决定只供合同准备，不是正式执行入口。

最新审阅候选、逐件依据及新增报告由首版 release/review.md 指定，详细未决工作见同目录 member-review.md。初稿 `sources.yaml` 与旧失败证据不覆盖；后续修改须保留原成员位置与字节断言，使用独立命名的 draft 修订，不自动切换 current。非业务件登记不等于丢弃或已经通过参考件保存验证；校验账的用途分类不会清除严格清点异常。三件首批 .tab 已按批准解释完成独立源复核，读取与未冻结列级提案见 text-review.md；不能据此按后缀给其他 TAB 使用 MapInfo 适配器。

## 当前可用的开发命令

PowerShell（Windows，只负责 Git 和文件同步）：

```powershell
Set-Location C:\Users\zkyxy\Documents\codex-xiangrugu
& .\scripts\sync-dev.ps1
ssh 192.168.3.32 'docker logs --tail 50 xiangrugu-dev'
ssh 192.168.3.32 'docker exec xiangrugu-dev python -m pytest datamgmt/tests/unit -q'
ssh 192.168.3.32 'docker exec xiangrugu-dev python -m xiangrugu_datamgmt --help'
```

普通源码修改同步后会自动触发测试，无须 `up` 或重建容器。同步仅覆盖文件，不自动删除远端残留；重命名或删除文件时先列出远端具体目标，按授权范围处理后再同步。同步脚本固定目标为 32 的 `deploy`，排除 `.git`、`.agents`、`.secrets`、`.env` 及变体、私钥文件、`data` 和 `usedata`。

Linux shell（32 主机，仓库同步目录；依赖或 Dockerfile 改变后执行）：

```bash
cd /opt/mydocker/xiangrugu/deploy
VCS_REF=1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05 SOURCE_STATUS=dirty sh scripts/build-task1.sh
# VCS_REF 必须换成 Windows 当前 git rev-parse HEAD；SOURCE_STATUS 如实填写。
docker compose --profile dev up -d dev
docker logs --tail 50 xiangrugu-dev
cat /opt/mydocker/xiangrugu/data/var/devwatch/status.json
```

首次部署的 `data/persistent`、`data/var` 所有者为 UID/GID `10001:10001`。开发容器无网络，只有这两个数据挂载和只读 `/workspace`；状态文件提供最近测试的运行序号、退出码和 UTC 时间。watcher 自身改动需要重启开发进程；依赖或镜像入口改动需要重建镜像并替换开发容器。生产及候选测试使用镜像内代码。

## 镜像晋级顺序

代码变更先进入常驻开发反馈，再按以下顺序晋级；不允许在运行中容器里直接修补：

```text
Git 工作区 → 同步 deploy → dev watcher 反馈
→ 构建候选镜像 → 镜像内单元/集成测试
→ 记录 Git commit 与镜像 digest → 替换长期容器 → 健康检查
```

持久目录不进入镜像。候选镜像测试失败不得替换长期容器；替换失败时使用上一镜像 digest 恢复，不能靠重新挂载旧源码回滚。

## 首次构建

```bash
python -m xiangrugu_datamgmt inventory --release <release_id>
python -m xiangrugu_datamgmt contract build --release <release_id>
python -m xiangrugu_datamgmt contract check --release <release_id>
python -m xiangrugu_datamgmt import --release <release_id> --database xiangrugu_sample
python -m xiangrugu_datamgmt verify --release <release_id> --database xiangrugu_sample
python -m xiangrugu_datamgmt rehearse --release <release_id>
python -m xiangrugu_datamgmt publish --release <release_id>
```

`publish` 只有在两次全量彩排均为 `CONFORMS` 时才允许继续，并且创建数据库、写正式库和开放权限仍须取得用户明确授权。

## 数据更新或新增来源

1. 用户先确认新源应进入 `usedata`；源件本身只读；
2. 创建新的、不可变的 `release_id`；
3. 运行 `inventory`，生成新 manifest；
4. 运行 `diff --from <current> --to <new>`，审阅新增、改变、删除和镜像变化；
5. 生成并审阅新合同；
6. 从本 release 对应的已验证项目快照完整重建影子 schema；
7. 完成两次彩排和全闸验证；
8. 获得授权后发布并切换 `current.yaml`；
9. 保留上一版 retired schema，清理须另获授权。

计划命令：

```bash
python -m xiangrugu_datamgmt diff --from <old_release> --to <new_release>
python -m xiangrugu_datamgmt status --run-id <run_id>
python -m xiangrugu_datamgmt cancel --run-id <run_id>
```

## 失败处理

- 合同不完整：停止在导入前；
- 对象导入失败：回滚该对象事务，记录 `FAILED`；
- 验证失败：禁止发布，保留结构化证据；
- 运行中断：由同一 `run_id` 恢复或清理，不能新开无关联修补任务；
- 资源门槛触发：自动暂停，不自行修改主机或数据库参数；
- 正式发布失败：事务回滚，稳定 schema 保持原版本；
- 已发布版本需回退：使用保留的 retired schema，执行前另获授权。

## 禁止操作

- 直接修改 `usedata`；
- 直接执行源 SQL 到正式库；
- 以旧 `cbdb`/`cbdb_reh` 生成期望值；
- 对正式业务表做临时 `UPDATE`/`DELETE` 修补；
- 跳过 `BLOCKED` 或未登记成员；
- 只有一次彩排就发布；
- 未经授权创建、删除、重建数据库或切换正式 schema。
- 在生产环境挂载宿主机源码覆盖镜像代码，或直接修改运行中容器的可写层；
- 修改第三方源码、第三方镜像或第三方容器内部文件来实现集成；
- 在快照缺少有效完成证书或内容未通过校验时启动导入，或把项目输出写入源/快照目录。
- 修补、截断或重写源内校验账；已知 `SHA256SUMS-b2` 尾部 NUL 异常必须按原字节留证并由固定摘要合同显式处置。
