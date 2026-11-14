# 提案 v5（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（迭代自 v6/4becf3d）。本轮及既往各轮均未登录或修改
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
> **v7（本 revision，回应 4becf3d 复核的三条）**：①新增 §4e GO 通道完整时序
> （create 前建道、bind 属组映射授 UID 10001 读权、宿主 O_RDWR 单持、双向截止
> 时间退出），nonce 以 confirmed+GO 同代摘要钉定，二次读取实测预期为 EAGAIN/
> EOF，重建走 rename 原子换 inode 不脱节已开读者；A-T9c 改用候选启动前挂起、
> 按容器 cgroup 关联的 procfs exec 事件流为主证据并记录采集丢失状态，源审计
> 与无产物降为辅助；nice 更正为 getpriority()/stat 第 19 字段；I/O 优先级
> **沿用现有进程级 ionice 核验**，io.weight 替代方案单列待茶香裁决（§8）。
> ②T9a 失败路径改"释 flock、锁文件保留"；A-T9a 拆锁竞争/静态拒绝两行且竞争
> 失败方不得触碰持锁方候选；§4f 补 GO 交付后留证前宿主退出的恢复规则——不能
> 确定是否放行一律按可能已放行处理，核实确切停止/回收后才补终态；start 计数
> 以入口发起 Docker 请求处的日志为主证据、docker events 佐证。
> ③授权发布权限路径可实际执行（xrgauthz 组 + setgid staging），宿主门与原件
> 属主/mode 统一；副本 root:10001 0644 + ro bind 使容器可读、操作员不可改；
> 副本+confirmed 作为同一代产物按候选 ID 固定命名，覆盖 Stage A/B 交错预检。｜as_of 2026-11-14
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
├── authz/                     ← 授权目录 root:xrgauthz 2710（setgid）；
│   ├── .staging/                  授权人写临时件（.staging/ 2733 sticky），
│   │   └── <uuid>.json            末步经固定 sudo 命令 xrg-authz-publish
│   └── authorization.json         NOREPLACE rename 发布（§3）；半成品不可见，
│                                  （root:xrgauthz 0400） 二次发布原子 EEXIST
├── run-authz/                 ← 同代副本区 root:root 0755；每候选一对产物
│   └── gen-<cid12>/               gen-<cid12>/authorization.json（root:10001
│       └── authorization.json     0644，容器可读）；ro bind 源即此目录
├── go/                        ← GO 通道区 root:root 0750；每候选
│   └── <cid12>/go                   go/<cid12>/go FIFO（root:10001 0640，
│                                    §4e）＋DELIVERED.json 留证
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
| 宿主门 | `xrg-p01-run stage-a/b` 预检（root） | `authz/authorization.json` 存在、mode 0400、属主 root:组 xrgauthz、JSON 键 status/attempt_id/task_card_sha256/one_attempt_only/granted_by 逐项等值 | 拒启，不创建容器，不留消费记录 |
| 容器门 | worker 容器内第一步（uid 10001，ro bind 挂同代 run-authz 副本） | 实读副本全文 sha256==同代 confirmed ＋绑定卡片 SHA/nonce（现 RUNBOOK 逻辑换挂载源） | 退出 2（设计使然），早于任何源读取 |

宿主门防"误触发起容器"，容器门防"入口被绕过/篡改后仍守授权"——两门独立失效。

**授权原件发布与容器副本（v7，条款③可执行化）**：

- **授权人可实际执行的独占发布路径**：`authz/` root:xrgauthz **2710**（setgid）；
  `authz/.staging/` root:xrgauthz **2733**（组可写、sticky——授权人可建不可互删）。
  授权人（xrgauthz 组成员，非 root 即可走全流程）：
  1. `open authz/.staging/<uuid>.json O_WRONLY|O_CREAT|O_EXCL`（0600，属主＝授权人）；
  2. 写 canonical JSON → fsync → close；
  3. `rename(.staging/<uuid>.json → authorization.json, RENAME_NOREPLACE)`。
  rename 穿越目录权限按 POSIX 由**父目录 w+x**决定：authz/ 组无 w ⇒ 只有 root
  或…——为保证"授权人真正能独立发布"，采用裁决过的形态：**authz/ 保持
  root:xrgauthz 2710，发布最后一步经 sudoers 第五条固定命令
  `/usr/local/bin/xrg-authz-publish <uuid>`（root 执行，仅做 NOREPLACE rename＋
  chmod 0400＋chown root:xrgauthz，无其它能力）**。第二次对同一目标发布原子
  失败 EEXIST；半成品在 rename 前于正式路径 ENOENT——**不可见**。
