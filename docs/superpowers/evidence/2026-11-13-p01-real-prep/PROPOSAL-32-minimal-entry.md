# 提案 v5（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（迭代自 v5/4ae88ec）。本轮及既往各轮均未登录或修改
> 32；真实任务卡 `real-p01-20261113-a` 保持 CLOSED。落地须先获总指挥批准。
> v2 复核意见的落实点：①操作员上传区与运行输入/授权/登记/原始收据物理分离；
> ②固定入口只消费操作员不可替换的已核验副本；③宿主授权门+容器授权门双保留；
> ④挂载与 cgroup 核验相对源读取的时序写死；⑤镜像身份沿用已验收 `.Id` 口径；
> ⑥补输入替换/未授权/重复启动三项验收条件。
> **v3.1（回应 caa1a13）**：新增端到端时序表。
> **v4（回应 20f6b2a 复核）**：正文与验收合并为**一张统一时序表
> §4b**，并落实四项：①权威 48 项清单由管理员从已审查提交独立固定，包内清单
> 仅供比对；②候选"创建→核验→启动"的等待机制写死，核验完成前读取进程无法
> 启动，核验失败/超时/控制器退出保持关闭；③授权目录归管理员，仅有授权权的
> 人可放置；临时互斥锁与持久消费记录分列，覆盖预检拒绝/并发/完成后重复/中断
> 恢复；④快照挂载沿用现有 run-real.sh 口径——受控快照根下任务卡指定版本目录
> 只读绑定；改源路径单列待裁决差异。｜as_of 2026-11-14
> **v5（本 revision，回应 1fa11e5 复核的三个实施条件）**：①T9–T10 重写为
> 两段等待机制——宿主实际 cgroup 读回全过之前 worker 无法启动，验收覆盖
> 读回失败/宿主退出/等待超时三态且均须证明 worker 从未启动；②消费记录提前到
> 首次 docker start 请求之前 fsync 落盘，配置预检拒绝仍可重试，恢复子命令与
> 活跃执行经运行锁互斥，补 ID 未落盘、启动结果不明两种中断；③授权原件独占
> 创建方式与容器 uid 10001 只读同字节副本的确认链写死，执行账号对原件/副本
> 均零写权。｜as_of 2026-11-14
> **v6（本 revision，回应 4ae88ec 复核的三个条款）**：①GO 选定为一次性命名
> pipe，绑定本次 attempt+容器 ID、旧 GO 以 unlink 失效、宿主放行前退出时容器
> PID1 自行超时关闭，I/O 优先级读回接口改正为 `/sys/fs/cgroup/<scope>/cpu.cgroup_weight`
> （cgroup v2 io.weight），A-T9c 三态各要求可覆盖瞬时启动的进程事件证据；
> ②T9b 消费文件与父目录双 fsync 成功才发首次 start，补半写/同步失败/终态更新
> 中断语义，stage-b 与 recover-orphan 改用同一稳定锁文件的独占 flock（持锁范围
> 写死），start 响应丢失区分原入口存活/已退出，A-T7/T9 拆为 T9a 可重试与 T9b
> 后已消费；③授权发布走独占 rename 流程（第二次提交原子失败、半成品不可见），
> 宿主从同一份已验证字节生成受保护副本+摘要并 ro bind 副本，验收含 UID 10001
> 实读核对与 Stage A 首读前副本就绪。｜as_of 2026-11-14

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
├── authz/                     ← 授权目录：root:xrgauthz 0710（仅授权人与 root
│   ├── .staging/                  在组）；原件 authorization.json 只能经
│   │   └── <uuid>.json            "独占临时件 → fsync → rename"发布（§3），
│   └── authorization.json         半成品永不可见；入口/xrgp01op 均不写
├── run-authz/                 ← 宿主生成的受保护副本区：root:root 0700，
│   └── authorization.json        stage-a/stage-b 预检时从已验证原件字节复制
│                                 （copy_file_range+fsync+chmod 0400），ro bind
│                                 进容器的是这份副本，不是原件
├── pins/                      ← 管理员独立固定的权威清单区（root:root 0755）
│   ├── INPUTS.admin.sha256    （48 项，取自已审查 Git 提交的 packet-inputs-real.sha256）
│   └── ATTEMPT_CONSUMED.json  （持久消费记录，见 §4c）
├── registry/                  ← 稳定 flock 文件＋GO FIFO 件所在区（root:root 0700，见 §4c）
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

**授权原件发布与容器副本（v6，条款③统一口径）**：

