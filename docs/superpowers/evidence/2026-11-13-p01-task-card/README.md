# p01 新 runtime 一次真实只读任务卡（关闭权限，待代跑核验与授权）

> 状态：**验收完成（独立复核 137/137 通过），停在真实读取授权前**｜as_of 2026-11-13
> 分支：`dsh/p01-taskcard-20261113`（基于交接提交 `2fde319`，按本次授权不提交不推送）
> 收据：Gitea 分支 `codex/p01-card-receipts-20261113` 提交 `5cd428af8d615b30e399c40c980edc5870c94709`

本目录为 `POSTED_TO_ADDR_DATA` 原 8 列准备一张新的 p01 **关闭权限**任务卡，绑定 2026-11-13 已验证的新 runtime 镜像、固定快照身份、读取范围、资源上限和停止条件，并在 32 上做纯元数据核验与缺授权拒绝验证。本次授权只涵盖任务卡准备和纯元数据核验；**不挂载/读取真实快照与 NAS，不连接数据库，不冻结、不导入、不替换常驻服务、不晋级镜像别名、不提交、不推送**。历史 p01 授权（11-08 b、11-09 c）已用完。

任务卡原件 `task-card.closed.json` 由 32 上的元数据运行从生成文档确定性组装（`prepare-closed-review.py`），已随收据回传并通过 DSH 独立重算验收；原件位于收据目录 `../2026-11-13-p01-task-card-receipts/returned/p01-card-metadata/output/task-card.closed.json`（顶层副本逐字节相同），本目录不另存副本、不手抄摘要。

## 固定任务卡

| 项目 | 固定范围 |
|---|---|
| 分区/唯一表 | large-p01 / POSTED_TO_ADDR_DATA，原 8 列 |
| 新 attempt | `real-p01-20261113-a`，只尝试一次 |
| 已有固定快照 | `2026-10-07-bootstrap`（232 成员＝189 文件/43 目录） |
| 快照 manifest | `03174f42f62dbea16402cdcbd05aa132a0a478453d7f31a09127374835f14699` |
| 源相对路径 | `harvard/cbdb/cbdb_20260919.sqlite3` |
| 源身份 | 586485760 字节，`bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400` |
| runtime 镜像 | `xiangrugu:runtime-request-reader-20261113-a` |
| runtime ID | `sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a` |
| Git 基线 | `8fbc8c97fcf1d818caddf6ab556fa82d986643ed`（dirty，与镜像标签一致） |
| 父级 review | `sqlite-value-project-partition-readiness.closed.json` `edf31997…046692e` |
| roots pin | `6235c356fca754a687a2f02998770c9609b20748ade674d0050d86a0a428e07c` |
| 证书 pin | `58cb2e50f2124829130d4a9d6b8e55b8f6b2418bca18458685cb5d16ff193f9a` |
| 新关闭 review 摘要 | `a7c2c5bdb69a17e8c6038065f16eff378b81f443bdc486a8af1a2b014630c93d` |
| 任务卡 SHA-256 | `41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69` |

8 列：`c_posting_id`、`c_personid`、`c_office_id`、`c_addr_id`、`c_created_by`、`c_created_date`、`c_modified_by`、`c_modified_date`。对象 ID `1650019e…63bc52ac`，schema_hash `a9420643…e0bb08`，rule_id `m007906`。源身份来自已验收仓库元数据（证书与父级 review 双重 pin），本次准备未重新读源；执行时必须重新核验。`expected_count`/`expected_sha256` 均为 null。

## 批准后的范围（本次不执行）

获得茶香对新 attempt 的明确授权后，执行链才允许：无快照挂载地 materialize 本次 request/approval；控制端独立固定 request/approval/roots 三原始 pin（approval 内部 request 摘要依既有协议剔除 approval_file/approval_sha256）；随后只读 roots 指定的项目版本快照，复核全部 232 成员及文件摘要，并对 SQLite 做批前后两次摘要；业务值仅读本表。全快照摘要会读取其他成员字节用于哈希，不查询其他业务表的值，不读 NAS。逻辑摘要预算 **3681959248 字节（约 3.43GiB）**＝189 文件尺寸和 2508987728 ＋ 2×586485760（批前后双摘要），不能省略摘要以赶时间。

## 资源、截止与停止条件

与 b/c 任务逐字段一致：半核（0.5 CPU）、768MiB、memory-swap=memory（cgroup swap 0）、单 worker 串行、nice19/ionice idle、pids128、network none、只读根/源、cap-drop ALL、no-new-privileges；候选 1800 秒、宿主 1830 秒、传输 1880 秒（本次元数据核验运行用 300/330/380 秒，真实候选截止未激活，`real_mode_activated=false`）。规范流 256MiB、应用临时 1GiB、chunk 2MiB/4096 行、fan-in 16/最多 1024 文件。应用总账不是文件系统硬配额，也没有硬 IO 带宽隔离。

停止门：候选/宿主/传输截止、操作员取消、request 字节变化、只读挂载丢失、心跳非法/EOF/空闲 15 秒、租约丢失/非法 25 秒、服务不健康或状态变化、内存/磁盘/负载/IO/内存压力/交换门、worker 退出或孤儿、启动前 cgroup 限额不合格。共享 flock 保证 32 上单任务串行。

## 授权协议与待裁决

