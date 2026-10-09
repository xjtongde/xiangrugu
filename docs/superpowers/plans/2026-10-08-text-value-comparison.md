# text/bigint 有序值比较 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 若用户另选逐任务Agent执行，使用superpowers:subagent-driven-development；不得自行派Agent。

**Goal:** 实现只处理text/bigint/显式NULL的纯合成有序值比较切片，逐值证明相等而非只比摘要。

**Architecture:** `canonical.py`负责无损字节编码、结构绑定和流摘要；`validate.py`负责独立输入、结构/序号/计数/逐值比较及有界报告。两者不访问文件、源、数据库或importer；真实源/库适配器留到另行批准的后续任务。

**Tech Stack:** 现有Python3.11、自有dev/test/runtime镜像、pytest及标准库dataclasses/hashlib/json/struct；不新增依赖。

**Spec:** `docs/superpowers/specs/2026-10-08-text-value-comparison-design.md`。2026-10-08用户“继续”回应规格审阅门，本批据此编写计划；本计划尚待审阅及实施授权。

## Global Constraints

- Windows `C:\Users\zkyxy\Documents\codex-xiangrugu`仅编辑/sync；所有Python和测试经SSH在32执行。
- text严格UTF-8、禁止Unicode规范化/strip/推断/替换；bigint排除bool且限定[-2^63,2^63-1]。
- 默认100,000记录/端、512列、单text1MiB、单行payload8MiB、完整流256MiB/端、差异明细100项；允许收紧不允许静默扩大。
- 字节标记、整数端序、列JSON/header/row/trailer完全按规格§4–5；最后一列为`derived:__src_rownum`，不得再发明格式。
- 不处理numeric、浮点、时区、bytea、JSON、空间/栅格、无序/Merkle；未知类型拒绝。不能宣称完成整个Task9或Task6。
- 不改旧truth/verifier、sources/decoding/assertions/current或已有release证据；不读NAS/快照、不连任何库、不启动test-db。
- 不提交、推送、切分支或另建工作树。每任务保存RED/GREEN证据及摘要到32运行目录，再回传新证据，不覆盖历史产物。
- 真实导入前先通知用户，共同确认pg32b原数据处置；此计划不授权真实导入、冻结、旧数据处置或重启长期容器。

## Review Focus

- 字符串中真实U+2400/U+0000和Unicode组合差异不能变成NULL或相等：Task1固定黄金向量。
- 容器/调用者传入bool、数字字符串或未知类型不能绕过严格类型：Task1负向参数化测试。
- 一次性迭代器中途失败或两端长度不同不能被当完整流：Task2/3单次消费及partial测试。
- 达到差异列表上限或摘要被注入碰撞不能提前通过：Task3继续遍历/直接字节比较测试。
- 巨字段、行、总流及恶意取消回调不能制造大分配/业务值泄漏：Task2/3预算与异常脱敏测试。

---

## 文件及执行约定

新增 `datamgmt/src/xiangrugu_datamgmt/canonical.py`、`validate.py`；新增 `datamgmt/tests/unit/test_canonical.py`、`test_value_validation.py`及 `datamgmt/tests/fixtures/value_v1_golden.json`。后者只含手工合成字节，不含真实源数据。不改CLI、依赖锁、Dockerfile或现有模型语义；最后同步README/主执行计划及文档日志。

每个RED/GREEN周期：Windows用apply_patch写测试或实现，PowerShell运行 `.\scripts\sync-dev.ps1`；32执行如下命令，退出码与对应断言都要核对。不得在Windows运行pytest。

```powershell
ssh root@192.168.3.32 'docker exec xiangrugu-dev python -m pytest /workspace/datamgmt/tests/unit/test_canonical.py -q -p no:cacheprovider'
```

Task3命令改为test_value_validation.py；累计命令指定整个 `/workspace/datamgmt/tests/unit`。dev已经设置PYTHONPATH=/workspace/datamgmt/src，测试文件和包均来自只读受控同步区。初始RED必须因新增接口缺失或具体行为错误，不因路径、环境、依赖故障；最小测试使用既有test_source_text.py的importlib发现模式，避免收集错误遮蔽原因。

### Task 1：严格列/预算模型与单元格字节