- **原件独占发布（真正的 atomic publish）**：唯一被接受的流程——授权人
  （`xrgauthz` 组成员，目录 root:xrgauthz 0710）在 `authz/.staging/<uuid>.json`
  O_EXCL 创建临时件、写入 canonical JSON、fsync，然后 `rename()` 到
  `authz/authorization.json`。rename 原子 ⇒ **半成品永不可见**；目标已存在时
  发布前用 `rename(..., RENAME_NOREPLACE)` ⇒ **第二次提交原子失败**（EEXIST），
  不存在"覆盖式更新"。除该流程外任何写路径都不被承认；入口与 xrgp01op 对
  authz/ 零写权。原件 mode 0400、属主＝授权人。
- **宿主确认 → 受保护独立副本**：stage-a/stage-b 预检中宿主门逐项校验原件
  字段后，从**同一份已验证字节**生成两份产物：
  1. `run-authz/authorization.json`——root:root 0400、目录 0700，
     copy_file_range + fsync + chmod；此后容器 ro bind 挂载的是**这份副本**
     （固定路径 `/authorization/authorization.json`），原件本身不进容器；
  2. `run-input/AUTHZ.confirmed.json`——摘要记录（原件 sha256 ＝ 副本回读
     sha256 ＝ attempt ＝ 时间），root 0644。
  副本区每次 stage-* 预检时由 root 重建（unlink+重发），操作员与容器均不可
  触碰。**就绪时序**：Stage A 容器创建（T4→T5）之前副本与 confirmed 记录
  必须已落盘——Stage A worker 第一次读取 `/authorization/...` 时拿到的就是
  这份经宿主确认的字节。
- **容器内 UID 10001 核验**：容器门第一步实际 open+read 副本全文，计算
  sha256 并与 AUTHZ.confirmed.json 记录值比对，再验卡片 SHA/attempt 绑定
  ——三方一致（原件＝副本＝confirmed）才继续；不一致退出 2。
- **执行账号零写权**：xrgp01op 不在 xrgauthz 组 ⇒ 对 authz/ 与其 .staging
  写/删/rename EACCES；对 run-authz/（0700 root）同样不可写、不可删、不可
  替换；对容器内挂载点（ro bind）只读；对 confirmed 记录只读。其唯一参与
  是 T1 上传包。

## 4b. 统一时序表（正文与验收共用；T# 即验收编号）

可信清单来源缩写：**P** = `pins/INPUTS.admin.sha256`（管理员从已审查提交独立
固定的权威 48 项清单）；**B** = 包内附送 `INPUTS.sha256`（仅为被检对象）；
**C** = 入口脚本 root 常量（attempt、三 SHA、镜像 .Id、资源值、挂载面）。

