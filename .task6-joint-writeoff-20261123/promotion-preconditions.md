# 转正前置清单（两条例外运行门 → 正式核销 → 冻结落盘）

基线 e7a132cbe6e7fdc0ddd0e4e48131f761c420c3ab。本轮终点为方案；以下各项须另行授权，顺序依赖：

1. **32 受控运行目录接收**：deploy 接收经核对的 Git 版本 e7a132c（含 reader/枚举/schema/接线/测试）——当前 deploy 未接收本提交；不直接形成未回传 Git 的独立修改（R-10）。
2. **两条例外入正式合同审批**：checksum_nul（SHA256SUMS-b2 固定身份）+checksum_path_binding（CHGIS line4）写入正式 ReleaseContract.exceptions，frozen+review（approved_by/approved_at/approval_ref）——茶香/Codex 批准事件。
3. **正式合同下证据再生**：现有两份证据绑 fixture 合同；正式核销须在正式合同 sha 下重跑 reader，产新证据绑 {正式 contract_sha256, 原清单 fb5e6b33…, 新证据 sha}。
4. **核销逻辑实施授权**：writeoff 评估器扩展（正常入口 evaluate+exception_run_inputs）产 writeoff_result；原清单 complete=false 与三 issue 逐字保留；多出/失配/未审批仍阻断（writeoff-plan.json）。
5. **首批七对象批准面**（第一优先）：规范值 expected_count/expected_sha256 生成（全 MISSING）+生产 PostgreSQL loader 实现（GAP）+table_names/target_mapping 批准（名称 CANDIDATE）——见 first-batch-seven-gaps.json。
6. **全量合同投影与冻结**：8004 成员规则面（消 unmatched_member 伪影）+全部 targets expected_count/expected_sha256 非空（frozen 模型门）→冻结。
7. **G0–G7 运行门与 ready_for_import**：合同门之外运行门全过方可 ready；真实清单 incomplete_inventory 恒门在核销视图单独记账。
8. **正式落盘与数据库写入授权**：32 落盘+xiangrugu 库写入另行授权；pg32 生产/pg32b cbdb 系不触。