**Files:** 新canonical.py、test_canonical.py、value_v1_golden.json。

**Interfaces:** 使用frozen dataclass并在构造/使用入口严格验证，不新引依赖；错误统一`ValueContractError(code: str, *, rownum: int | None = None, column_key: str | None = None)`，字符串消息只含固定错误码和位置，不含输入值或第三方异常正文。

生产接口：`ValueColumn(column_key: str, target_name: str, pg_type: str, nullable: bool)`；`ValueSchema(source_object_id: str, columns: tuple[ValueColumn, ...], format_version: int = 1)`；`ValueLimits(max_rows=100000, max_columns=512, max_field_bytes=1048576, max_row_bytes=8388608, max_stream_bytes=268435456, max_differences=100)`；`encode_cell(column: ValueColumn, value: object, *, limits: ValueLimits) -> bytes`。

列key限定64位小写hex或固定派生key；target_name按现有naming.quote_identifier边界检查并拒绝重复；源列可为text或bigint。schema末列必须是key `derived:__src_rownum`、target_name `__src_rownum`、bigint、nullable=false，其余列不能占用派生名/key。普通nullable必须原生bool；预算必须原生正int（排除bool），max_differences允许0且此时只累计不保留明细，其他预算大于0。身份、格式版本、列key/名称/重复/未知类型、派生位置均严格验证，格式版本仅原生int 1有效。

- [ ] 写手工向量测试`test_null_empty_text_and_literal_null_symbol_have_distinct_bytes`：nullable text分别None/空串/␀，断言完整hex为`00`/`010000000000000000`/`010000000000000003e29080`且两两不同。
- [ ] 写`test_bigint_golden_and_bounds`：1/-1断言`020000000000000001`/`02ffffffffffffffff`；两端边界有效，越界、bool、float、Decimal、数字字符串拒绝；text不能接受int/bytes，nullable=false不能接受None。
- [ ] 写Unicode/空白/TAB/LF/CR/引号/NUL原样黄金测试，组合与分解Unicode编码不同，孤立surrogate拒绝；参数化覆盖未知类型、身份/列结构、预算和版本非法输入，错误不得含测试秘密值。
- [ ] sync并运行上述测试RED，留存真实失败原因。
- [ ] 实现上述模型和encode_cell；使用严格UTF-8与struct.pack大端，编码前做字符上界检查，编码后核验字段字节预算。
- [ ] 同命令GREEN，固定向量不得由encode_cell生成；新测试及累计单元均通过。仅记录变更，不Git提交。

### Task 2：结构绑定、行帧与完整流摘要

**Files:** 修改canonical.py/test_canonical.py，扩充合成黄金夹具。

**Interfaces:** 消费Task1模型/API。生产`schema_bytes(schema: ValueSchema) -> bytes`、`header_bytes(schema: ValueSchema) -> bytes`、`trailer_bytes(count: int) -> bytes`；`EncodedRow(frame: bytes, cells: tuple[bytes, ...], rownum: int)`；`encode_row(schema: ValueSchema, values: tuple[object, ...], *, expected_rownum: int, limits: ValueLimits) -> EncodedRow`；`StreamSummary(row_count: int, field_count: int, stream_bytes: int, sha256: str)`；`summarize_rows(schema: ValueSchema, rows: Iterator[tuple[object, ...]], *, limits: ValueLimits, cancelled: Callable[[], bool] | None = None) -> StreamSummary`。

内部`ValueStreamState(schema: ValueSchema, limits: ValueLimits)`单次维护header/行/trailer哈希与计数，提供`accept(values: tuple[object,...]) -> EncodedRow`及`finish() -> StreamSummary`；状态只供validate复用字节构造，不复用源解析。finish后拒绝accept/再次finish；失败后不能finish成功。最后序号与下一期待号严格相同，bool不当整数；行payload拼装前逐cell累计并检查8MiB及总流预算，给trailer预留9字节。

