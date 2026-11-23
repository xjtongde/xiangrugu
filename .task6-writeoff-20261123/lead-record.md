# 三条固定清点 issue 核销实施 · lead 记录（30 分钟盒）

- 起表 15:32:27 UTC。基线 912a883（M=2 完好）。a02 起始即失败→lead 接管（披露）。
- 实施链（15:33–15:38 UTC）：
  1. writeoff.py 新件（~90 行）：FIXED_ISSUES 三条完整身份；run_writeoff 审批门→sorted 身份+出现次数核→同合同同清单重跑 run_fixed_nul_exception+run_fixed_path_binding_exception→DispositionLedger.evaluate 正常路径→exception_not_implemented 仍在拒→派生结果（contract/inventory/两新证据 canonical sha 绑定、closed_issues 三条、original_inventory_complete=False、incomplete_inventory_written_off=True、derived_issue_codes=ledger−{incomplete_inventory}、ready_for_import=派生门 frozen+无余 issue+coverage 除 errors 全合、original_ledger_ready_for_import）。原 manifest 绝不改。
  2. test_writeoff.py 10 用例（正例只核销三条+原样保留断言 sha/issues/complete；合成全覆 3 成员+3 规则合同证派生门可闭 derived []→ready True；反例缺证据×2/跨合同证据 sha 随合同变+绑定失配/摘要变化/增添/重复/缺失 issue/未审批/unmatched 阻断）。
  3. rollup 两更正：rgp C7/C8 input 全 64 位；fbd 两 Ca1884route approved_scope SRID 已批注（approved 2 除外语义+值随 .prj 装载重算）；VCS_REF→912a883；SUMMARY 本盒节。38 三跑+收敛 0/0 stderr 0/0。
  4. 容器 /tmp/wo：**10 passed WO_EXIT=0 stderr 0B；五套全回归 140 passed REG_EXIT=0 stderr 0B**。
  5. 机器证据：正例 closed 3/derived [unmatched_member]/ready False/written_off True/新证据 sha nul b74c33847935…/chgis e24ed0f17ebd…/original_preserved 全 True；七反例全 rejected（missing×2/cross_contract/added/duplicated/missing_issue/unapproved）。
  6. rsync→32 三跑 0/0；**38/32 全 19 件全等**。关键 sha：rgp 5d39580691aecfe4/fbd 97e5d19627e27784/manifest 9975956c04e6fa9c/SUMMARY c5b6d66eae76604c/生成器 d8bfde9da93b81e1/all-members fdff9c82947dff7e。
- a03 R37 一期（原样基线核+门位预期 W0/X1–X6+两更正预核取证）全 PASS；二期交叉核进行中（硬停 15:57）。
- 边界：原 inventory 字节未动；fixture review 仅测试面零真实审批录入；五块+既有源码（contracts/disposition/checksum_reader）零改写；M=2 未触；源件只读。
