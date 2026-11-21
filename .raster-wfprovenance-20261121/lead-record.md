# 世界文件文本出处定点更正 · lead 记录（2026-11-21，10 分钟盒）

- 起表 17:02:33 UTC，硬停 17:12:33 UTC。基线 c2ef3ca64ea6f4f83a02484b634b13486ce3e8c3（M=2 完好、暂存空）。
- 范围：只改世界文件文本出处标注及对应文案，复用已有读取证据，不重新探测源件。
- 缺陷确证：lead 38 实测交付 1926_01.jgw 文本 CRLF=0；lead 32 只读实测原件（1926_China_Atlas.zip![39]）120 B CRLF=6 sha f070b7935f68389f…==inventory——probe 转录已规整换行，「verbatim/源成员字节转录」声明不实（锚点预核 lead-anchor-precheck.md）。
- a02 交付（硬停 17:08 内）：probe_evidence 25 处键 verbatim→probe_text 值零动（基线对照件 wf_verbatim_baseline_d59010b.json 守卫 25/25 入码）；产物 text_provenance 五键（probe_text/probe_text_label 探测文本换行及末尾空白已规整/normalized_text/normalized_text_label 六浮点重序列化/original_locator source_member+SHA-256 定位）；parameter_semantics.note「逐字登记」→「按探测文本登记」；SUMMARY/TODO 措辞同步；VCS_REF=c2ef3ca；32 双跑 0/0 stderr 0/0 字节一致。
- lead 快核（17:06:28 UTC）：六件 sha 匹配；25/25 五键+键级 verbatim 残留 0；标签文案准确；SUMMARY 残留 0。
- lead 裁定：TODO 历史变更日志行（L226）与新记录引述语境（L228）保留原文不改写（R-10 不改史），更正记录就地指认。
- 终态 sha：members 045a5ea95a8c6f2d… / raster-mapping 21f19ffa7b678af9… / evidence-gaps 6556dc4efd3453ca… / SUMMARY 1e032c853ee90327… / 生成器 fb9a74823fdb1225… / probe_evidence be613e2bc099953a…。
- 边界：未装依赖/未建镜像/未写库；entry/rehearsal M=2 未触；数值/绑定分级/26-17/归属账零漂移（守卫+a03 核）。
