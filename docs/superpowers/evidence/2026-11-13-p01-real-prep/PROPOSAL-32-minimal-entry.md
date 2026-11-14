# 提案 v5（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（迭代自 v4/1fa11e5）。本轮及既往各轮均未登录或修改
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

**授权原件与容器副本（实施条件③）**：

- **原件独占创建**：`authz/authorization.json` 由有授权权的人以
  `install -m 600 -o root /dev/null authz/authorization.json` 先建空件占位
  （O_EXCL 语义），再单次写入 canonical JSON；目录 root:root 0710、组为
  `xrgauthz`（仅该用户＋root 在组）。写毕 `chmod 0400`，入口只读。任何第二
  次独占创建失败即视为冲突，人工裁决。
- **宿主确认 → 同字节只读副本**：stage-b 宿主门按 §3 表逐项校验原件字段后，
  入口计算原件 sha256 并写入本次运行收据 `run-input/AUTHZ.confirmed.json`
  （root 属主，含摘要+时间）；随后把原件以 **ro bind 挂载到容器固定路径**
  `/authorization/authorization.json`（现 run-real.sh 同款）。容器门第一步
  重读该 ro 副本、比对卡片 SHA 与宿主门记录的同一摘要——**字节级三方一致**
  （原件＝副本＝confirmed 记录）才继续。副本无法与原件漂移：同一 inode 的
  ro bind，且 confirmed 摘要在 T9b 前已钉入消费链。
- **执行账号零写权**：xrgp01op 对 `authz/`（0710 不在组）、对容器内挂载点
  （ro bind）、对 `run-input/AUTHZ.confirmed.json`（root 0644）均不可写、
  不可删、不可 chmod；其唯一参与是 T1 上传包。

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
| T9a | **create 态静态核验**：`.Mounts` ↔ mount-plan.txt 逐条、HostConfig cgroup 参数 ↔ C；任一不符 → rm 容器、lock 删除、refusals 记录，**可重试**（未发过 start 请求） | root（入口） | `docker inspect`（create 态即含全部配置） | mount-plan.txt + C | lock 持有；**无消费记录** | 否——尚未 start，无任何执行 |
| T9b | **消费记录前置（实施条件②）**：T9a 全过后、**发出首次 `docker start` 请求之前**，O_EXCL+fsync 持久写 `pins/ATTEMPT_CONSUMED.json`（state=START_REQUESTED，container_id 取 create 返回值）；写失败（含目录不可写/EEXIST）⇒ 不发 start、rm 容器 | root（入口） | — | C | **消费记录在此刻诞生＝名额消耗点前移到 start 请求之前** | 否 |
| T9c | **等待机制（实施条件①）**：`docker start` 后入口轮询宿主 cgroup **实际读回**：`/sys/fs/cgroup/system.slice/docker-<id>.scope/{cpu.max,memory.max,memory.swap.max,pids.max}` 逐字等于 C，且容器 PID1 的 nice/ionice 读回符合；每轮间隔 0.2s，总预算 10s。**只有全部读回通过，入口才向 supervisor 控制通道写 GO**。读回失败/超时 ⇒ 立即 `docker stop`＋`docker rm`，消费记录改写 state=INVALID_READBACK（fsync），worker 保持未被放行 | root（入口） | cgroup fs + `/proc/<pid>/stat`,`/proc/<pid>/io_scheduling` | C | lock 持有，消费记录已存在 | 否——GO 未写，supervisor 不 Popen |
| T10 | **放行点**：supervisor 阻塞等 GO（FIFO/控制文件，ro 挂载 `/control`）→ 收到后先跑容器门字节校验，通过才 Popen task_control | 容器内 uid 10001 | 三方 pin 交叉 + GO | 容器门 | lock 持有 | **是——全流程唯一读取窗口自 T10 开始，且必然在 T9c 读回通过之后** |
| T11 | 收尾：原始收据落 output/（uid 10001 写，操作员 r-x）；入口把消费记录更新为终态（COMPLETED/STOPPED/TIMEOUT，fsync）、lock 改名 `.done` | 容器 + root（入口） | — | — | 消费记录承载终态 | 窗口随进程终止关闭 |

⇒ 输入、镜像、挂载、资源四类核验（T9a）与宿主 cgroup 实际读回（T9c）全部
结构性先于 GO/放行（T10）；源读取只存在于 T10–T11。GO 通道单向：入口写、
容器只读；xrgp01op 对控制目录零写权，故无法伪造放行。

## 4c. 锁与消费记录语义（实施条件②重写）

