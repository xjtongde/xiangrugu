# Task 6 NUL 证据绑定补正 · lead 预核（2026-11-22/23，15 分钟盒）

- 起表 18:59:02 UTC，硬停 19:14:02 UTC。基线 804000b86d1aa2929191618b4d356e2e22478845（M=2 完好、暂存空）。
- 范围仅 NUL reader 证据绑定+回归；CHGIS 继续单列。

## 现版缺口（lead 18:59 UTC 源码核）
checksum_reader.run_fixed_nul_exception 现检查：审批 frozen+review / 恰一白名单声明 / _whitelisted_rule（code+raw_sha256+location[0]==ledger）。**缺三核**：
1. manifest.sha256 == contract.inventory_sha256（preview 仅绑 candidates.inventory_sha256=manifest.sha256 自洽，未绑合同声明）。
2. selector.location 精确外层三元组 ("SHA256SUMS-b2", (), ())（现仅 [0]，归档链/序号未查）。
3. rule.expected (kind,size,sha256)==("file",22071,900d98c6…)（未查）。
补正位置：L52-53 _whitelisted_rule 检查后、candidate 构造前；任一失配 ValueError→nul_exception_closed False→evaluate 保持 exception_not_implemented。

## 正例兼容
fixture 合同 selector 默认空链空序、expected file/22071/固定 sha、inventory_sha256=manifest.sha256——三核全合，正例不变。

## 本盒交付控制
- checksum_reader.py 三核插入+test_checksum_reader.py +3 反例（12→15）；四套回归 118；机器证据正例+两反例拒绝记录。
- rollup 不动（VCS_REF 保持 e3dd139）；五块+模型核心源码零改写；M=2 不触；源件只读。
- a02 硬停 19:05（失败 lead 即接管）；a03 硬停 19:10（独立重现 Codex 两反例+现行为缺口证）。