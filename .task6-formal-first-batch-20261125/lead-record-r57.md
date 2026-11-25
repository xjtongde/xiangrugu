# 正式装载放行前定点补正 · lead 记录（30 分钟盒）

- 起表 2026-11-25 17:28:17 UTC，硬停 17:58:17。基线 2da0e2f3c62675ff813784cc4d65448e1aeffc9b。只补正式命令及其直接依赖；**本盒不更新 deploy/不改生产权限/不连生产 PG/不写正式库**；第二阶段继续等 Codex 放行。lead 收口（a02 起始失败惯例接管披露）。

## 补正交付
1. **审批 SHA 钉死**：APPROVAL_SHA256=88f4f1acebbf03536a386d16d13ba8c229253a31eb02db11b56cef34170753b5；--real 连接前验原文完整 sha——任意文件/篡改原文/测试审批→APPROVAL_SHA_MISMATCH exit 2；缺文件→APPROVAL_FILE_MISSING。
2. **模式隔离**：real 固定 pg32b 容器+外部 5433+instance-id==inspect pg32b Id；isolated 拒正式实例/端点（pg32b/pg32 名/5433/pg32b Id）；**禁止 real 注入故障**；real/isolated 互斥。全部 pre-connection 门仅 docker 元数据，**零生产 PG 连接**。
3. **解析版本绑定**：取消 /tmp/lb 默认；--parse-src 默认 deploy/datamgmt/src（受控接收树）→exec tar 单跳管道入 dev:/tmp/formal-parse-src（tmpfs）→host/容器逐文件 sha256（LC_ALL=C 排序）全等绑定入证：**46 件 mismatch 0，contracts_py_sha 94a1e564…**。
4. **凭据卫生**：PGPASSWORD 仅进程 env（docker run -e PGPASSWORD 无值+subprocess env），不入 argv/日志/证据；PsqlSession 增 env 参数。
5. **EWKB 事务内核验**：fbl 空间回读增 ST_AsEWKB(geom)→字节拼接 sha256 与源侧 ewkb_hex 逐点拼接期望比对，**geom_ewkb_sha_match 纳入提交条件**；七项事务内核验+XY 重建/geom_stream 双轨保留。
6. **隔离八反例 8/8 连接前拒**（N1 任意文件/N2 篡改/N3 测试审批→APPROVAL_SHA_MISMATCH；N4 注入→INJECTION_FORBIDDEN_IN_REAL；N5 real 打临时容器→REAL_MODE_FIXED_TO_PG32B_5433；N6/N7/N8 isolated 打 pg32b/5433/pg32b Id→FORMAL_INSTANCE_OR_ENDPOINT_IN_ISOLATED_MODE）。
7. **同一命令隔离复验**（容器 xiangrugu-r57-iso-20261125-173223-9239cb62，Id d7905899c32fa5e3…，ext 32772→5432）：**--inject-failure FAIL_EXIT=2 REFUSED_readback_mismatch 零残留**；**PASS_EXIT=0 total 47725**；**m002709/m002717 geom_ewkb_sha_match True（5262fe452df3…）+geom/attr 全等**；owner==xiangrugu_loader；current_user 同会话==角色。
8. **回归九套 R15_EXIT=0 stderr 0B 212 passed**。

## 披露（三次门拒迭代，均连接前拒零 PG）
- dev 容器 **ReadonlyRootfs=true**（13:43:10Z 起始固有态，Restarts 0，非本盒改动）：docker cp 被 daemon 拒→首两次隔离运行 PARSE_SRC_COPY_FAILED（门序正确）→改 exec tar 管道（3370d5f）。
- host/容器 locale 排序差异致 46 件同 sha 异序→PARSE_VERSION_BINDING_MISMATCH→两侧 LC_ALL=C（59214a6）。
- 前盒 r57-fail 首版证据实为 PARSE_SRC_COPY_FAILED（非回滚反例），已以 59214a6 重跑真回滚反例覆盖。

## 边界
deploy 未更新；生产权限未改；生产 PG 零连接（八反例仅 docker 元数据）；正式库零写入；源件只读；旧库 ACL 不动；镜像/服务不改不重启；ready false/7995；M=2 不提交。隔离容器保留供 a03，复核后经 Id 清理。

## 首个剩余缺口
第二阶段（受控接收+最小授权+正式装载）仍待 **Codex 明确放行**；其后执行 formal_first_batch.py --real。
