# 提案 v3.1（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（替代 v2/8f351fa）。本轮及既往各轮均未登录或修改
> 32；真实任务卡 `real-p01-20261113-a` 保持 CLOSED。落地须先获总指挥批准。
> v2 复核意见的落实点：①操作员上传区与运行输入/授权/登记/原始收据物理分离；
> ②固定入口只消费操作员不可替换的已核验副本；③宿主授权门+容器授权门双保留；
> ④挂载与 cgroup 核验相对源读取的时序写死；⑤镜像身份沿用已验收 `.Id` 口径；
> ⑥补输入替换/未授权/重复启动三项验收条件。
> **v3.1（本 revision，回应 caa1a13 复核）**：新增 §4b 端到端时序表——逐步标明
> 写入者、可信清单来源、占锁/消耗 attempt 时点与 worker 放行步骤；明确 Stage A
> 成功后首次 Stage B 必可运行、预检拒绝不消耗名额、并发/重复 Stage B 只放行一次；
> 授权由有授权权的人独占放置；可读源仅在容器核验完成后，挂载限定任务卡指定的
> 快照版本目录。｜as_of 2026-11-14

## 1. 硬约束（继承 v2，不变）

1. 操作账号 `xrgp01op` **不入 docker 组、不触 `/var/run/docker.sock`**，无任何可
   间接调用容器运行时的 sudo 条目。
2. 容器启动能力只存在于管理员安装的**固定任务入口**
   `/usr/local/bin/xrg-p01-run`（sudoers 白名单钉到完整 argv，仅
   `stage-a` / `stage-b` 两个子命令）。
3. 真实执行的独立授权门不被入口旁路（见 §3 双门）。

## 2. 目录分区：上传区与运行区分离

```text
/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a/
├── inbox/                     ← 操作员唯一可写区（staging 上传落点）
│   └── source-green-v1/…      （48 项包 + INPUTS.sha256）
├── run-input/                 ← 管理员核验区：root:root 0755，xrgp01op 无写权
│   ├── source-green-v1/       （由入口以 root 从 inbox 复制并 sha256sum -c 后固化）
│   └── VERIFIED.sha256        （核验收据，含核验时间）
├── authorization.json         ← 操作员独占创建(install -m 600)，入口只读挂载
├── registry/                  ← 单次 attempt 登记（O_EXCL，root 属主）
└── output/                    ← 原始收据树（monitor/batch/failure-report/心跳/
                                 worker-output），容器 uid 10001 写入；
                                 操作员仅可读（ACL r-x），不可写、不可删
```

要点：
- **固定入口只使用 `run-input/` 内经核验且操作员无法替换的副本**。流程：操作员
  传包进 `inbox/` → 触发 `xrg-p01-run verify-inbox`（第三条 sudo 白名单，纯本地
  校验）→ 入口以 root 把 inbox 整树复制到 run-input、逐字节跑权威 INPUTS 清单、
  核对卡片/review/roots 三 SHA，全部通过才写 `VERIFIED.sha256` 并把 run-input
  chown root:root 0755（此后 xrgp01op 对该树零写权）。stage-a/stage-b 一律只认
  run-input，绝不回读 inbox。
- 原始收据只在 `output/`：容器写、操作员读；入口不提供任何删除/改写收据的子命令。

## 3. 双授权门（都保留，语义不同）

| 门 | 位置 | 校验内容 | 失败行为 |
|---|---|---|---|
| 宿主门 | `xrg-p01-run stage-b` 启动前（root） | `authorization.json` 存在、mode 600、属主合法、JSON 键 status/attempt_id/task_card_sha256/one_attempt_only/granted_by 逐项等值 | 拒启，不创建容器，不消耗登记 |
| 容器门 | worker 容器内第一步（uid 10001，ro 挂载该文件） | 同文件再验字节 + 绑定卡片 SHA（现 RUNBOOK 既有逻辑，不改） | 退出 2（设计使然），早于任何源读取 |

宿主门防"误触发起容器"，容器门防"入口被绕过/篡改后仍守授权"——两门独立失效。

## 4. 固定入口启动前核验时序（写死；全部先于任何源读取）

顺序即安全属性，编号步骤之间不得插入其他动作（逐步责任与放行动作见 §4b 时序表）：