- **宿主门与原件属主/mode 统一**：发布完成后原件＝**root:xrgauthz 0400**；
  宿主门以 root 读取（属主），校验字段后其判定即代表该字节代次生效。§3 表中
  "mode 600/属主合法"统一改为 mode 0400、属主 root、组 xrgauthz。
- **同代产物（generation-bound）**：每次预检生成一对产物并以**候选 ID 命名**：
  `run-authz/gen-<cid12>/authorization.json`（root:10001 **0644**，copy_file_range
  +fsync）＋ `run-input/AUTHZ.confirmed.gen-<cid12>.json`（root 0644，含原件
  sha256＝副本回读 sha256＝nonce 输入）。ro bind 挂载源正是 `gen-<cid12>/`
  （T8 命令行钉死），容器读到的副本与其 nonce 期望值必然同代。**Stage A/B
  交错预检**：stage-a 用 `gen-<stageA-cid>`、stage-b 用 `gen-<stageB-cid>`，
  各候选各绑各代，互不覆盖；旧代目录保留至终态归档。
- **可读性与防替换**：副本文件 root:10001 0644 ⇒ 容器 uid 10001 直接可读；
  所在 `gen-*` 目录 root:root 0755、文件属主 root ⇒ xrgp01op 对目录无写权，
  **不能写/删/替换任何一代**；挂载 ro ⇒ 容器内亦只读。confirmed 摘要同代同绑。
- **容器内 UID 10001 核验**：容器门第一步实读同代副本全文、sha256 比对
  confirmed、验卡片 SHA/attempt/nonce——一致才继续；不一致 exit 2。
- **就绪时序**：Stage A worker 第一次读取 `/authorization/...` 之前，其
  gen- 对已在 T4 落盘（验收断言 confirmed mtime < create 时间戳）。

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
| T9a | **create 态静态核验**：`.Mounts` ↔ mount-plan.txt 逐条、HostConfig cgroup 参数 ↔ C；任一不符 → rm 容器、**释放 flock（锁文件保留不删）**、refusals 记录，**可重试**（未发过 start 请求） | root（入口） | `docker inspect`（create 态即含全部配置） | mount-plan.txt + C | flock 持有；**无消费记录** | 否——尚未 start，无任何执行 |
| T9b | **消费记录前置（条款②）**：T9a 全过后、**首次 `docker start` 请求之前**：`open(O_WRONLY\|O_CREAT\|O_EXCL)` 写 `pins/ATTEMPT_CONSUMED.json`（state=START_REQUESTED，container_id=create 返回值）→ fsync(fd) → **fsync(pins/ 父目录 fd)**；两步全成功才准发 start。EEXIST（半写残留）⇒ 读回校验：字节完整且合法 ⇒ 视为已消费立拒重试；字节截断/非法 JSON ⇒ 拒绝启动（`consumed_record_corrupt`），人工裁决，绝不自动覆盖。任一 fsync 失败 ⇒ 不发 start、unlink 本次半成品、rm 容器、释锁（视同预检拒绝，可重试） | root（入口） | — | C | **双 fsync 完成＝名额消耗点，先于 start 请求** | 否 |
| T9c | **等待机制（条款①，通道细节见 §4e）**：start 后入口轮询宿主读回四项 cgroup 值 `{cpu.max,memory.max,memory.swap.max,pids.max}` 逐字等于 C；nice/ionice 沿用现有**进程级核验**（candidate_supervisor check_limits 自报 worker_nice=getpriority、worker_ionice=`ionice -p` 查询回读，收据入 limits.json；io.weight 替代方案见 §8 待裁决）。每轮 0.2s、预算 10s。全过后按 §4e 交付 GO（rename 原子入位、宿主 O_RDWR 写入 `GO <nonce>` 后保持至 supervisor ack）。读回不符/超时 ⇒ stop+rm、终态 INVALID_READBACK；**宿主在放行前退出**：PID1 等待 open 至自身 deadline（start+20s）⇒ SUPERVISION_ABORTED_NO_GO exit 1 自行关闭 | root（入口） | cgroup fs ＋ supervisor 自报 limits 收据 | C | flock 持有，消费记录已存在 | 否——GO 未交付，supervisor 超时自毙 |
| T10 | **放行点（§4e）**：PID1 supervisor 于 deadline（start+20s）内 `open(/control/go,'O_RDONLY')` 成功且读到 `GO <nonce>`＋验 nonce ⇒ 先写 ack（同 fd `ACK <nonce>`）→ 容器门实读本代 run-authz 副本比对同代 confirmed → 通过才 Popen task_control；超时/open 失败/nonce 不符 ⇒ exit 1，全程零源读取 | 容器内 uid 10001（bind 属组映射 10001 可读） | GO nonce + 三方 pin | 容器门 | flock 持有 | **是——唯一读取窗口自 T10 开始，且必然在 T9c 读回通过之后** |
| T11 | 收尾：原始收据落 output/（uid 10001 写，操作员 r-x）；入口把消费记录更新为终态（COMPLETED/STOPPED/TIMEOUT/INVALID_*，fd+父目录双 fsync），释 flock（锁文件保留不删） | 容器 + root（入口） | — | — | 消费记录承载终态；flock 释放 | 窗口随进程终止关闭 |

