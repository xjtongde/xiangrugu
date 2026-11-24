# 合同摘要兼容与首批冻结校验补正 · lead 记录（30 分钟盒）

- 起表 15:33:59 UTC（2026-11-24），硬停 16:03:59。基线 5595c64a24a2e1721647cfc3e3e942df9092e2c9。lead 收口，a03 独立复核。构建测试只在 32 隔离环境。不录真实审批/不冻结正式合同/不接收 deploy/不改服务/不写库；工作树源件保全；未重跑试装。

## 缺陷确认与补正
- **缺陷**：前盒扩展给 ObjectTarget 增四可选字段（None 默认），canonical_bytes 裸 model_dump 含 null 键→**旧合同 canonical bytes/sha 相对 450d68d 漂移**。
- **补正一（摘要兼容）**：canonical_bytes 对 target 四扩展键（columns/derived_rownum/duplicate_reconciliation/geometry）**值为 None 时剔除**；实际值保留参与摘要。
- **补正二（冻结强制）**：release_consistency frozen 门增 `rule_id∈FIRST_BATCH_RULES → _check_first_batch_rule(rule)`（列映射/派生行号/重复口径必填+非空+count/sha+重复不超 count+空间几何+SRID4326+文本禁几何）；**非首批合同维持原 review+count/sha 规则**。_check_first_batch_rule 自 validate_first_batch_seven 提取共享（候选 draft 门语义不变：frozen 仍拒「must be unfrozen」）。

## 证据
1. **旧新摘要对照**（digest-comparison.json+probe-baseline/extended.json）：同容器双 PYTHONPATH（/tmp/dcb 基线 450d68d contracts.py vs /tmp/dc 新树）对同一旧合同文档（legacy draft+frozen 两面，合成 review 仅隔离测试）：
   - legacy draft：899B，sha **156b6354d509bfd6…** 基线==新版逐字节 ✓
   - legacy frozen：1020B，sha **db5e163df3d970c0…** 基线==新版逐字节 ✓
   - 基线解析扩展候选→REJECTED ValidationError（extra forbid，证明扩展为新面）✓
   - **扩展值参与摘要**：候选 sha bb715799…；改一 target_column→62022257…；改 LAT 宽度 19→20（pg_type 同步 numeric(20,5)）→5edcf43e…，三者互异 ✓
2. **冻结正反例**（test_contract_freeze_compat.py 12 例，正式 model_validate 入口）：旧合同 draft/frozen 摘要锚定+canonical 无 null 扩展键/扩展值参与/候选+合成 review frozen 正例通过（validate_first_batch_seven 对 frozen 拒语义不变）/7 反例全拒（缺 columns/缺 rownum/缺 dup/空间缺几何/SRID4327/文本带几何/宽度矛盾）/**冻结候选 vs 待批表映射摘要逐项一致**（名称/count/attr sha/文本逐列 column_key→target/type/nullable/重复 63/74/空间 geom sha+SRID+DBF 身份 0b4b86cb/eb9dfed2@16937B+numeric 宽标自洽）。
3. **回归**：七套 **R7_EXIT=0 stderr 0B 172 passed**（141 既有+19 扩展+12 冻结兼容）r7.out 在证据目录。schema 未变（无模型字段增删，test_published_schema 通过含于 172）。
4. 环境披露：跨日容器 /tmp 基线树失效→重建；探针候选路径首版错（HERE 应为父目录）修正；容器树缺 pending-seven 路径件致 1 failed→补送即 172 全过（环境性非交付缺陷）。

## 边界
真实审批未录（REVIEW 常量显式 isolated-test-only-not-a-real-approval）；正式合同未冻结（候选文件仍 draft）；deploy 未接收；服务未改；库未写；M=2 未触；rollup/原 inventory/五块零改写。
