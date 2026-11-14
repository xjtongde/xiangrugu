# RUNBOOK-REAL —— p01 真实只读执行（real-p01-20261113-a）

> 每条命令标注运行侧：**[Windows PowerShell]** 或 **[32 Linux shell]**（经 Windows ssh 发起）。
> 常量：`ROOT=/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a`；
> `IMAGE=sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a`；
> 卡片 SHA `41bd0ecf…`；review SHA `a7c2c5bd…`；roots `6235c356…`。
> **Stage B 是一次性 attempt：启动过一次后，无论结果如何都不得再次启动。**
>
> **38 人工演练（2026-11-14）**：success/fail/wrongpin/hang 四用例全部通过；worker argv 已修正为
`python /installed-origin.py …` 解释器钉定形式（本 RUNBOOK 引用的 run-real.sh 已同步）。收据见
`manual-cases-38/`。详见 README 顶部结论与 `rehearsal-evidence.json`。

## 步骤 R0：无授权拒绝验证 [Windows PowerShell]（现在即可安全执行，无需茶香授权）

```powershell
cd docs\superpowers\evidence\2026-11-13-p01-real-prep
powershell -ExecutionPolicy Bypass -File stage-real.ps1        # 预期 "Staged 48 …"，远端 packet-real-check.txt 48/48
powershell -ExecutionPolicy Bypass -File invoke-real.ps1 -ImageId $IMAGE -RunSuffix real-refuse-noauth -Mode refuse -LocalLog refuse.log
```

预期：退出 **2（设计使然）**；`ROOT/real-refuse-noauth/refusal-receipt.json` `refused_before_materialize:true`、可执行件 0、materialization 目录 0、候选容器 false。此步证明：授权缺失时 Stage A/B 都无法启动。

## 步骤 R1：茶香授权 → 放置 authorization.json [操作员在 32]

仅当茶香对本卡明确回复授权（建议语句见任务卡 README），按 `authorization.template.json` 生成并放置：

```bash
# [32 Linux shell] 独占创建，绑定校验由运行器执行
install -m 600 /dev/null ROOT/authorization.json   # 然后一次性写入 canonical JSON（键序同模板）
```

字段硬性要求：version=1、status=AUTHORIZED_REAL_P01_SINGLE_ATTEMPT、attempt_id=real-p01-20261113-a、task_card_sha256=41bd0ecf…、one_attempt_only=true、granted_by 非空。任何偏差＝未授权，运行器拒绝。

## 步骤 R2：Stage A 组装 [Windows PowerShell]

```powershell
powershell -ExecutionPolicy Bypass -File invoke-real.ps1 -ImageId $IMAGE -RunSuffix real-materialize-a -Mode materialize -LocalLog materialize.log
```

预期：退出 0；worker.log 含 `MATERIALIZE_REAL_REQUEST_OK`；`ROOT/real-materialize-a/controller-pins.txt` 五行摘要（request/approval/scope/budget/receipt）。容器**无快照挂载**——本步不读任何源字节。收据：`ROOT/real-materialize-a/output/durable/materialization/{request,approval,scope,budget}.json + materialize-receipt.json`。

## 步骤 R3：三 pin 独立审阅 [Windows PowerShell]

```powershell
ssh root@192.168.3.32 "cat ROOT/real-materialize-a/controller-pins.txt; sha256sum ROOT/real-materialize-a/output/durable/materialization/request.json"
```

人工比对 request.json 内容对卡片：source_mode=project_snapshot、lifecycle_seconds=1800、snapshot/member/manifest/rule/image/revision 逐项一致、output/scratch_parent 位于证据根。记录 request/approval 两 pin 供下一步外部传入。

## 步骤 R4：Stage B 唯一真实候选 [Windows PowerShell]

```powershell
powershell -ExecutionPolicy Bypass -File invoke-real.ps1 -ImageId $IMAGE -RunSuffix real-candidate-b1 -Mode real `
  -MaterializeSuffix real-materialize-a -RequestPin <R3审阅的request摘要> -ApprovalPin <approval摘要> -LocalLog real.log
```

传输截止 1880s；候选 1800s／宿主 1830s。两种合法终态：
- **成功**：退出 0，worker.log `CONTROLLED_SOURCE_ONLY_TASK_STAGED`，`output/durable/executions/real-p01-20261113-a/batch.staged.json`（file_digest_passes=2、manifest 复核通过）。仍**不是**导入依据——发布另授权。
- **有界停止**（超时/取消/门触发）：非零退出＋`failure-report.json`/`worker-failure.json` 关联完整。**attempt 已消耗：不重试、不换 attempt、不下一表、不放宽预算**，直接进 R5/R6 收尾回报。

## 步骤 R5：原生复核 [32 Linux shell]

```powershell
ssh root@192.168.3.32 "bash ROOT/source-green-v1/docs/superpowers/evidence/2026-11-13-p01-real-prep/verify-real.sh ROOT real-refuse-noauth real-materialize-a real-candidate-b1"
```

预期退出 0：`P01_REAL_STAGED_VERIFIED` 或 `P01_REAL_STOPPED_VERIFIED`（证据链完整）；任一不符 `P01_REAL_READONLY_VERIFICATION_FAILED` 退出非 0，保留现场。核验覆盖：三 pin 外部固定吻合、卡片绑定、资源逐字段、双摘要、回收、服务/boot/交换/NAS、边界旗标。

## 步骤 R6：收据回传 [Windows PowerShell]

```powershell
ssh root@192.168.3.32 "set -e; cd ROOT; tar -czf p01-real-receipts.tar.gz real-refuse-noauth real-materialize-a real-candidate-b1 verification-real.json packet-real-check.txt"
scp -O root@192.168.3.32:ROOT/p01-real-receipts.tar.gz .
Get-FileHash p01-real-receipts.tar.gz | Format-List
```

连同三个 `.log.controller.jsonl` 交 DSH 复核、回填、呈总指挥。

## 失败处理与独占性

- 串行 flock＋dev 空闲门不变；任何非预期退出：停止后续步骤、保留全部现场、回报，不按前缀清理。
- `packet-real/`、`packet-real.tar.gz`、`ROOT`、各 run 目录、`verification-real.json`、`authorization.json` 均独占创建；重跑同名后缀必然失败即停。
- 覆盖包/Gitea 交付走项目授权提交；本 RUNBOOK 不含任何数据库连接或发布步骤。