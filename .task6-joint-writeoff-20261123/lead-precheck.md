# 两条例外联验与清点核销方案 · lead 预核（2026-11-23，30 分钟盒）

- 起表 14:54:20 UTC，硬停 15:24:20 UTC。基线 e7a132cbe6e7fdc0ddd0e4e48131f761c420c3ab（M=2 完好）。
- 范围仅隔离只读联验+方案交付；核销逻辑实施/候选转正/冻结/落盘另行授权。零源码改动。

## 原 inventory 三 issue 逐字（lead 14:54 UTC 直核，sha fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db）
①{archive_chain[], archive_ordinals[], blocking true, code checksum_line, detail "line=173", relative_path SHA256SUMS-b2}
②{同链序, blocking true, code checksum_nul, detail "count=126", relative_path SHA256SUMS-b2}
③{同链序, blocking true, code checksum_missing, detail "line=4", relative_path harvard/chgis/SHA256SUMS.txt}

## 对应设计（须字节级证）
- NUL 证据闭①+②：line=173 幻影行==NUL 尾段本身——prefix 恰 172 换行（末换行 @21944）、raw[21945:22071]==126×NUL、无尾换行→严格解析器第 173「行」恰为 NUL 段。条件：172 逐条 matched+固定身份+审批。
- CHGIS 证据闭③：line4 声明 harvard/chgis/China_Periods_ReignDates.zip 缺席（entries 0）→显式绑定 resolved chgis-v6/…（155774/7452ae6c 外层唯一）；strict assertion matched=False 保留原声明。
- incomplete_inventory：三 blocking issue 派生恒门，原清单 complete=false 保留不改。
- unmatched_member：测试合同仅两规则（8004 成员面外）伪影，非原 issue；正式全量合同下消失。

## 首批七缺口（first-batch-preload-table.json gaps_itemized 逐字）
「运行门 loader 未实现（GAP 字样照录 load_method）」「table_names/target_mapping 未批」「expected_count/expected_sha256 未生成（frozen 门 L178 要求非空）」；5 文本+2 空间逐对象 canonical_value_gap 全 MISSING。

## 本盒交付
joint-comparison.json（机器对照表+容器联验实跑+留门反例）/writeoff-plan.json（最小核销方案）/first-batch-seven-gaps.json/promotion-preconditions.md；TODO；零源码/rollup 不动。