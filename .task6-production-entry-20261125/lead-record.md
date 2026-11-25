# 首批七项生产装载入口候选 · lead 记录（30 分钟盒）

- 起表 2026-11-25 13:47:55 UTC，硬停 14:17:55。基线 a1bd50236efc6a8e15518d22cf95ac7eff88e93b。授权候选分支实现+32 隔离测试；**本盒不接收 deploy/不改镜像服务/不连生产 PG/不写正式库**。lead 收口（a02 起始失败惯例接管披露）。

## 交付
1. **生产入口候选** production_entry.py：绑冻结合同 ba8118fb/原清单 fb5e6b33/两核销证据/七目标；摘要重算（容器正式 parse）比对，漂移拒；**独立首批写库批准门** write_approval 四面+approval_class∈{test,real}；real 须正式端点 pg32b:5433/xiangrugu+real_authority_ref；**本轮 test-only**（ref test-only-not-a-real-write-approval@a1bd502）；全量 ready false/7995 不动。
2. **同一 DDL 会话内核目标身份**：current_database()/port/inet_server_addr/server_version/postmaster_start+库面（cbdb/pg32b 可见即拒）；**正式目标常量 pg32b:5433/xiangrugu**；**建库/PostGIS/schema 先决分列，非装载器默认动作**（缺→prerequisite_missing 拒，不代建；正例 create_prerequisites=False）。
3. **单测 14 条全过**（test_production_entry.py）：正例先决零代建/错库/错端口/缺写批准/real 须正式端点/real 须授权 ref/合同漂移/证据漂移/目标已存在/postgis 缺不代建/schema 缺不代建/**注入回读失败 ROLLBACK 零残留+干净重试**/生产库可见/ready 与 7995 门。fbl 重构共享事务体 _load_and_verify（14 旧测仍过）。
4. **32 隔离试装 PYEXIT=0 PRODENTRY_TRIAL_PASS**：临时唯一名容器 **xiangrugu-prodentry-trial-20261125-135328-6a53fa5c**（Id f4cfe330ff88a6ee…，镜像 d562e436 核，--network none，POSTGRES_DB=xiangrugu）；先决预建分录（postgis/harv/chgis exit 0）；**A 注入回读失败→readback_mismatch 整批回滚→to_regclass 零残留**；**B 干净重试→单事务 committed 47725 行**（59/59/29/3389/2957/40199/1033）七 attr+两 geom 摘要全合已批锚，m008003 63 组；**D 四活体反例** target_already_exists/wrong_database/write_approval_missing/artifact_drift 全拒+**零突变**。
5. **正式执行与回退步骤** formal-execution-runbook.md（A 先决另批/B 独立批准链/C 同会话执行/D 事务内自动回滚+提交后恰七表 DROP 另批/E 隔离映射）。
6. **回归九套 R11_EXIT=0 stderr 0B 200 passed**（186+14）。

## 过程披露
- fbl 重构中间态重复 check_targets_absent 两行（a03 在案观察）→修去其一；production_entry 死代码行删；CSV 含逗号字段引号面（string_agg）→_rows_csv 解析；ProdFake fixture 同步真实 CSV 语义（4 failed→修后 200 全过，活体试装先证真实行为）；GATE_STOP 分支落盘补；两失败容器（17f60939/0a56e891 前缀）本盒创建经 Id 核清除；/tmp/lb 隔夜清重建。
- **M=2 划界**（a03 询问已答）：p01-entry 二件系跨盒长期保留未提交件，早于基线即 M，非本盒新改，不提交不触碰。

## 边界
源件只读；deploy 未接收；镜像/服务未改；**生产 PG 零连接、正式库零写入**（仅临时唯一名实例）；test 审批≠真实写库批准。试装容器保留供 a03 真回读，复核后经 Id 清理。

## 首个剩余缺口
真实首批写库批准事件（独立于合同评审，另批）+先决建库授权（pg32b:5433 CREATE DATABASE xiangrugu）；其后正式执行按 runbook。
