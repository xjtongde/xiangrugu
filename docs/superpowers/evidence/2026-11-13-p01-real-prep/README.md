# p01 真实只读执行交付包（real-p01-20261113-a｜停在授权前）

> 状态：执行准备完成，静态核验通过；**未执行任何 Stage A/B，等待茶香对绑定任务卡的具名授权**｜as_of 2026-11-13
> **38 人工演练结论（2026-11-14）**：success / fail / wrongpin / hang 四个人工用例全部通过（success 为上轮独立目录单次通过，本轮未重跑）。生产 worker argv 已按总指挥裁决修正为解释器钉定形式：Stage A `python /installed-origin.py /materialize-real.py …`，Stage B `python /installed-origin.py -m xiangrugu_datamgmt.task_control …`（run-real.sh 同步落地）。原始终态收据与逐用例实际 argv 归档于 [`manual-cases-38/SUMMARY.json`](manual-cases-38/SUMMARY.json)；success 原件树缺失已如实记录（不补造、不重跑），见 `manual-cases-38/success/missing-originals.json`。演练脚本 [`rehearsal.py`](rehearsal.py)，机器可读汇总 [`rehearsal-evidence.json`](rehearsal-evidence.json)（`P01_REAL_PREP_REHEARSAL_OK`）。
> 绑定任务卡 SHA-256：`41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69`（验收提交 `5cd428af`，137/137）

本目录把已验收的关闭任务卡接入既有产品执行链，形成可代跑的两段式交付：**Stage A 组装（纯元数据，不挂快照）**与 **Stage B 唯一真实候选（挂载固定快照只读，1800 秒截止）**。所有输入使用收据回传的**已验收字节原样复现**，不重新生成、不改写。

## 卡片范围保持不变（逐项绑定）

POSTED_TO_ADDR_DATA 原 8 列；快照 `2026-10-07-bootstrap`（232 成员全摘要复核＋SQLite 批前后双摘要，逻辑预算 3681959248B）；镜像 `sha256:8f8995689096…`（revision `8fbc8c9…` dirty、10001:10001）；半核（cpu.max 50000/100000）、768MiB、memory-swap=memory（cgroup swap 0）、pids128、network none、只读根/源、cap-drop ALL、no-new-privileges、nice19/ionice idle、单任务串行 flock；候选 1800s／宿主 1830s／传输 1880s。**禁止**：NAS、其他业务表值、PG、冻结、导入、发布、重试、下一分区、放宽预算。一次 attempt，失败即停。

## 两段流程与授权门

```text
authorization.json（茶香授权后由操作员放置于运行根，绑定卡片SHA+attempt）
   │ 缺失或绑定不符 → 两执行模式在创建容器前拒绝（退出 2）
   ▼
Stage A materialize（容器内，无快照挂载）
   installed-origin 验 7 模块 → materialize-real.py：
   卡片字节=41bd0ecf… → 授权文件绑定核验 → 关闭 review 字节=a7c2c5bd… →
   product.materialize_project_partition_request → request/approval/scope/budget
   → materialize-receipt.json；宿主记录 controller-pins.txt（外部固定三 pin）
   ▼
操作员独立核对三 pin（对照 Stage A 收据），作为命令行外部输入进入 Stage B
   ▼
Stage B real-readonly（容器内，快照 /data/imports/usedata 只读挂载）
   supervisor --seconds 1800 --authorized-source-mode project_snapshot
   + request/controller/worker 三方 pin 交叉 → task_control.execute_controlled_batch
   成功 = CONTROLLED_SOURCE_ONLY_TASK_STAGED + batch.staged.json（file_digest_passes=2）
   超时/失败 = 有界停止 + failure-report/worker-failure 关联；attempt 即消耗，绝不重启
```

产品语义依据（源码逐行核对）：`task_control.execute_controlled_batch` 文档明确"digest pins 与 approval JSON 都不能证明人类授权；选择权属于被授权的操作员"——所以人类授权门在本交付的运行器与 Stage A worker 中实现（双层：宿主检查＋容器内再验证）。`readonly_batch` 强制 output/scratch 位于证据根且非快照路径、批结果仅 STAGED 不 Publish。

## 防坑设计

- **B-23**：每轮全新 `$run/output`；已验收输出以 `cp -a` 复现进可写 `/data/var/run`，先复核关键 SHA 再启动；durable 目录预建并 chown 10001。
- **CRLF**：staging 逐文件对 `packet-inputs-real.sha256`（48 项，2026-11-14 重生成）字节门；controller 脚本用证据树 LF 副本。
- **pin 外部性**：Stage B 三 pin 来自 Windows 命令行参数（操作员从 controller-pins.txt 审阅后传入），运行器不从 request 文件学习 pin；roots pin 硬绑 `6235c356…`。
- **心跳/回收**：与已验收 run-review.sh 同一协议（tick 初始心跳、≤2s 续期、EOF/空闲 15s、租约 10s 采样、精确名 stop→kill→rm、removal.txt）。
- **一次 attempt**：运行器无任何自动重试路径；Stage B 非零退出传播给传输层并保留全部现场。

