# RUNBOOK —— p01 新任务卡纯元数据核验（Windows/Codex 代跑）

> 每条命令标注运行侧：**[Windows PowerShell]** 或 **[32 Linux shell]**（后者一律经 Windows 的 ssh 发起，项目命令实际在 32 执行）。
> 全程串行；不挂载/读取真实快照与 NAS；不连接数据库；不冻结/导入；不替换常驻服务/晋级别名；不提交/推送。
> 本包没有 materialize 调用路径，无法启动真实候选。

常量：

```text
ROOT     = /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113
EVIDENCE = docs/superpowers/evidence/2026-11-13-p01-task-card
IMAGE    = sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a
REVISION = 8fbc8c97fcf1d818caddf6ab556fa82d986643ed
HANDOFF  = 2fde319cb7e00d9cc6efb807aae3de44c55a6465
```

## 步骤 0：基线与材料覆盖 [Windows PowerShell]

在 Windows 仓库根目录（`C:\Users\zkyxy\Documents\codex-xiangrugu`）：

```powershell
git fetch origin
git status --porcelain   # 必须为空；有未提交改动先处置
git checkout -b codex/p01-proxy-20261113 2fde319cb7e00d9cc6efb807aae3de44c55a6465
git rev-parse HEAD       # 必须 = HANDOFF；main 与交接分支保持不动
```

把 DSH 交付的 `p01-task-card-overlay.tar.gz` 与 `overlay.sha256` 放到仓库根目录，然后：

```powershell
if (Test-Path docs/superpowers/evidence/2026-11-13-p01-task-card) { throw '证据目录已存在，停止' }
tar -xzf p01-task-card-overlay.tar.gz
foreach ($line in Get-Content overlay.sha256) {
  if (-not $line) { continue }
  $parts = $line -split '  ', 2
  $actual = (Get-FileHash -LiteralPath $parts[1]).Hash.ToLowerInvariant()
  if ($actual -cne $parts[0]) { throw "Overlay 字节不符: $($parts[1])" }
}
Write-Output 'Overlay verified'
```

预期：`Overlay verified`。覆盖包只新增本证据目录，不改任何已有文件。

## 步骤 1：staging [Windows PowerShell]

```powershell
cd docs\superpowers\evidence\2026-11-13-p01-task-card
powershell -ExecutionPolicy Bypass -File stage-review.ps1
```

预期输出：`Staged 25 metadata/tool files. No source snapshot or installed product override.`

- 本地：`packet-files.txt`（25 行）、`packet.tar.gz`；每个 staged 字节先对 `packet-inputs.sha256` 校验，任何 CRLF/漂移在离开 Windows 前失败。
- 远端收据：`ROOT/packet-check.txt`（25 行 OK）、`ROOT/source-green-v1/INPUTS.sha256`；远端 `bash -n` 通过。
- 若报 `Staged byte mismatch`：`git config core.autocrlf` 必须为 `false`；改正后 `git checkout -f HEAD -- datamgmt scripts docs` 刷新工作树，删除本地 `packet/` 与 `packet.tar.gz` 后重试（远端根若已建，须先经授权清理，见文末）。

## 步骤 2：metadata 运行 [Windows PowerShell]

```powershell
powershell -ExecutionPolicy Bypass -File invoke-review.ps1 `
  -ImageId sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a `
  -RunSuffix p01-card-metadata -Mode metadata -LocalLog metadata.log
```

预期：远端退出 **0**；`metadata.log` 末行含 `CLOSED_REAL_PARTITION_REVIEW_AND_CARD_PREPARED` 与 `task_card_sha256`。容器内完成：父 10 表 235 列校验→p01 八列投影→关闭 review（missing=[]，四权限 false）→关闭任务卡。无快照挂载、无源字节、无 approval。

收据（32）：`ROOT/p01-card-metadata/` 下 `output/review/review.json`、`output/review/descriptor.review.json`、`output/review/request.review.json`、`output/task-card.closed.json`、`output/card-receipt.json`、`output/metadata-only-receipt.json`、`output/installed-origin.json`（7 模块）、`output/monitor.json`、`output/limits.json`、`worker.log`、`host-config.json`、`container-state.json`、`exit-code.txt`、`removal.txt`、`controller-events.jsonl`、`host-samples.txt`、`image-identity.txt`、`deadlines.txt`、`services-before.txt`、`services-after.txt`、`boot-id.txt`。

## 步骤 3：product-gate 运行 [Windows PowerShell]

```powershell
powershell -ExecutionPolicy Bypass -File invoke-review.ps1 `
  -ImageId sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a `
  -RunSuffix p01-card-product-gate -Mode product-gate -MetadataSuffix p01-card-metadata `
  -LocalLog product-gate.log
