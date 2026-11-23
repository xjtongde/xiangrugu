# 首批七对象审批包 · lead 记录（30 分钟盒）

- 起表 16:14:37 UTC，硬停 16:44:37。基线 8f3d014（M=2 完好）。a02 起始即失败→lead 接管（披露）。
- 范围仅核查已交付证据+编制审批包+受控接收方案；零实现零 rollup 改动。
- 事实核（lead 直读）：text-value-contract-approved.draft.json 5 对象 row_count 2957/40199/1033/29/3389 和==totals 47607；value_contract_approved=true/table_names/target_mapping/frozen false；spatial-crs-approved.draft.yaml srid=4326/dimensions 2/Point/原始 X/Y 保留/59 记录/geometry_expected_hash=null；spatial-attributes 列映射批；六证据件全 TRACKED。
- 交付：approval-table.json（7 逐项 SID64/候选名/映射/依据 sha+字段/缺口/关闭证据/ledgers 三账 false×7×3）；evidence-list.json 18 条 sha 自算 mismatch 0；controlled-reception-plan.md（版本锚 8f3d014/run_writeoff 入口四核+证据再生/验证命令/回退 R0+R1）；build_approval_package.py 确定性双跑字节全等（ITEMS 7 EVIDENCE 18 ROWS 47607）。
- a03 R39 一期（文本复算+追溯链闭合+七名称 7/7）PASS；R39b 二期（CRS 六要素+缺口 null×2+审批表逐项+三账+受控四锚+独立双跑三 sha 稳定+18 sha 全等+范围核）全 PASS。一期 spatial-crs find 空系 a03 搜索面误，lead 更正路径后重核成立。
- 边界：rollup 19 件不动；原 inventory/五块/源码零改写；M=2 未触；源件只读；未触 pg32/pg32b。
- 批准后顺序（a03 核）：table_names/target_mapping 批复→正式合同冻结→证据再生→run_writeoff 核销→装载授权。