| 记录 | 载体 | 生命周期 |
|---|---|---|
| 临时互斥锁 | `registry/<attempt>.lock`（O_EXCL 空文件，root） | T7 获取；T9a 之前的失败即删（不消耗）；越过 T9b 后由消费记录接管，收尾时改名 `.done` |
| 运行锁（恢复互斥） | `registry/<attempt>.running`（O_EXCL，内容＝入口 PID＋容器 ID） | T8 create 前获取、进程存活期持有（异常退出靠 flock/PID 判活回收）；**recover-orphan 子命令必须先原子取得它**——活跃执行期间恢复路径拿不到锁即拒，反之恢复进行中 stage-b 在 T8 拿不到运行锁也拒 ⇒ 两路严格互斥 |
| 持久消费记录 | `pins/ATTEMPT_CONSUMED.json`（O_EXCL+fsync，root） | **T9b：首次 docker start 请求之前**写入（state=START_REQUESTED）；此后任何再启动在 T7 前置检查即立拒 |

- **可重试窗口（明确）**：凡未发出过 start 请求的失败——T7 预检、T9a create 态
  静态核验不符（rm 容器即可）——均删 lock、落 refusals/、**不写消费记录**，
  修正后可重试。一旦到达 T9b，名额即消耗，无论后续结果如何。
- **并发**：双发 stage-b ⇒ T7 O_EXCL 只有一个进 T8；即便同时过了 T7，运行锁与
  消费记录两道 O_EXCL 兜底，start 请求至多发出一次。
- **完成后重复启动**：T7 先查消费记录（存在 ⇒ 立拒 `attempt_consumed`）；`.done`
  lock 二次阻断；原收据零触碰。
- **中断恢复两型（实施条件②点名）**：
  1. *容器已 create、ID 尚未落盘*：恢复子命令取运行锁后按 label
     `io.xiangrugu.synthetic-run=<suffix>` 反查孤儿容器（run-real.sh :190 同款
     口径），stop→rm；因未越过 T9b 判定为"无消费记录 ⇒ 保守补记
     INVALID_PRESTART（fsync）并永久消耗该 attempt"——宁可烧名额，不留第二
     执行窗口。
  2. *start 结果不明（响应丢失/超时）*：消费记录必已存在（T9b 在前）⇒ 恢复
     路径读回容器 `State.Status`：running → 交回主循环继续 T9c 等待核验；
     exited/unknown → 补记 INVALID_START_UNCONFIRMED、stop/rm 清场。任何分支
     都不重发 start。

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
- **A-T9c 等待机制三态（实施条件①，逐态出收据）**：分别注入
  ① cgroup 读回值被篡改为不符、② 入口进程在轮询中被 kill、③ 读回预算超时
  （模拟 sysfs 延迟）——三种情况下都必须证明 **worker 从未启动**：容器内
  PID1 始终是阻塞等 GO 的 supervisor（docker top 时间线）、`/control` 无 GO
  写入记录、output/ 无 monitor/task 收据新增；容器最终 stopped/rm，消费记录
  终态 INVALID_READBACK（②由恢复路径补记）。放行前读回通过的正常对照一次：
  GO 时间戳晚于全部四项 cgroup 读回通过时间戳。
- **A-T9b 消费前置**：断言 ATTEMPT_CONSUMED.json 的 mtime/fsync 序早于首次
  start 请求日志时间戳；T9a 静态核验失败注入 ⇒ 无消费记录、可重试成功。
- **A-T8~T10 中断恢复两型（实施条件②）**：
  ① create 后 ID 未落盘处 kill → recover-orphan 经 label 反查孤儿、stop→rm、
  补记 INVALID_PRESTART；此后 stage-b 立拒。
  ② start 响应丢失（注入 docker CLI 超时）→ 恢复路径读回 State.Status，
  running 交回主循环 / exited|unknown 补记 INVALID_START_UNCONFIRMED；
  全程不重发 start，start 请求计数 ≤1。
  ③ 恢复与活跃互斥：stage-b 主循环持运行锁期间调用 recover-orphan → 拿锁
  失败即拒，反之亦然（两侧各验一次）。
- **A-AUTHZ 原件/副本（实施条件③）**：xrgp01op 向 authz/ 写、改 confirmed
  记录、remount 副本任一动作 EACCES/EPERM；正常走查中容器门读到的副本字节
  sha256 == AUTHZ.confirmed.json == 宿主门记录，三方一致入收据；原件二次
  install 独占创建失败留证。
- **A-R 越权写**：xrgp01op 对 run-input/pins/registry/authz/output 的写删 chmod
  全部 EACCES，audit 留痕。
- **A-F 回退**：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01
  /usr/local/bin/xrg-p01-run; setfacl -b <运行根>` 后回到现状。

## 7. 残余风险

- root ssh 通道仍在：定位为管理员安装/审计通道；是否收紧另列裁决项。
- docker 守护进程本身仍是全局能力——本方案收缩的是**操作者可达面**，不声称
  消除 daemon 权力本身。
