# 提案 v4（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（替代 v2/8f351fa）。本轮及既往各轮均未登录或修改
> 32；真实任务卡 `real-p01-20261113-a` 保持 CLOSED。落地须先获总指挥批准。
> v2 复核意见的落实点：①操作员上传区与运行输入/授权/登记/原始收据物理分离；
> ②固定入口只消费操作员不可替换的已核验副本；③宿主授权门+容器授权门双保留；
> ④挂载与 cgroup 核验相对源读取的时序写死；⑤镜像身份沿用已验收 `.Id` 口径；
> ⑥补输入替换/未授权/重复启动三项验收条件。
> **v3.1（回应 caa1a13）**：新增端到端时序表。
> **v4（本 revision，回应 20f6b2a 复核）**：正文与验收合并为**一张统一时序表
> §4b**，并落实四项：①权威 48 项清单由管理员从已审查提交独立固定，包内清单
> 仅供比对；②候选"创建→核验→启动"的等待机制写死，核验完成前读取进程无法
> 启动，核验失败/超时/控制器退出保持关闭；③授权目录归管理员，仅有授权权的
> 人可放置；临时互斥锁与持久消费记录分列，覆盖预检拒绝/并发/完成后重复/中断
> 恢复；④快照挂载沿用现有 run-real.sh 口径——受控快照根下任务卡指定版本目录
> 只读绑定；改源路径单列待裁决差异。｜as_of 2026-11-14

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
├── authz/                     ← 授权目录：root:root 0710，仅 root 与"有授权权
│   └── authorization.json        的人"所在组可及；放置由该人独占创建
│                                 （install -m 600），入口/xrgp01op 均不写
├── pins/                      ← 管理员独立固定的权威清单区（root:root 0755）
│   ├── INPUTS.admin.sha256    （48 项，取自已审查 Git 提交的 packet-inputs-real.sha256）
│   └── ATTEMPT_CONSUMED.json  （持久消费记录，见 §4c）
├── registry/                  ← 临时互斥锁目录（O_EXCL lock，root 属主，见 §4c）
└── output/                    ← 原始收据树（monitor/batch/failure-report/心跳/
                                 worker-output），容器 uid 10001 写入；
                                 操作员仅可读（ACL r-x），不可写、不可删