| T# | 步骤 | 执行者/写入方 | 读取来源 | 可信清单 | 锁/消费记录 | worker/源可读？ |
|---|---|---|---|---|---|---|
| T1 | scp 上传包至 inbox | 操作员 xrgp01op（唯一可写区） | Windows packet-real.tar.gz | — | 无 | 否 |
| T2 | `sudo xrg-p01-run verify-inbox` | **root（入口）**：复制 inbox→run-input、双清单核验、chown root 0755、写 VERIFIED.sha256 | inbox 整树 | **先 P==B 逐字节，再按 P 验 48 文件**＋C 三 SHA | 无 | 否 |
| T3 | 发布授权 | **仅授权人**走 `.staging/<uuid>` O_EXCL → write → fsync → RENAME_NOREPLACE 独占发布（§3）；二次提交原子失败；目录 root:xrgauthz 0710 | — | 内容绑定卡片 SHA+attempt | 无 | 否 |
| T4 | `stage-a` 宿主预检 | root（入口）：校验原件字段→**生成 run-authz 副本＋AUTHZ.confirmed**（T5 首读前就绪） | run-input + authz 原件 | P + C | flock `registry/stage-a.flock`（常驻，同 §4c 语义；成功收据存在则幂等跳过） | 否——Stage A 容器无快照挂载 |
| T5 | Stage A 容器 materialize | uid 10001 | run-input ro、**run-authz 副本** ro（宿主门已在 T4 前生成副本+confirmed，首读即就绪） | 容器门实读副本字节 sha256==confirmed＋卡片 SHA | 同上 | 否 |
| T6 | 操作员核对 controller-pins.txt 三 pin | 人（离线） | output/ Stage A 收据 | — | 无 | 否 |
| T7 | `stage-b` 宿主预检（**持稳定锁**） | root（入口） | run-input + Stage A 成功收据 + authz 原件 → 现场重建 run-authz 副本＋confirmed | P + C + Stage A 收据 pin | `flock(LOCK_EX\|LOCK_NB)` on `registry/<attempt>.flock`（O_CREAT 常驻不删；§4c 持锁范围）；此步失败→释锁、落 refusals，**不写消费记录** | 否 |
| T8 | **docker create（只创建不启动）** | root（入口内部 docker CLI） | 命令行由入口拼装：仅任务卡指定版本目录 `$SNAPSHOT_HOST_ROOT/$SNAPSHOT_ID` ro bind → `/data/imports/usedata/$SNAPSHOT_ID`（现 run-real.sh :341 口径，受控快照根，父目录不挂）；其余同 C | 生成 mount-plan.txt | flock 持有 | **进程尚未运行**——create 态无任何执行 |
| T9a | **create 态静态核验**：`.Mounts` ↔ mount-plan.txt 逐条、HostConfig cgroup 参数 ↔ C；任一不符 → rm 容器、lock 删除、refusals 记录，**可重试**（未发过 start 请求） | root（入口） | `docker inspect`（create 态即含全部配置） | mount-plan.txt + C | flock 持有；**无消费记录** | 否——尚未 start，无任何执行 |
| T9b | **消费记录前置（条款②）**：T9a 全过后、**首次 `docker start` 请求之前**：`open(O_WRONLY\|O_CREAT\|O_EXCL)` 写 `pins/ATTEMPT_CONSUMED.json`（state=START_REQUESTED，container_id=create 返回值）→ fsync(fd) → **fsync(pins/ 父目录 fd)**；两步全成功才准发 start。EEXIST（半写残留）⇒ 读回校验：字节完整且合法 ⇒ 视为已消费立拒重试；字节截断/非法 JSON ⇒ 拒绝启动（`consumed_record_corrupt`），人工裁决，绝不自动覆盖。任一 fsync 失败 ⇒ 不发 start、unlink 本次半成品、rm 容器、释锁（视同预检拒绝，可重试） | root（入口） | — | C | **双 fsync 完成＝名额消耗点，先于 start 请求** | 否 |
| T9c | **等待机制（条款①）**：start 后入口轮询宿主**实际读回**五项：`/sys/fs/cgroup/system.slice/docker-<id>.scope/{cpu.max,memory.max,memory.swap.max,pids.max}` 逐字等于 C，加 **I/O 优先级：v5 误写 `/proc/<pid>/io_scheduling`（不存在）——正确接口为 cgroup v2 同路径 `io.weight`**（宿主无 BFQ/IOPRIO 类接口可依赖；容器内 ionice 不作为核验面）。nice 读回 `/proc/<pid>/stat` field 7。每轮 0.2s、预算 10s。全过才执行一次性 GO：向 mkfifo `registry/<attempt>.<container-id12>.go`（root:root 0600，文件名钉 attempt+容器 ID）open O_WRONLY 写单行 `GO <nonce>` 并 close——pipe 语义保证**恰好一个读者收到、写完即 EOF、重开无数据 ⇒ 一次性生效**。进入 T9c 前先 unlink 任何同名旧 go 件 ⇒ **旧 GO 失效**。读回不符/超时 ⇒ unlink GO 件、stop+rm、消费记录 fsync 改 INVALID_READBACK；**宿主在放行前退出**：无人写 GO，容器 PID1（supervisor）对 FIFO open(O_RDONLY) 侧自带 15s 超时 ⇒ 打印 SUPERVISION_ABORTED_NO_GO、exit 1，自行关闭 | root（入口） | cgroup fs（io.weight）+ `/proc/<pid>/stat` | C | flock 持有，消费记录已存在 | 否——GO 未写，supervisor 超时自毙 |
| T10 | **放行点**：supervisor 启动即以 ro bind 打开 `/control/<attempt>.<cid12>.go` FIFO open(O_RDONLY)，**15s 内收到 `GO <nonce>`** 才继续：先容器门字节校验（实读 run-authz 副本比对 confirmed），通过才 Popen task_control；超时/EOF 无数据/nounce 不符 ⇒ exit 1，全程零源读取 | 容器内 uid 10001 | GO nonce + 三方 pin | 容器门 | flock 持有 | **是——唯一读取窗口自 T10 开始，且必然在 T9c 五项读回通过之后** |
| T11 | 收尾：原始收据落 output/（uid 10001 写，操作员 r-x）；入口把消费记录更新为终态（COMPLETED/STOPPED/TIMEOUT/INVALID_*，fd+父目录双 fsync），释 flock（锁文件保留不删） | 容器 + root（入口） | — | — | 消费记录承载终态；flock 释放 | 窗口随进程终止关闭 |

