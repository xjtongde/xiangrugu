# 第 5/6 块证据标注收尾 · lead 记录（2026-11-21，15 分钟盒）

- 起表 16:43:30 UTC，硬停 16:58:30 UTC。基线 d59010b8127d086f5f55c84579092b7af3a37d6f（M=2 完好、暂存空）。
- 范围：只补证据字段/生成文案/进度记录，复用首盒读取证据，probe_evidence.json 不动（63e7102d… 原值）。
- a02 交付（硬停 16:51 内）：25 处 text_provenance 四键分级（verbatim/verbatim_label 原文逐字 + normalized_text/normalized_text_label 规整文本），normalized_text 由六浮点 repr 拼接与顶层值全等 0 失配；wkt_provenance×43 统一「GDAL GetProjectionRef 返回值」；per_band note 按 executed_this_round 分支 26/17；VCS_REF=d59010b；漂移守卫断言入码；32 双跑 0/0 stderr 0/0 字节一致。
- lead 快核（16:45:17 UTC）：五件 sha 匹配声明；25/25 四键齐备；note 分支 {26 已执行, 17 仅登记} 无错位；wkt_provenance 全覆盖；baseline_git=d59010b 三件一致；class_counts 614/1446/299/116/43/3/1 不变；缺口 7 组。members/gaps sha 变化系 baseline_git 字段更新（VCS_REF 926ed98→d59010b），语义不变。
- 终态 sha：members c36668c158e70ca2… / raster-mapping 79b0d917f9ccf19d… / evidence-gaps a916e1d9cfeef05c… / SUMMARY 456adb0e9c8d96a3… / 生成器 40d34664b56c6fa9…。
- TODO：块5收尾记录+表行/页首状态+讨论账同步。
- 边界：快照未触（本轮无新读取，复用证据）；未装依赖/未建镜像/未写库；entry/rehearsal M=2 未触；块3/块5补正面历史交付不改写。