1. **attempt/常量绑定**：argv 仅 `verify-inbox|stage-a|stage-b`；attempt id、路径、
   超时为脚本常量。
2. **登记预占**：`registry/<attempt>.lock` O_EXCL 创建（已存在 → 立即拒绝，
   对应"重复启动"验收 R3）。
3. **run-input 完整性**：对 run-input 重放 `sha256sum -c VERIFIED.sha256` 引用的
   权威清单 + 三 SHA（卡片 `41bd0ecf…`、review `a7c2c5bd…`、roots `6235c356…`）。
4. **镜像身份（沿用已验收口径）**：`docker image inspect --format '{{.Id}}'` 必须
   逐字等于交付包收据中记录的镜像 `.Id`
   `sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a`
   ——与 materialize/演练收据链同源（controller-pins.txt、batch 记录均按 .Id
   钉定）。本提案**不引入 RepoDigests 口径**；若总指挥要求仓库摘要，须另行在
   registry 侧核实后再修订本节，当前视为未验证信息。
5. **挂载计划生成与自检**：入口内部拼装 docker 命令行（快照源固定
   `/mnt/wd61workmetadata/usedata` ro bind → `/data/imports/usedata/<SNAPSHOT_ID>`；
   run-input ro、output rw、authorization ro、其余全 ro；read-only rootfs、
   cap-drop ALL、no-new-privileges、network none），落盘 `mount-plan.txt`。
6. **cgroup 资源常量**：cpu.max `50000 100000`、memory 768MiB、swap=mem、pids 128。
7. **启动容器**（此时才允许出现任何能触源的进程）。
8. **启动后立即比对**：`docker inspect .Mounts` ↔ mount-plan.txt 逐条一致、
   cgroup 文件读回值 ↔ §4.6 一致（同已验收演练口径）；任一不符 → 立即 stop、
   保留现场、登记标记 INVALID。

⇒ 源读取只可能发生在步骤 8 通过的窗口内；输入、镜像、挂载、资源四类核验全部
结构性先于源读取。

## 4b. 端到端时序表（上传 → 读取，caa1a13 复核意见）

可信清单来源缩写：**A** = run-input 内随包钉入的权威 `INPUTS.sha256`（48 项，
verify-inbox 固化时逐字节核验过）；**C** = 入口脚本 root 常量。

| # | 步骤 | 执行者/写入方 | 读取来源 | 可信清单 | 锁/attempt | 源可读？ |
|---|---|---|---|---|---|---|
| T1 | scp 上传包至 inbox | 操作员（xrgp01op，唯一可写区） | Windows packet-real.tar.gz | — | 无 | 否 |
| T2 | `sudo xrg-p01-run verify-inbox` | **root（入口）**：复制 inbox→run-input、chown root 0755、写 VERIFIED.sha256 | inbox 整树 | A（包内附送，先对 C 中卡片/review/roots 三 SHA） | 无 | 否 |
| T3 | 放置 authorization.json | **有授权权的人（茶香/被其点名的操作员本人）**，`install -m 600` 独占创建；入口与 xrgp01op 通道均不写 | — | 绑定卡片 SHA+attempt（内容自证） | 无 | 否 |
| T4 | `sudo xrg-p01-run stage-a` 宿主预检 | root（入口） | run-input（拒绝再读 inbox） | A + C | O_EXCL `registry/stage-a.lock`（幂等：Stage A 成功收据存在即视为已完成，不重复跑） | 否——容器无快照挂载，物理不可读源 |
| T5 | Stage A 容器（materialize） | uid 10001 | run-input ro、authorization ro | 容器门再验字节+卡片 SHA | 同上 | 否（本阶段设计上不触源） |
| T6 | 操作员核对 controller-pins.txt 三 pin | 人（离线） | Stage A 收据 output/ | — | 无 | 否 |
| T7 | `sudo xrg-p01-run stage-b` 宿主预检 | root（入口） | run-input + Stage A 成功收据 | A + C + Stage A 收据 pin | **O_EXCL `registry/<attempt>.lock`＝attempt 名额在此消耗**；预检任何一步失败 → 删除本次 lock 文件并落 registry/refusals/（**不消耗名额**） | 否 |
| T8 | 启动候选容器（挂载拼装见 §4.5） | root（docker CLI 在入口内部） | 快照**仅任务卡指定版本目录** `/mnt/wd61workmetadata/usedata/<SNAPSHOT_ID>` ro bind → `/data/imports/usedata/<SNAPSHOT_ID>`；父目录不挂 | 生成 mount-plan.txt | lock 已持有 | **尚未**——worker 未放行 |
| T9 | 启动后即时核验 | root（入口） | `docker inspect .Mounts`、cgroup 读回值 | mount-plan.txt + C | 不符→stop+登记 INVALID（消耗 attempt，留全现场） | **仍未**——核验不过绝不放行 worker |
| T10 | **放行 worker**（supervisor Popen task_control） | 容器内 uid 10001 | 容器门字节校验通过 + T9 通过后由 supervisor 拉起 | 三方 pin 交叉（§4） | lock 已持有 | **是——全流程唯一读取窗口自此开始** |
| T11 | 原始收据落 output/ | 容器 uid 10001 写；操作员 ACL r-x 只读 | — | — | 结束时 lock 转 done | 读取窗口随进程终止关闭 |