## 文件

| 文件 | 职责 |
|---|---|
| `materialize-real.py` | Stage A 容器 worker：卡片/授权/review 三重字节门 → 产品 materialize → 收据 |
| `run-real.sh` | 32 宿主运行器：refuse-no-authorization / materialize / real-readonly |
| `verify-real.sh` | 32 宿主原生复核，独占发布 verification-real.json |
| `stage-real.ps1` / `invoke-real.ps1` | Windows staging 字节门（三模式：默认传输只读消费权威清单；`-LocalOnly` 仅本地校验；`-RegeneratePins` 独立重钉，本机专用校验步骤仅在本地保留，不作为 clone 后的项目依赖）/ SSH 传输（real 模式传输截止 1880s） |
| `packet-inputs-real.sha256` / `packet-files-real.txt` | 48 项权威清单（含 stage-a-inputs.tsv、verify-mount-table.py、verify-terminal.py） |
| `stage-a-inputs.tsv` | Stage A/B 全部绑定路径的 sha↔容器路径↔staged 路径闭包表 |
| `verify-mount-table.py` / `verify-terminal.py` | 挂载闭包复核 / Stage B 终态收据复核（38 演练已跑通） |
| `rehearsal.py` / `rehearsal-evidence.json` | 38 人工演练脚本与机器可读汇总（四用例） |
| `manual-cases-38/` | 四用例原始终态收据 + 实际 worker argv + success 缺件记录 |
| `authorization.template.json` | 授权文件模板（canonical 键序；放置与否由茶香决定，本包不含已生效授权） |
| `RUNBOOK-REAL.md` | 逐条命令、预期结果、收据路径 |
| `ACCESS-32.md` | 32 登录方案与权限裁决材料（**方案 A/C 已被茶香明令禁止，仅作现状记录；以 ADMIN-STEPS-32.md 为准**） |
| `p01-entry/` | **v14 最小权限入口实现轮交付物**：固定入口程序＋sudoers 包装＋GO 门 supervisor 变体＋夹具 stub docker/runner＋九用例人工夹具套件（当前 9/9 PASS，机器可读 `.suite/SUMMARY.json`），见其 [README](p01-entry/README.md) |
| `INSTALL-CHANGES-32.md` | 32 安装变更清单：逐项路径/属主/mode、安装前状态核对、sudoers 片段＋visudo 校验、逐项回退依据 |
| `MANUAL-ACCEPTANCE-32.md` | 32 人工夹具验收手册：正常路径→四项关键行为→⑥收尾窗口→人工资源清理；失败即保留现场停在验收阶段 |
| `ADMIN-STEPS-32.md` | 管理员最少步骤 ＋ DSH 后续必备权限最小集（单独裁决单；不申请 root SSH 密钥/其他凭据/Codex 代跑） |

## 待裁决

- **32 最小权限执行入口 v14**：静态定稿（`20d8219`）后进入实现轮——实现与夹具验收套件已在 `p01-entry/`（9/9 PASS），32 侧部署与人工验收按 INSTALL/MANUAL/ADMIN 三件文档待管理员执行。**尚未登录 32、未实施任何 32 变更**。上一轮（v14 定稿轮）改动：§4g.3/.4、验收 ⑥ 与本指针：RESOLVED 发布定式＝root 独占临时件一次写齐最终内容＋属主/mode＋published 尾标 → 文件 fsync → 原子 rename → 父目录 fsync，双同步后不再改尾标。重入判定改为**一条不推断上一进程退出方式**的规则：新入口持 B 锁检查同一代次的 RESOLVED 与该路径要求的终态/refusals/Stage A 收据——缺失、损坏或绑定不一致即 `recovery_pending` 交恢复补齐；记录齐全也须重新确认候选状态（exited|dead|404）并对所需文件与父目录各补一次幂等 fsync；核实或同步失败保持阻断；全部成功后才按原有消费/重试规则决定去留。验收 ⑥ 扩为五窗，新增 (e)"所有记录均已可见、最后一次同步结果未知"：注入补同步失败断言零新增 create/start，补同步成功后 T9a 拒绝径才可重试、已消费 attempt 仍拒，另设正常收尾对照证明重入规则不惩罚善终。见 [PROPOSAL-32-minimal-entry.md](PROPOSAL-32-minimal-entry.md)（未实施、未登录 32）。
- 其余见 [ACCESS-32.md](ACCESS-32.md) 与 RUNBOOK-REAL「授权」节。本包完成后停在授权前：未放置 authorization.json，未创建运行根，未启动任何 Stage A/B 容器。
