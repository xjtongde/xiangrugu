# 正式端口与装载角色补正 · lead 记录（30 分钟盒）

- 起表 2026-11-25 15:50:53 UTC，硬停 16:20:53。基线 bc7cb15ce2e6a2723d20b0fd977156024275275d。授权候选补正+32 隔离测试；**本盒不更新 deploy/不改生产角色或授权/不写正式库**。lead 收口（a02 起始失败惯例接管披露）。

## 补正交付
1. **端口分离**（缺陷确认：旧版会话 port 比外部 5433 会拒正确 pg32b 目标）：scope 声明 internal_port=5432+endpoint_mapping_verified；expected endpoint_mapping 三方绑定；会话 port==internal_port（wrong_internal_port）+映射一致（endpoint_mapping_mismatch）BEGIN 前拒；标记同会话校验保留。
2. **隔离复现外部→内部**：临时容器 -p 127.0.0.1::5432（loopback 发布，ext 32770）；客户端容器 --network host psql -h 127.0.0.1 -p 32770 → **会话内 port 实测 5432**；正确映射通过。
3. **NOLOGIN 角色实际切换**：PsqlSession(role=…) 连接后 SET ROLE；current_user 实测==xiangrugu_loader；**角色下 CREATE+COPY 七表 47725 行，tableowner==角色**；直连 FATAL not permitted to log in（本地 trust 通道实证；外部通道先密码认证——通道差异记录在证）。
4. **最小权限实证**：harv/chgis USAGE+CREATE、public USAGE、marker 仅 SELECT（true,false）；marker UPDATE/INSERT/DELETE 活体 permission denied×3；CREATE EXTENSION 拒；CONNECT cbdb/cbdb_reh=false（隔离 REVOKE CONNECT FROM PUBLIC 演示；**生产授权未动**）。
5. **单测 26 条全过**（新增 wrong_internal_port/external_mapping_mismatch/internal_port_not_declared/mapping_not_verified；real 门端点补 internal_port）。
6. **32 隔离试装 PYEXIT=0 R55_TRIAL_PASS**：容器 **xiangrugu-r55-trial-20261125-155953-14753512**（Id a1fe79f5651241d2…，镜像 d562e436 核）；A 注入回滚零残留；B 角色装载 47725；**D 八反例**（target_exists/wrong_instance/wrong_database/**external_mapping_mismatch**/**internal_mapping_mismatch**/artifact_drift/execution_mismatch/evidence_missing）；E 角色权限全证；F 标记四态+恢复全 0；旧库前后快照全等。
7. **回归九套 R14_EXIT=0 stderr 0B 212 passed**（186+26）。
8. **runbook 校准 G1/G2/G3**：端口分离门/角色切换路径/最小权限清单/实际调用命令。

## 披露
- 两次失败运行（驱动断言 CSV 解析瑕疵：SET 回显/布尔引号；NOLOGIN 证明通道选错）经 Id 全号核后清理（d11bccbc…/624df05b…），非代码缺陷；第三次 PYEXIT=0。
- 本盒网络模式：loopback 发布端口（非 --network none），为复现外部映射路径所必需；仅 127.0.0.1 绑定，LAN 不可达。

## 边界
deploy 未更新；生产角色/授权未改（xiangrugu_loader 生产现状仍仅 SELECT 标记，harv/chgis CREATE 授权随首批写库批准另授）；正式库零写入；ready false/7995 保持；M=2 不提交。

## 首个剩余缺口
首批七表装载授权事件（approval_class=real+real_authority_ref 绑七目标）+生产角色 harv/chgis CREATE 授权与旧库 CONNECT REVOKE（另批）；其后按校准 runbook 执行。

## a03 复核与清理收口
- **R55 终报 PASS（16:06 UTC 盒内）**：diff 恰九件/M=2 不在 diff；端口分离门+角色切换读码 ✓；独立反例 6/6+活体角色权限逐项与 G2 一致；外部→内部自复现（SHOW port 5432/错端点拒）；真回读 47725/七摘要/EWKB/63·74/**owner==角色×7**；NOLOGIN FATAL 自证；旧库互等；回归 212 自洽；**生产角色现状只读核（harv CREATE=f/CONNECT cbdb=t PUBLIC 未动）与另批划界一致**；deploy 未更新。
- **cleanup_execution 16:05:56 UTC**：试装容器经 Id 全号+名核一致后清除（CLEANUP_OK，计数 0）。
