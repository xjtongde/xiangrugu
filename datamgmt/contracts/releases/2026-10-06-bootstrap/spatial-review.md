# 空间组件清单级审阅

> 状态：两组组件、chgis、属性/行号、二维Point及SRID4326已批准；表名、正式读取器与完整空间合同未完成｜as_of 2026-10-08

## 最新两组 SRID 4326 批准

用户“继续”回应仅这两组空间对象使用SRID4326、保持原始X/Y、不交换、不转换的明确提问；这是逐案参考系标签批准，不是由工具候选自动推导的授权。新增 `spatial-crs-decisions.draft.yaml`，绑定前批诊断文件SHA-256 `8505b5112076b094f1ee7472333b2916739fce45251b957c4e54aecf162ef8ce` 与几何批准投影SHA-256 `21d15e4308b7cf9ea4a945942708ffcdeb4e76438917705bd4300ca206e760c5`，精确列出1251/UTF8两个对象身份及m002709/m002717主成员；不扩展到其他来源或换版。

固定自有runtime只读取既有声明及新决定，复核两组身份、4件原PRJ/QPJ bytes/base64/摘要、锁定PROJ目录和诊断比较一致。各声明仍唯一EPSG4326候选/confidence100，PRJ east/north、QPJ north/east，严格不等价、忽略轴序等价；不把批准写成消除了轴序差异，PRJ/QPJ都保留、不覆盖。批准明确geom.X=原SHP.X、geom.Y=原SHP.Y，禁止以EPSG轴序要求自动交换、转换、舍入或替换为DBF LAT/LONG。

另存 `spatial-crs-approved.draft.yaml` 非执行投影：两组srid=4326、crs_resolution_approved=true，原Point/二维/记录关联及声明不变，旧几何决定/投影及离线诊断不覆盖。原诊断中的srid_assigned=null/未批准是历史事实，不是本轮批准被撤销。投影不进入BLOCKED规则targets，不生成DDL或运行几何，不把SRID批准扩大为全版本名称、规范几何摘要、正式读取器、导入或冻结；geometry_expected_hash仍null、ready_for_import仍false。

`validation-spatial-crs-approved.json` 记录2对象/4声明核验、真实contracts/current.yaml不存在及正式sources/metadata/decoding/assertions文件摘要未变；`artifact-hashes-spatial-crs-approved.json` 绑定决定/投影/报告3项断言，回传Windows核对后受控同步32。完整292回归通过，现dev与pg32/pg32b身份/启动时间均不变。没有NAS/源快照新读取或新快照核验，无产品代码/依赖/镜像/服务变更、数据库、冻结或Git提交推送，BLOCKED=7,914，Task6未完成。后续仍需全release对象/表名及规范值合同、独立生产读取器与验收路径；以下均为前批历史，SRID待批准不代表当前这两个精确对象。

## 最新回退恢复及 dev 更新验证

用户“继续”批准前批export/import替代备份方案。旧dev为read-only根文件系统，先确认备份目标及回退标签不存在，再导出到32 `/opt/mydocker/xiangrugu/data/var/task6/dev-rollback-rootfs-20261008.tar`；179,631,616字节，SHA-256 `05994147399a2042daaba39d657088e2e5748dc3845fd6409486da8c9fdc7e72`，tar保留在32、不回传Windows。新救急镜像 `xiangrugu:dev-pre-crs-20261008` 摘要 `sha256:c7107ca6144d1a1cdb7978d987ad020b647e5243dfabe9d7755c61d21d673008`，标记emergency-only/rootfs-export；显式恢复USER10001:10001、WORKDIR/workspace、必要ENV及原真实watcher CMD。无网络、只读核验旧包/devwatch可导入、非root及pip check通过；旧环境没有pyproj符合原状态，不声称旧环境通过新CRS测试。挂载workspace/data不进入tar，备份不还原当前Git工作树或业务数据，也不是原构建历史/可复现发布镜像。

先在固定test摘要离线/只读、1CPU/768MiB/64pids完整重跑292项通过，再执行既定compose的 `--profile dev up -d --no-deps --force-recreate dev`，只替换xiangrugu-dev。新ID `14b0d8dc5801e6e680ece510abec9c9d8405fa5a172311cbf4a2494bce82a5a4`，image `sha256:121f86c85e784cd78d145c8bf7db36722c17472c055926f53ef096421bcd5f10`，启动 `2026-10-08T07:41:42.507592242Z`（北京时间15:41:42）。真实watcher284单元通过，status returncode0、finished_at07:41:47Z；容器非root、/workspace、read-only、network none。pg32/pg32b前后过滤状态逐字段一致，包括ID、镜像、启动时间、running/paused；没有连接业务库。旧容器经明确授权的compose替换已移除，其旧根文件系统可由保留tar/救急镜像恢复。

生成 `validation-dev-recovery-20261008.json` 与前后容器JSONL、完整测试/回退检查日志、tar摘要/大小及产物哈希，共8件新证据回传，7项断言核对。首次证据容器读取root-owned 0600 tar被拒绝，未生成报告；不放宽权限，改由SSH宿主计算并另存摘要/大小，再非root核对生成报告，历史失败不伪装成成功。B-14的部署回退阻断已解除，但旧原manifest未恢复、自动构建前固化tag的防漏尚未实现；后续构建先保留当前可寻址镜像，不能再次只覆盖标签。

用户说明此前关机，与三个容器启动时间变化相容；不据此认定旧manifest丢失由关机造成。HEAD仍为 `1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05`、source_status=dirty；无产品代码/依赖/构建变更，无NAS或源快照读取、新快照核验、数据库、冻结或Git提交推送。两组CRS候选/轴序差异沿用前批已验证报告，SRID4326仍是待批准建议，未自动赋值；Task6未完成。以下均为前批历史记录，旧dev未替换/备份待授权不代表当前状态。

## 最新 dev 回退备份已授权但失败

用户“继续”批准前批明确提出的 `docker container commit` 救急备份，并授权仅在备份核验成功后替换dev。本轮先核对HEAD仍为 `1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05`；现dev和pg32/pg32b的容器ID仍同前批，但启动时间在本轮操作前已经变化，采用本轮实际基线，原因未调查，不归因于本次操作。32可用磁盘195,327,840,256字节、可用内存5,830,504,448字节，原回退标签不存在，新dev保留标签可寻址。

执行commit返回exit1：`NotFound: content digest sha256:b0f1034cd934e7deb6458beabcb8645c2a95c95bf97017dfa7ab6e740749e9e8: not found`。已确认缺失的是旧平台manifest内容，不仅仅是旧tag；不能据此推断删除原因。回退镜像没有生成，dev仍运行且未暂停，容器ID/启动时间与本轮操作前一致，pg32/pg32b亦同。按明确失败边界停止，没有export/import、compose替换、删除或重建。真实日志及摘要为 `dev-rollback-commit-20261008.log`、`validation-dev-rollback-commit-20261008.json`、`artifact-hashes-dev-rollback-commit-20261008.json`；三个新文件回传并核对两项断言。B-14仍未解决；本轮不声称重新跑过前批292测试，无产品代码、依赖或构建变更，无源读取、数据库、冻结或Git提交推送。

