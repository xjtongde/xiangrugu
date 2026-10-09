# 五件文本规范值合同提案执行账

## 范围与短计划

2026-10-09用户“同意”批准：新增五件文本规范值合同提案和测试，Windows修改后同步到32验证；保留原始证据及批准投影，不读真实源、不连接数据库、不导入，不批准表名、不冻结，整体BLOCKED不变。

依据：IMPLEMENTATION-PLAN Task6、DESIGN §4/6/11、release/text-review.md最新五件源侧规范值期望，以及上轮获批短设计。

1. 写元数据测试，同步32，观察缺少新草案的RED。
2. 新增非执行JSON草案，绑定已有源证据、批准投影、对象/源摘要、列映射引用、schema摘要及完整流期望。
3. 32既有dev中运行定向及累计单元测试，复核旧文件摘要和禁止放行标记，再作独立审阅。

Ruling：沿用用户指定Windows权威工作区及受控同步，不新建worktree、不切换main、不提交；原有脏树保留。若错误，隔离不足可能影响相邻未提交资产，故本批只新增两个文件并小范围更新文档。

Ruling：只增加数据草案和元数据消费测试，不新增产品生成器/CLI或依赖。列映射通过固定文件SHA-256及JSON Pointer绑定已有88个值列，避免第二份映射；不是直接可加载ReleaseContract。若错误，后续集成仍需转换，不能把本草案当IMPORT入口。

预检查：HEAD 1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05，标题未变；32 dev为sha256:89f1a0978cb817871d50d6468f3dec19e3ea1e67d5bc73457a62fd10b5b8732d，运行中、uid10001。2026-10-09实测磁盘可用192886894592字节；已有单元476 passed in 5.09s。

## TDD与诊断

32开发容器定向命令：python -m pytest -q datamgmt/tests/unit/test_text_value_contract_proposal.py --tb=short。
先同步测试，9项均因缺少非执行草案失败；新增草案后8通过/1失败。
失败是来源时间戳被Windows PowerShell ConvertFrom-Json自动转成System.DateTime，再序列化为+08:00；原证据实际为2026-10-08T13:00:25.704678+00:00。
按诊断技能核对原始文本及转换后的类型，只恢复新草案的原始字符串；不修改原证据、不放宽精确来源测试。

修正后定向9 passed in 0.34s；累计单元485 passed in 5.91s。

完整命令docker exec -w /workspace/datamgmt xiangrugu-dev python -m pytest -q也已执行，488 passed / 5 failed in 5.41s。失败全部是container测试读取/app/docker-compose.yml缺失：test_compose_declares_a_real_isolated_dev_process、test_dev_mounts_only_controlled_source_and_non_source_data、test_sync_script_excludes_repository_and_sensitive_runtime_state、test_compose_keeps_source_mount_confined_to_development、test_project_snapshot_volume_is_readonly_without_dynamic_source_propagation。Dockerfile只在test target复制Compose/同步脚本到/app；dev target没有这些资产，完整镜像契约须在候选test镜像运行。本批没有构建授权，不修改镜像/测试以掩盖环境差异，不声称完整镜像套件通过。

## 独立审阅与一次修复

requesting-code-review技能派只读text_contract_review审阅本批，未审整个旧脏树。Critical无，Important一项：test target不复制仓库合同/evidence，新增测试若按/app定位会新增9失败。固定8输入SHA、5对象/源/schema/期望、88列指针及partial门均确认正确；无Minor。

修复先在既有32 dev中合成/app模块上下文，使用pytest真实收集同一测试文件，9项全部因缺仓库草案失败（0.20s）；只新增针对固定/app根的明确skipif，不以缺文件跳过。修复后同一探针9 skipped in 0.17s；/workspace真实定向9 passed in 0.29s（无skip）、累计单元485 passed in 5.77s（无skip）。这是合成镜像上下文，不冒充新test镜像构建/完整契约通过。没有产品代码、Dockerfile、依赖或服务变更，不派二次审阅。