⇒ 输入、镜像、挂载、资源四类核验（T9a）与五项宿主读回（T9c：cpu.max、
memory.max、memory.swap.max、pids.max、io.weight ＋ nice）全部结构性先于
GO/放行（T10）；源读取只存在于 T10–T11。GO＝一次性命名 pipe：文件名钉
attempt+容器 ID、每次重建 unlink 旧件失效、pipe EOF 不可重放；FIFO 所在
registry/ root 0700，xrgp01op 与容器均只读 ⇒ 无法伪造放行；宿主放行前退出
时 PID1 的 15s FIFO open 超时自行关闭，不存在"无宿主也常驻等待"的窗口。

## 4c. 锁与消费记录语义（v6，条款②统一）

| 记录 | 载体 | 生命周期 |
|---|---|---|
| **稳定独占锁** | `registry/<attempt>.flock`（O_CREAT 常驻文件，root 0600，**永不删除**） | stage-b 与 recover-orphan **同一文件**上 `flock(LOCK_EX\|LOCK_NB)`：拿不到即立拒。持锁范围＝T7 预检起 → 经 T8/T9a/T9b/T9c/T10 → 主循环观测至 worker 进程终止 → T11 终态 fsync 完成 ⇒ **从预检到收尾全程独占**；进程死亡（含 SIGKILL）内核自动释锁 |
| **持久消费记录** | `pins/ATTEMPT_CONSUMED.json`（O_EXCL＋fd fsync＋父目录 fsync，root） | T9b 双同步成功＝消耗点，先于首次 start 请求；终态更新（COMPLETED/STOPPED/TIMEOUT/INVALID_*）同样 fd+目录双 fsync |
| GO 一次性件 | `registry/<attempt>.<cid12>.go`（mkfifo 0600） | 每次进入 T9c 前 unlink 重建 ⇒ 旧 GO 天然失效；写完 close、EOF ⇒ 不可重放 |

- **可重试窗口（T9a 及更早）**：T7 预检失败、T9a create 态静态核验不符——
  未写消费记录 ⇒ rm 容器、释锁、refusals/ 留明细，修正后可重试。
- **T9b 之后一律已消费**：双 fsync 完成的瞬间起，任何后续失败（start 不明、
  读回不符、超时、崩溃）只能走恢复/终态路径，不再释放重试资格。
- **终态更新中断**：入口若在"改写终态 fd fsync 后、父目录 fsync 前"崩溃，
  重启方读到的可能是旧内容 START_REQUESTED ⇒ 恢复子命令按 state≠终态且
  容器已不存在处理：补记 INVALID_FINALIZATION_LOST（双 fsync），仍为已消费。
- **并发**：双发 stage-b ⇒ flock 只有一个进 T8；另一路 `busy_or_consumed`
  立退。start 请求至多发一次由锁范围覆盖 T9b–T9c 保证。
- **完成后重复启动**：stage-b 起手三查（持锁后）：消费记录存在 ⇒ 立拒
  `attempt_consumed`；GO 件残留 ⇒ unlink（不影响判定）；原收据零触碰。
- **start 响应丢失（区分两型，条款②点名）**：恢复子命令拿到 flock 后先看
  原入口 PID（记录于 run-input/PID 文件，持锁期间有效）：
  1. *原入口仍存活*：说明它仍在 T9c 等待/主循环——恢复路径**只报告不接管**
     （`holder_alive` 退出），等其自行收敛；
  2. *原入口已退出*：读容器 `State.Status` 与 GO 件写入痕迹——若**尚未放行**
     （无 GO 写出记录）⇒ 恢复**只做核对与回收**：stop→rm、按读回/崩溃现场
     补记 INVALID_START_UNCONFIRMED 或 INVALID_READBACK，**绝不代补发 GO、
     绝不重发 start**；若已放行过（有 GO 写出记录）⇒ 仅补终态。
- **create 后 ID 未落盘**：仍按 label `io.xiangrugu.synthetic-run=<suffix>`
  反查孤儿容器（run-real.sh :190 口径）stop→rm，保守补记 INVALID_PRESTART
  并永久消耗（验收 A-T8a 保留）。

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
- 授权发布只认 §3 独占 rename 流程；原件与 run-authz 副本对入口和操作员
  通道都是只读源；副本由宿主从已验证字节生成，不经任何共享可写区。
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
- **A-T9a 可重试拒绝（原 A-T7/T9 拆分①）**：构造 T7 flock 占用失败与 T9a
  静态核验不符各一次 → 两径均：无消费记录、锁释放、refusals/ 留明细、容器
  已 rm；修正后重试成功进入 T9b。
