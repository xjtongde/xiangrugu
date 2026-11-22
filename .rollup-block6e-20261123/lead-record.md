# 第 6/6 块续盒四 · lead 记录（2026-11-22/23，30 分钟盒）

- 起表 17:29:53 UTC，硬停 17:59:53 UTC。基线 f54dd968094c78f8e20912cb50926c734d53eb8b（M=2 完好、暂存空）。
- 只读核查+草案交付；合同冻结/正式落盘/数据库写入另行授权。
- lead 预核（lead-precheck.md）：789 来历确证（txt751+csv7+ods4+xlsx13+xls14=789 类目选择面；disposition{174,620,846,0}=1640；提案 5+170）；CBDB 68/78 值验证、10 表 235 列未决、36 declaration-only、ready_for_import=False；pending 14 类基线态。
- a02 交付（硬停 17:46 内）：manifest-draft（8004 四分类 2066/5635/4/299+1293 对象+1311 绑定+36 产物 sha+naming 引用 b963ed2f+PROPOSED_NOT_LANDED）；mirror-registration-dispositions（五默认节+381 源身份+合表单列空置+追溯预登记）；load-blockers（11 项三级 2/7/2+closure 全+789 纠正节+CBDB/checksum17 逐件）；双跑十三件字节一致；32 evidence 补 spatial__MAP-READ-PLAN.md 键集 36=36 闭合。
- a03 ROUND 29+29b 全 PASS：四分类独立派生逐格全等；36 sha 全量复算 mismatch 0；抽 20 件双验 20/20；规范化 identities 1532↔1532 symdiff 0（字面差 10 表示法迁移）；closure 11/11（机器可验 6+授权事件 5）；checksum executed26+deferred17==43；CBDB canary3+small55+medium10=68；零漂移/五块零改写/M=2/二进制 0。
- **lead 裁定微修**：SUMMARY 加机械对账注记（字面 symdiff 10 表示法迁移/规范化 1532 symdiff 0）防 Codex 复核误读——a02 硬停 17:51，仅 SUMMARY+生成器 sha 变。
- **lead 件**：load-and-verification-order.md（阶段 0–4，首批当前不可执行+缺口证据）；pending-decisions.md（A 冻结 4/B 镜像配准 7/C 装载 8/D 说明级，每项影响+证据+关闭方式）。
- 口径注记：manifest 四分类系派生草案口径（B4 wrappers retain 与 structural_container 并存），冻结时可按裁定重派生（a02 提示）；dispositions twin 十记录完整链在 draft per_case（a03 观察①审计便利建议留下轮）。
- 终态 sha（微修后以 a02 回报+lead 实物核为准）：manifest-draft 3968e11455af81… / dispositions a409d571dabae7… / load-blockers e3dd22d92c815c… / SUMMARY b5696dbf36e645…（微修后新值待录）/ 生成器 1f72d55f327a7b…（同）；既有九件不变。
- **微修完成（17:43 UTC lead 终核）**：SUMMARY 注记在文（1532/表示法迁移）；变化三件 **SUMMARY 448f625ec6e91f0e… / 生成器 88ef4875346f397c… / manifest-draft 53c374d886be0e32…**（manifest artifact 表 import-package/rollup/SUMMARY.md 条目==448f625ec6e91f0ea4ab1ea7672270eba44a85b4b67652bdc4a017a25494772a==实物全 sha，联动设计预期）；其余十一件不变；artifact 36 件。TODO 终态 sha+微修记录已更新。a03 终版窄域核进行中（硬停 17:53）。