- [ ] 写`test_schema_header_row_and_empty_stream_match_hand_derived_fixture`：完整列JSON字节及对象流固定人工构造，独立hashlib对fixture bytes算期望，不从待测模块反推黄金答案；空表仍含header+trailer0。
- [ ] 写分隔歧义测试：`('ab','c')`与`('a','bc')`不同；列名/顺序/type/nullable改变schema bytes；身份改变header；表位置不在值流。
- [ ] 写`test_stream_requires_normal_eof_and_contiguous_rownum`：零行/重复业务行允许，1/2/10错误跳号、重复号、头部/宽度错误、额外行均拒绝；一次性迭代器只消费一次。抛错生成器不得返回StreamSummary。
- [ ] 写严格字段/列/行/记录/总流预算边界，取消为true或回调抛异常均失败且脱敏，取消回调返回非原生bool也拒绝；未知版本拒绝。取消每次获取下一行前检查，结束前再检查，不能宣称能中断一个永不返回的next()。
- [ ] RED后实现固定帧、ValueStreamState、summary；记录中途错误计数由Task3报告完成，纯summarize抛脱敏ValueContractError，不返回成功前缀摘要。
- [ ] GREEN及累计单元通过，人工参考序列化路径逐字节复核所有golden，检查内存只与当前受限行相关；不提交Git。

### Task 3：独立输入接口与有界逐值差异报告

**Files:** 新validate.py/test_value_validation.py；消费Task1/2，不改装载器或旧verify。

**Interfaces:** `ValueEvidence(kind: str, reference: str, sha256: str)`为冻结数据记录，kind仅synthetic/source/target，reference非空，sha256严格64位小写hex；它只是调用者证据引用，不证明来源已验收。`ValueInput(schema: ValueSchema, rows: Iterator[tuple[object,...]], evidence: ValueEvidence)`；`compare_ordered(expected: ValueSchema, source: ValueInput, target: ValueInput, *, expected_count: int, limits: ValueLimits, cancelled: Callable[[],bool] | None = None) -> ComparisonReport`。expected_count原生非负int，且不超过max_rows。

`ComparisonReport`为frozen报告，提供`to_dict() -> dict`。字段固定：format_version/source_object_id/schema_hash/source_evidence/target_evidence、source_count/target_count、source_partial/target_partial、source_sha256/target_sha256（失败不完整端为None）、compared_fields/difference_count/differences/details_truncated/limits/result/error_code。result仅comparison_equal/comparison_failed；禁止CONFORMS/ready_for_import字段。

每条差异为冻结`ValueDifference(rownum: int | None, column_key: str | None, code: str, expected_type: str | None, actual_type: str | None, expected_bytes: int | None, actual_bytes: int | None, expected_sha256: str | None, actual_sha256: str | None)`。不保存值、异常正文或完整编码字节；业务不同值按cell累计，多/少行各按row累计，结构不符按结构错误计1并拒绝消费rows，报告的“总差异数”是这套检查项数而非都解释成字段数。

- [ ] 写同值/重复业务行/空表成功测试；source/target分别使用独立手工迭代器，结构/expected_count必须吻合，结果不得出现CONFORMS。
- [ ] 写空串→None/U+2400/改单值/Unicode变体/类型改变/列换序/漏列/漏行/多行/重号失败测试；类型或非法序号错误明确失败，不宽松纠正。结构错误不得调用rows.next。
- [ ] 写`test_digest_collision_does_not_bypass_cell_equality`：替换摘要返回相同串，源/库cell bytes不同仍失败；验证使用EncodedRow.cells直接逐个bytes比较，无hash捷径。
- [ ] 写`test_detail_cap_preserves_total_count_and_full_scan`：限制1项，三行各一差异，total=3、details长度1、truncated=true、两端完整count=3；限制0仍失败且count=3。多/少行后必须消费较长端至EOF或明确预算失败。
- [ ] 写某端迭代器中途异常/取消/回调异常/预算失败，partial与None摘要正确，异常不打印业务值；成功端仅在正常EOF/finish后有摘要。对于运行中取消，两端均不能报完整通过。
- [ ] 写“双方适配器同时丢空串”故障，由独立黄金期望而非双方互证检出；测试不读真实文件/库。
- [ ] RED后实现一次zip_longest式遍历、两条ValueStreamState和直接cells比较；计数末尾与expected_count核对，超过明细上限仍全量检查。固定错误码分类structure/value/count/rownum/unsupported_type/budget/cancelled/input_error，schema_hash来自expected。
- [ ] GREEN及累计单元通过；确认报告to_dict只包含JSON原生值、无Iterator/bytes/业务字符串，所有预算/拒绝规则均覆盖。不提交Git。