- **A-T9b 后已消费（拆分②）**：双 fsync 完成后注入任意失败（start 超时、
  读回不符、终态更新崩溃）→ 一律不得回到可重试态：stage-b 再发起立拒，
  终态只能经恢复路径补记，消费记录 fd+目录双同步痕迹入收据。
- **A-T9b 半写/同步失败**：kill 于 write 中途 → 重启 stage-b 读到截断 JSON
  ⇒ `consumed_record_corrupt` 拒绝且无自动覆盖（人工裁决标记文件生成）；
  注入父目录 fsync 失败（模拟 EIO）⇒ 不发 start、半成品 unlink、可重试。
- **A-T9c 等待机制三态（条款①，逐态出收据）**：注入 ① io.weight/cpu.max
  任一读回不符、② 入口在轮询中被 SIGKILL、③ 读回预算 10s 超时。三种情况
  都必须以**进程事件证据**证明 worker 从未启动——仅时间线不够，因 task_control
  可能瞬时完成：(a) 宿主机 audit 规则 `-w $SNAPSHOT_HOST_ROOT -p r` 全程零
  命中＋`fanotify FAN_OPEN_PERM` 挂快照目录返回 0 次询问；(b) 容器内
  `/proc/<pid>/` 快照序列显示除 supervisor PID1 外从未出现第二进程（每 0.1s
  采样入 monitor-absent 收据）；(c) output/ 无 task_control 可产生的任何文件
  （含 scratch 残留）。②另证 PID1 于 15s 打印 SUPERVISION_ABORTED_NO_GO
  exit 1；正常对照一次：GO 写出时间戳晚于五项读回＋nice 全部通过时间戳，
  收据逐项列五值读回原文。
- **A-GO 一次性**：同一 attempt 重放第二次 open 该 FIFO ⇒ EOF 无数据；新
  create 容器 GO 件名含新容器 ID，旧件被 unlink 的审计记录入收据。
- **A-T8~T10 中断恢复（条款②）**：
  ① *ID 未落盘*：create 后 kill → recover-orphan label 反查孤儿、stop→rm、
     补记 INVALID_PRESTART；此后 stage-b 立拒（验收保留）。
  ② *start 响应丢失，原入口仍存活*：恢复调用得 `holder_alive` 只报告退出，
     主循环不受扰继续收敛终态。
  ③ *start 响应丢失，原入口已退出且未放行*：恢复 stop→rm、补记
     INVALID_START_UNCONFIRMED；断言恢复路径日志无 GO 写、无 start 请求
     （docker events 时间线佐证 start 计数 ≤1）。
  ④ *flock 互斥双向*：stage-b 持锁期 recover-orphan 拿不到锁即拒；恢复持锁
     期 stage-b 同样立拒（两侧各验一次，锁文件始终存在不被删）。
- **A-AUTHZ（条款③）**：
  ① 发布语义：授权人走 staging→fsync→RENAME_NOREPLACE 成功；同目标二次
     提交原子失败 EEXIST 留证；staging 半成品在 rename 前对容器/操作员
     不可见（open 返回 ENOENT 记录）。
  ② 副本链核验：**实施轮以 uid 10001 在容器内实际 open+read 副本全文并
     输出 sha256**，与 AUTHZ.confirmed.json、宿主门记录三方一致入收据；
     Stage A 首读前副本就绪（confirmed mtime < Stage A 容器 create 时间）。
  ③ 操作员破坏面：xrgp01op 对 authz/、.staging/、run-authz/ 的写/删/改名/
     chmod 全 EACCES（audit 留痕）；替换原件后再跑 stage-b ⇒ 宿主门按新
     字节重新生成副本但 confirmed 摘要随之变化并被卡片 SHA 绑定校验把关。

- **A-R 越权写**：xrgp01op 对 run-input/pins/registry/authz/output 的写删 chmod
  全部 EACCES，audit 留痕。
- **A-F 回退**：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01
  /usr/local/bin/xrg-p01-run; setfacl -b <运行根>` 后回到现状。

## 7. 残余风险与前提声明

- 本提案的 cgroup 读回路径按 **cgroup v2 unified**（32 现 host 已核实口径）
  书写；若实施轮发现混合层级，路径以 `docker inspect .GraphDriver`/
  `systemd.detect_v2` 实测为准修订 §4b，不改语义。
- I/O 优先级核验面限定为 `io.weight`；容器内 ionice/BFQ 类调度不作为验收项
  （v5 的 `/proc/<pid>/io_scheduling` 系笔误，本版更正）。


- root ssh 通道仍在：定位为管理员安装/审计通道；是否收紧另列裁决项。
- docker 守护进程本身仍是全局能力——本方案收缩的是**操作者可达面**，不声称
  消除 daemon 权力本身。
