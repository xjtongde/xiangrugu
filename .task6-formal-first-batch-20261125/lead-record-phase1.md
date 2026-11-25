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

## 3. 同一命令隔离验证
（待跑：git archive 绑定提交→临时容器 loopback 端口→--isolated 整批+--inject-failure 回滚）

## 边界
本阶段不更新 deploy/不改生产权限/不写正式库（预检仅 SELECT）；源件只读；旧库 ACL 不动；镜像/服务不改不重启；ready false/7995 保持；M=2 不提交。