- 关闭态四权限全 false；不存在可执行 request/approval，包内**没有任何 materialize 调用路径**。
- 缺授权拒绝双层验证：宿主门（`reject-no-authorization` 模式，预期退出 2，无候选、无 materialize 目录）＋产品门（安装态 `task_control` 默认 artificial 模式对 project_snapshot 模板必须报 `real_execution_closed`）。
- 未来真实执行前，`authorization.json` 必须绑定任务卡 SHA-256 与 attempt_id，经茶香明确授权；建议确认语句：**批准 real-p01-20261113-a 按本任务卡进行一次真实只读尝试，包括全快照摘要复核；失败即停，不重试、不接数据库。**
- 仅完整批及独立核验都通过，才新增本表源侧期望，最多 69/78。失败或取消即保存证据、停止并回收本轮精确候选，不自动重试、换 attempt 或下一表，不输出原始值。任何数据库写入前仍须另行通知并确认 pg32b 旧数据处置。

## 风险声明

真实 p01 两次尝试（11-08 b、11-09 c）均在原 1800 秒截止超时，未形成完整批。11-13 人工 465284 行整批 1338.41 秒通过、黄金/双文件摘要一致，**只证明人工候选通过**：人工样本快照规模与值分布与真实任务有差异，计时开销未单独校准，真实吞吐未证明。不因超时提高预算，不把人工改善当真实重试的充分依据。

## 准备与核验（代跑后回填）

本地已完成：交接三件套与最新证据阅读；父级 review 14 项绑定 pin、roots、证书、7 个安装模块与 11-13 构建输入逐项吻合；逻辑摘要预算推导核对。32 侧纯元数据核验（metadata/product-gate/reject 三运行＋原生 verify）由 Windows/Codex 侧按当时的本机代跑步骤执行（Windows 专用 runbook 现仅本机保留，不作为共享依赖），收据回传后在此回填摘要与结论。

第二轮（验收准备）：修复 `invoke-review.ps1` 默认 `source-green-v1` 被自身校验正则拒绝的缺陷（14 组用例静态验证；代跑侧证实该缺陷真实发生并在其 Windows 副本同样处置）；6 份非 `-text` staging 输入的字节差异与来源见 [input-byte-diff-analysis.md](input-byte-diff-analysis.md)。

第三轮（验收完成）：收据提交 `5cd428af` 同步核验（父提交＝交接 `2fde319`，仅新增 3 文件，提取字节与提交树逐项一致）；外层 SHA `5adc58c1…`、内层归档摘要均通过。DSH 独立验收 **137/137 通过**（[acceptance-check.py](acceptance-check.py) → [acceptance-check.json](acceptance-check.json)），全部摘要从原始字节重算：

- 任务卡 `41bd0ecf…` 与关闭 review `a7c2c5bd…` 重算一致，并在 card-receipt、verification.json、拒绝收据、卡片绑定间交叉吻合；8 列 column_key 与父级权威绑定逐项一致。
- 镜像身份三运行一致：`sha256:8f8995689096…` ＋ revision `8fbc8c9…` ＋ 10001:10001 ＋ dirty。
- 资源：两容器运行 HostConfig（0.5CPU/768MiB/swap=memory/pids128/network none/只读根/CapDrop ALL/no-new-privileges）与 cgroup 实测（cpu.max `50000 100000`、memory.swap.max `0`、nice19/ionice idle）全吻合；无 NAS 挂载。
- 两道拒绝：宿主门退出 2（`refused_before_materialize:true`，无授权/无可执行件/无候选容器）；产品门 `real_execution_closed`（默认 artificial 模式，无 batch/request/approval 生成）。
- 候选回收：两容器 exited 0、无 OOM、按精确名回收（`xiangrugu-evidence-p01-card-metadata`/`-product-gate`），进程组消失，`removed_candidates=2`；全包无 batch.json/approval.json/authorization.json/可执行 request。
- 边界：服务前后一致且健康、boot_id 一致、pswpout 0、dev 空闲、ext4 非 NAS；未读源、未接 PG、未冻结、授权未消耗；覆盖仍 68/78、Task8 未完。
- 环境事实：32 locale zh_CN（packet-check 输出"成功"）；`.incomplete` 为产品 no-clobber 发布协议保留的硬链接副本（与终件逐字节相同）；SSH .log 为空属设计（输出在运行目录，传输退出 0/0/2 记录于 controller JSONL）。

## 本目录文件

| 文件 | 职责 |
|---|---|
| `prepare-closed-review.py` | 容器内元数据准备：父 10 表 235 列校验→p01 投影→关闭 review→关闭任务卡 |
| `product-gate-probe.py` | 容器内产品门探针：无授权必须 real_execution_closed |
| `run-review.sh` | 32 宿主运行器：metadata / product-gate / reject-no-authorization |
| `verify.sh` | 32 宿主原生核验，独占发布 verification.json |
| `stage-review.ps1` | Windows staging：25 文件字节级 pin 校验→独占远端根→32 复核 |
| `invoke-review.ps1` | Windows SSH 传输：心跳/截止/传输证据 |
| `controller-evidence.sh`、`controller-heartbeat.sh` | scripts/ 原件的字节相同 LF 副本（evidence 树 -text，防 Windows CRLF） |
| `packet-inputs.sha256`、`packet-files.txt` | 权威 staging 清单（25 文件） |
| `input-byte-diff-analysis.md` | 6 份非 -text 输入文件的 LF/CRLF 字节差异与来源记录（实测/推断分记） |
| `acceptance-check.py`、`acceptance-check.json` | DSH 独立验收脚本与 137 项结果（可复现） |
| `RUNBOOK.md` | 逐条代跑命令、预期结果、收据路径 |
| `progress.md` | 准备与代跑进度账 |

## 编辑位置说明

项目约定 Windows 为编辑入口；本次按用户明确指令在 DSH Linux 工作区（用户指定为本项目工作目录）准备材料，Windows 仅承担 staging/传输与代跑，不在 Windows 运行项目代码。该适配已在本轮指令范围内；如需回写 AGENTS.md/codemap 的入口表述，另获授权。