```

预期：远端退出 **0**；`product-gate.log` 含 `PRODUCT_GATE_REFUSED_AS_EXPECTED`、`real_execution_closed`。安装态 task_control 在无真实读取授权（默认 artificial 模式）下拒绝 project_snapshot 关闭模板，且拒绝发生在 approval pin 比较之前；无 batch.json、无可执行 request/approval。

收据（32）：`ROOT/p01-card-product-gate/output/product-gate-receipt.json` 及与步骤 2 同构的运行收据；`request-template.sha256`。

## 步骤 4：缺授权拒绝运行 [Windows PowerShell]

```powershell
powershell -ExecutionPolicy Bypass -File invoke-review.ps1 `
  -ImageId sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a `
  -RunSuffix p01-card-reject-noauth -Mode reject-no-authorization -MetadataSuffix p01-card-metadata `
  -LocalLog reject-noauth.log
```

预期：远端退出 **2（设计使然的拒绝，不是故障）**。宿主门确认：无 authorization、无 request.json/approval.json/scope.json/budget.json、无 executions 目录、无真实候选容器；本模式不创建任何容器。

收据（32）：`ROOT/p01-card-reject-noauth/rejection-receipt.json`（`refused_before_materialize:true`、`task_card_sha256` 绑定）、`exit-code.txt`（2）、`controller-events.jsonl`、`services-before/after.txt`、`boot-id.txt`。

## 步骤 5：原生核验 [32 Linux shell，经 Windows ssh]

```powershell
ssh -o BatchMode=yes root@192.168.3.32 "bash /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113/source-green-v1/docs/superpowers/evidence/2026-11-13-p01-task-card/verify.sh /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113 p01-card-metadata p01-card-product-gate p01-card-reject-noauth"
```

预期：退出 **0**，输出 `verification: P01_TASK_CARD_METADATA_VERIFIED_CLOSED`；独占发布 `ROOT/verification.json`。核验覆盖：镜像身份（docker inspect）、两容器运行的 0.5CPU/768MiB/swap0/pids128/network none/只读根/cap-drop/no-new-privileges、cgroup 限额与 nice19/ionice idle、监督完成态、7 安装模块摘要对 11-13 构建输入、关闭 review/任务卡、拒绝收据＋活体复查、服务前后一致、boot_id/pswpout/内存/负载/磁盘/dev 空闲、文件系统非 NAS、无 batch.json、候选精确回收。任何一项失败→状态 `P01_TASK_CARD_VERIFICATION_FAILED` 并退出非 0，保留现场回报。

## 步骤 6：收据回传 [Windows PowerShell]

```powershell
ssh -o BatchMode=yes root@192.168.3.32 "set -e; cd /opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113; tar -czf p01-card-receipts.tar.gz p01-card-metadata p01-card-product-gate p01-card-reject-noauth verification.json packet-check.txt"
scp -O root@192.168.3.32:/opt/mydocker/xiangrugu/data/var/batch-runner-p01-task-card-20261113/p01-card-receipts.tar.gz .
Get-FileHash p01-card-receipts.tar.gz | Format-List
```

回传给 DSH：`p01-card-receipts.tar.gz` ＋ 其 SHA-256 ＋ `metadata.log`、`product-gate.log`、`reject-noauth.log` 及三个 `.controller.jsonl`。DSH 复核后回填任务卡 SHA-256 与核验结论，汇总交总指挥，由茶香裁决是否放行一次真实只读及全快照摘要复核。

## 边界与失败处理

- 串行：共享 `sqlite-synthetic-batch.lock` flock；同一时刻只允许一个运行。步骤 2–4 必须依次执行。
- dev 空闲门：运行前要求 `xiangrugu-dev` 空闲（最多等约 60 秒）；不满足则退出 1，稍后重试，不触碰常驻服务。
- 心跳：invoke 每 ≤2 秒发 `tick`；传输截止 380 秒；心跳非法/EOF/空闲会触发远端精确停止。
- 独占性：本地 `packet/`、`packet.tar.gz`、远端 `ROOT`、各 run 目录、`verification.json` 均独占创建。**失败重试前不得按前缀批量清理**；确需清理时逐路径经用户授权后删除。
- 任何步骤出现非预期退出：保留全部现场与收据，停止后续步骤，回报 DSH；不自动重试、不放宽资源、不省略摘要。
- 本包不读取真实快照：`/metadata` 只含仓库元数据；product-gate 只读关闭模板；reject 模式只做宿主元数据检查。快照根仅做 findmnt/存在性元数据检查，不读内容。