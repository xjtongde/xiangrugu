# ADMIN-STEPS-32 —— 管理员在 32 的最少步骤 ＋ DSH 后续必备权限（单独裁决单）

> 供茶香裁决用。本轮 DSH **未登录 32、未新增任何凭据**：不申请 root SSH 密钥、
> 不尝试其他凭据、不由 Codex 代跑（均为明令禁止项）。真实任务卡保持 CLOSED；
> 本轮零访问 NAS / 真实快照 / 数据库。

## 一、管理员最少步骤（全部人工执行，逐条可回退）

1. **取件与比对**：从 Gitea `deepseekharness/xiangrugu` 分支
   `dsh/p01-real-prep-20261113` 按既有同步流程更新 32 的
   `/opt/mydocker/xiangrugu/deploy`；核对交付回报中列出的工件 SHA-256。
2. **安装前状态核对**：执行 INSTALL-CHANGES-32.md §4，保存 pre-install 清单；
   发现同名既存物即停。
3. **建账号/组**：§1（`xrgp01op` 系统账号不入 docker 组；`xrgauthz` 成员由
   茶香指定授权人）。
4. **建运行根分区骨架**：§2（纯 mkdir/chmod，不动任何既有路径）。
5. **装四个程序文件**：§0 表 C1/C2/C3/C9（install -m 0755/0644 root:root）。
6. **sudoers 两段片段**：§3 —— 先 `visudo -cf` 临时文件，通过才落
   `/etc/sudoers.d/`，随后全量 `visudo -c -q`；`sudo -l -U xrgp01op` 断言
   恰四条且不含 publish。
7. **人工夹具验收**：按 MANUAL-ACCEPTANCE-32.md 顺序——正常路径先行，再四项
   关键行为，再⑥收尾窗口；全程只用合成夹具与独立 `/var/tmp` 根。
8. **清理与移交**：手册 §4 清理人工资源，evidence/ 收据打包移交。
   任一项失败 ⇒ 保留现场停在验收阶段。

每步的回退依据都在 INSTALL-CHANGES-32.md §5（原件备份 + pre/post diff），
无一步需要改 sshd、docker daemon、pg32/pg32b 或 systemd。

## 二、DSH 后续必须具备的权限（最小集，逐项标注用途）

前提事实：32 当前对 DSH 无任何可用凭据（直连与 35/36/37 跳转均拒；本机为
Linux 宿主 38，非 Windows 协议入口）。以下任一组合成立后 DSH 才能自行执行
验收命令并采集机器可读收据；否则第 7–8 步只能继续由管理员人工执行、DSH
离线分析回传收据。

| # | 权限 | 具体形态 | 用途 | 拒绝后果 |
|---|------|----------|------|----------|
| P1 | 以 `xrgp01op` 身份的非交互 shell（专用低权账号，**非 root**） | 例如该账号一条来源受限密钥或 sudo 派生会话，仅可跑白名单四条 | 直接执行 verify-inbox/stage-a/stage-b/recover-orphan 夹具轮并采收据 | 验收由管理员代打，DSH 仅审读回传件 |
| P2 | 只读访问 `$AROOT`（夹具根）与 evidence 目录 | ACL/组读权即可，不需要写 | 复核 receipts、journal、requests 日志 | 同上 |
| P3 | 部署通道复用既有同步流程 | 无需新权限：Gitea→deploy 已由项目流程覆盖 | 交付实现工件 | 人工拷贝，版本追溯变慢 |
| P4（可选） | 观察 docker 状态的只读口 | 明确**不建议**给 docker 组；如需要，仅限 `docker ps --filter label=io.xiangrugu.attempt-gen=*` 级别的固定包装 | 恢复演练中的候选核对 | 用入口自身 inspect-only 路径替代 |

**不申请**（且已遵令放弃）：root SSH 密钥追加、其他凭据尝试、Codex 代跑。
P1+P2 即可让 DSH 完成 v14 §6 全部夹具验收自动化；缺一则维持"管理员执行＋
DSH 审计"双签模式，结论效力不变但时延增加。

## 三、待茶香裁决要点

1. 是否批准第一节步骤由持有 32 shell 的管理员执行（含 sudoers 片段启用）。
2. P1/P2 授予形态（账号侧配置同样走 INSTALL §4/§5 的留痕—回退模式）。
3. 授权人（%xrgauthz 成员）名单。
4. §8 遗留裁决项（io.weight 替代口径、进程级 nice/ionice 立场）不受本轮影响，
   仍待批。
