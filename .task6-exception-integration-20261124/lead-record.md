# 两条例外接入与装载前核验 · lead 记录（30 分钟盒）

- 起表 17:42:32 UTC，硬停 18:12:32。基线 0e7fed12d335a080c2a62e4c8553d937c7d0a049。批准范围仅限两条已审固定例外。lead 收口，a03 独立复核。只在候选分支+32 隔离环境。

## 实施
1. **审批登记**（approval-record.json）：批准原文逐字/基线锚/两例外固定身份（NUL：SHA256SUMS-b2 raw 900d98c6…/22071B/172 有效行/126NUL@21945；路径绑定：harvard/chgis/SHA256SUMS.txt raw 694c101f…/551B 第 4 行 China_Periods_ReignDates.zip→chgis-v6/… 目标 7452ae6c…/155774B）/范围外四件（deploy 不更新/镜像服务不改/库不写/核销≠写库批准）。
2. **更新冻结候选**（build_updated_candidate.py）：前 frozen（2dd40642…）+**两条 ContractException**（checksum_nul/checksum_path_binding，raw_sha256 绑白名单常量）+**两条账本锚规则**（r-sha256sums-b2/r-chgis-sha256sums，NON_TABULAR/checksum_ledger/none，selector+expected 恰白名单身份）+**本次批准新 review**（茶香/2026-11-24T17:42:32Z/chaxiang-approval-20261124-two-exceptions-integration@0e7fed1…）。**七项业务规则 deep-equal True**（update-delta-report：差面恰 exceptions/review/rules 三键，rules 差=+2 账本规则）。**新 canonical sha ba8118fb5188478c7a891c37a0ae9d84687910c472946fe44709f3533843bd62**（容器正式入口复算）。
3. **正式核销**（writeoff_driver.py，32 隔离容器 /tmp/wo）：32 只读快照读两账本 raw（sha==白名单 900d98c6/694c101f）；原清单重建 sha==fb5e6b33 双锁；**run_writeoff 正式入口 WO_EXIT=0**：**恰核销三条**（checksum_line line=173/checksum_nul count=126/checksum_missing line=4）exactly3 True；**两证据摘要可重算**（nul 5dd1739c326d4cc5…/chgis 623723ff2c7c2fbd…，本地独立重算 True×2）；**原清单字节未触+complete=false 保持**；derived [unmatched_member] **ready False 其他阻断如实保留**。
4. **装载入口核验**（load-entry-check.json）：正式批入口 batch_execution.execute_batch=approved-readonly-batch-v1，scope_authority 门 postgresql_authorized=False/ready_for_import=False、invalid_staging 门 postgresql_connected=False——**PG 写入路径结构性关闭**；**首个实际阻断=PG 生产装载器未实现（loader GAP，TODO 未决项①）**，叠加 unmatched_member 派生阻断+装载授权事件未到；覆盖 8004 总/9 匹配（7 业务+2 账本）/**7995 未覆盖**（uncovered-members.txt 全列）；关闭条件四条（装载授权事件/生产装载器实现验收/全成员处置覆盖或批准范围合同/例外已入候选本盒完成）。**现有装载门保持；核销结果≠写库批准**。
5. **回归七套 R9_EXIT=0 stderr 0B 172 passed**（首轮 2 failed 系 /tmp/wo 树缺 config 目录环境性，补送即全过，披露）。src/inventory/五块 diff 空；模型零改动。
6. 环境披露：docker cp 报 /tmp/wo 不存在（容器 /tmp 面）→改 exec 管道传 raw；DispositionRecord 字段 member.relative_path 首跑误→修正（驱动面，非模型）。

## 边界
deploy 未更新（现件仍 f546783 接收态）/镜像服务未改/库未写；M=2 未触；原清单字节保持。

## 首个剩余缺口
装载授权链：①装载授权事件（另批）②PG 生产装载器实现（loader GAP）③7995 未覆盖成员处置。