⇒ 输入、镜像、挂载、资源四类核验（T9a）与四项 cgroup 读回＋进程级
nice/ionice 自报核验（T9c）全部结构性先于 GO 交付/放行（T10）；源读取只
存在于 T10–T11。GO 通道的创建时机、权限归属、身份绑定、一次性语义与双向
截止时间规则统一见 §4e；xrgp01op 对 go/ 区零写权 ⇒ 无法伪造放行。

## 4c. 锁与消费记录语义（v7，条款②统一）

| 记录 | 载体 | 生命周期 |
|---|---|---|
| **稳定独占锁** | `registry/<attempt>.flock`（O_CREAT 常驻文件，root 0600，**永不删除**） | stage-b 与 recover-orphan **同一文件**上 `flock(LOCK_EX\|LOCK_NB)`：拿不到即立拒。持锁范围＝T7 预检起 → 经 T8/T9a/T9b/T9c/T10 → 主循环观测至 worker 进程终止 → T11 终态 fsync 完成 ⇒ **从预检到收尾全程独占**；进程死亡（含 SIGKILL）内核自动释锁 |
| **持久消费记录** | `pins/ATTEMPT_CONSUMED.json`（O_EXCL＋fd fsync＋父目录 fsync，root） | T9b 双同步成功＝消耗点，先于首次 start 请求；终态更新（COMPLETED/STOPPED/TIMEOUT/INVALID_*）同样 fd+目录双 fsync |
| GO 通道 | `go/<cid12>/go` FIFO（root:10001 0640，§4e） | T8 create 前建道并随挂载固化于 mount-plan；换代 rename 原子换 inode（禁止 unlink 同名重建）；交付+ack 后 close ⇒ 二次读取阻塞或 EOF，不可重放 |

- **可重试窗口（T9a 及更早）**：T7 预检失败、T9a create 态静态核验不符——
  未写消费记录 ⇒ rm 容器、**释放 flock（锁文件保留不删）**、refusals/ 留明细，
  修正后可重试。
- **T9b 之后一律已消费**：双 fsync 完成的瞬间起，任何后续失败（start 不明、
  读回不符、超时、崩溃）只能走恢复/终态路径，不再释放重试资格。
- **终态更新中断**：入口若在"改写终态 fd fsync 后、父目录 fsync 前"崩溃，
  重启方读到的可能是旧内容 START_REQUESTED ⇒ 恢复子命令按 state≠终态且
  容器已不存在处理：补记 INVALID_FINALIZATION_LOST（双 fsync），仍为已消费。
- **并发**：双发 stage-b ⇒ flock 只有一个进 T8；另一路 `busy_or_consumed`
  立退且**不得触碰持锁方的候选**（无 stop/rm/inspect-set，其 go/ 与 gen- 代次
  字节不变）。start 至多一次：主证据＝发起 Docker 请求处的先记账日志（§4f.4），
  docker events 仅佐证状态。
- **完成后重复启动**：stage-b 起手三查（持锁后）：消费记录存在 ⇒ 立拒
  `attempt_consumed`；GO 件残留 ⇒ unlink（不影响判定）；原收据零触碰。