Declined to judge裁定：真实源/快照/数据库与G0/G4仍不在本批授权；候选镜像构建和完整镜像契约未运行，本批仅合成上下文修复新增测试兼容问题；旧脏树、完整release、表名、生产读取器及导入就绪均不在本批成果中。若把这些限制理解为放行，会误用不完整合同，故草案及文档明确全部保持阻断。

## 产物和验证证据

草案SHA-256：c86be708b7469c095ae7bd35f4751dc17d9045f353da799cda651d6af38a2189。
机器报告：[verification.json](../evidence/2026-10-09-text-value-contract/verification.json)，绑定草案/测试和8原输入摘要、定向/累计/合成上下文JUnit计数与原报告摘要。原JUnit在32宿主data/var/text-value-contract-20261009；报告容器时间为UTC（本地用户日期2026-10-09），原始字符串不转换。源证据继续绑定其历史生成镜像，不用当前dev替换它。

dev、pg32、pg32b的容器ID/启动时间与上批记录一致；仅查看容器元数据，不连接数据库。pip check无依赖冲突，首次未禁缓存发出只读home缓存警告，不修改权限。未提交推送，HEAD未变。元数据引用和输入摘要通过定向测试，R-06入口/索引/Task6/日志已对齐；正式sources/metadata/decoding/assertions、批准投影及读取决定字节未变，current不存在。

状态：本批草案整理及测试完成，值合同本身仍待用户审阅批准；Task6/阶段0未完成，BLOCKED=7,914不变。导入前通知并共同决定pg32b旧数据处置的用户门保留。

## 随后五件规范值批准记录

用户对交付提问“五件规范值口径与摘要期望，不包含表名、冻结或导入”答复“同意”。本轮仅记录该批准，新增决定text-value-contract-decisions.draft.json及非执行text-value-contract-approved.draft.json；绑定原提案c86be708b7469c095ae7bd35f4751dc17d9045f353da799cda651d6af38a2189。旧提案与源证据不覆盖，scope不扩大到表名/完整目标/全版本合同/冻结/源或数据库访问/导入/旧数据处置。

批准投影与原提案相比，仅status改为DRAFT_VALUE_APPROVED、value_contract_approved=true，新增批准日期及决定/原提案摘要引用；全部对象、值期望、映射引用、输入摘要和历史source_evidence_provenance保持一致。固定/app镜像上下文仍明确不适用这些仓库审计，不按缺文件跳过。

使用TDD/verification-before-completion技能：新增3项批准范围消费测试，先3 failed/9 passed（缺决定/投影）；补入后12 passed in 0.31s、累计单元488 passed in 5.41s且均无skip。合成/app探针12 skipped in 0.18s；完整dev命令pytest -q --tb=no为491 passed/5 failed in 5.47s，仍是上节具名五项/app/docker-compose.yml环境失败，不声明新镜像或完整镜像契约通过。本轮没有产品功能或依赖/镜像变更；只自检批准数据与既有提案精确相等，不重复派审阅Agent。

决定SHA-256 e4c666c0f1d17b7d4c60f986379fa8084120c9a98db9583da183ef790048df93；批准投影SHA-256 ecb0282805d19930266ec8f82605ed94477b24fd73e1d881ec42b77cb7810f47。机器报告[approval-verification.json](../evidence/2026-10-09-text-value-contract/approval-verification.json)绑定新旧文件摘要及四组JUnit计数/具名失败；原XML另存32的data/var/text-value-contract-20261009-approval，不覆盖前批JUnit。12项测试校验所有旧输入、原提案不变、批准投影仅改变批准元数据、非ReleaseContract入口及禁止放行标记。

dev/pg32/pg32b容器ID和启动时间与上批相同，仅查看运行元数据；未连接数据库、未重新读取源/快照、未构建镜像/重启服务、未提交推送。索引/入口/text-review/Task6/日志同批对齐，Git diff --check通过（既有LF/CRLF提示保留，不进行格式批改）。当前是“五件规范值已批准”，不是完整release或数据库验收：BLOCKED=7,914、current不存在、ready_for_import=false。下一步仍需补齐其他对象合同及全版本命名，真正导入前须通知用户并共同决定pg32b旧数据如何处理。
