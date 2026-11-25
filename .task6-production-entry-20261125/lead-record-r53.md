# 生产装载合同与实例标记补正 · lead 记录（30 分钟盒）

- 起表 2026-11-25 14:40:26 UTC，硬停 15:10:26。基线 37a51f24dff8e122a3439725af50017f30dfa42f。授权候选补正+32 隔离测试；**本盒不接收 deploy/不连生产 PG/不建库/不写正式库**。lead 收口（a02 起始失败惯例接管披露）。

## 补正交付
1. **单次正式解析驱动**：run_production_load 收 contract_parse_fn，**只解析一次**实际冻结合同→同一解析结果出 canonical 摘要（==已批锚 ba8118fb）+确认七目标（target_set_mismatch 门）+**驱动装载**（_load_and_verify 用解析 dump）。**新反例：已验合同与执行对象不一致→contract_execution_mismatch BEGIN 前拒**（None 扩展键两侧同规归一比对）。
2. **核销证据恰两份**：set(evidence)=={nul,chgis} 硬门（缺任一/多余→evidence_set_invalid BEGIN 前拒）；逐份 compact canonical 重算对绑定锚。
3. **标记四态明确拒**（同会话序）：to_regclass 表存在（缺→marker_table_missing）→count 恰 1（空→marker_empty/多→marker_multiple_rows）→值==批准指纹（错→marker_value_mismatch）。**prereq_check.py 同步四态**（marker_table_present/marker_exactly_one_row/instance_marker_matches，只读 exit 0/2）。
4. **单测 23 条全过**（新增：执行对象不一致/缺 NUL/缺 CHGIS/多证据/标记缺表/空/多行/错值；保留旧库共存正例/工件变-调用方一致×3/注入回滚干净重试等）。
5. **32 隔离试装 PYEXIT=0 R53_TRIAL_PASS**：临时唯一名容器 **xiangrugu-r53-trial-20261125-144308-7117f609**（Id deaaa982586b68da…，镜像 d562e436 核，--network none）；cbdb+cbdb_reh 哨兵旧库共存正例通过；先决分录+prereq_check exit 0；A 注入回读失败整批回滚零残留；B 干净重试 **47725 行单事务 committed**（单次解析 gates 在证）；**D 六活体反例**（target_already_exists/marker_value_mismatch/wrong_database/artifact_drift_recomputed/**contract_execution_mismatch**/**evidence_set_invalid**）；**E 标记四态活体反例**（empty/multiple/wrong_value/table_missing 各明确码，夹具变异逐次恢复 exit 0 在账）；**旧库前后快照全等未改动**。
6. **回归九套 R13_EXIT=0 stderr 0B 209 passed**（186+23）。

## 边界与披露
源件只读；deploy 未接收；服务未改；生产 PG 零连接、正式库零写入；全量 ready false/7995 不动；test 审批≠生产授权；M=2 不提交不触碰。标记四态活体反例仅变异隔离实例标记夹具并逐次恢复（restores 全 0 在证），旧库与七表零触。试装容器保留供 a03 独立核，复核后经 Id 清理。

## 首个剩余缺口
真实首批写库批准事件（绑七目标）+先决建库与标记预置授权（pg32b:5433）另批；其后按 runbook 正式执行。

## a03 复核与清理收口
- **R53 终报 PASS（14:47 UTC 盒内）**：diff 恰七件/M=2 不在 diff；补正读码三面 ✓；独立反例 8/8（执行对象不一致/缺 nul/多第三份/标记四态全 begins=0）；独立真回读全过（47725/七摘要/EWKB/63·74）；旧库未动互证（611c4eae/aab5e169 逐字全等）；marker 恰 1 行恢复实证；prereq_check 正例 0/错指纹 2/错库 2；回归 209 自洽；四不动实证。
- **cleanup_execution 14:47:35 UTC**：试装容器经 Id 全号核一致后清除（CLEANUP_OK，计数 0）。
