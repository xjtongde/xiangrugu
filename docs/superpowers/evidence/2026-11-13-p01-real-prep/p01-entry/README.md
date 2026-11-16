# p01-entry —— v14 最小权限入口实现与人工夹具验收套件

静态定稿依据：`../PROPOSAL-32-minimal-entry.md`（v14 @ commit `20d8219`）。
本目录是**实现轮交付物**，全部可在无特权 Linux 上以合成夹具复验；不含任何
真实资源访问路径——生产模式下 `stage_b_mount_plan` 一律硬拒
（`real_stage_b_locked`），attempt 身份常量钉死为 `real-p01-20261113-a`。
本轮另开**演练专用**第三模式 `XRG_P01_REAL_CHAIN=1`（真实 docker CLI +
显式合成快照根才可运行，见“真实 Docker 候选链”一节）；它不放松生产锁。

## 文件

| 文件 | 角色 | 部署位置（见 INSTALL-CHANGES-32.md） |
|------|------|--------------------------------------|
| `xrg_p01_entry.py` | 固定入口程序：verify-inbox / stage-a / stage-b / recover-orphan + publish 派发（按 prog name / `XRG_P01_CALLER_UID`） | C1 `/usr/local/bin/xrg-p01-entry-python` |
| `xrg-p01-run` | sudoers 白名单包装（操作员四条） | C2 |
| `xrg-authz-publish` | 授权人独占发布包装（传 SUDO_UID） | C3 |
| `go_gated_supervisor.py` | candidate_supervisor 的 GO 门加性变体（原件未改动）：两阶段 FIFO 读、单帧 `GO <hex64>`、nonce=sha256(confirmed‖gen‖attempt)、只读挂载复核、无 GO ⇒ `SUPERVISION_ABORTED_NO_GO` | C9 |
| `stub-docker.sh` | 夹具 docker：状态机 created/running/exited + outcome.json 归档 + calls.log；旋钮 `XRG_P01_STUB_STATE/START_FAIL/BAD_MOUNTS` | 仅夹具 |
| `stub-runner.sh` | 容器内 UID 10001 仿真 runner：FIFO 两阶段读 + 副本 SHA 复核 + go-gate 收据 | 仅夹具 |
| `local-suite.py` | 十五用例人工夹具验收套件（机器可读 `.suite/SUMMARY.json`；支持 `--only 名[,名…]` 单跑，写 SUMMARY-only.json） | 仅夹具 |
| `go_gated_overlay.py` | 真实链 stage-b 包垫片：把绑定目录注册为包并链接镜像内产品包路径，使监督器相对导入按 v14 语义生效（create 前存在性核验 `supervisor_overlay_missing`） | C11 `/usr/local/lib/xrg-p01/` |
| `probe/probe_real_chain.py` | 收紧项①真实 Docker 候选链验收探针（演练件，见下节） | 仅本机复验 |

## 运行套件（38 或任意非特权 Linux）

```bash
python3 local-suite.py        # 全合成、零真实资源；约 3–4 分钟
```

当前状态：**15/15 PASS**（本轮新增 `root_read_boundary_hardening`、
`argv_grammar_and_isolation`，并把 ⑥(e) 两分支与对照组拆成独立用例）。
覆盖 = v14 §6 关键项映射：

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
| window_e_resync_success_t9a_retry_ok | ⑥(e) 分支一：补同步成功后 T9a 可重试（重试成功 STAGE_B_COMPLETED） |
| window_e_resync_success_consumed_still_refuses | ⑥(e) 分支二：已消费 attempt 补同步成功后仍即时 attempt_consumed |
| control_well_behaved_close_not_penalized | ⑥(e) 对照组：正常收尾不受恢复规则惩罚 |
| window_e_half_record_no_start | ⑥(b) 半记录窗：绝不 rm/stop 未启动候选 |
| root_read_boundary_hardening | 收紧项④：inbox 符号链接成员、admin pins 清单换链、staging 换链 ⇒ 全部 Refused(3)，零半原件 |
| argv_grammar_and_isolation | 收紧项②：sudoers 镜像语法（后缀/64hex pin/旗标形状）越界即 usage 拒且零 docker；正式↔夹具程序模式互斥门 |

## 真实 Docker 候选链（收紧项①实现口径与实测收据）

第三种运行模式 `real_docker_mode()`＝非夹具且显式 `XRG_P01_REAL_CHAIN=1`：
同一程序、同一 sudoers argv、真实 docker CLI；再缺显式
`XRG_P01_SNAPSHOT_HOST` 即拒。生产模式（两者皆无）中 `stage_b_mount_plan`
仍硬抛 `real_stage_b_locked` —— **真实 Stage B 保持锁死**，本链只服务
38 上的合成演练件。身份三参 `XRG_P01_IMAGE_ID`（完整 digest）、
`XRG_P01_IMAGE_REF`（digest 必须等于钉死值，缺失即 `image_ref_missing`）、
`XRG_P01_SNAPSHOT_HOST` 全部落披露收据 `image-identity-disclosure.json`。

