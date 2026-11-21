# 第 3/6 块 Codex 独立验收补正 · lead 记录（2026-11-21，30 分钟盒）

- 起表 15:51:31 UTC，硬停 16:21:31 UTC。基线 b39f8ed49a29ac9640bb2efc15db7af9deeb11a1（M=2 完好、暂存空）。
- 范围：仅 SHP 头长度证据 + 第 3 块缺口记账（派工明示）。
- lead 独立锚点预核（15:54:42 UTC，32 只读 /tmp 隔离即清）：asia_contour.shp offset24 字节 0417b88a；大端 68,663,434 字 ×2=137,326,868==成员 size；小端缺陷读法 -1,967,646,972×2=-3,935,293,944 逐位复现记录值；offset32 shape_type 小端=3 正确（SHP 规格仅 offset24 大端）。详见 lead-anchor-precheck.md。
- a02 S1–S4（硬停 16:08 内交付）：S1 镜像仓首跑失配——缺 .mapinfo-verify-20261120/ MIE 证据 3 件+生成器旧版（VCS_REF=5478271），按预案从 38 同步后四件 sha 全匹配基线（f3f5374b/fc94fbf0/d6453376/2ff507fc）；S2 probe L97 改 '>i' 字单位不乘 2，s2_reprobe_shp_length.py 重探 705/705 length_match True，jsonl 恰 705 行变更 2003 行逐字节不动（3f347a12→225ef334）；S3 断言入码+counts.shp_header_length_reconciled=705+分区文案 903=2+899+2+v5 缺口措辞（源组件缺失+属性合同未决）+孪生零触碰+VCS_REF=b39f8ed；S4 双跑 0/0 stderr 0 字节一致。
- lead 实物快核（15:59:40 UTC）：四件+生成器+jsonl+probe sha 全匹配 a02 声明；groups 内 705 件 shp words×2==size 失配 0；jsonl 705 length_match 全 True；锚点 68663434/137326868；lane_partition {approved 2, proposed 899, text-owned-by-block2 2}；mapping 901=899+2；gap reason 新措辞在证。
- 映射漂移：五保护字段（sid/表名/geometry_proposal/attribute_order/crs/status）漂移 0，批准 2 件逐字节沿用；变化仅 basis.evidence_files_sha256（jsonl 225ef334/probe 5e178a11 自然更新）——a03 独立列字段清单。
- 观察项（本轮不改产物，scope 纪律）：SUMMARY 提案括号注记 702+142+52=896 未含孪生 2+部分 1（机器 counts.carrier_distribution 完整 899）；留块 6 或下轮文案统一。
- 新 sha：groups 050b258310168f7f…/om f94cf3e0d73d1b1d…/gaps eba8e4646b9b6783…/SUMMARY 7d60f70414e40a47…/生成器 7f98e1168e6f1477…/jsonl 225ef334df725e85…/probe 5e178a115fa2cdcc…。
- 边界：快照 :ro 零触；隔离提取件不入 git；未装依赖/未建镜像/未写库；entry/rehearsal M=2 未触；块5交付未触（probe_evidence a8b543f2… 原值）。