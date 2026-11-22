# 第 6/6 块续盒三 · lead 记录（2026-11-22，30 分钟盒）

- 起表 14:57:55 UTC，硬停 15:27:55 UTC。基线 2b37abd50b4313eaa047bbd459eebf5730dd3de5（M=2 完好、暂存空）。
- 本轮只读核查+草案交付；正式批准/合并/落盘/入库留后续授权。
- lead 预核（lead-precheck.md）：Peking 两案 wf6→GT 换算六项 repr 级全等（原证据直取预换算）；现 mirror-draft 孪生 2 组缺陷（字符串 identities+evidence_ref 误引 approved 面）；批准 2 件 .shp 主件 ord[6]/[14] 同 sha 109d74b1…/1752B。
- a02 交付（硬停 15:14 内）：S1 孪生结构化重写（真实 SID/五对三元组/内层 ZIP sha 69b5119f01f2b593…6,089,146B 一致断言/counts 2案10对10记录/evidence_ref 更正+correction_note）；381 构成更正（377+V4 1+孪生案组 1+Peking 按件 2=378 byte_identical+1 mixed+2 association；旧组身份 per_case[].group_id 保留）。S2 V4 主表/冲突表同源派生 39 SID 全等断言（de4==crm True）；两字节版本+两同摘要副本身份保留；批准 2 件 ca1884route_przh_1251/utf8+schema_draft chgis（原批准不动）；1293 联查 name≤63 全过/新碰撞 0/组合最长 69 登记。S3 Peking affine_reconciliation_this_box（公式+原值+换算值+全等断言，独立复算）；升级建议附证据最终留茶香；pdb2 三绑定保留+V4[159,6] UNRESOLVED_PENDING；存储复用与逻辑表合并 policy 分离。S4 双跑 0/0 stderr 0/0 十件字节一致。
- **过程披露**：a02 中途误合并孪生致 380、Peking 重复致 382，盒内断言纠回 381 后终版双跑。
- lead 快核（15:04 UTC）：counts_by_class 378+1+2=381；孪生 entry 1 per_case 2 结构化键齐（identity_triples/mirror_role_pairs_per_case/inner_zip_equality/note_counts/candidate_records）；naming counts 83+1208+2=1293/v4_sid_rows 39/joint max 69/new collisions 0；owners {3,174,5294,11,2522}/refs 1311。
- 终态 sha：all-members df61d3da… / reconciliation 3001b7d1… / historical-blockers 1e2cc636… / mirror 55d738e9… / mirror-draft ff148c51… / naming-scan 2e06c99e… / naming-draft b963ed2f… / object-index e0581a05… / pending 390b8754… / SUMMARY 2b079d29… / 生成器 ab445844…。
- TODO：续盒三记录+表行/页首状态+讨论账。
- 边界：五块零改写；归属+引用零漂移；M=2 未触；源件只读；草案不预决批准/合并。

## 微修轮（lead 裁定，a03 R27 观察项闭环 + 回退丢失面补回）
- **观察项⑧闭环**：a02 加 legacy_string_identities=基线 2b37abd 旧孪生 2 组 identities 字符串原样 4 条（git show 提取，lead 独立集合 symdiff==0 验证）+correction_note（表示法迁移/语义等价/旧串别名供机械对账）。
- **ledger 回退裁定**：mirror-adjudication.json 维持基线字节形（lead diff 证 vs 2b37abd 仅 baseline_git 变）——稳定账与草案分离，更正面只入 draft；a02 前盒误染已清，不切回。
- **draft 构成归正**：381=379 byte_identical（377+孪生 groups-derived 2 原位升级结构三元组+legacy 别名）+1 mixed+1 association（Peking 合 1 基线口径）；孪生详证在 priority_cases.mapinfo_twin_2_groups.structured_case_group（per_case 2×5 角色对/内层 ZIP sha 69b5119f…一致/note_counts 2案10对10记录）；affine_reconciliation_this_box+six_item_identical 保留（lead 核在件）。
- **微修二（lead 快核发现回退丢失面）**：①pdb2 V4 副本 [159,6] 显式 georeference_status=UNRESOLVED_PENDING+reason（派工明文要求）；②四 priority_cases 补案级 recommendation+remaining_adjudication_points（组级 381/381 已在，案级汇总）。硬停 15:20。
- 微修一后 sha：mirror-adjudication ef56c9d4（基线形+VCS）/ mirror-draft eaf15b70 / 生成器 dbf77da8；其余八件不变（df61d3da/3001b7d1/1e2cc636/2e06c99e/b963ed2f/e0581a05/390b8754/2b079d29）。微修二后终版 sha 以 a02 回报+lead 实物核为准。
- **微修二完成（15:15 UTC lead 终核）**：V4 [159,6] georeference_status=UNRESOLVED_PENDING+georeference_reason「内部 GT=null、无世界文件（exact-stem tifw 不在同容器）；配准取舍未决留裁定」在件；wf 绑定恰 3 原样；四案 case_recommendation+case_remaining（2/3/2/3 点）齐；counts 379+1+1 groups 381；legacy aliases 4；affine 保留。**终版 sha：mirror-draft f5a78d0dad56da43… / 生成器 010a5561ec095dab…，其余九件不变**（df61d3da/3001b7d1/1e2cc636/ef56c9d4/2e06c99e/b963ed2f/e0581a05/390b8754/2b079d29）。TODO 终态 sha+微修闭环记录已更新。a03 终版窄域核进行中（硬停 15:22）。
