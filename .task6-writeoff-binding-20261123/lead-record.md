# 核销器原清单绑定补正 · lead 记录（15 分钟盒）

- 起表 15:52:46 UTC。基线 0da4f0f（M=2 完好）。a02 起始即失败→lead 接管（披露）。
- 实施链（15:53–15:55 UTC）：
  1. writeoff.py：ORIGINAL_INVENTORY_SHA256=fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db；run_writeoff 审批门后双核（manifest.sha256/contract.inventory_sha256 各!=固定值→ValueError）；三条身份+次数核保留；结果增 run_evidence{nul,chgis} 全文字段。
  2. test_writeoff.py 10→11：test_positive_derived_gate_closes_when_all_else_conforms 改为 test_negative_substitute_inventory_same_three_issues（拒绝用例）；新增 test_negative_contract_binds_substitute_digest；正例增证据全文重算==两条摘要+双 contract_sha 绑定断言。
  3. 容器 /tmp/wb：11 passed WO_EXIT=0 stderr 0B；五套回归 141 passed REG_EXIT=0 stderr 0B。
  4. 机器证据：正例 closed3/derived[unmatched_member]/ready False/ev sha nul b74c33847935cdcd…/chgis e24ed0f17ebd91f5…（同 fixture 合同确定性同值）/evidence_recomputable True×2/original_preserved 全 True；替代清单 sha 3b8f5f3e2f90e632…；两反例 rejected（错误消息逐字在账）。取回时混入 grep 计数首行，lead 剥离修正（纯整数行断言后 JSON 解析）。
- a03 独立核进行中（硬停 16:04）：替代清单反例复现+旧版缺口对照+正例/重算/原样/回归/范围。
- 边界：rollup 19 件不动；原 inventory 字节未动；五块+其余源码零改写；M=2 未触；源件只读。