- **start 响应丢失（区分两型，条款②点名）**：恢复子命令拿到 flock 后先看
  原入口 PID（记录于 run-input/PID 文件，持锁期间有效）：
  1. *原入口仍存活*：说明它仍在 T9c 等待/主循环——恢复路径**只报告不接管**
     （`holder_alive` 退出），等其自行收敛；
  2. *原入口已退出*：读容器 `State.Status` 与 DELIVERED/ack 留证——若可确定
     **尚未放行**（GO 未交付）⇒ 恢复**只做核对与回收**：stop→rm、按读回/崩溃
     现场补记 INVALID_START_UNCONFIRMED 或 INVALID_READBACK，**绝不代补发 GO、
     绝不重发 start**；若落在"已交付、留证前"不可确定窗口 ⇒ 一律按**可能已
     放行**处理，走 §4f：核实确切 stopped/rm 后才补 INVALID_DELIVERY_UNVERIFIED，
     attempt 保持已消费；若已放行过（DELIVERED+ack 在案）⇒ 仅补终态。
- **create 后 ID 未落盘**：仍按 label `io.xiangrugu.synthetic-run=<suffix>`
  反查孤儿容器（run-real.sh :190 口径）stop→rm，保守补记 INVALID_PRESTART
  并永久消耗（验收 A-T8a 保留）。

## 4d. 快照挂载口径（复核意见④）

沿用现有 run-real.sh：源为**受控快照根下的任务卡指定版本目录**
`/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap`（ro bind →
`/data/imports/usedata/2026-10-07-bootstrap`），非 NAS 原路径直挂；演练与已验收
收据链同源。**本提案不改源路径**。若未来确需改（例如换快照根位置），属实现
差异而非本入口细节——单列为待裁决事项，须总指挥另行批准并重钉卡片绑定。

## 4e. GO 通道完整时序（v7，条款①可执行化）

**选型：命名 FIFO + rename 原子换 inode。** 各要素钉死如下：

| 维度 | 规则 |
|---|---|
| 创建时机 | **T8 `docker create` 之前**：入口在运行根建 `go/<container-id12>/`（root:root 0755）并 `mkfifo go/<cid12>/go`；create 命令行以 `--mount type=bind,src=$run/go/<cid12>,dst=/control,readonly` 挂入——因此 PID1 起跑时通道必已存在且路径随容器配置固化于 mount-plan.txt（T9a 静态核验项）。 |
| UID 10001 读权限 | bind 挂载下宿主 inode 的 uid/gid/mode 原样呈现。FIFO 属主 root、**组经 `chgrp 10001` ＋ `chmod g+r`（0640）**；镜像 USER 10001 即容器内唯一可读身份。操作员 xrgp01op 不在 10001 组、对 go/ 目录无 w/x 之外权限 ⇒ 不可写不可伪造。 |
| 宿主独占写 | 入口以 `O_RDWR` 打开自持 fd（既读又写：避免 writer-only open 阻塞语义歧义，并可同 fd 读 ack）。**open O_WRONLY/O_RDWR on FIFO 成功本身即排他证明**——实施轮约定第二个 writer open 直接拒绝（入口单实例＋flock 已保证）。 |
| 身份绑定 | 通道名钉本次 `container-id12`（create 返回值，T9b 消费记录同源）；`nonce = sha256(confirmed_sha ‖ container_id ‖ attempt)`——PID1 启动时从同代 confirmed 副本重算期望 nonce，GO 行内容必须逐字匹配 ⇒ 通道与候选一一对应、跨候选不可复用。 |
| 一次性生效 | 交付＝`write("GO <nonce>\n")` 后保持 writer 打开直至读到 `ACK <nonce>` 才 close。**二次读取实测预期**：supervisor 读完首行后即 exit/close 其 reader fd；此后任何新 reader `open(O_RDONLY)` 在无 writer 时**阻塞**（有 flock 下无人再开 writer），若曾有 reader 全部退出且 writer 已关，重新 open+read 返回 **EOF（0 字节读回）**——两种形态都拿不到第二份 GO；收据记录该实测值。 |
| 重建不脱节 | **禁止 unlink-then-mkfifo 同名重建**（会使已打开读者与旧 inode 脱节）。换代一律 `mkfifo go/<cid12>.new; rename()` 原子替换目录内条目——已打开的旧 FIFO fd 继续指向旧 inode 有效，新读者只能看到新件。旧代目录整体保留至 attempt 终态后才由 T11 归档移动，不原地删除。 |
| 双向截止 | 宿主侧：T9c 读回预算 start+10s 内未全过 ⇒ 不交付 GO，stop+rm。容器侧：PID1 等待 open/read 至 **start+20s** deadline；超时或 open 失败 ⇒ `SUPERVISION_ABORTED_NO_GO` exit 1。宿主若在交付前被杀：无人 open writer ⇒ PID1 open 永久阻塞到自身 deadline 关闭；宿主若在交付后、留证前被杀：见 §4f。 |