下一批替代备份提案，尚未授权：仅导出现有xiangrugu-dev根文件系统到32项目data/var/task6内一个新的tar，记录大小及SHA-256；从该tar导入专用救急回退镜像，显式恢复非root USER、WORKDIR、必要ENV和真实watcher CMD并标注emergency-only。导出不包含挂载的workspace/data，但也不保留原构建历史和启动元数据；它不是可复现发布镜像。[Docker export](https://docs.docker.com/reference/cli/docker/container/export/)及[import](https://docs.docker.com/reference/cli/docker/image/import/)官方说明支持根文件系统导出与显式配置恢复。保留tar和现容器，先无网络/只读核验原包、用户及启动配置；任一步失败停止，只有备份验证通过才仅替换dev，并复核watcher与数据库容器身份。不读取usedata或复制业务数据，不安装依赖、修改Docker存储或第三方镜像，不删除旧产物。新增tar/镜像占磁盘，不能把原始导出直接当生产镜像或默认root运行。

以下均为前批记录；前批“备份待授权”不表示本轮仍未获commit授权，原路径已获批尝试但失败。

## 最新离线 CRS 工具验证及开发容器回退阻断

用户“同意”批准下节离线工具方案。Windows权威仓库新增通用 `crs_diagnostic.py`，仅接受原始WKT bytes；原文/base64/摘要与规范化结果分开，保留完整候选及置信度、严格/忽略轴序两种比较。字节/嵌套预算在解析前检查；候选数量上限是PROJ返回后的拒绝门，不是查询CPU硬预算。拒绝联网环境，不调用Transformer、下载网格或自动选SRID，不写真实源布局特例。

在32核实Linux amd64、Python3.11.16及资源预算后，锁定官方二进制wheel pyproj3.7.2及certifi2026.7.22；两份依赖锁保留原pins并按官方PyPI metadata增量加入wheel哈希，不声称重新运行pip-compile。Docker安装强制only-binary/require-hashes。实际PROJ9.5.1、EPSG v11.022（2024-11-05）、内置proj.db 9,261,056字节，SHA-256 `a25d85a2ebfc4584eba65186b7c41743b084ce5d391941cbb41c805947b77109`；版本/摘要写入toolchain，各镜像均核验一致。该内置目录是工具只读资源，不是目标业务库。

TDD初始27项RED；独立审阅未发现Critical/Important，指出多候选/置信度及candidate_limit测试缺口。补3项回归，其中新增显式歧义标志先见1失败/28通过，再最小实现GREEN；六候选全部保留，5条预算拒绝、6条精确边界接受。最终292项及镜像契约/pip check通过，额外以network=none、read-only、1CPU/768MiB/64pids和/tmp tmpfs完整复测通过。构建串行并监控资源，未声称Docker build有CPU硬限制。证据为 `crs-*-tests.log`、`crs-final-build-contract.log` 与 `validation-offline-crs-tools.json`。

最终自有镜像构建时间2026-10-07T17:28:04Z（北京时间10月8日），HEAD仍为 `1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05`，source_status=dirty：

| 镜像 | 最终可寻址摘要 |
|---|---|
| dev | sha256:121f86c85e784cd78d145c8bf7db36722c17472c055926f53ef096421bcd5f10 |
| test | sha256:474da53d4fb0d7033ebe61eb74ac2b623cc7907b55b719fbc5f829270810a240 |
| runtime | sha256:c15019fed0fba9a8319ab129d0b1be1814ac22e775c7dccf8083e01220b4cb78 |

只从前批批准投影读取四件PRJ/QPJ原bytes证据，逐件摘要/原文核对；最终固定runtime生成 `offline-crs-diagnostics-final.json`，首轮诊断另存不覆盖。两组PRJ/QPJ各自唯一候选均为EPSG:4326、confidence100，但PRJ轴为east/north，QPJ为north/east，严格不等价、忽略轴序等价。不能把后者写成严格等价，PRJ和QPJ都留存。建议下一批仅审阅这两个精确对象的SRID4326标签，同时继续保留geom.X=原SHP.X、geom.Y=原SHP.Y、不交换或转换；本批没有批准或落实该建议。

部署收尾遇阻：我方没有在覆盖dev标签前先固定旧镜像回退标签。运行中旧容器配置摘要 `da7aa6a8…` 和ImageManifestDescriptor摘要 `b0f1034c…` 均不能由Docker image inspect寻址，旧tag也不存在；因此不能宣称已保留可重建的旧镜像。打回退标签失败后未执行compose替换，`xiangrugu-dev` ID/启动时间仍为 `449fa5d6…` / `2026-10-07T06:27:35.063201904Z`，依赖仍是旧版；新工具镜像通过不等于常驻watcher依赖已更新。pg32/pg32b身份和启动时间不变、data未改。原因记录不推断是谁删除了镜像或Docker垃圾回收细节；接续先申请把现有自有dev容器保存为专用回退镜像并验证，再仅替换dev，禁止无回退强行替换。缺陷登记B-14。

收尾补充 `validation-offline-crs-lifecycle.json`：原诊断current字段误检查/evidence父目录，不能作为真实current证据；本报告显式把宿主contracts目录映射为/contracts再检查current.yaml，确认不存在，原报告不覆盖。旧watcher最新29失败/255通过、returncode=1，不能写成开发环境测试通过；新镜像292通过与旧容器失败分别留证。三个新镜像已另加 `*-crs-verified-20261008` 保留标签，不是旧镜像备份。

下一批备份授权提案：仅针对现有xiangrugu-dev执行 `docker container commit` 保存专用 `xiangrugu:dev-pre-crs-20261008` 救急回退镜像，并核验非root、启动配置与旧包可用性；默认会短暂停顿该开发容器，不包含挂载的workspace/data，不作为可复现发布镜像，也不是Git提交。[Docker官方说明](https://docs.docker.com/reference/cli/docker/container/commit/)明确其暂停及挂载排除行为。若旧父镜像不可寻址导致备份失败，停止，不自动导出/import或删除容器；备份验证通过才按前批授权仅替换dev，再核对watcher及数据库容器身份。该新备份操作尚未授权或执行。

本批共10件证据回传Windows，8项新增产物断言及代码/工具链摘要核对一致；正式sources/metadata/decoding/assertions文件摘要未变，current不存在、BLOCKED=7,914。无NAS/源快照新读取或新快照核验，无数据库连接、Git提交推送或冻结；Task6仍未完成。下列工具缺口/待授权文字为前批历史，不表示当前工具实现状态。

## 最新二维 Point 批准及 CRS 工具授权缺口

用户“同意。继续”批准前批两组各59点的 `geom` 二维Point映射；`spatial-geometry-decisions.draft.yaml` 锁定精确提案摘要、两个对象身份和主SHP规则。原X/Y IEEE754值及1起始物理记录关联保留，不交换、舍入、投影、补Z/M或以DBF LAT/LONG代替；不增加原提案没有的几何约束。批准不包括SRID、表名、导入或冻结，不能把null SRID变成默认0。

固定runtime只处理既有决定和提案，核验两组Point映射及四件PRJ/QPJ声明的base64、原文和摘要，另存 `spatial-geometry-approved.draft.yaml` 批准投影及 `validation-spatial-geometry-approved.json`。正式sources/metadata/decoding/assertions摘要未变，current仍不存在；没有读取NAS或源快照，没有新做快照核验或目标G5验证。旧提案及前批证据不覆盖，全部组件仍BLOCKED。

该报告实测Python 3.11.16 runtime：pyproj/osgeo模块均不可用，projinfo/gdalsrsinfo命令均不存在。可用性检查不是CRS解析；不能把本地工具缺口误报为源CRS未知，PRJ和QPJ分别留证、不覆盖。3项新增产物断言回传核对，262项回归通过；无产品代码、依赖、镜像或服务变更，无数据库连接、冻结或Git提交推送，Task6未完成。

### 下一批拟申请：自有镜像内离线 CRS 核验

本节是具体授权提案，尚未实施。采用pyproj的CRS接口，不新增GDAL、PostGIS或LibreOffice。[官方CRS文档](https://pyproj4.github.io/pyproj/stable/api/crs/crs.html)提供from_wkt、axis_info、equals和to_authority；后者是最佳候选匹配并带置信阈值，不能把默认阈值返回值直接当无歧义结论。分别保留严格轴序比较与忽略轴序比较，不交换源坐标；记录候选、歧义和解析失败，不自动赋SRID。

拟授权操作范围：

1. 在Windows权威仓库修改依赖输入/哈希锁、工具链记录、镜像契约及通用CRS诊断代码/测试；不写真实源布局特例加载器。
2. 在32核实Python/架构和资源预算，选择官方发布且兼容Python3.11的二进制wheel，锁定pyproj及必要传递依赖版本/哈希；记录实际PROJ和数据库版本/摘要。不安装到Windows或宿主Python，不对第三方镜像打补丁，不在运行容器可写层pip安装。[官方安装文档](https://pyproj4.github.io/pyproj/stable/installation.html)支持PyPI二进制wheel；若适配wheel不可用，停止并报告，不擅自源码编译或增加系统工具。
3. 按TDD覆盖正确/无效WKT、冲突声明、轴序差异、候选歧义、输入预算及不可联网边界；自有dev/test/runtime镜像在32重建，先通过完整回归和镜像契约，再仅替换xiangrugu-dev以恢复一致开发依赖。保留data及旧镜像回退点，pg32/pg32b不变。
4. 网络关闭地分别解析这两组既有证据中的PRJ/QPJ，留存完整诊断和候选身份；不下载转换网格、不调用Transformer、不上传来源声明或连接数据库。源字节已保存于前批证据，本步骤不需要重新访问NAS；诊断不等于生产独立读取器或G5验收。

影响与风险：新增镜像依赖和构建缓存会占磁盘/内存，开发容器替换产生短暂测试监视中断；先检查预算、限制构建/测试资源，验证失败不替换。工具匹配可能受版本、PROJ数据库或轴序影响，因此需锁定和留证，SRID结论仍另行审阅。替代方案是继续其他成员合同审阅并保留本组CRS待定，不把待定偷换成0或4326。以下均为前批记录。

## 最新属性批准及二维 Point 映射提案

用户“同意，继续”批准前批整体属性提案：14个C列text、24个属性列名称及nullable=false、每组一个 `__src_rownum bigint` 的1起始物理SHP/DBF记录关联。`spatial-attribute-decisions.draft.yaml` 绑定前批提案的精确文件摘要和两个对象身份；批准不包含表名、几何、SRID或导入，派生行号没有追加未提议的约束。数字类型/读取继续沿用前批批准，字符尾空格保持，DATE_仍bigint。

固定runtime复核24列身份/名称/引用、原字符与数值批准标志及两组派生行号范围，另存 `spatial-attributes-approved.draft.yaml` 作为明确批准投影；旧提案不覆盖。投影与决定结合使用，仍是非执行sidecar，不能写入BLOCKED规则的targets；正式sources、metadata、decoding、assertions文件摘要未变，current不存在。

几何接续只重核已有 `dbf-numeric-point-observations.json` 的118个坐标对原字节和记录序号，不重读原SHP或快照。原报告各59点、无非有限值、索引与顺序寻址一致、包回IEEE754字节一致、bbox与点min/max一致；本轮对已有16字节XY拆包并与float.hex、打包结果逐条核对，记录序号均1–59。该复核共享标准库struct解码，不能当独立生产空间读取器、源重新校验或目标G5验收。

`spatial-geometry-proposal.draft.yaml` 明确提议两个 `geom` 源几何映射：Point、二维、每组59条；按批准物理行号关联属性，不交换X/Y、不舍入、不投影、不用DBF LAT/LONG替换原SHP坐标、不补Z/M、不去重。geometry type字段只描述待审映射，不是可执行DDL；规范几何摘要仍空，正式目标验证未实现。CPG是字符编码声明，不作为CRS；PRJ/QPJ原文、摘要和各自来源均留存，不互相覆盖。

CRS/SRID从本次几何批准范围中排除，提案srid为null而不是已批准0或4326。当前锁定自有镜像未包含CRS解析工具，本轮没有安装工具、调用CRS服务或运行PostGIS。QPJ末端EPSG声明不能代替PRJ解析及无歧义匹配核验；若最终不能无歧义映射，再按DESIGN §8审阅SRID 0，不因尚未实现解析器就断言源CRS未知。官方文档说明[ST_SetSRID只标记参考系，不转换坐标](https://postgis.net/docs/ST_SetSRID.html)，[ST_GeomFromWKB省略SRID默认0](https://postgis.net/docs/ST_GeomFromWKB.html)；因此本次“未批准SRID”不能通过省略参数偷偷变成批准0，后续执行必须显式落实获批值。

`validation-spatial-attributes-approved.json` 记录批准核验、既有坐标复核和未决边界。本轮没有NAS/快照读取或新快照校验，无产品代码、依赖、镜像或服务变更；4项新增产物断言回传核对，262项回归通过。BLOCKED=7,914不变，未冻结、连接数据库或Git提交推送；Task6未完成。以下均为前批记录，不表示当前批准状态。

## 最新 schema 批准及属性映射整体提案

用户“同意，继续”明确批准仅这两组对象归入 `chgis`。`spatial-schema-decisions.draft.yaml` 锁定前批 `spatial-objects-chgis.draft.yaml` 文件摘要、两个对象身份及主成员规则；历史提案中未批准标志保留，不覆盖。当前有效批准需把该决定与原提案结合读取，不能把历史标志误作撤销，也不能把schema批准扩大为整个目标映射批准。

固定runtime只读取已同步的决定与前批证据，核验两个ObjectTarget组件模型、SHP锚定对象身份和24个列身份/名称/引用映射。`validation-spatial-schema-approved.json` 记录正式sources/metadata/decoding/assertions文件摘要未变；本轮没有读取NAS或快照，没有新做快照完整性核验，前批全快照结论仅引用原报告。诊断不是生产读取器或完整合同Schema校验。首次命令未覆盖runtime固定CLI入口，被参数解析拒绝，未生成报告；核对Dockerfile后仅修正一次性命令入口，不修改镜像。

新增非执行 `spatial-attributes-proposal.draft.yaml`，把两组相同的12个属性映射集中供一次审阅，共24列：

| 原字段（两组相同顺序） | 目标列名 | 目标类型 | 当前批准状态 |
|---|---|---|---|
| NAME_RUS | name_u5f_rus | text | 读取已批准，类型/列映射待审 |
| NAME_ROM | name_u5f_rom | text | 同上 |
| TYPE | type | text | 同上 |
| LAT | lat | numeric(19,5) | 读取/类型已批准，列映射待审 |
| LONG | long | numeric(19,5) | 同上 |
| POS_CERT | pos_u5f_cert | bigint | 同上 |
| DATE_CERT | date_u5f_cert | bigint | 同上 |
| DATE_ | date_u5f_ | bigint | 同上，不转日期 |
| MAP_NAME | map_u5f_name | text | 读取已批准，类型/列映射待审 |
| MAP_CITE | map_u5f_cite | text | 同上 |
| ID | id | text | 同上，不按外观转整数 |
| RAS_ID | ras_u5f_id | text | 同上 |

整体提案的待批准内容：14个C列类型text、24个源属性列的上述名称映射和nullable=false约束，以及两组各一个 `__src_rownum bigint` 派生列（1起始物理SHP/DBF记录关联，保留1–59、不排序或去重；不在本提案增加派生列约束）。仅针对这两件已核验59条、无逻辑删除和已批准读取不产生NULL的对象；遇未授权token拒绝，不猜NULL，其他来源或换版不自动继承。C尾空格继续保留，N外围0x20读取及数值类型沿用前批批准，不重开编码或日期推断。

表名仍须全release分配及批准，本提案不含表名批准；几何列、CRS/SRID、规范值摘要、实际IMPORT处置及冻结全部排除。两个对象仍独立，不合并为MIRROR。两组全部组件和同包其他成员仍BLOCKED；metadata合同BLOCKED=7,914不变。3项新增产物断言回传核对，262项回归通过；无产品代码依赖镜像变更、源写入、数据库连接、服务重启或Git提交推送，Task6未完成。以下均为前批记录。

## 最新组件绑定批准及 CHGIS 来源核验

用户“同意。继续”批准前批两组各六件的精确组件绑定及SHP主成员身份锚定，决定另存 `spatial-binding-decisions.draft.yaml`，绑定前批提案摘要、两组身份、原名和物理序号。固定runtime重新逐件核对12组件，另读同包README及HTML来源说明；全快照前后校验通过。`approved-spatial-binding-context.json` 保留原字节base64、摘要、解码候选和批准边界，`spatial-objects-bound.draft.yaml` 记录绑定成立，不改变其他批准状态。

| 来源成员 | 原字节观察 | 来源事实 |
|---|---|---|
| m002704，物理序号1，ca1884_przh_Tarim_README.txt | 1052字节，UTF-8 BOM、CRLF；UTF-8和cp1251均严格解码成功 | 英文原文列出CHGIS Editor and Publisher及chgis_ras地址，分别声明UTF8/1251两套SHP |
| m002711，物理序号8，Ca1884route_przh_ru.htm | 13483字节，全ASCII；HTML声明ISO-8859-1 | Title为CHGIS Tarim Basin 1884 Points，Originator/Publisher指向CHGIS、Harvard Yenching Institute |

README非ASCII部分的业务编码未获批准；HTML候选文本相同只是全ASCII的结果，不是批准其业务编码。HTML仅用标准库提取文本作来源观察，不执行脚本或网络请求，不充当完整语义读取器。原说明的拼写、重复和字节保留，不改写。HTML中win1251说明不覆盖已批准的UTF8版本读取。说明中的非商业学术研究分发及Academic use限制仅原样登记，不推断法律许可或授权范围。

Ruling：依据DESIGN §6及源说明，将这两组schema提案从暂定harv修订为chgis，另存 `spatial-objects-chgis.draft.yaml`；原提案及绑定版本不覆盖。两组身份、七件范围名称、组件和列映射保持不变，2个ObjectTarget模型校验通过，见 `validation-spatial-schema-chgis.json`。schema归属仍待用户批准；该修订步骤只处理已有证据，不声称再次读取源或全快照。

本批批准的是12组件绑定，不包括schema/table、C列text/nullable提案、geom/__src_rownum映射、CRS/SRID或导入。PRJ和QPJ分别保留，不覆盖、不因4326声明赋SRID。README/HTML虽已读取，和未读的两件图片仍BLOCKED，外包记录不变；全版本命名尚未完成。两个新摘要文件绑定5项产物断言，回传Windows核对；262项回归通过。无产品代码、依赖或镜像变更，无NAS读取、源修改、数据库连接、服务重启、冻结或Git提交推送，Task6未完成，BLOCKED=7,914不变。

## 前批两组空间对象及映射提案

用户令继续整理两组完整组件关系；新增 `spatial-objects-canary.draft.yaml`，它是非执行 sidecar，不是 sources/decoding 合同或 frozen 发布。每组保留独立对象，不因 SHP/SHX/PRJ 相同就忽略不同 DBF。SHP 作为提议主成员，关联同一物理 ZIP、精确目录及 stem 的 SHX/DBF/CPG/PRJ/QPJ，共每组6件、两组12件；全部大小/原摘要、规则ID、原名/物理序号及成员身份保存，不按casefold或跨容器拼组。

本轮读取12件原字节并逐件复核，包含此前未读取的两件257字节QPJ；外包全部16件中央目录的物理序号、名字及大小与原清单一致。包内其余4件（README、HTML和两件图片）在提案另列，未在本批读取，不裁掉、不自动判NON_TABULAR，仍BLOCKED；外层ZIP原记录也不改变。两件QPJ均原文含 `AUTHORITY["EPSG","4326"]`，SHA-256 `1de411dcdeedce3219242306fc29bfa1d7fa08883e4ff6779baf798ec50d1657`。PRJ/QPJ完整原文、base64及摘要分别保留，不假定它们完全等价或以QPJ覆盖PRJ；没有CRS解析或SRID赋值。

对象原名提议为精确SHP basename stem：Ca1884route_przh_1251、Ca1884route_przh_utf8；carrier=shapefile。对象身份使用既有v1 API，原路径为外层ZIP路径，archive_chain明确包括主SHP叶成员，完整精确原名/物理序号继续单独保留。这是主成员锚定约定提案，不将全部组件摘要偷偷塞入v1身份，也不改变既有身份实现。

每组12个DBF源属性列按原序登记，共24列；列身份、原名、目标名与引用形式由既有API生成，原类型/宽度/小数位留证。14个C列严格编码及尾空间保留引用已批准字符决定，目标text/nullable=false仍是未批准提案；10个N列引用已批准读取及numeric(19,5)/bigint类型，不再把类型批准标成未批准。字段与两件精确DBF摘要绑定，目标映射还未批准。

每组另提一个 `geom geometry(Point)` 源几何映射（不计入24属性列），按原XY double保留，SRID留未定；不是可执行DDL，也不因QPJ出现4326而赋SRID。另提 `__src_rownum bigint` 为这两件没有删除记录的SHP/DBF物理序号关联，1–59，与源列名字不碰撞；关联及派生列未批准，不推广为带删除记录来源的过滤规则。

目标schema暂提harv，仅为Harvard来源候选分组，来源领域归属（是否应属于chgis）仍待依据README等说明审阅；未据后缀或路径完成领域分类。namespace提议保留外层源父目录加成员目录。表名由现有API对5个TSV＋2个空间对象的七件范围重新分配：顺序反转一致、无碰撞、原五件文本名称未变。全版本对象尚未齐备，名称不可冻结。expected_count=59引用已观察记录数；expected_sha256留null，不把源字符/数值/坐标诊断摘要混成正式G4/G5期望。

`validation-spatial-objects-canary.json`只证明2个ObjectTarget、14个ColumnEncoding现有组件模型校验及七件命名检查，不证明完整sidecar通过JSON Schema、生产读取器实现或目标验收。Ruling：BLOCKED规则仍不得有业务targets，提案独立保存，不放宽模型、不提前改IMPORT；完整组件绑定、schema/table、C类型、几何/CRS仍待批准及正式验证路径。

全快照读取前后与证书一致，`artifact-hashes-spatial-objects-canary.json`绑定新增文件、回传Windows核对通过后受控同步32；262项回归通过。复用固定自有镜像和既有API，无产品代码依赖镜像变更、NAS读取、源修改、数据库、服务重启、冻结或Git提交推送。Task6未完成，BLOCKED=7,914不变。下列批准及观察是前批记录，不回写历史。

## 最新 N 字段批准及精确复核

用户对前批数值提案答复“继续，同意。”，批准仅这两个精确 DBF 的五个 N 字段：移除 N 格式外围0x20后严格读取，LAT/LONG 为精确十进制及 `numeric(19,5)` 类型，POS_CERT/DATE_CERT/DATE_ 为整数及 `bigint` 类型，DATE_ 不转日期；原字段字节保留。C 尾部空间继续保留，不指定 SRID。批准另存 `shapefile-numeric-decisions.draft.yaml`，绑定前批证据 SHA-256、两件大小/摘要、物理序号、逐字段原名/序号、N宽度/小数位；原字符决定和历史候选不覆盖。

本件未发现空白N或不支持token，因此批准不扩大为其他源的空白/NULL、星号、指数表示、异常哨兵规则。决定明确未批准空白N的NULL语义，遇到未授权token只能拒绝，不能猜零或NULL。批准的列类型不是已发布schema/table映射，更不是建库或导入授权。

固定 runtime 直接重读两件，并以绝对偏移切片和独立顺序游标两条路径从原始DBF头部/描述符取全部字段，原字节逐项一致。N 路径A按批准语法使用 Decimal或int；路径B自行跳过外围0x20、逐数字累计整数系数和小数位，构造精确Fraction。590个数值逐项精确相等，并与前批候选序列一致，不仅比较摘要；LAT/LONG全部恰为5位小数且绝对值小于10^14，其他三个整数均在bigint范围内，无舍入/量化/float中转。N源字段完整保留，辅助类型化字符串摘要不冒充正式G4规范摘要。

按既有字符决定重新复核826个C值，逐字段严格解码结果一致，全部尾部空间保留。报告 `approved-dbf-numeric-reading.json` 记录逐列原声明、批准类型、比较数量、无损适配检查、决定/候选/正式metadata合同摘要和未决授权范围。两条路径是源诊断，不是经黄金夹具验证的生产独立DBF读取器或目标G4/G5验收。

Ruling：仅落实逐案批准的N读取和类型，不借此建立未批准的空间对象绑定/目标映射，C去空间、NULL、CRS/SRID仍未放行；若后续对象合同方案改变，原批准和证据保留另存，不覆盖历史。全快照前后核验通过，`artifact-hashes-dbf-numeric-reading.json`绑定决定与报告、回传核对通过；262项回归通过。无产品代码依赖镜像变更、NAS读取、源修改、数据库连接、服务重启、冻结或Git提交推送，Task6未完成，BLOCKED=7,914不变。

## 前批数值、填充与 Point 原字节观察

用户令继续，固定 runtime 对前述两个精确组重读 DBF/SHP/SHX，报告另存 `dbf-numeric-point-observations.json`，不覆盖已批准字符决定或前批证据。只处理同一 1884route 包的两组，每组选中成员原名、物理序号、大小和摘要再次核对，全快照读取前后仍与完成证书一致。

两组各 59 个 Point：逐 SHX 索引寻址与从 SHP 起始顺序扫描的 X/Y 原始 16 字节实际比较一致；每条原字节、float.hex 和记录序号全部留证。118 次“坐标对”观察均为有限 double，打包回原字节完全一致；两组头部 XY bbox 与各自全部 59 点的 min/max 一致，不做舍入、投影或 Z/M 补维。索引和顺序路径共享 struct 浮点解码器，这是取址/字节观察，不是独立浮点实现、生产空间读取器或 G5 验收。

Point 字节位置依据 [Esri 官方规格 Table 4](https://www.esri.com/library/whitepapers/pdfs/shapefile.pdf)：shape type 1，依次为 X、Y。PRJ 仍只保留原声明，不因坐标范围或名字赋 SRID；DBF LAT/LONG 与 SHP X/Y 没有被假定等同或互相替换。

两件 DBF 的 5 个 N 字段逐物理记录保留完整原始字段 base64，并单独对去外围 0x20 的**诊断候选 token**检查普通十进制语法。去空间与 Decimal 只存在候选观察，不修改原字节、已批准字符值或正式合同；每个 token 由 Decimal 文本路径及符号/数字/小数位元组路径构造，精确值与 as_tuple 相同，无二进制浮点中转、舍入或量化。

| N 字段（两组相同声明） | 声明宽度/小数位 | 每件完整观察（各59条） | 未批准读取/类型提案 |
|---|---|---|---|
| LAT | 19/5 | 全部5位小数；候选范围35.98985–41.25143 | 去除 N 格式外围0x20后严格精确十进制；目标 numeric(19,5) |
| LONG | 19/5 | 全部5位小数；候选范围79.53750–89.87492 | 同上；不作为坐标替代值 |
| POS_CERT | 16/0 | 全部整数；候选范围7716–9775 | 严格整数；目标 bigint，不推断业务含义 |
| DATE_CERT | 16/0 | 全部整数365 | 严格整数；目标 bigint，不推成 NULL/哨兵或日期 |
| DATE_ | 16/0 | 全部整数18850101 | 严格整数；目标 bigint，不转日期 |

合计 2×59×5=590 个 N 字段均为普通十进制候选，无全空格、NUL、星号或不支持 token，实际小数位没有超过声明；两件的各 N 列完整原始字段逐条实际相同，不只比较摘要。以上目标类型及数值解释仍待用户批准；nullable=false 若后续提出，也只能解释本件没有空白/NULL 候选，不得自动扩展到其他 DBF 的空白或哨兵规则。

本件 N 字段只有前导0x20、无尾部0x20；每件五列合计3,245个前导空间字节。C 字段无前导0x20、存在此前保留的尾部0x20，全部12列无NUL/全空格记录。继续保持 C 固定宽度字符串，包括尾部空间，不启用 rstrip。dBASE [字段存储说明](https://www.dbase.com/Knowledgebase/INT/db7_file_fmt.htm) 可作 C/N 空格存储背景，但其 Level 7 布局不套入本件 version=3；官方 GDAL 源页面本轮无法读取，不冒称核对了当前驱动去空白实现。本轮不据经验决定 C 的最终逻辑去填充规则。

Ruling：数值/填充的候选成功仅提供提案依据，不自动把 N 转 float、DATE_ 转 date，或把全空白与0解释为相同；C 的编码批准不包含去尾空格。几何观察不批准 SRID/组件绑定，也不把同包不同 DBF 合并。若数值提案获否决，另存修订与复核，不覆盖完整原字段证据。

新增报告由 `artifact-hashes-dbf-numeric-point.json` 绑定，回传 Windows 核对后同步32；262项回归通过。无产品代码、依赖或镜像变更，没有 NAS 读取、源修改、数据库连接、长期服务重启、冻结或 Git 提交推送。Task6 未完成，BLOCKED=7,914 不变。

## 最新 DBF 字符列批准及字节复核

用户对两件精确 DBF 的各 7 个字符列严格 cp1251/UTF-8 提案答复“同意，继续”。决定独立保存为 `shapefile-character-decisions.draft.yaml`，锁定 m002706/m002714 的完整外层路径、ZIP 原名与物理序号、大小和原始 SHA-256，逐列记录原序号、名字及 codec；不修改 sources/decoding，不覆盖前批候选证据。

批准仅覆盖 NAME_RUS、NAME_ROM、TYPE、MAP_NAME、MAP_CITE、ID、RAS_ID 的字符字节严格解码。两件都是固定宽度 C 字段；编码批准不等于剥除空格或 NUL、NULL 规则、数值转换、目标类型/映射、空间组件绑定、CRS/SRID 或冻结/导入批准。对纯 ASCII 字段也逐列留有决定，不将一个笼统文件编码自动套到其他字段或源件。

固定 runtime 直接重读两件原字节，并由两个诊断路径独立取字段：A 使用 struct 解析原始头部、描述符和绝对记录偏移切片；B 使用 BytesIO 顺序读取、from_bytes 解析头部，独立读取描述符及逐字段推进游标。没有复用旧 truth/importer，也不从前批报告取得期望切片。两条路径的头部/描述符、记录标记及全部字段原字节实际比较一致：2 件 × 59 条 × 12 字段 = 1,416 个切片。随后各自按已批准 codec 严格解码 C 字段，2 件 × 59 条 × 7 列 = 826 个字符串实际比较零差异，非仅摘要比较。

`approved-dbf-character-reading.json` 记录逐列原字节辅助摘要、解码后固定宽度字符串辅助摘要、空格/NUL观察及批准决定摘要；原字节辅助摘要与前批观察一致。原字节摘要用每值 4 字节大端长度前缀加原值；解码字符串摘要用每值紧凑 ASCII JSON 字符串加 LF，均按记录顺序，只作本批诊断辅助，不是正式目标 G4 规范摘要。

两件各 59 条活动标记、零删除标记；全部固定宽度字节保留。7 个字符列合计 `_1251` 保留 5,964 个尾部 0x20 字节、`_utf8` 保留 5,544 个，所有 C 字段本批无 NUL 或全空格记录。差异来自 NAME_RUS 的固定宽度占用，但本批不以此推断业务文本相等或合并对象，不裁掉任何空格。尾部空间如何对应逻辑 DBF 值仍须格式语义和独立读取路径审阅。

这些是两条源字节分区诊断路径，不是经过黄金夹具验证的独立生产 DBF/空间读取器；两路径共享 Python codec 解码器，不证明该解码器实现独立。N 值、几何、CRS、目标库与 G4/G5 均未验证。Ruling：已批准编码只作为受限字节解释落实，不把填充未决的固定宽度字符串包装成最终逻辑值合同；若后续明确 DBF 填充语义，须新证据保留本批原字节及历史结果，不能覆盖它们。

全快照读取前后与证书一致，`artifact-hashes-dbf-character-reading.json` 绑定批准决定与新报告，回传 Windows 核对通过；262 项回归通过。复用现有自有镜像，无产品代码、依赖或镜像变更，无 NAS 读取、源修改、数据库连接、服务重启、冻结或 Git 提交推送。Task 6 未完成，BLOCKED=7,914 不变。以下为前批批准前的候选观察，不回写历史。

## 前批 Shapefile canary：结构及编码候选

用户令继续审阅空间组件。选择不含嵌套链、核心成员和 CPG/PRJ 均完整的最小候选包 `harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip`，同时检查同包 `5_1884route/Ca1884route_przh_1251` 与 `5_1884route/Ca1884route_przh_utf8` 两组。外层包 2,156,327 字节、SHA-256 `39f505c1c4f719348fc0e8ee5ebf49c5c017ce1143a9a7755b742518101153d7` 与快照完成证书一致。逐件大小/摘要、原名及零基 ZIP 序号见新增 `shapefile-canary-observations.json`，不覆盖旧清单级或未决位置报告。

本批固定自有 runtime 直接读取 10 件 SHP/SHX/DBF/CPG/PRJ 原字节；ZIP 中央目录由已有 preflight 限定 16 MiB/100,000 件，外包限制 16 MiB、选中单成员 1 MiB，无解压落地。成员按精确物理序号打开并核对原名，不用同名首匹配。仅为源格式诊断片段，不新增产品读取 API、装载器或正式验证器，不复用旧 truth 中替换解码/猜测行为。

两组各自结果：

| 范围 | 已观察事实 | 不能据此声称 |
|---|---|---|
| SHP/SHX | file code 9994、version 1000、shape type 1；文件声明长度与实际一致；59 个 SHX 项逐件偏移/长度匹配 SHP，记录号顺序 1–59，完整消费到文件末 | 尚未逐坐标核验有限值、范围、几何语义或独立第二空间解析路径，不是 G5 |
| DBF | version byte 3、头长 417、记录长 280、声明 59 条、12 个 32 字节描述符；字段宽度和记录长一致，所有记录完整、尾部无额外字节 | 未解析 N 值/精度、未确定 NULL、字段填充或目标类型，不是 G2/G4 |
| 删除标记 | 59 条标记均为 0x20，无 0x2A 或其他标记；DBF 物理条数与 SHX 一致 | 不推广到其他组，不跳过未来发现的删除记录 |
| PRJ | 两件原字节相同，原文为 GEOGCS/GCS_WGS_1984，含 D_WGS_1984、WGS_1984 椭球、Greenwich、Degree；完整原文/base64/摘要留证 | 未解析 CRS，未指定 EPSG/SRID，未转换坐标 |

12 个字段按原序为 NAME_RUS、NAME_ROM、TYPE、LAT、LONG、POS_CERT、DATE_CERT、DATE_、MAP_NAME、MAP_CITE、ID、RAS_ID。原始字段描述符、名称字节、类型字节、长度和小数位均保留；其中 7 个 C 字段、5 个 N 字段，不能因字段名 DATE_ 就改成日期。

`_1251` 的 CPG 4 字节原文为 `1251`，`_utf8` 的 CPG 5 字节原文为 `UTF-8`，两件 DBF language driver byte 均为 0。对每个 C 字段的全部 59 条固定宽度原值分别尝试严格 UTF-8/cp1251，不剥空格、不改字节、不吞错误，含全部物理记录：

- `_1251`：7 个字符字段按 cp1251 全部成功；NAME_RUS 按 UTF-8 有 59 条失败，首次在第 1 条、DBF 原字节偏移 418。其余 6 个 C 字段本件只含 ASCII 字节，不能凭可解码成功独立辨认其编码。
- `_utf8`：7 个字符字段按 UTF-8 全部成功；NAME_RUS 按 cp1251 有 2 条失败，首次在第 33 条、偏移 9379。其他 6 个 C 字段本件只含 ASCII。

CPG 声明与上述全列观察相容，**待批准提案**为这两个精确 DBF 的 7 个字符列分别严格 cp1251、UTF-8；并非从文件名猜编码，也不推成其他包的通用规则。字段名严格 ASCII 可读的事实与值列编码分开；“可解码”不证明语义唯一正确，不代表已实现独立 DBF 值读取或批准去填充空格。列级批准、DBF 空白/数值语义及正式读取路径仍待下一步。

两组 SHP、SHX、PRJ 不只摘要相同，实际字节比较也相同；DBF 与 CPG 实际不同。Ruling：共享几何不使整个对象成为 MIRROR，不将两组字段值覆盖或合并，保留独立源对象候选；若后续证明解码后的部分业务值相同，也不能据此绕过原字节与完整对象的镜像合同。QPJ 和包内其他成员未在本批读取，仍有原清单记录和 BLOCKED 处置，没有静默消失。

格式背景核对 [Esri Shapefile 官方说明](https://www.esri.com/library/whitepapers/pdfs/shapefile.pdf) 的头部、索引和按记录序号关联要求，以及 [GDAL Shapefile 编码文档](https://gdal.org/en/stable/drivers/vector/shapefile.html#encoding) 对 CPG/LDID 的说明；没有安装或调用 GDAL，也没有启用其自动解码。本批 DBF 使用已观察 version=3 的 32 字节描述符布局，不把 dBASE 7 的 48 字节描述符规格套入本件。

全快照读取前后核验通过，`artifact-hashes-shapefile-canary.json` 绑定新报告，回传 Windows 核对通过；262 项回归通过。没有代码依赖镜像变更、NAS 读取、源修改、数据库连接、服务重启、冻结或 Git 提交推送。Task 6 未完成，BLOCKED=7,914 不变。

## 最新只读字节核验

后续两件外层 TAB 的解释已获用户逐件批准并重新源复核，最新结果统一见 `text-review.md` 的“最新批准与五件对象提案”。下面是本批空间观察时的历史状态；新文本批准不自动绑定空间组件或扩展其他成员的读取规则。

后续用户令继续核验未决位置；新证据为 `spatial-exception-observations.json`，不覆盖下列清单级报告。固定自有 runtime 对已验收快照只读打开了 9 个物理归档（包含为抵达内层而读取的外层包），使用每层精确原名和零基物理序号，不使用 ZipFile 的同名首匹配或解压到源目录。每层大小/摘要核对清单，中央目录全部成员的原名、物理序号和大小与清单一致；嵌套包限制 64 MiB/件，小观察成员 1 MiB/件，中央目录 16 MiB。源输入只读，临时 spool 在容器 tmpfs，结束关闭回收。

下述 1 个 DBF 与 3 个 PRJ 在**各自物理归档全部中央目录**中，既无精确同名，也无 casefold 同名，且该归档没有任何同后缀成员。不是仅因前一轮分组 stem 严格而漏配。这个结论只针对这些已锁摘要的归档；不等于裁定源数据损坏、允许补件或推断 CRS。缺 DBF 的属性/几何保真方案及缺 PRJ 的源声明/空间策略仍须单独审阅，不创建空属性表、不从其他版本拷 PRJ。

4 件 TAB 原字节大小/摘要核验通过，观察如下：

| 精确规则 | 已观察源声明/头部 | 尚未批准事项 |
|---|---|---|
| m003577、m003971（两个不同 V3 内包） | `!table`、version 410、WindowsSimpChinese、Type NATIVE、Fields 23；未检出本次受限 File 声明行模式 | 不把声明字符集当作 DAT 值编码证明；不自动关联大小写不同的 DAT/MAP/ID/IND，不推定两包 MIRROR |
| m004812（上海 presentations 索引） | authorlast、authorfirst、format、language、type、title、filename；第一物理行 6 个 TAB | 制表文本候选；未批准引号/BOM/空值语义，未建立逻辑记录数或列级合同 |
| m006642（GB_91_HZ_040201_UTF8） | GB_91、HZ_NAME、PY_NAME、ADM2、ADM1、ADM_LVL；第一物理行 5 个 TAB | 制表文本候选；名称或全文 UTF-8 能解码不是独立编码/方言合同 |

两件外层 TAB 没有 `!table` 起始标记，应转入文本格式审阅，不能继续按“缺 DAT 的 MapInfo”解释。三件首批文本的读取批准只绑定此前三个精确摘要，不自动扩展到这两件。4 件 TAB 全文 UTF-8 可严格解码这一事实已记录；对 Native TAB，定义文件能解码尤其不能证明伴随 DAT 的业务值编码。

m006629 的 5 个原字节为 ASCII `UTF-8`，已保留 base64 及摘要。它的原名仍是 `Ming_Stations_2016.cpg`，没有因为同处 Ming_Routes 包就改名或强加到其他 stem；组件适用关系未批准。

本轮全快照读取前后核验与既有证书一致，快照清单摘要仍为 `03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699`；没有再读原 NAS。`artifact-hashes-spatial-exceptions.json` 绑定新增报告，回传 Windows 后摘要核验通过。未改源、代码、依赖或镜像，未安装 GDAL，未连接数据库、冻结、提交或推送；最新合同 BLOCKED=7,914 保留。下面的清单级计数与“尚未读取声明”叙述是前批次历史范围，不用新结论覆盖旧证据。

## 前批次清单级范围与方法

前批次复用固定自有 runtime `sha256:f67768cf44dfbdd183766d5828404a8905932912b720a3cd8f7098f1feb38b00`，只处理既有清单和候选合同，不重新读取快照源字节，不安装 GDAL 或修改代码/依赖/镜像。报告 `spatial-component-candidates.json` 绑定清单摘要 `fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db` 及 metadata 合同摘要 `0b98f0078dd3d2756984881610df67a5a937fa1b93005ecf99fba66f6626422c`；该清单级报告本身不是新的源未变检查或格式验收证书。

分组键为完整物理包含容器身份（外层路径、包含归档链与每层序号）＋精确成员目录＋精确 basename stem。最终成员原名/物理序号/大小/摘要逐件保留；不会按跨归档同名拼组。只有后缀大小写用于候选分类，目录与 stem 不折叠、不重命名。casefold 仅另报可能歧义，不自动合并或选取第一个命中。无归档成员按完整源相对目录分组。

Shapefile 核心三件关系依据 [Esri 官方技术说明](https://www.esri.com/library/whitepapers/pdfs/shapefile.pdf)，TAB/DAT/MAP/ID/IND 等为常见 MapInfo 组件集合，依据 [GDAL 官方 MapInfo 文档](https://gdal.org/en/stable/drivers/vector/mitab.html)。这些资料只规定格式背景，不能证明当前候选字节就是相应格式；带 .tab 后缀的表格、栅格参照或其他内容必须分别识别。归档父目录写着 shapefiles 或 mapinfo 也不是格式证明。

## 计数口径

分母是既有清单中的 7,918 件文件；命中本轮候选后缀的 5,248 件（包含此前已验证的 3 件 TSV）。已知 3 件外层 TSV 精确排除出 MapInfo 关系候选，仍保持原 BLOCKED；不按扩展名排除其他 TAB。

| 清单关系候选 | 数量 | 含义与限制 |
|---|---:|---|
| Shapefile 组 | 705 | 由 SHP 或 SHX 作为关系入口，不是已确认图层数 |
| 未找到同组核心组件的 Shapefile 组 | 1 | 同物理容器/目录/精确 stem 没有 DBF；不是损坏或可修复结论 |
| 未找到同组 PRJ 的 Shapefile 组 | 3 | 不猜 CRS，不从其他版本补 PRJ |
| TAB/MapInfo 关系组 | 146 | 后缀候选，声明文件尚未读取 |
| TAB/DAT/MAP/ID 四后缀同组 | 140 | 存在同名组件不等于能读、几何正确或可导入 |
| 大小写可能歧义集合 | 2 | 精确 stem 组仍分开 |
| 未配对相关成员 | 1 | CPG 保留，不能静默丢弃或配给其他 stem |

本轮候选范围没有 MIF/MID。Shapefile 候选组未发现同组同后缀多物理成员，但这一观察不代表其他未审阅格式不存在重名。完整每组成员、原位置和候选问题均在机器报告，不用上述汇总代替逐件处置。

## 精确未决位置

同基名 DBF 未找到：`harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_pref_pts_utf.zip` 根目录 stem `v5_time_pref_pts_utf`。下次须核对原归档中央目录及相关字节，不跨版本查找并补入 DBF，不创建空属性表。

同基名 PRJ 未找到：

- `harvard-full/doi_10_7910/DVN/ELTD3L/RAS_1900_pdb2_gis.ZIP` 根目录 stem `tib19pdb`；
- `harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip` → `shapefiles/v2_time_cnty_pgn_utf.ZIP`，内层物理序号 104，stem `v2_time_cnty_pgn_utf`；
- 同一外层包 → `shapefiles/v2_time_cnty_pts_utf.ZIP`，内层物理序号 106，stem `v2_time_cnty_pts_utf`。

大小写差异出现在 `harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip` 的两个不同内包：`shapefiles/v3_time_pref_pgn_PRC.ZIP`（序号 66）与 `mapinfo/v3_time_pref_pgn_PRC.ZIP`（序号 114）。两包各自都有 `V3_time_pref_pgn_PRC.TAB/.ID` 与 `v3_time_pref_pgn_PRC.DAT/.MAP/.IND` 的精确 stem 差异。没有把两包合并、推定镜像，或自动把大小写不同的组件绑定为同一表；须读取各 TAB 的明确引用并核验原字节。

未配对 CPG 为 m006629：`harvard-full/doi_10_7910/DVN/SB8ZTM/Ming_Routes_2016.zip` → `Ming_Stations_2016.cpg`，物理序号 2，5 B。没有据此给同包其他 stem 强加编码，也不判断它是无用文件。

另有两件只有外层 TAB 的候选：`harvard-full/doi_10_7910/DVN/MI56KU/2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab` 与 `harvard-full/doi_10_7910/DVN/SK7KGK/GB_91_HZ_040201_UTF8.tab`。它们尚未做头部或全文格式核验，不能从名称推定为 MapInfo、TSV 或缺件空间表。

## 边界与接续

报告覆盖相关候选后缀并显式列出未配对件；其他后缀成员仍在原全量处置账，不是被丢弃。本报告不是 frozen 合同、组件适配器或加载器；未决定编码、字段、记录数、几何/CRS、镜像或目标表。所有成员仍按原规则处置，8,004 唯一匹配、BLOCKED=7,914、incomplete_inventory 保留、ready_for_import=false。

`artifact-hashes-spatial-components.json` 绑定清单级报告，已回传 Windows 并核对摘要；旧证据不覆盖。上述未决位置及 TAB 声明的后续受限字节观察见本页最新节；接续须审阅两件新增文本的方言与编码，以及 Native TAB 大小写关联、缺件保真和空间独立验证方案。不修源、不猜编码或 CRS，不安装未授权工具、不访问数据库。源生缺件/命名观察不记为我方代码缺陷。
