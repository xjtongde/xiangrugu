# p01-entry —— v14 最小权限入口实现与人工夹具验收套件

静态定稿依据：`../PROPOSAL-32-minimal-entry.md`（v14 @ commit `20d8219`）。
本目录是**实现轮交付物**，全部可在无特权 Linux 上以合成夹具复验；不含任何
真实资源访问路径——`stage_b_mount_plan` 在非 `XRG_P01_FIXTURE` 模式硬拒
（`real_stage_b_locked`），attempt 身份常量钉死为 `real-p01-20261113-a`。

## 文件

| 文件 | 角色 | 部署位置（见 INSTALL-CHANGES-32.md） |
|------|------|--------------------------------------|
| `xrg_p01_entry.py` | 固定入口程序：verify-inbox / stage-a / stage-b / recover-orphan + publish 派发（按 prog name / `XRG_P01_CALLER_UID`） | C1 `/usr/local/bin/xrg-p01-entry-python` |
| `xrg-p01-run` | sudoers 白名单包装（操作员四条） | C2 |
| `xrg-authz-publish` | 授权人独占发布包装（传 SUDO_UID） | C3 |
| `go_gated_supervisor.py` | candidate_supervisor 的 GO 门加性变体（原件未改动）：两阶段 FIFO 读、单帧 `GO <hex64>`、nonce=sha256(confirmed‖gen‖attempt)、只读挂载复核、无 GO ⇒ `SUPERVISION_ABORTED_NO_GO` | C9 |
| `stub-docker.sh` | 夹具 docker：状态机 created/running/exited + outcome.json 归档 + calls.log；旋钮 `XRG_P01_STUB_STATE/START_FAIL/BAD_MOUNTS` | 仅夹具 |
| `stub-runner.sh` | 容器内 UID 10001 仿真 runner：FIFO 两阶段读 + 副本 SHA 复核 + go-gate 收据 | 仅夹具 |
| `local-suite.py` | 九用例人工夹具验收套件（机器可读 `.suite/SUMMARY.json`） | 仅夹具 |

## 运行套件（38 或任意非特权 Linux）

```bash
python3 local-suite.py        # 全合成、零真实资源；约 3–4 分钟
```

当前状态：**9/9 PASS**。覆盖 = v14 §6 关键项映射：

| 用例 | v14 条款 |
|------|----------|
| normal_path | T1→T11 正常走查（含 BOUND/PREPARED 双收据、RESOLVED published:true 五步收尾） |
| readback_failure_worker_never_started | ①宿主核验实际 cgroup 后才发 GO；失败⇒worker 从未启动 |
| host_exit_before_go_delivery | ②入口在消费记录后、start 前退出⇒恢复 inspect-only、零重发、候选保留人工可见 |
| consumption_precedes_start_and_no_resend | ③journal 中 CONSUMED_STATE 先于 START_REQUEST；二次⇒attempt_consumed 零请求 |
| authz_exclusive_publish | ④独占发布：二次 EEXIST、原件 0400、发布后改暂存件不影响原件 |
| uid10001_reads_same_bytes_via_mount | ④容器侧 go-gate 回显 copy SHA == 原件 SHA；FIFO 0640 |
| operator_cannot_replace_original_or_copy | ④caller-owner 门拒外来暂存件；写探针（沙箱 SKIP 如实标注，32 上必测） |
| window_e_sync_result_unknown | ⑥(b/e) dir-fsync 未知窗口：半记录保留、恢复不重发、后续拒绝 |
| t9a_retry_qualification | T9a 静态拒绝可重试资格：无消费记录、无 start、recover 后可成功 |

## 故障注入（供 MANUAL-ACCEPTANCE-32.md §3）

`XRG_P01_FAULT=HOOK[:PATHFRAG][,…]`，钩子：`consumed_file_fsync`（记录前）、
`consumed_dir_fsync`（记录后 dir-sync，§4f b/e 窗）、`consumed_pre_start`
（记录持久后、start 请求前，§4f c 窗）、`terminal_update`（终态同步未知，
⑥e）、`rename_publish` / `publish_file_fsync` / `publish_parent_fsync`
（发布器三步）、`docker_request@<op>`（请求层崩溃）。

## 已知环境边界（诚实披露）

- 沙箱 umask 可能令 FIFO mode 显示 0644（套件按文档降级并标注）；32 安装
  契约强制 0640，人工验收必测。
- setpriv 探针在无特权沙箱返回 SKIP；同字节读证据由 runner 收据承担。
- 真实 Stage B 永久锁死直至茶香另行授权（代码级，非口头）。
