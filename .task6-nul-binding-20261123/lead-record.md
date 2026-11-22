# Task 6 NUL 证据绑定补正 · lead 记录（15 分钟盒）

- 起表 18:59:02 UTC，硬停 19:14:02 UTC。基线 804000b86d1aa2929191618b4d356e2e22478845（M=2 完好）。
- a02 起始即失败（零产物）→lead 接管补正（披露）。
- 补正三核（checksum_reader.py run_fixed_nul_exception，_whitelisted_rule 后插入）：①manifest.sha256==contract.inventory_sha256（原缺：preview 仅绑 candidates 自洽 sha）②selector.location==("SHA256SUMS-b2",(),())（原仅查 [0]）③expected (kind,size,sha256)==("file",22071,固定 sha)（原缺）。任一失配 ValueError→nul_exception_closed False→evaluate 保持 exception_not_implemented。
- 测试 +3（12→15）：N9 inventory 绑定失配（model_copy inventory_sha256="0"*64）/N10 归档链非空（doc 改 selector model_validate）/N11 expected size 22072+sha "0"*64 双失配。
- 容器执行（/tmp/task6b 隔离，tar 含 config schema+inventory）：**15 passed T6_EXIT=0 stderr 0B；118 passed REG_EXIT=0 stderr 0B**。
- 机器证据（machine-evidence.json）：正例 172/21945/126/172 matched/inventory_sha256 fb5e6b334b898d62…/issues [incomplete_inventory, unmatched_member]/ready false/complete false；三反例 rejected=True+exception_not_implemented 保持+ready false（错误消息逐字在账）。
- rollup 不动（19 件 sha 保持 804000b 态）；改动恰 checksum_reader.py+test_checksum_reader.py+证据目录+TODO。
- a03 独立核进行中（硬停 19:10）：Codex 两反例重现+旧版缺口证+复跑+范围。