### Task 4：候选镜像验证、记录与交付

**Files:** 修改datamgmt/README.md、datamgmt/docs/IMPLEMENTATION-PLAN.md、docs/log.md；证据新建于release或专用开发验证目录，不能覆盖历史文件。

- [ ] 实施前只读检查32磁盘/负载、dev/pg32/pg32b的ID和StartedAt，记录当前三个自有镜像ID及其可寻址性。任何缺失回退内容先停止，不重演B-14。
- [ ] 在重新构建前固定当前可寻址自有dev/test/runtime的日期回退tag，并inspect验证；只增自有tag，不重启容器。不复用已存在的日期tag覆盖旧版本。
- [ ] sync所有代码与测试，在32 Linux shell构建唯一日期候选tag；不覆盖现行xiangrugu:dev/test/runtime，不执行compose up。

```sh
cd /opt/mydocker/xiangrugu/deploy
task_stamp=$(date -u +%Y%m%dT%H%M%SZ)
build_date=$(date -u +%Y-%m-%dT%H:%M:%SZ)
for target in dev test runtime; do
  docker build --target "$target" --tag "xiangrugu:${target}-value-v1-candidate-${task_stamp}" \
    --build-arg BUILD_DATE="$build_date" --build-arg SOURCE_STATUS=dirty \
    --build-arg VCS_REF=1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05 --build-arg VERSION=0.1.0 . || exit 1
done
```

开始执行时须复核HEAD确为该提交；如不同停止更新计划，不沿用旧revision标签。该shell命令须记录三个候选实际digest，运行按digest而非猜tag。

- [ ] 用候选test digest在无网/只读/tmpfs/1CPU/768MiB/64pids的一次性容器执行 `python -m pytest datamgmt/tests/unit datamgmt/tests/container -q -p no:cacheprovider`，无任何源码或数据卷。必须比当前292项新增对应测试，不能用旧镜像的292通过证明新实现。
- [ ] 用候选runtime digest同限制运行纯合成golden及pip check；检查非root、/app代码、OCI标签、无敏感文件/源码挂载和无运行中pip安装。dev候选只做一次性启动/帮助核验，不替换xiangrugu-dev。
- [ ] 验证器代码/测试映射复核规格§1–8，保留失败/通过日志、镜像ID/digest、HEAD/source_status=dirty、fixture与产物SHA-256。回传Windows新文件并核验摘要，再sync；不把合成结果称源/库验收。
- [ ] docs更新仅展开一次新功能现状，其余指针；R05最新行≤300字，R06索引/锚点/授权/状态一致，git diff --check通过。明确未读源/未接库/未冻结/未提交/未换长期容器，Task6及完整Task9未完成。
- [ ] 按适用代码评审技能复核后报告用户；长期容器镜像更新、真实源规范期望生成、DB适配器/测试库、发布和pg32b旧数据处置另问授权，不自行执行。

## 执行方式与批准门

2026-10-08用户“同意”后已按本会话顺序实施Task1–4；完成证据及评审修复统一见[执行账](2026-10-08-text-value-progress.md)。下方批准门描述为实施前历史，不追加真实源/库、长期容器或Git授权。

建议本会话顺序实施Task1→2→3→4，接口依赖紧密且仅两个纯模块，避免并行编辑冲突。此建议尚不是用户对计划及代码执行的批准；若用户要求逐任务Agent再改为对应技能流程。

用户须确认本计划，包括提前进行Task9纯合成切片来补Task6值合同准备的有限顺序调整，以及源码/测试修改、sync、32合成测试、三个自有候选镜像构建及旧自有镜像回退tag的实施范围。不因此允许真实源/快照访问、数据库连接、新依赖、既有服务重启、Git提交推送或导入。

作者自审：规格§1–3对应范围/独立接口/旧路径禁用，§4对应Task1，§5对应Task2，§6对应Task3，§7贯穿Task1–3预算，§8对应全部RED/GREEN及Task4。未覆盖项均明确在范围外，不勾选主Task9完成。