关键机制（38 实测固化，部署约束全文见 INSTALL §3c/§3d）：

- **GO 帧不过 bind 面**：daemon 拒绝 FIFO bind 源 ⇒ 容器内 argv 预lude 在
  私有 tmpfs `/gochan` 上建一次性 FIFO，宿主经 `docker exec -i … cat >
  /gochan/go` 写恰好一帧后关闭；两阶段读状态机、nonce 推导与
  DELIVERED.json 审计字节不变；`--network none` 全程保留。
- **lease 文件级绑定 + 宿主原地喂样**：MonitorFeeder truncate+write 保
  inode（rename 会永久遮蔽），样本恰 9 行，间隔 10 s < 25 s 新鲜窗。
- **证据面 create 前整树移交**（`_chown_tree`，run-real.sh chown 义务）。
- **GO 前宿主核验顺序**：四项 cgroup 实读回 → 等 limits.json（nice/ionice
  之后才落盘）→ 进程级 nice==19 ∧ ionice∈{idle,none} 快照（procfs 不可见
  时经 exec 读容器自身 procfs，判定范围限 cmdline 含监督器的进程）→ 全绿
  才投递 GO；任一失败 ⇒ stop+rm+RESOLVED+INVALID_READBACK，GO 永不写出，
  收据 `receipts/priority-audit-<GEN>.json`。

```bash
cd p01-entry && timeout 580 python3 probe/probe_real_chain.py   # 全绿 rc=0
```

演练替换（如实披露）：镜像用 `xiangrugu-rehearsal:p01-local`（非钉死
digest）；worker 用合成 materialize/installed-origin 孪生件（真件依赖
NAS/数据库，本轮禁触）；快照根为合成 leaf。产物：
`.suite/real-chain-probe/PROBE-SUMMARY.json` +
`runtime-root/receipts/`（verify-inbox / stage-a / stage-b /
priority-audit / image-identity-disclosure / entry-journal /
docker-requests）+ `go/gen-*/DELIVERED.json` +
`output/gen-*/{go-gate,monitor,limits,supervision-verdict}.json`。
nonce 链已逐字节核对：宿主 sha256(confirmed‖gen‖attempt) ==
DELIVERED.nonce == 容器 go-gate.nonce；go-gate 的
authorization_copy_sha256 == 发布原件摘要。

## 故障注入（供 MANUAL-ACCEPTANCE-32.md §3）

`XRG_P01_FAULT=HOOK[:PATHFRAG][,…]`，钩子：`consumed_file_fsync`（记录前）、
`consumed_dir_fsync`（记录后 dir-sync，§4f b/e 窗）、`consumed_pre_start`
（记录持久后、start 请求前，§4f c 窗）、`terminal_update`（终态同步未知，
⑥e）、`rename_publish` / `publish_file_fsync` / `publish_parent_fsync`
（发布器三步）、`docker_request@<op>`（请求层崩溃）。

## root 读取边界（收紧项④实现口径）

所有由特权入口读取的“操作员可写/授权人可写”路径统一走
`open_nofollow()`（O_NOFOLLOW + 对已打开 fd 的 S_ISREG 复核）：verify-inbox
的包成员复制与两份清单、publish 的暂存件、宿主门的授权原件与副本确认。
符号链接/fifo/设备一律 `Refused(nofollow_open_failed|not_regular_file)`，
退出码 3。publish 成功后删除并 fsync 暂存目录（消费暂存件），不留可被再
放演的第二份。

## 部署隔离（收紧项②实现口径）

夹具轮使用独立别名 `xrg-p01-fixture-run`（INSTALL §3b，C10）：白名单按程
序名隔离；程序内 `XRG_P01_PROGRAM=fixture ↔ XRG_P01_FIXTURE` 双向互斥门
保证误配即拒（`argv_grammar_and_isolation` 用例证明两个方向）。正式
`xrg-p01-run` 在真实 Docker 链开启前只服务生产模式。

## 已知环境边界（诚实披露）

- 沙箱 umask 可能令 FIFO mode 显示 0644（套件按文档降级并标注）；32 安装
  契约强制 0640，人工验收必测。
- setpriv 探针在无特权沙箱返回 SKIP；同字节读证据由 runner 收据承担。
- 真实 Stage B 永久锁死直至茶香另行授权（代码级，非口头）。
