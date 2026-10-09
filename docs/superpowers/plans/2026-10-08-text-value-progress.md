# SDD ledger — plan: docs/superpowers/plans/2026-10-08-text-value-comparison.md

2026-10-08 用户“同意”批准本会话顺序实施、代码/测试/sync/合成测试及自有候选镜像；不读源/库、不换常驻容器、不提交。

Pre-flight: Task1→2模型和encode_cell、Task2→3EncodedRow/ValueStreamState接口一致；Task4只消费测试与产物，无共享编辑冲突。

Ruling: 用户禁止新工作树/Git提交，且Windows禁止执行项目Python — 原地保留既有修改，使用本持久账替代依赖Git提交/本地脚本的skill helper；不删除账或证据 — 若记录不完整需依据实测日志补核查，不能靠Git提交恢复。

Baseline: HEAD 1a34956fbcbe7877fbad04ee5a7ec9e3dd52bf05；32磁盘可用194942922752B，load 0.00/0.06/0.12；旧自有镜像可inspect，完整292通过。dev/pg32/pg32b基线ID/StartedAt与上一批一致。

Task 1: complete — 42 RED（模块缺失）→42 GREEN；累计326单元通过，日志value-v1-task1-red/green.log在32 data/var。

Task 2: complete — 22新RED（接口缺失）、42旧测试通过→64 GREEN；累计348单元通过；日志value-v1-task2-red/green.log。

Task 3: complete — 33 RED（比较模块缺失）→33 GREEN；累计381单元通过；日志value-v1-task3-red/green.log。

Task 4: complete — 最终候选test无网、只读、无源码/数据卷，385单元+8镜像契约=393通过；runtime已安装包合成golden/有序比较smoke及pip check通过，dev一次性help通过。

Review: 单次独立静态评审发现两个Important，无Critical；不判真实源/库、PostgreSQL NUL可装载性及范围外类型。4个回归RED（另97通过）→修复后385单元GREEN；最终候选再393通过。取消在每端next前检查；列数在header前、行/剩余流预算在cell/frame分配前检查，UTF-8字节长度扫描不先分配超预算payload。不能中断已阻塞的next。

Ruling: 预算/取消修复遵循批准规格，不扩大功能；收尾技能的集成菜单/清理受用户禁止Git变更约束，保持原工作区和所有证据，不提交、不合并、不删除。

最终候选ID（本地Docker image ID，不称registry RepoDigest）：
- dev sha256:2e0ebd5cdc13630d423449e8ee78f80ab82a5df73764e3e16f9cb48a1a603835
- test sha256:570feb4ae317e9087a57ac40309d031e88a21585c752afa57f4a3482ae4c92a7
- runtime sha256:fdee8599f754466d37994dee75e483d422d9f4fff2c048ebf9d48e0182980f13

候选标签为xiangrugu:{dev,test,runtime}-value-v1-final-20261008T1230Z，created构建参数手工指定2026-10-08T12:30:00Z，不作为实际墙钟时间；验证日志实际开始12:28:33 UTC。revision为原HEAD、source.status=dirty。旧三个镜像已完整save至/dev/null核验并增pre-value-v1-20261008T122211Z回退tag；既有标签、三个长期容器ID/StartedAt保持基线。首次候选构建完成后shell末尾CR字符导致退出1，不能把该命令称全程成功；修复后独立最终构建退出0。首次JS字符串插值错误未启动远端命令。

新证据目录：[2026-10-08-value-v1](../evidence/2026-10-08-value-v1/README.md)，包含各任务/评审RED/GREEN及最终构建/验证日志，Windows回传后逐件SHA-256与32核对。

完成范围：纯合成text/bigint/NULL有序字节比较；未读真实源/快照、未连接数据库、未冻结合同、未导入、未更新常驻容器镜像、未Git提交推送。Task6及完整Task9仍未完成。真实导入前通知用户并共同确认pg32b旧数据处置。