关键不变式：
- **首次可运行**：T5 Stage A 成功收据存在 + attempt lock 不存在 ⇒ T7 必然放行到
  T10；同 attempt 第二次 stage-b 在 T7 O_EXCL 即拒（`attempt_consumed`），并发
  双发起同理只有一个能持锁——**只能放行一次**。
- **预检拒绝不消耗**：T7 在容器创建前的失败路径删除本次 lock、只留 refusals
  记录；T9/T10 之后的失败才计入消耗（现场完整保留）。
- 源读取仅存在于 T10–T11 窗口，且挂载面只有卡片钉定的快照版本目录（ro）。

## 5. 明确不做

- 不给 `xrgp01op` docker 组/socket/通用 CLI/systemctl 权；不给 run-input、
  registry、output 写权。
- 入口无任意命令/挂载/镜像参数面；脚本本体 root:root 0755，其 sha256 写入任务
  卡附注供 verify-real.sh 复核；安装由管理员执行（visudo -cf 校验）。
- authorization.json 放置仍纯人工独占创建；入口与操作员通道都不写它。
- 不在 32 直接编辑 Git 内容。

## 6. 验收条件（获批后的实施轮，逐项出机器可读收据）

基础项（继承 v2）：
1. `id xrgp01op` 无 docker 组；socket EACCES；`sudo -l -U xrgp01op` 恰三条固定
   argv 白名单。
2. 正常走查：`verify-inbox`→`stage-a` 产物与现 RUNBOOK R2 预期一致；
   `stage-b` 仅在茶香授权后、总指挥现场监督下启用。

本轮新增三项（否决性）：

- **R1 输入替换攻击**：verify-inbox 通过后，操作员改 inbox 内任一文件（如
  run-real.sh 加一行注释）→ 再跑 `stage-a`：入口必须以 run-input 为准照常
  校验通过（证明不受 inbox 影响）；随后直接改 run-input 内任一字节（需 root，
  模拟篡改者）→ `stage-a` 必须在 §4.3 拒绝、退出非 0、无容器创建、登记标记
  REFUSED 且不消耗 attempt 名额（REFUSED 记录单独落 registry/refusals/）。
- **R2 未授权**：无 authorization.json（或字段不符）时 `stage-b`：宿主门拒启
  （无容器）；放入合法外观但**未绑定本卡片 SHA** 的文件：容器门退出 2。两种
  拒径都必须留各自收据，且 `output/` 无可执行副作用。
- **R3 重复启动**：同一 attempt 第二次 `stage-a`/`stage-b` → §4.2 O_EXCL 立即
  拒绝，退出非 0，错误串 `attempt_consumed`，不新建容器、不覆盖原收据。
- **R4 越权写**：`xrgp01op` 对 run-input/registry/output 的写、删、chmod 全部
  EACCES，audit 留痕。
- **R5 回退**：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01 /usr/local/bin/xrg-p01-run;
  setfacl -b <运行根>` 后回到现状。

## 7. 残余风险

- root ssh 通道仍在：定位为管理员安装/审计通道；是否收紧另列裁决项。
- docker 守护进程本身仍是全局能力——本方案收缩的是**操作者可达面**，不声称
  消除 daemon 权力本身。
