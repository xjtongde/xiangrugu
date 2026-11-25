# 首批七表正式导入·第一阶段 lead 记录（30 分钟盒）

- 起表 2026-11-25 16:09:11 UTC，硬停 16:39:11。基线 7e8622ec9f18aa18006f961497457c3b4504d650。**茶香真实写库审批原文**存 real-write-approval-20261125.txt（sha256 绑定，禁止测试审批代替）；第二阶段须 Codex 明确放行。lead 执行（a02 起始失败惯例接管披露）。

## 1. 正式命令 formal_first_batch.py
- 固定连接 pg32b:5433/xiangrugu（客户端容器 --network host psql -h 127.0.0.1 -p 5433，scram 密码运行时取容器 env，**绝不入 Git/证据**）；CWD=受控 repo 根；单会话单连接禁切库。
- 绑定：冻结合同 ba8118fb…/原清单 fb5e6b33…/两核销证据（WO run_evidence_sha256 nul 5dd1739c/chgis 623723ff）/七 rule_id（m002709/m002717/m004812/m006642/m008002/m008003/m008004）；real 门 approval_class=real+real_authority_ref=审批原文 sha+bound_object_rule_ids 恰七。
- 连接前独立核：docker inspect Id==--instance-id、docker port 映射含 :5433->5432/tcp；同外部路径只读 probe 绑 server_addr；**同一会话 SET ROLE xiangrugu_loader+current_user 校验**；标记四态+七表 absent 由入口同会话核。
- --isolated 与 --real 同一命令同一代码路径（仅端点/审批类参数化）。

## 2. 5433 实测只读预检（生产，仅 SELECT）
- PREFLIGHT_EXIT=0：dbname xiangrugu/**内部 port 5432**/marker 恰一行==pg32b Id 3d93fc7741f6…/loader NOLOGIN（canlogin f）/harv CREATE=f chgis CREATE=f（授权属第二阶段）/marker SELECT=t UPDATE=f/**七表 present 0**/旧库 ACL default-public-connect 现状录（不动）。
- harv/chgis 所需最小权限（第二阶段授予）：GRANT USAGE, CREATE ON SCHEMA harv, chgis TO xiangrugu_loader；标记保持仅 SELECT。

## 3. 同一命令隔离验证（绑定提交 3ab337e419d462abe5df6c0a8184ee0f77d45b3d）
- git archive 3ab337e → /opt/mydocker/xiangrugu/formal-exec-20261125（受控执行根，版本绑定）；临时容器 **xiangrugu-formal-iso-20261125-161259-8cfc7467**（Id 1344201972de2dd8…，镜像 d562e436 核，-p 127.0.0.1:32771->5432 loopback）；先决+角色授权（隔离内）分录 exit 0。
- **--inject-failure m006642：ISO_FAIL_EXIT=2 REFUSED_readback_mismatch，harv/chgis 表计数 0（整批回滚零残留）**。
- **--isolated 干净重试：ISO_PASS_EXIT=0 FIRST_BATCH_TRIAL_LOAD_PASS，total_rows 47725（独立 SQL 复核 47725），tableowner==xiangrugu_loader**；current_user 同会话==角色；gates 单解析/证据恰二/入口重算/审批绑七/正向身份/先决不代建/目标 absent 全在证。
- 披露：①首跑映射核解析 docker port 输出格式瑕疵（ENDPOINT_MAPPING_MISMATCH）→修正提交 3ab337e 重跑，非门缺陷；②反例须净面——正例先跑后七表已在，隔离夹具 DROP 七表重置（FIXTURE_RESET_OK 在账，仅临时实例，生产零触）再按 fail→pass 序重跑。
- 证据：iso-pass.json/iso-fail.json（本目录）；容器保留供 a03 独立核，复核后经 Id 清理。

## 第一阶段判定
**PASS**（正式命令+5433 只读预检+同一命令隔离整批/回滚全证）。**等 Codex 独立验收明确放行后才进第二阶段**；本阶段未更新 deploy/未改生产权限/未写正式库。

## 边界
本阶段不更新 deploy/不改生产权限/不写正式库（预检仅 SELECT）；源件只读；旧库 ACL 不动；镜像/服务不改不重启；ready false/7995 保持；M=2 不提交。
