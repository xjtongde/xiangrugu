# 首批两件空间对象源侧值证据 · lead 记录（30 分钟盒）

- 起表 16:28:27 UTC，硬停 16:58:27。基线 19a7718（M=2 完好）。茶香明确授权开工。a02 起始即失败→lead 接管（披露）。
- 实施链：
  1. 32 host 只读解析 1884route.zip（sha 39f505c1c4f71934…/2156327B）：SHP（file code 9994/type 1 Point/1752B=100+59×28）+DBF（16937B=417+59×280，无 0x1A EOF——长度断言修正）+CPG；组件 sha 全 match（shp 109d74b1 两件同/dbf 0b4b86cb/eb9dfed2/cpg ea80b523/3ad3031f）。
  2. 沿用已批：编码 cp1251/utf-8 strict、12 字段映射（spatial-attributes-approved.draft.yaml）、__src_rownum 一基物理行号 [1,59]、2D Point/SRID 4326、原始 X/Y IEEE754 LE 字节保留不交换不变换；C 尾空格保留；N raw bytes 保留为 text，blank numeric NULL 未批→停报门。
  3. 属性期望 XRGVALUE-v1（canonical.py 复用，ValueSchema 12 text NOT NULL+ROW_KEY bigint）：1251 sha 3519649f663f8a6d…（59 行 767 字段 24634B）/utf8 a2ad2d24ff4cae8c…（24214B）；几何期望 XRGGEOM-v1（header XRGGEOM\0\1+SID+srid>iB+dims>B；row 0x52+rownum>Q+X8LE+Y8LE；trailer 0x45+count>Q）：1251 ff7081a0013d721f…/utf8 3c6067845a7938e8…（各 1530B；SID 异故 sha 异）。
  4. **两件各 59 行==已知 ✓/aligned True/deleted 0/blankN 0/重复 attr 0+xy 0**；SV_EXIT=0 stderr 0B；计数≠59 留证停报门在码（exit 2）。
  5. 实际核销调用：容器 /tmp/wb run_writeoff fixture 合同 WO_CALL_EXIT=0 stderr 0B（closed3/derived[unmatched_member]/ready false/ev b74c3384/e24ed0f1）→writeoff-call.json。
  6. 审批包修正：approved_mapping vs pending_value_expectations/source_side_value_expectations 分开；文本 precise_field_mapping_refs（value_columns_ref+approved_object_ref）；value_expectations_ledger 三态；approval-table a35393bd8f69a190/生成器 10bc8f8a 双跑全等；evidence-list 8a3c01ca 不变。
  7. 接收方案：回退恢复接收前完整版本锚 19a7718（整体 R0/全量 checkout 禁局部挑拣）+保留已验收核销保护（fb5e6b33 锁定+四核+11 用例）+实跑核销节+代码基线与审批包提交分列。
  8. 回归：五套 141 passed REG_EXIT=0 stderr 0B（src 零改写，canonical.py 复用）。
- a03 R40 PASS：同一只读快照自写解析器独立复算 attr/geom sha True×2+59/对齐/零重复全合；分账/回退/审批表修正/范围核全 PASS。
- **首个不一致（观测级）处置**：a03 指出 schema_sha256 节点 nullable 语义混用（nullable_proposal false 恰同 nullable=False）；lead 注明修正——attribute_expectation 增 schema_nullability_note：流 schema 按 XRGVALUE-v1 全源列 text NOT NULL（空串保留）nullable=False；yaml nullable_approved=true 为目标表 DDL 可空性批准（另一批准面）非流可空性。重跑 SV_EXIT=0，attr/geom sha 稳定不变，approval-table a35393bd 不变。值流与 sha 不受影响（a03 已证）。
- 边界：源件只读；rollup 19 件不动；src/config/tests 零改写；原 inventory/五块不动；M=2 未触；未触 pg32/pg32b。
- 提交分列：A 代码基线（驱动器+证据+核销调用+记录）；B 审批包（approval-table/生成器/接收方案+TODO）。
