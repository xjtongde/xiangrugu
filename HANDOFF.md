# 香如故数据接入交接

截至 2026-11-13，正式请求读取器已经接入并通过安装候选人工验证。开发回归 1347 项通过，安装版 1324 项通过、23 项跳过。465,284 行人工整批用 1338.41 秒完成，独立黄金摘要和两次 SQLite 文件摘要一致。 [本轮证据](docs/superpowers/evidence/2026-11-13-request-reader-integration/README.md)

真实源值期望已覆盖 **68/78 表**，余 10 表 235 列，Task8 未完成。11 月 9 日 p01 尝试在原 1800 秒预算内超时，未形成完整批。 [真实运行停点](docs/superpowers/evidence/2026-11-09-real-p01-attempt/README.md)

1. 先读 [AGENTS.md](AGENTS.md)、[rules.md](rules.md)、[项目索引](docs/index.md)、[数据接入模块](datamgmt/README.md) 和 [阶段计划](datamgmt/docs/IMPLEMENTATION-PLAN.md)。Windows 是项目编辑入口，项目构建、测试和执行都在 32 上串行进行。
2. 下一步用已验证的新 runtime 准备 p01 `POSTED_TO_ADDR_DATA` 八列的关闭权限任务卡。绑定固定快照及控制输入，核验候选身份和主机状态，保持半核、768MiB、无交换、1800 秒候选截止。
3. 任务卡经茶香明确授权后方可执行一次真实只读及全快照摘要核验。以上次授权已用完为准。只有完整批和独立核验通过后才能增加真实源值期望。数据库写入前另行通知茶香并确认 pg32b 旧数据的处置。

交接基线为 `8fbc8c97fcf1d818caddf6ab556fa82d986643ed`。阅读和同步时以项目授权为准。历史日志中的授权收据仅说明对应历史操作，当前权限以本次用户指令为准。