## 4f. GO 交付与留证之间宿主退出的恢复规则（v7，条款②补全）

入口正常序：交付 GO → 收 ack → 落 `go/<cid12>/DELIVERED.json`（双 fsync）。
若崩溃落在"已交付（ack 可能已达）而 DELIVERED 未落"窗口，**放行与否不可确定
⇒ 一律按"可能已放行"处理**：

1. 恢复子命令持 flock 后读容器 `State.Status`＋PID 树：**必须核实确切已
   stopped（或已回收 rm）**——running/created/状态漂移中一律先 stop→观察
   exited→rm，不得凭猜测补记；
2. 核实到位后才补终态 `INVALID_DELIVERY_UNVERIFIED`（fd+目录双 fsync），
   并从 output/ 既有收据反查 worker 是否曾实际启动（task_control 产物、
   exec 事件流命中），把结论附进同一收据；
3. attempt **保持已消费**，任何分支不重发 start、不补发 GO。
4. **start 请求计数主证据**＝入口在发起 Docker 请求处的本地日志行
   （`START_REQUEST cid=<id12> ts=…`，每次调用先记账后发起，fsync）；
   docker events 仅作容器状态佐证，不作计数依据。

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
1. `id xrgp01op` 无 docker 组；socket EACCES；`sudo -l -U xrgp01op` 恰五条固定
   argv 白名单（verify-inbox / stage-a / stage-b / recover-orphan /
   xrg-authz-publish）；`sudo -l -U <授权人>` 仅 xrg-authz-publish 一条。
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
- **A-T9a-1 锁竞争**：持锁方 stage-b 运行中另发 stage-b ⇒ 竞争方
  `busy_or_consumed` 立退，且**全程不得触碰持锁方候选**——断言竞争方对
  该 container ID 无 stop/rm/inspect-set 调用、其 go/<cid12>/ 与
  run-authz/gen-<cid12>/ 字节前后摘要不变（audit/exec 日志双证）。
- **A-T9a-2 静态配置拒绝**：注入 `.Mounts` 或 HostConfig 与 plan/C 不符 ⇒
  rm 容器、**flock 释放而锁文件仍在**（ls 证据）、refusals/ 明细、无消费
  记录；修正后重试成功进入 T9b。
- **A-T9b 后已消费（拆分②）**：双 fsync 完成后注入任意失败（start 超时、
  读回不符、终态更新崩溃）→ 一律不得回到可重试态：stage-b 再发起立拒，
  终态只能经恢复路径补记，消费记录 fd+目录双同步痕迹入收据。
- **A-T9b 半写/同步失败**：kill 于 write 中途 → 重启 stage-b 读到截断 JSON
  ⇒ `consumed_record_corrupt` 拒绝且无自动覆盖（人工裁决标记文件生成）；
  注入父目录 fsync 失败（模拟 EIO）⇒ 不发 start、半成品 unlink、可重试。
- **A-T9c 等待机制三态（条款①，主证据＝按候选身份关联的进程事件流）**：
  注入 ① 四项 cgroup 任一读回不符、② 入口在轮询中被 SIGKILL、③ 读回预算
  超时。**主证据**：start 请求发出**之前**即挂 exec/fork 采集器（按
  `docker-<id>.scope` cgroup inode 关联过滤，事件含 comm/pid/ts），三态各自
  要求事件流中**除 PID1 supervisor 外零命中**——即便 task_control 瞬时启动
  也必被捕获，不依赖时间线推断。采集器随收据输出 `capture_status`
  （armed_at 早于 start 请求时间戳、events_seen、dropped 计数）；**dropped>0
  或 arm 迟于 start ⇒ 该态验收判无效重跑**。辅助证据（不作唯一依据）：源
  访问审计（audit -w ＋ fanotify 零命中）、output/ 无 task_control 产物。
  ②另证 PID1 至 deadline 打印 SUPERVISION_ABORTED_NO_GO exit 1。
  **正常对照**：同采集器下一次成功放行运行须看到 worker exec 事件（证明
  采集面确实可见 worker）＋GO 交付时间戳晚于四项 cgroup 读回与 nice/ionice
  自报通过时间戳，收据逐项列读回原文。
