# 第 6/6 块续盒二 · lead 记录（2026-11-22，30 分钟盒）

- 起表 14:33:31 UTC，硬停 15:03:31 UTC。基线 17097e850d2fcaaa870b7048e1986108933b5bfb（M=2 完好、暂存空）。
- 本轮限只读验证+草案交付；正式合并/合同冻结/32 版本化落盘/入库留后续授权。
- lead 预核（lead-precheck.md）：孪生 2 案定位（proposed_objects 含 components_exact_identity 恰 2，5 组件字节全同）；现 index 各 3 绑缺 TAB/ID 共 4 条；批准 2 件 Ca1884route 系 shapefile 6 组件面非孪生；pdb2/Peking 原读值位置（raster-mapping proposed_objects[9]/[11] 与 [10]/[36]，binding_basis exact-stem vs casefold_PENDING）。
- **过程披露**：a02 回合 14:36 前异常中断一次（无产物落盘、工作树干净），lead 唤醒续作，硬停 14:50 内完成全四段。
- a02 交付：S1 补 4 链（每案 5/5，根因=组清单仅小写词干 3 件、TAB/ID 大写 V3_… 在 inventory，chain ['mapinfo/v3_time_pref_pgn_PRC.ZIP',…] ordinals [114,0]/[114,1]）；双向孤儿 0；mapped 1140→1142（共享组件）；coverage_semantics 五面；归属零漂移断言入码。S2 mirror-draft 381=379 byte_identical（377+孪生 2）+1 mixed（V4：access_database 直接件独立字节、两 zip-wrapped 同 sha 子对）+1 association_pending（Peking）；四案详证 pdb2（GT=null/GCP=0/CRS null、3/4 伴 tifw exact-stem、V4 副本无 wf）与 Peking（内部 GT 均在/CRS 非 null、tfw casefold 原文）分别核对原读值照录；DRAFT_NOT_APPROVED 不预决。S3 naming-draft 83 RETAIN+1208 derive_candidate 可复算+2 批准单列+13 组 V4 区分段 _x+sha256(链串)[:8]（首版载体 sha 撞车改链串哈希披露）+联查新碰撞 0+≤63。S4 双跑 0/0 stderr 0/0 十件字节一致。
- lead 快核（14:45–14:47 UTC）：twin bindings [5,5]、coverage_semantics 在件；counts_by_class 379+1+1=381、priority_cases 4、DRAFT_NOT_APPROVED；naming counts 83+1208+2=1293、joint new_collisions 0、v4_resolved 13；blockers 三状态语义零变（EXCLUDED/FORMAT_ANOMALY/ASSOCIATED）、issues 3 verbatim、complete flag 值 false 保留；owners {3,174,5294,11,2522}、mapped 1142。
- 终态 sha：all-members 68b6a171… / reconciliation 2e82b8d8… / historical-blockers 9019ac05… / mirror 92664a81… / mirror-draft e9d2837c… / naming-scan a1842d9a… / naming-draft b5a6662c… / object-index 8e045afc… / pending debb3e1b… / SUMMARY 3fb34fcb… / 生成器 7333ec58…。
- TODO：续盒二记录+表行/页首状态+讨论账。
- 边界：五块原交付零改写；归属账语义零漂移（仅 mapped_objects 增列）；M=2 未触；源件只读；草案不预决合并/批准。
