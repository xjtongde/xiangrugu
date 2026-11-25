# 生产入口身份与工件绑定补正 · lead 记录（30 分钟盒）

- 起表 2026-11-25 14:17:28 UTC，硬停 14:47:28。基线 16f94a6081cebde65ccde307913b5a78b18f904a。授权候选补正+32 隔离测试；**本盒不接收 deploy/不改服务/不连生产 PG/不建正式库/不写正式库**。lead 收口（a02 起始失败惯例接管披露）。

## 补正交付
1. **正式目标识别修正**（production_entry.py R52）：撤旧版「cbdb 可见即拒」一刀切（真实 pg32b 上 cbdb/cbdb_reh 必然存在——旧门会拒正确目标，缺陷确认）；改**正向身份证明**：同 DDL 会话读先决预置 public.xrg_instance_marker（值=带外 docker inspect 独立核实容器 Id），与 scope 绑定 instance_fingerprint 比对；**标记缺失/不符→identity_unproven 写入前拒**；错库 wrong_database/错端口 wrong_port 照拒；cbdb/cbdb_reh 可见时正确目标**通过**（legacy_databases_visible 记录在证）。
2. **入口内重算摘要**：recompute_artifact_digests 从实际工件文档重算——冻结合同经注入正式 parse 函数（容器 pydantic）、原清单 InventoryManifest canonical 重建、两核销证据 compact canonical；与 scope 锚及 expected 锚逐项比对。**新反例落地：工件已变但调用方两处摘要仍互相一致→artifact_drift_recomputed 拒**（合同/清单/证据三面单测+活体合同面）。
3. **审批绑定七目标**：write_approval.bound_object_rule_ids 须恰七 rule_id（缺/少→拒）；**test 审批指向正式端点 pg32b:5433/xiangrugu→test_approval_cannot_target_production 拒**；real 须正式端点+real_authority_ref。
4. **可执行先决检查** prereq_check.py（只读，exit 0/2）：库可连/postgis/schema×2/标记值==独立核实 Id；试装内运行 **exit 0**。
5. **单测 17 条全过**（test_production_entry.py R52）：旧库共存正例（legacy_visible==[cbdb,cbdb_reh]+标记核+先决零代建）/错库/错端口/标记缺失/标记不符/指纹漂移/**工件变-调用方一致×3（合同/清单/证据）**/缺审批/审批未绑七/test 指正式端点/real 门×2/目标已存在/先决缺不代建/注入失败回滚零残留干净重试/ready 与 7995 门。
6. **32 隔离试装 PYEXIT=0 R52_TRIAL_PASS**：临时唯一名容器 **xiangrugu-r52-trial-20261125-142128-1bf48938**（Id 4f48de901086eea2…，镜像 d562e436 核，--network none）；**隔离实例预置 cbdb+cbdb_reh 两同名旧库含哨兵数据**；先决分录（postgis/harv/chgis/marker 表+值 exit 0）；**入口内重算 ba8118fb/fb5e6b33/两证据 sha 全合已批锚**；A 注入回读失败→整批回滚零残留；B 干净重试**47725 行单事务 committed，旧库共存身份门通过**；D 四活体反例（target_already_exists/identity_unproven/wrong_database/**artifact_drift_recomputed**）全拒+零突变；**旧库前后快照（表清单/行数/内容 sha）全等——试装未改动 cbdb/cbdb_reh**。
7. **回归九套 R12_EXIT=0 stderr 0B 203 passed**（186+17）。

## 边界与披露
源件只读；deploy 未接收；服务未改；生产 PG 零连接、正式库零写入（旧库仅隔离实例内测试复制件）；全量 ready false/7995 不动；test 审批≠生产写入授权。M=2 跨盒保留件不提交不触碰。试装容器保留供 a03 独立回读+旧库未动独立比对，复核后经 Id 清理。

## 首个剩余缺口
真实首批写库批准事件（绑七目标）+先决建库与标记预置授权（pg32b:5433）另批；其后按 runbook 正式执行。
