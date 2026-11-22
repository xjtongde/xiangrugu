# Task 6 固定摘要 NUL 运行门实施 · lead 预核（2026-11-22/23，30 分钟盒）

- 起表 18:34:22 UTC，硬停 19:04:22 UTC。基线 e3dd1399f54cdc9254b5d748cd0e783eb149aa6b（M=2 完好、暂存空）。
- **茶香明确授权隔离实现+测试**；真实合同冻结/正式落盘/服务变更/数据库写入另行授权。范围仅 SHA256SUMS-b2 checksum_nul 例外。

## 现有核验逻辑（lead 18:34 UTC 全文读，150 行）
datamgmt/src/xiangrugu_datamgmt/checksum_candidates.py：
- ChecksumCandidate{rule_id, ledger, raw_sha256, raw_size, reason}；TrailingNulCandidate{kind trailing_nul, valid_lines, trailing_nul_bytes}；PathBindingCandidate{kind exact_path_binding, line, raw_name, declared_target, resolved_target, expected_sha256, expected_size}。
- ChecksumCandidates{version 1, status draft, release_id, source_version, inventory_sha256, rules≥1}；rule_id/ledger 唯一。
- preview_checksum_candidates(manifest, candidates, raw_ledgers)：inventory sha 绑定；raw bytes==rule.raw_size+sha256+inventory entry (size,sha256) 断言；**TrailingNul 逐条核验**：tail 全 NUL+prefix 无 NUL+prefix 末尾 \n+prefix.count(\n)==valid_lines；_record 正则 ([0-9a-fA-F]{64}) ([ *])(.*)；name 唯一；assertion 数==records 数；逐行 (line, raw_name, target, expected_sha256, matched=True) 全等。
- 返回 DRAFT_PREVIEW_ONLY/runtime_applied=False/ready_for_import=False/strict_inventory_complete=manifest.complete/strict_issue_count。
- **docstring L5-6：deliberately no runtime/activation API；frozen release integration separate gate；preview success never changes strict inventory evidence**——本盒新增窄域运行面（Task 6）。

## 接线点（lead 读 disposition.py L50-89）
- evaluate(cls, manifest, contract)：L63 inventory_mismatch；L65-66 **complete=false→incomplete_inventory**；L67-68 empty_inventory；**L69-71 `if contract.exceptions: issues.append(LedgerIssue("exception_not_implemented"))`**（注释：Exceptions are declarations only until the narrowly scoped Task 6 reader exists）。
- L81-85 primary_bytes 仅 IMPORT；L86-89 target_collision。
- 最小改设计：evaluate 增可选参数（默认 None 向后兼容）；白名单命中+审批（frozen+review）+证据核验通过→该条不记 issue；否则保持；CHGIS 仍 exception_not_implemented。

## 固定身份（派工锁定）
SHA256SUMS-b2 / 900d98c69cf9b72f20313aa562b8da5e18e9c3e3def423fa6f618b4b1bafb3cb / 22071B / 172 有效行（171 harvard-full DVN+1 chgis-v6）/ 偏移 21945 起 126 尾部 NUL（[21945,22070] 单连续段）。实物 32 快照只读。

## 恒门保留（a03 必核）
inventory.complete=false 原样保留→incomplete_inventory 恒触发→**ready_for_import=false 不因 NUL 门关闭而变**；其余阻断（stale_assertion/unmatched_member/invalid_mirror/target_collision/empty_inventory）零改动。

## 草案歧义清除（派工）
checksum-exceptions-candidates.json 两候选顶层 raw_sha256/raw_sha256_full_note 歧义（NUL 顶层=载体 sha；CHGIS 顶层=目标 sha 7452ae6c≠载体 sha 694c101f）→清除，保留 source_ledger_identity/target_identity/nul_lock 分字段；CHGIS 注单列待实施。

## 本盒交付控制
- 新件 checksum_reader.py+test_checksum_reader.py+fixture（provenance）；disposition.py 最小接线；rollup ced 段歧义清除+VCS_REF e3dd139+SUMMARY；测试显退出码；机器证据绑定 contract_sha256+inventory_sha256+172 逐条。
- 五块零改写；源件只读；M=2 不触；不冻结/不落盘/不写库。