- **A-GO 语义（§4e 逐项实测入收据）**：①通道在 create 前已存在且
  mount-plan 含之；②UID 10001 实开成功、xrgp01op open(O_WRONLY) EACCES；
  ③二次读取实测记录实际形态（阻塞至超时或 EOF 0 字节）——两种都不得取回
  第二份 GO；④换代 rename 测试：旧代读者仍持旧 inode 正常收 ack，新读者
  只见新件；⑤nonce 由 confirmed+cid+attempt 重算匹配，伪造行被拒。
- **A-T8~T10 中断恢复（条款②）**：
  ① *ID 未落盘*：create 后 kill → recover-orphan label 反查孤儿、stop→rm、
     补记 INVALID_PRESTART；此后 stage-b 立拒（验收保留）。
  ② *start 响应丢失，原入口仍存活*：恢复调用得 `holder_alive` 只报告退出，
     主循环不受扰继续收敛终态。
  ③ *start 响应丢失，原入口已退出且未放行*：恢复 stop→rm、补记
     INVALID_START_UNCONFIRMED；断言恢复路径日志无 GO 写、无 start 请求。
     **start 计数主证据＝入口发起 Docker 请求处的先记账日志**（§4f.4，grep
     计数 ≤1），docker events 仅佐证容器状态轨迹。
  ③b *交付后留证前宿主退出（§4f 不可确定窗口）*：kill 于 write(GO)+ack
     之后、DELIVERED.json 落盘之前 → 恢复必须按"可能已放行"处理：核实
     确切 stopped/rm 后才补 INVALID_DELIVERY_UNVERIFIED，附 exec 事件流
     反查结论；attempt 保持已消费，后续 stage-b 立拒。
  ④ *flock 互斥双向*：stage-b 持锁期 recover-orphan 拿不到锁即拒；恢复持锁
     期 stage-b 同样立拒（两侧各验一次，锁文件始终存在不被删）。
- **A-AUTHZ（条款③）**：
  ① 授权人（非 root，xrgauthz 组）全流程实走通：staging O_EXCL 临时件 →
     fsync → `sudo xrg-authz-publish <uuid>` 成功发布为 root:xrgauthz 0400；
     同目标第二次 publish 原子失败 EEXIST 留证；publish 前正式路径 open
     ENOENT（半成品不可见）记录在案。
  ② 同代绑定：交错预检演练——stage-a(gen-A) 与 stage-b(gen-B) 各绑各代
     FIFO/gen- 副本互不覆盖；**容器内 UID 10001 实读全文 sha256 == 同代
     confirmed == 宿主门记录**三方一致入收据；confirmed mtime < 对应候选
     create 时间戳（Stage A 首读前就绪）。
  ③ 操作员破坏面：xrgp01op 对 authz/、.staging/、run-authz/gen-*、go/ 的
     写/删/rename/chmod 全 EACCES/EPERM（audit 留痕）；替换原件后再预检 ⇒
     新生成代次摘要随之变化并被卡片 SHA/nonce 绑定校验把关。

- **A-R 越权写**：xrgp01op 对 run-input/pins/registry/authz/output 的写删 chmod
  全部 EACCES，audit 留痕。
- **A-F 回退**：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01
  /usr/local/bin/xrg-p01-run; setfacl -b <运行根>` 后回到现状。

## 7. 残余风险与前提声明

- 本提案的 cgroup 读回路径按 **cgroup v2 unified**（32 现 host 已核实口径）
  书写；若实施轮发现混合层级，路径以 `docker inspect .GraphDriver`/
  `systemd.detect_v2` 实测为准修订 §4b，不改语义。
- I/O 优先级采用进程级 ionice 核验（§8 待裁决项除外）；v5/v6 关于
  `/proc/io_scheduling`、`io.weight` 作为核验面的表述均已废止。


- root ssh 通道仍在：定位为管理员安装/审计通道；是否收紧另列裁决项。
- docker 守护进程本身仍是全局能力——本方案收缩的是**操作者可达面**，不声称
  消除 daemon 权力本身。

## 8. 单列待裁决事项

- **I/O 优先级核验口径**：本提案沿用现有**进程级 ionice 核验**
  （candidate_supervisor check_limits：`ionice -c 3` 设置＋`ionice -p` 查询
  回读＋limits.json 自报 worker_ionice/worker_nice；nice 以 `os.getpriority`
  为准——如解析 stat 则为第 19 字段，v6 所写"field 7"系误标，本版更正）。
  若总指挥拟改以 cgroup v2 `io.weight` 作宿主侧核验面，属接口变更，需茶香
  另行裁决后再修订 §4b/§6；本版不改语义。