```

要点：
- **权威清单独立固定（复核意见①）**：管理员从**已审查的 Gitea 提交**取出
  `packet-inputs-real.sha256`（48 项），落到 `pins/INPUTS.admin.sha256` 并
  chown root 0644；入口核验时以此文件为准。**包内自带的 INPUTS.sha256 只是
  被检对象**：verify-inbox 先比 `包内清单 == pins 权威清单`（逐字节），再对
  48 个文件逐一跑权威清单——两份都过才固化 run-input。攻击者换包内清单无用
  （对不上 pins），改文件更无用（对不上清单）。
- **固定入口只使用 `run-input/` 内经核验且操作员无法替换的副本**。流程：操作员
  传包进 `inbox/` → 触发 `xrg-p01-run verify-inbox`（sudo 白名单之一，纯本地
  校验）→ 入口以 root 复制 inbox→run-input、按上条双清单核验、核对卡片/review/
  roots 三 SHA，全过才写 `VERIFIED.sha256` 并 chown root:root 0755（此后
  xrgp01op 对该树零写权）。stage-a/stage-b 一律只认 run-input，绝不回读 inbox。
- 原始收据只在 `output/`：容器写、操作员读；入口不提供任何删除/改写收据的子命令。

## 3. 双授权门（都保留，语义不同）

| 门 | 位置 | 校验内容 | 失败行为 |
|---|---|---|---|
| 宿主门 | `xrg-p01-run stage-b` 启动前（root） | `authz/authorization.json` 存在、mode 600、属主合法（有授权权的人）、JSON 键 status/attempt_id/task_card_sha256/one_attempt_only/granted_by 逐项等值 | 拒启，不创建容器，不留消费记录 |
| 容器门 | worker 容器内第一步（uid 10001，ro 挂载该文件） | 同文件再验字节 + 绑定卡片 SHA（现 RUNBOOK 既有逻辑，不改） | 退出 2（设计使然），早于任何源读取 |

宿主门防"误触发起容器"，容器门防"入口被绕过/篡改后仍守授权"——两门独立失效。

## 4b. 统一时序表（正文与验收共用；T# 即验收编号）

可信清单来源缩写：**P** = `pins/INPUTS.admin.sha256`（管理员从已审查提交独立
固定的权威 48 项清单）；**B** = 包内附送 `INPUTS.sha256`（仅为被检对象）；
**C** = 入口脚本 root 常量（attempt、三 SHA、镜像 .Id、资源值、挂载面）。

| T# | 步骤 | 执行者/写入方 | 读取来源 | 可信清单 | 锁/消费记录 | worker/源可读？ |
|---|---|---|---|---|---|---|
| T1 | scp 上传包至 inbox | 操作员 xrgp01op（唯一可写区） | Windows packet-real.tar.gz | — | 无 | 否 |
| T2 | `sudo xrg-p01-run verify-inbox` | **root（入口）**：复制 inbox→run-input、双清单核验、chown root 0755、写 VERIFIED.sha256 | inbox 整树 | **先 P==B 逐字节，再按 P 验 48 文件**＋C 三 SHA | 无 | 否 |
| T3 | 放置授权 | **仅有授权权的人**在 `authz/` 独占创建（install -m 600）；目录 root:root 0710，管理员控制，xrgp01op 与入口均不写 | — | 内容绑定卡片 SHA+attempt | 无 | 否 |
| T4 | `stage-a` 宿主预检 | root（入口） | run-input | P + C | O_EXCL `registry/stage-a.lock`（临时互斥；成功收据存在则幂等跳过） | 否——Stage A 容器无快照挂载 |
| T5 | Stage A 容器 materialize | uid 10001 | run-input ro、authz ro | 容器门再验字节+卡片 SHA | 同上 | 否 |
| T6 | 操作员核对 controller-pins.txt 三 pin | 人（离线） | output/ Stage A 收据 | — | 无 | 否 |
| T7 | `stage-b` 宿主预检 | root（入口） | run-input + Stage A 成功收据 + authz 授权 | P + C + Stage A 收据 pin | O_EXCL `registry/<attempt>.lock`（**临时互斥锁**；此步任何失败→删本次 lock、落 refusals 记录，**不写消费记录**） | 否 |
| T8 | **docker create（只创建不启动）** | root（入口内部 docker CLI） | 命令行由入口拼装：仅任务卡指定版本目录 `$SNAPSHOT_HOST_ROOT/$SNAPSHOT_ID` ro bind → `/data/imports/usedata/$SNAPSHOT_ID`（现 run-real.sh :341 口径，受控快照根，父目录不挂）；其余同 C | 生成 mount-plan.txt | lock 持有 | **进程尚未运行**——create 态无任何执行 |
| T9 | **等待机制（复核意见②）**：对 create 态容器核验 `.Mounts` ↔ mount-plan.txt、HostConfig cgroup 值 ↔ C；通过后 `docker start`，启动后再读回 cgroup 文件比对 | root（入口） | `docker inspect`（未启动态即可读全部配置）+ cgroup fs | mount-plan.txt + C | lock 持有 | **核验完成并全过之前，worker 根本不存在**；核验失败/等待超时/控制器自身退出 ⇒ 不 start 或立即 stop，**保持关闭**，登记 INVALID（此时才写消费记录） |
| T10 | **放行点**：start 后 supervisor 先跑容器门字节校验，通过才 Popen task_control | 容器内 uid 10001 | 三方 pin 交叉 | 容器门 | lock 持有 | **是——全流程唯一读取窗口自 T10 开始** |
| T11 | 收尾：原始收据落 output/（uid 10001 写，操作员 r-x）；入口把 lock 改名转 done 并**写持久消费记录 `pins/ATTEMPT_CONSUMED.json`**（O_EXCL，含 container_id、终态、时间） | 容器 + root（入口） | — | — | **临时锁退役，消费记录接管** | 窗口随进程终止关闭 |

⇒ 输入、镜像、挂载、资源四类核验全部结构性先于 T10；源读取只存在于 T10–T11。

## 4c. 锁与消费记录语义（复核意见③，四场景全覆盖）

| 记录 | 载体 | 生命周期 |
|---|---|---|
| 临时互斥锁 | `registry/<attempt>.lock`（O_EXCL 空文件，root） | T7 获取；预检失败即删（不消耗）；成功走到 T11 时改名 `.done` 并让位给消费记录 |
| 持久消费记录 | `pins/ATTEMPT_CONSUMED.json`（O_EXCL，root，fsync） | 仅在越过 T9（容器真正 start 过）或 T11 正常完成时写入；一经写入永不可被 stage-b 路径删除 |

- **预检拒绝**：T7/T9 前置失败 ⇒ lock 已删、无消费记录、refusals/ 留明细 ⇒
  attempt 名额仍在，修正后可重试。
- **并发**：两个 stage-b 同时到 T7 ⇒ O_EXCL 只有一个成功，另一个立拒
  `busy_or_consumed`；即便都过了 T7（不可能），T11 消费记录仍 O_EXCL 兜底。
- **完成后重复启动**：T7 先查消费记录（存在 ⇒ 立拒 `attempt_consumed`，不碰
  lock）；即使记录被绕过，`.done` lock 亦阻断。双重检查任一命中都不新建容器、
  不覆盖原收据。
- **中断恢复**：入口若在 T8–T10 间崩溃，重启后 `stage-b` 检测到 lock 存在且
  `container-id.txt` 有 create/start 痕迹 ⇒ 不重用该 attempt：走"孤儿容器
  stop→rm→补写消费记录 INVALID"的恢复子命令（白名单第四条），之后该 attempt
  永久消耗——宁可保守烧掉名额，绝不留下第二个可执行窗口。

## 4d. 快照挂载口径（复核意见④）

沿用现有 run-real.sh：源为**受控快照根下的任务卡指定版本目录**
`/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap`（ro bind →
`/data/imports/usedata/2026-10-07-bootstrap`），非 NAS 原路径直挂；演练与已验收
收据链同源。**本提案不改源路径**。若未来确需改（例如换快照根位置），属实现
差异而非本入口细节——单列为待裁决事项，须总指挥另行批准并重钉卡片绑定。

## 5. 明确不做

- 不给 `xrgp01op` docker 组/socket/通用 CLI/systemctl 权；不给 run-input、
  registry、output 写权。
- 入口无任意命令/挂载/镜像参数面；脚本本体 root:root 0755，其 sha256 写入任务
  卡附注供 verify-real.sh 复核；安装由管理员执行（visudo -cf 校验）。
- 授权放置仍纯人工独占创建，且只有具备授权权的人可达 `authz/`；入口与
  操作员通道都不写它。
- 不在 32 直接编辑 Git 内容。

## 6. 验收条件（获批后的实施轮；逐项出机器可读收据，标注对应 T#）

基础项：
1. `id xrgp01op` 无 docker 组；socket EACCES；`sudo -l -U xrgp01op` 恰四条固定
   argv 白名单（verify-inbox / stage-a / stage-b / recover-orphan）。
2. 正常走查 T1→T11：`verify-inbox`→`stage-a` 产物与现 RUNBOOK R2 预期一致；
   `stage-b` 仅在茶香授权后、总指挥现场监督下启用。

否决性（对统一时序表的攻击面逐行验证）：
- **A-T2 清单替换**：改包内 INPUTS.sha256 或任一 staged 文件 → verify-inbox 在
  "P==B"或"P 验 48"任一门拒固化为 REFUSED；inbox 改动永不影响 run-input。
- **A-T2b 篡改固化区**：root 模拟改 run-input 一字节 → stage-a 在 P 重放下拒绝、
  退出非 0、无容器创建、不写消费记录（可修正重试）。
- **A-T3 未授权**：无授权文件 → 宿主门拒启（无容器）；合法外观但未绑本卡片 SHA
  → 容器门退出 2。两径各留收据，output/ 无副作用；xrgp01op 向 authz/ 写入
  EACCES（目录权限即证）。
- **A-T7/T9 预检拒绝不消耗**：构造 T7 失败与 T9 核验失败各一次 → 前者 lock 已删、
  无消费记录、名额保留；后者按 §4c 记 INVALID 消耗并留全现场。
- **A-T7 并发**：同时双发 stage-b → 恰一个进入 T8，另一个 `busy_or_consumed`；
  全程容器创建数 ≤1。
- **A-T11 完成后重复**：正常完成后再发 stage-b → 消费记录命中立拒
  `attempt_consumed`，原收据零触碰。
- **A-T8~T10 中断恢复**：kill 入口于 create 后/start 前 → recover-orphan 子命令
  stop→rm→补记 INVALID；此后该 attempt 任何再启动被拒。
- **A-T9 等待机制**：在 T9 注入挂载比对失败 → 断言 worker 进程从未存在
  （inspect 时间线 + 无 monitor 文件）、容器保持停止、状态 INVALID。
- **A-R 越权写**：xrgp01op 对 run-input/pins/registry/authz/output 的写删 chmod
  全部 EACCES，audit 留痕。
- **A-F 回退**：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01
  /usr/local/bin/xrg-p01-run; setfacl -b <运行根>` 后回到现状。

## 7. 残余风险

- root ssh 通道仍在：定位为管理员安装/审计通道；是否收紧另列裁决项。
- docker 守护进程本身仍是全局能力——本方案收缩的是**操作者可达面**，不声称
  消除 daemon 权力本身。
