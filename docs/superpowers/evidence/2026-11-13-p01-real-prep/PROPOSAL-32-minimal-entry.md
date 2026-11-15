# 提案 v14（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（迭代自 v13/e15c2c4）。本轮及既往各轮均未登录或修改
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
> **v5（回应 1fa11e5 复核的三个实施条件）**：①T9–T10 重写为
> 两段等待机制——宿主实际 cgroup 读回全过之前 worker 无法启动，验收覆盖
> 读回失败/宿主退出/等待超时三态且均须证明 worker 从未启动；②消费记录提前到
> 首次 docker start 请求之前 fsync 落盘，配置预检拒绝仍可重试，恢复子命令与
> 活跃执行经运行锁互斥，补 ID 未落盘、启动结果不明两种中断；③授权原件独占
> 创建方式与容器 uid 10001 只读同字节副本的确认链写死，执行账号对原件/副本
> 均零写权。｜as_of 2026-11-14
> **v7（回应 4becf3d 复核的三条）**：①新增 §4e GO 通道完整时序
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
> **v8（回应 72c4a44 复核的三条）**：①引入入口在 create 前生成的
> 唯一代次标识 GEN-ID——GO 路径、授权副本、confirmed 摘要全部按 gen-<GEN-ID>
> 固定，GEN-ID 随 create 写入候选标签；create 返回后、start 前把完整容器 ID
> 绑定进 gen 记录，读回/放行/恢复三方共验同一绑定；Stage A/B 时序与 ID 未落盘
> 恢复验收统一到该口径。②GO 改纯单向通道（去同 FIFO 回写 ACK；如需回执另定
> 独立路径与权限），非阻塞等待/截止/EOF 与部分消息/一次性消费规则写死，已绑定
> 候选的通道不换 inode（换代次＝新 GEN 目录，不是 rename 换件）；A-T9c 事件流
> 允许已声明预检进程白名单，说明采集器 start 前启用并经 gen 标签关联启动时才
> 出现的 cgroup。③§1/§3/T3/§6 统一为操作员四条固定入口、发布命令只授授权人；
> xrg-authz-publish 改为从调用者暂存件读取校验→root 独占目录建新 inode→先固
> 定字节/属主/mode 并同步→RENAME_NOREPLACE 发布＋父目录同步；staging mode 描述
> 修正（0664 sticky，非 2733）。｜as_of 2026-11-14
> **v9（回应 34b3175 复核的三条）**：①§4e/T10/A-GO 按 Linux FIFO
> 真实语义统一——reader open 成功不代表 writer 在场、首次空读 EAGAIN 不得提前
> 结束等待、部分帧后断链即拒绝、ENXIO 归宿主非阻塞写端；/control 目录权限改
> 0710＋FIFO 0644 并写明 UID 10001 的实际组身份与遍历路径；A-T9c 删"除 PID1
> 外零命中"旧句，采集器先全量留存早期事件、再按实际出现的 cgroup 身份关联。
> ②create 前持久 PREPARED 收据（attempt+GEN+阶段），ID 未落盘时以该记录↔
> 候选标签↔固定创建配置三方核对，BOUND 后才用完整容器 ID 三元组核对；零匹配/
> 多匹配/状态查询失败处置写死；DELIVERED 只证明宿主写出 GO——入口已退出时
> 无论 DELIVERED 是否存在都必须核实确切停止/回收才补终态；验收增补
> "DELIVERED 已落盘但候选仍运行"恢复分支。③.staging 目录权限修正为
> root:xrgauthz 0770，§2/§3/T3 统一并验证非 root 授权人可建件、操作员不可
> 访问不可调用发布；就绪时序改用 create 前 PREPARED 收据与 start 前 BOUND
> 收据两段正向断言，移除对最终 gen.json mtime 的反向断言。｜as_of 2026-11-14
> **v10（回应 486309e 复核的两条）**：①/control 挂载根与 FIFO
> 权限按容器实际映射身份统一为 root:10001 目录 0710／FIFO 0640（无 UID/GID
> 重映射前提写明），以实际 UID/GID 10001 验证遍历与读端打开、以操作员身份
> 验证写与替换被拒；T10/§4c/§4e/A-GO 统一帧校验规则——零字节阶段 read=0
> （EOF）与 EAGAIN 一律等到截止；开始收帧后 EAGAIN 继续等、EOF 时校验整段
> 字节恰为唯一合法 GO 帧；截断/附加字节/逾时均拒；补验"完整行后 writer 延迟
> 追加"分支；ENXIO 只在无 reader 的写端记录。②PREPARED 查找结果与候选回收
> 结果分离：单次零匹配仅代表当时未见候选，create 是否在途不明 ⇒ 持久标记
> RECOVERY_PENDING 并阻止再次启动，取得确证后才收尾；多匹配/配置不符/查询
> 失败保留现场升级人工，**禁止仅凭标签批量 stop/rm**；DELIVERED 只证明宿主
> 写出 GO，确认确切候选 stopped/deleted 后才补终态，unknown/daemon 超时保持
> 待恢复；exec 事件只回答 worker 是否启动，TIMEOUT 须有独立截止证据；验收
> 覆盖 create 响应丢失且首查为零、同标签多匹配、DELIVERED 已落盘但候选仍
> 运行；任何恢复分支不补 GO、不重发 start。｜as_of 2026-11-14
> **v11（回应 8337120 复核的三条）**：①未完成收尾的 PREPARED/BOUND
> 记录本身即构成再启动阻断（不依赖 recover-orphan 先写 RECOVERY_PENDING，该
> 文件降级为进度注记）；新入口与恢复在同一 flock 边界内完成"检查→核实→先持
> 久 RESOLVED→后解除阻断"，T9a 配置拒绝的重试资格须待确切候选回收并留证后
> 恢复；验收补 ⑤崩溃后先重发 stage-b、⑥核实后收尾前再中断两分支，均断言零
> 第二次 create/start。②§4c 删除"DELIVERED 在案⇒仅补终态"旧分支，统一引用
> §4f：DELIVERED 只证明宿主写出 GO；确切候选停止/删除才补终态；查询不明保持
> 阻断；恢复不补 GO、不重发 start。③保留 EOF 才校验整帧的状态机；§4e/A-GO
> 分列无 writer 时 read=0 与有 writer 暂无数据时 EAGAIN（均等到截止）；UID/
> GID 10001 读权验收以实际只读挂载后的容器内 /control/go 为准，宿主 setpriv
> 降为补充。另修正正文标题滞留 v9 的问题。｜as_of 2026-11-14
> **v12（回应 eb88a76 复核的三条）**：①A-T8~T10⑤ 主故障点移至
> create 请求已发出、T9b 尚未落盘，覆盖 PREPARED 未 BOUND 与 BOUND 后未消费
> 两个子态，断言消费记录与 RECOVERY_PENDING 均不存在时先重发 stage-b 得
> recovery_pending、零新增 create/start，再调恢复。②新增 §4g 统一锁序（A→B
> 固定方向）与收尾五步序（终止→核实→RESOLVED 双 fsync→终态→释锁），T4/T5/
> T9a/T11 与 §4c/§4f 同口径；定义 RESOLVED 有效性判定（全量解析＋双字段匹配
> ＋published 尾标），半写/损坏/同步不明一律无效＝阻断维持；验收 ⑥ 增补
> 「RESOLVED 已出现但发布未完成」中断窗与 ⑦ 锁序/五步齐备演练。③删除 §4e
> 一次性消费旧句；A-GO 分别实测无 writer read=0 与 writer 在场未写 EAGAIN，
> 两者均不得提前退出。｜as_of 2026-11-14
> **v13（回应 8b43ff9 复核的两条）**：①RESOLVED 发布与生效分离
> ——完整 JSON＋published:true 只证明内容完整；上次入口中断/同步结果不明时，
> 新入口持 B 锁保持阻断，由恢复路径对同一代次重新核实并完成文件与父目录同步
> 后才生效（§4g.3/.4）；验收 ⑥(b) 增补"正式件已可见、内容与尾标完整、父目录
> 同步未完成或失败"用例，断言无新增 create/start。②统一 T9a/T5/T11/§4g/⑥(c)
> 收尾条件：该路径要求的 refusals/终态/成功收据必须持久化于释锁之前；RESOLVED
> 有效而收尾记录未落 ⇒ 新入口仍阻断、由恢复补齐；⑥(c) 恢复前先重发 stage-b
> 证明零新增请求；④ 把持锁期竞争（busy）与原入口退出后的 recovery_pending
> 分为两案，返回码与日志标记不同源。｜as_of 2026-11-14
> **v14（本 revision，回应 e15c2c4 复核）**：§4g.3/.4 改为不依赖推断上一进程
> 退出方式的单条重入规则——发布定式＝临时件一次写齐最终内容与权限（含
> published 尾标）→文件 fsync→原子 rename→父目录 fsync，双同步后不再改尾标；
> 新入口持 B 锁检查同一代次的 RESOLVED＋该路径要求的终态/refusals/Stage A
> 收据：缺失/损坏/绑定不一致即 recovery_pending 交恢复补齐；记录齐全也须重新
> 确认候选状态并对所需文件与父目录补同步，核实或同步失败保持阻断，全部成功
> 后才按原有消费/重试规则决定去留。验收 ⑥ 扩为五窗并补测"所有记录均可见、
> 最后一次同步结果未知"：注入补同步失败断言零新增 create/start；补同步成功后
> T9a 拒绝径才可重试、已消费 attempt 仍拒；另设正常收尾对照。仅动 §4g.3/.4、
> 对应验收与 README 指针。｜as_of 2026-11-14
> **v6（回应 4ae88ec 复核的三个条款）**：①GO 选定为一次性命名
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
   `/usr/local/bin/xrg-p01-run`（sudoers 白名单钉到完整 argv）。**操作员
   xrgp01op 恰四条固定入口**：verify-inbox / stage-a / stage-b /
   recover-orphan；`xrg-authz-publish` **只授权给授权人（xrgauthz 组）**，
   不在操作员白名单（§3/§6 同口径）。
3. 真实执行的独立授权门不被入口旁路（见 §3 双门）。

## 2. 目录分区：上传区与运行区分离

```text
/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a/
├── inbox/                     ← 操作员唯一可写区（staging 上传落点）
│   └── source-green-v1/…      （48 项包 + INPUTS.sha256）
├── run-input/                 ← 管理员核验区：root:root 0755，xrgp01op 无写权
│   ├── source-green-v1/       （由入口以 root 从 inbox 复制并 sha256sum -c 后固化）
│   └── VERIFIED.sha256        （核验收据，含核验时间）
├── authz/                     ← 授权目录 root:xrgauthz 0750；
│   ├── .staging/                  暂存区 root:xrgauthz 0770+S_ISVTX（组
│   │   └── <uuid>.json            rwx 可入可建，sticky 防互删），授权人
│   └── authorization.json         0600 建件；publish 四步只认调用者（§3）
│                                  ；原件 root:xrgauthz 0400
├── run-authz/                 ← 同代副本区 root:root 0755；每候选一对产物
│   └── gen-<GEN-ID>/              gen-<GEN-ID>/authorization.json（root:10001
│       ├── authorization.json     0644）＋gen 记录（含 GEN-ID、attempt、
│       └── gen.json               create 后回填的完整容器 ID，§4e）
├── go/                        ← GO 通道区 root:root 0750；每候选单向道
│   └── gen-<GEN-ID>/go            FIFO（root:10001 0640，§4e）＋
│       └── go, DELIVERED.json     DELIVERED.json 留证
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
| 宿主门 | `xrg-p01-run stage-a/b` 预检（root） | `authz/authorization.json` 存在、mode 0400、属主 root:xrgauthz（§3 publish 产物）、JSON 五键逐项等值 | 拒启，不创建容器，不留消费记录 |
| 容器门 | worker 容器内第一步（uid 10001，ro bind 挂本代 gen-<GEN-ID> 副本） | 实读副本全文 sha256==本代 gen.json confirmed ＋卡片 SHA/attempt/GEN-ID/nonce（现 RUNBOOK 逻辑换挂载源） | 退出 2（设计使然），早于任何源读取 |

宿主门防"误触发起容器"，容器门防"入口被绕过/篡改后仍守授权"——两门独立失效。

**授权原件发布与容器副本（v8，条款③）**：

- **权限布局（v9 定稿）**：`authz/` root:xrgauthz **0750**（授权人经组位读
  目录与原件所在名、不可写）；`authz/.staging/` root:xrgauthz **0770＋
  S_ISVTX**——目录需 w 才能 create/unlink，故组位必须给 **rwx**（v8 的 0664
  缺目录执行位，非 root 授权人根本无法进入/建件，本版修正）；sticky 使
  授权人之间不能删改他人暂存件（删除仅文件属主或目录属主 root 可为）。
  xrgp01op 不在 xrgauthz 组 ⇒ 对 authz/ 连遍历都不可得（EACCES）。原件
  最终态 **root:xrgauthz 0400**。
- **发布流程（唯一被承认的路径）**：授权人
  1. `open authz/.staging/<uuid>.json O_WRONLY|O_CREAT|O_EXCL`（0600，属主＝授权人）；
  2. 写 canonical JSON → fsync → close；
  3. `sudo xrg-authz-publish <uuid>`（**仅授权人白名单**；操作员调用 EPERM）。
     该固定程序以 root 执行且只做四步：
     a. 从**调用者的** `.staging/<uuid>.json` 读取全文并按宿主门同一 schema
        校验字段（status/attempt_id/task_card_sha256/one_attempt_only/granted_by）；
     b. 在 root 独占目录 `authz/.publish-tmp/`（root:root 0700）**新建 inode**
        写入校验后的字节，先固定最终内容＋chown root:xrgauthz＋chmod 0400，
        fd fsync ＋ `.publish-tmp` 父目录 fsync；
     c. `rename(..., RENAME_NOREPLACE)` 到 `authz/authorization.json`；
     d. fsync `authz/` 父目录。
     二次发布原子失败 EEXIST；半成品永不出现在正式路径（新 inode 在 root
     独占区成形，非调用者可写的 staging rename）；**发布后原暂存件保留**
     ——其后续任何改动不影响已发布原件（不同 inode）。崩溃于 b/c/d 任一点：
     c 前 ⇒ 正式路径仍 ENOENT 可重发；c 后 d 前 ⇒ 件已在但父目录未同步，
     publish 幂等检测目标存在且摘要一致则仅补 d。
- **同代产物按 GEN-ID 绑定（条款①）**：入口每次预检生成唯一代次标识
  `GEN-ID = sha256(attempt ‖ 随机 128bit ‖ ts)`，一对产物固定命名：
  `run-authz/gen-<GEN-ID>/authorization.json`（root:10001 0644，copy_file_range
  +fsync）＋ `gen-<GEN-ID>/gen.json`（含 GEN-ID、attempt、原件 sha256＝副本
  回读 sha256、confirmed 时间）；GO 道亦建在 `go/gen-<GEN-ID>/go`。**create
  命令行把 GEN-ID 写入候选标签** `io.xiangrugu.attempt-gen=<GEN-ID>`；
  create 返回后、**start 之前**，入口把完整容器 ID 回填进 gen.json 并双同步
  （state=BOUND）——此后读回核验、GO 交付、恢复回收都以 `attempt+GEN-ID+
  container_id` 三元组共同校验（docker inspect Labels ↔ gen.json ↔ 消费记录）。
  nonce = sha256(confirmed_sha ‖ GEN-ID ‖ attempt)。Stage A/B 交错预检各自
  独立 GEN 代次，互不覆盖；旧 gen 目录只读保留至终态归档。
- **可读性与防替换**：副本 root:10001 0644 ⇒ 容器 uid 10001 可读；gen 目录
  与 go 目录 root:root 0755/0750 ⇒ xrgp01op 不能写/删/替换任何一代；挂载 ro
  ⇒ 容器内只读。
- **容器内 UID 10001 核验**：容器门实读**本代**副本全文、sha256 比对 gen.json
  confirmed、验卡片 SHA/attempt/GEN-ID/nonce 一致才继续；不一致 exit 2。
- **就绪时序（两段正向证明，v9）**：①`gen-<GEN-ID>.PREPARED.json` 于
  **create 请求发出之前**已双 fsync 落盘——其内嵌本代副本与 gen.json 的
  sha256，证明产物先于候选存在；②BOUND 收据于 **start 请求之前**写入。
  不再使用"最终 gen.json mtime < create"的反向断言（BOUND 回填会合法地
  刷新 mtime，反向断言不成立且无必要）。

## 4b. 统一时序表（正文与验收共用；T# 即验收编号）

可信清单来源缩写：**P** = `pins/INPUTS.admin.sha256`（管理员从已审查提交独立
固定的权威 48 项清单）；**B** = 包内附送 `INPUTS.sha256`（仅为被检对象）；
**C** = 入口脚本 root 常量（attempt、三 SHA、镜像 .Id、资源值、挂载面）。

| T# | 步骤 | 执行者/写入方 | 读取来源 | 可信清单 | 锁/消费记录 | worker/源可读？ |
|---|---|---|---|---|---|---|
| T1 | scp 上传包至 inbox | 操作员 xrgp01op（唯一可写区） | Windows packet-real.tar.gz | — | 无 | 否 |
| T2 | `sudo xrg-p01-run verify-inbox` | **root（入口）**：复制 inbox→run-input、双清单核验、chown root 0755、写 VERIFIED.sha256 | inbox 整树 | **先 P==B 逐字节，再按 P 验 48 文件**＋C 三 SHA | 无 | 否 |
| T3 | 发布授权 | **仅授权人**在 `.staging/`（0770+sticky）O_EXCL 建件 → write → fsync → `sudo xrg-authz-publish <uuid>` 四步发布（§3）；二次 EEXIST；操作员不可访问该树亦无 publish 权 | — | 内容绑定卡片 SHA+attempt | 无 | 否 |
| T4 | `stage-a` 宿主预检 | root（入口）：校验原件字段→**生成 GEN-ID 与本代产物**（run-authz/gen-<GEN>/ 副本＋gen.json＋go/gen-<GEN>/ FIFO，T5/T8 首读前就绪） | run-input + authz 原件 | P + C | **锁序（§4g）**：先 `stage-a.flock`，凡涉本 attempt 代次记录读写即升级取 `attempt.flock`（顺序固定 a→b，绝不反向）；成功收据存在则幂等跳过 | 否——Stage A 容器无快照挂载 |
| T5 | Stage A 容器 materialize | uid 10001 | run-input ro、**本代 gen-<GEN> 副本** ro | 容器门实读副本 sha256==本代 gen.json confirmed＋卡片 SHA/attempt/GEN/nonce | 同 T4 锁序 | 否。**收尾（§4g.2）**：Stage A 容器 exited→核实该确切容器状态→写本代 RESOLVED（双 fsync）→Stage A 成功/失败收据持久化（先于释锁）→释两把锁；RESOLVED 有效但收据未落 ⇒ 新入口仍阻断、由恢复补齐（§4g.4）；失败/中断走 §4f 同一纪律 |
| T6 | 操作员核对 controller-pins.txt 三 pin | 人（离线） | output/ Stage A 收据 | — | 无 | 否 |
| T7 | `stage-b` 宿主预检（**持稳定锁**） | root（入口） | run-input + Stage A 成功收据 + authz 原件 → **新 GEN-ID 与本代产物**（与 stage-a 代次相互独立） | P + C + Stage A 收据 pin | `flock(LOCK_EX\|LOCK_NB)` on `registry/<attempt>.flock`（O_CREAT 常驻不删；§4c 持锁范围）；此步失败→释锁、落 refusals，**不写消费记录** | 否 |
| T8 | **create 前持久准备收据 + docker create** | root（入口）：create 请求发出前先写 `run-authz/gen-<GEN-ID>.PREPARED.json`（attempt、GEN-ID、阶段＝pre-create、完整创建配置摘要含标签/挂载计划，fd+目录双 fsync），再执行 create（`--label io.xiangrugu.attempt-gen=<GEN-ID>`；bind 源＝本代 go/gen-<GEN>（/control ro）与 run-authz/gen-<GEN>（/authorization ro）；快照版本目录口径见 §4d） | 命令行由入口拼装 | 生成 mount-plan.txt + PREPARED 收据 | flock 持有 | **进程尚未运行**。create 返回后、start 前：完整容器 ID 回填 gen.json（state=BOUND，双 fsync）——此后三元组 attempt+GEN-ID+container_id 方可用于核对 |
| T9a | **create 态静态核验**：`.Mounts` ↔ mount-plan.txt 逐条、HostConfig cgroup 参数 ↔ C；任一不符 → rm 容器→**核实该候选 exited/deleted→写本代 RESOLVED（双 fsync）→refusals 记录持久化（fd+父目录双 fsync，先于释锁）→再释 flock（锁文件保留不删）**；重试资格须待 RESOLVED 生效**且** refusals 已持久（§4g.4；未发过 start 请求） | root（入口） | `docker inspect`（create 态即含全部配置） | mount-plan.txt + C | flock 持有；**无消费记录** | 否——尚未 start，无任何执行 |
| T9b | **消费记录前置（条款②）**：T9a 全过后、**首次 `docker start` 请求之前**：`open(O_WRONLY\|O_CREAT\|O_EXCL)` 写 `pins/ATTEMPT_CONSUMED.json`（state=START_REQUESTED，container_id＋GEN-ID 取自已 BOUND 的 gen.json）→ fsync(fd) → **fsync(pins/ 父目录 fd)**；两步全成功才准发 start。EEXIST（半写残留）⇒ 读回校验：字节完整且合法 ⇒ 视为已消费立拒重试；字节截断/非法 JSON ⇒ 拒绝启动（`consumed_record_corrupt`），人工裁决，绝不自动覆盖。任一 fsync 失败 ⇒ 不发 start、unlink 本次半成品、rm 容器、释锁（视同预检拒绝，可重试） | root（入口） | — | C | **双 fsync 完成＝名额消耗点，先于 start 请求** | 否 |
| T9c | **等待机制（条款①，通道细节见 §4e）**：start 后入口轮询宿主读回四项 cgroup 值 `{cpu.max,memory.max,memory.swap.max,pids.max}` 逐字等于 C；nice/ionice 沿用现有**进程级核验**（candidate_supervisor check_limits 自报 worker_nice=getpriority、worker_ionice=`ionice -p` 查询回读，收据入 limits.json；io.weight 替代方案见 §8 待裁决）。每轮 0.2s、预算 10s。全过后按 §4e 交付 GO（单向道：宿主 open O_WRONLY\|O_NONBLOCK 轮询至 reader 出现，写一行 `GO <nonce>` 即 close）。读回不符/超时 ⇒ stop+rm、终态 INVALID_READBACK；**宿主在放行前退出**：PID1 等待 open 至自身 deadline（start+20s）⇒ SUPERVISION_ABORTED_NO_GO exit 1 自行关闭 | root（入口） | cgroup fs ＋ supervisor 自报 limits 收据 | C | flock 持有，消费记录已存在 | 否——GO 未交付，supervisor 超时自毙 |
| T10 | **放行点（§4e 状态机，单向）**：PID1 supervisor open(O_RDONLY\|O_NONBLOCK) `/control/go`（root:10001 0710 目录遍历＋0640 组位可读）；read 两阶段——零字节阶段 read=0/EAGAIN 均等到 deadline；收帧阶段 EAGAIN 续等、EOF 时终校验整段恰为唯一 `GO <nonce>\n` ⇒ 容器门实读本代副本比对 gen.json confirmed → 通过才 Popen task_control；截断/附加字节/nonce 不符/deadline（start+20s）未到完整帧 ⇒ exit 1，全程零源读取。**不回写 ACK** | 容器内 uid/gid 10001（无 userns-remap 前提） | GO nonce + 三方 pin | 容器门 | flock 持有 | **是——唯一读取窗口自 T10 开始，且必然在 T9c 读回通过之后** |
| T11 | 收尾（§4g 统一序）：原始收据落 output/（uid 10001 写，操作员 r-x）；worker 进程终止→**核实确切候选 exited**→写本代 RESOLVED（双 fsync）→消费记录更新终态（COMPLETED/STOPPED/TIMEOUT/INVALID_*，fd+父目录双 fsync，**先于释锁**）→释 flock（锁文件保留不删） | 容器 + root（入口） | — | — | RESOLVED 先于终态、终态先于释锁；RESOLVED 有效但终态未落 ⇒ 阻断维持（§4g.4）；消费记录承载终态 | 窗口随进程终止关闭 |

⇒ 输入、镜像、挂载、资源四类核验（T9a）与四项 cgroup 读回＋进程级
nice/ionice 自报核验（T9c）全部结构性先于 GO 交付/放行（T10）；源读取只
存在于 T10–T11。GO 通道的创建时机、权限归属、身份绑定、一次性语义与双向
截止时间规则统一见 §4e；xrgp01op 对 go/ 区零写权 ⇒ 无法伪造放行。

## 4c. 锁与消费记录语义（v12，条款②统一）

| 记录 | 载体 | 生命周期 |
|---|---|---|
| **稳定独占锁** | `registry/<attempt>.flock`（O_CREAT 常驻文件，root 0600，**永不删除**） | stage-b 与 recover-orphan **同一文件**上 `flock(LOCK_EX\|LOCK_NB)`：拿不到即立拒。持锁范围＝**起手代次检查（§4f.1 阻断判定）**→ T7 预检 → T8/T9a/T9b/T9c/T10 → 主循环观测至 worker 进程终止 → T11 终态 fsync 完成 ⇒ **从检查到收尾全程独占**；recover-orphan 的核实与 RESOLVED 写入亦在同一锁内 ⇒ 新入口与恢复不可能交错；进程死亡（含 SIGKILL）内核自动释锁 |
| **持久消费记录** | `pins/ATTEMPT_CONSUMED.json`（O_EXCL＋fd fsync＋父目录 fsync，root） | T9b 双同步成功＝消耗点，先于首次 start 请求；终态更新（COMPLETED/STOPPED/TIMEOUT/INVALID_*）同样 fd+目录双 fsync |
| **未完成代次记录（自带阻断）** | `gen-<GEN-ID>.PREPARED.json` / `gen.json`（state∈{PREPARED,BOUND}，未收到 §4f.4 的 RESOLVED 收尾标记） | **记录本身即阻断**：任何 stage-a/stage-b 在持 flock 后的起手检查里发现本 attempt 存在未 RESOLVED 的代次 ⇒ 直接拒绝 `recovery_pending`——**不依赖 recover-orphan 是否已写 RECOVERY_PENDING**（该文件降级为恢复进度注记，非阻断依据）。解除唯一路径＝§4f.4"先核实落盘、后解除阻断"两步序；全链路统一顺序与锁序见 §4g |
| GO 通道 | `go/gen-<GEN-ID>/go` FIFO（root:10001 0640，§4e 单向） | T8 create 前建道并随挂载固化；BOUND 后 inode 终生不换（换代＝新 GEN 目录）；write+close 即消费 ⇒ 二次读按 §4e 状态机等到 deadline 后拒（ENXIO 仅记录于无 reader 写端），不可重放 |

- **可重试窗口（T9a 及更早，v11 收紧）**：T7 预检失败（无代次记录）可直接
  重试。**T9a create 态静态核验不符的重试资格不是即时的**：PREPARED 已落盘
  ⇒ 该代次进入"未 RESOLVED"状态并自带阻断——必须走 §4f 对**确切候选**完成
  stop→rm→核实结果先持久落盘（RESOLVED）**且 refusals 收据持久化（释锁前，
  §4g.2）**后，重试资格才恢复；期间任何新 stage-* 一律 `recovery_pending`
  拒绝。入口若在 rm 之前崩溃，同一阻断逻辑天然覆盖（记录仍在、未 RESOLVED）；
  RESOLVED 在场但 refusals/终态未落亦不解除（§4g.4）。
- **T9b 之后一律已消费**：双 fsync 完成的瞬间起，任何后续失败（start 不明、
  读回不符、超时、崩溃）只能走恢复/终态路径，不再释放重试资格。
- **终态更新中断**：入口若在"改写终态 fd fsync 后、父目录 fsync 前"崩溃，
  重启方读到的可能是旧内容 START_REQUESTED ⇒ 恢复子命令按 state≠终态且
  容器已不存在处理：补记 INVALID_FINALIZATION_LOST（双 fsync），仍为已消费。
- **并发**：双发 stage-b ⇒ flock 只有一个进 T8；另一路 `busy_or_consumed`
  立退且**不得触碰持锁方的候选**（无 stop/rm/inspect-set，其 go/ 与 gen- 代次
  字节不变）。start 至多一次：主证据＝发起 Docker 请求处的先记账日志（§4f.7），
  docker events 仅佐证状态。
- **完成后重复启动**：stage-b 起手三查（持锁后）：消费记录存在 ⇒ 立拒
  `attempt_consumed`；GO 件残留 ⇒ unlink（不影响判定）；原收据零触碰。
- **start 响应丢失（区分两型，条款②点名）**：恢复子命令拿到 flock 后先看
  原入口 PID（记录于 run-input/PID 文件，持锁期间有效）：
  1. *原入口仍存活*：说明它仍在 T9c 等待/主循环——恢复路径**只报告不接管**
     （`holder_alive` 退出），等其自行收敛；
  2. *原入口已退出*：**统一走 §4f**——DELIVERED 只证明宿主写出 GO，不证明
     读到或放行，其存在与否都不改变处置：只有确认确切候选已停止或删除才补
     终态（§4f.5），查询不明则代次保持未 RESOLVED＝阻断维持；任何恢复分支
     不补 GO、不重发 start。（v10 及以前"DELIVERED.json 在案⇒仅补终态"的
     旧分支删除。）
- **create 后 ID 未落盘**：PREPARED↔标签↔固定配置三段核对（§4f.1）；单次
  零匹配＝"当时未见"⇒ 由未 RESOLVED 的代次记录本身维持阻断（§4c 表行），
  而非收尾；多匹配/配置不符/查询失败保留现场升级人工（§4f.3）。BOUND 后
  才用完整容器 ID 三元组核对，回收仅针对该确切容器；解除一律走 §4g.2 五步。

## 4d. 快照挂载口径（复核意见④）

沿用现有 run-real.sh：源为**受控快照根下的任务卡指定版本目录**
`/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap`（ro bind →
`/data/imports/usedata/2026-10-07-bootstrap`），非 NAS 原路径直挂；演练与已验收
收据链同源。**本提案不改源路径**。若未来确需改（例如换快照根位置），属实现
差异而非本入口细节——单列为待裁决事项，须总指挥另行批准并重钉卡片绑定。

## 4e. GO 单向通道完整时序（v12，条款①修订）

**选型：命名 FIFO，纯单向（宿主→容器），通道按 GEN-ID 固定，已绑定候选的
通道不换 inode。** v7 的同 FIFO 回写 ACK 机制废止。

| 维度 | 规则 |
|---|---|
| 创建时机与路径 | **T8 create 之前**：入口建 `go/gen-<GEN-ID>/`（**root:10001 0710**）并 `mkfifo go/gen-<GEN-ID>/go`（**root:10001 0640**）；create 以 `--mount type=bind,src=$run/go/gen-<GEN-ID>,dst=/control,readonly` 挂入——PID1 起跑时通道必已存在且随 mount-plan.txt 固化（T9a 静态核验项）。 |
| UID/GID 10001 实际身份与可达路径 | **前提：本部署无 user-namespace UID/GID 映射（daemon `userns-remap` 为空，实施轮以 `docker info` 输出留证）**⇒ 容器内 USER 10001 进程的 euid/egid 即宿主 10001/10001（镜像内显式 `groupadd -g 10001 xrgworker`）。遍历链：`/`(ro rootfs)→`/control`（bind 根＝gen 目录，root:10001 **0710**＝组与其他身份仅 x 遍历、不可列名不可写）→FIFO root:10001 **0640**＝组位可读、others 无权限、写位仅属主 root。操作员 xrgp01op（非 10001 组）对 gen 目录只有 x：可直达已知名但 open FIFO 得 EACCES（others 无 r）、写/替换/删除全拒（目录无 w）；容器侧 uid/gid 10001 遍历＋读端 open 成功。**宿主独占写**由 FIFO 属主 root 0640 保证。 |
| 宿主写权限（独占、单向） | 仅入口（root）open O_WRONLY\|O_NONBLOCK；**通道内不存在反向数据面**。若未来确需回执：另定独立路径 `go/gen-<GEN-ID>/ack`（root:root 0600，仅宿主可读，容器侧无任何写身份），本版不启用。 |
| 身份绑定 | 目录名钉 GEN-ID（create 前生成，§3）；create 返回后 start 前把完整容器 ID 回填 gen.json（state=BOUND）⇒ `attempt+GEN-ID+container_id` 三元组由标签、gen.json、消费记录三方共验；`nonce = sha256(confirmed_sha ‖ GEN-ID ‖ attempt)`，PID1 从本代 gen.json 重算期望值。 |
| 双方非阻塞等待（Linux FIFO 语义，v10 统一） | **容器侧 reader**：open(O_RDONLY\|O_NONBLOCK) **成功与否都不代表 writer 在场**（NONBLOCK 下无 writer 也能打开）。read 状态机两阶段：**零字节阶段**（缓冲为空）——read 返回 0（EOF）或 EAGAIN 都**继续等到 deadline**（writer 可能尚未连接；EOF 此刻只是瞬时态，重新 read 仍可等到数据）；**收帧阶段**（缓冲已有字节）——EAGAIN 继续等更多字节，read 返回 0（EOF＝writer close）时才进入终校验：整段缓冲必须**恰好等于唯一合法帧** `GO <nonce>\n`。任何其它形态——EOF 时缓冲不完整（截断）、含第二帧/附加字节（行数≠1）、nonce 不符 ⇒ 拒绝 exit 1，收据记 read_bytes 全文与帧计数。**宿主侧 writer**：open(O_WRONLY\|O_NONBLOCK) 在尚无 reader 时返回 **ENXIO**——**ENXIO 只在无 reader 的写端记录**；入口据此轮询（0.1s 步长）直到 open 成功＝reader 在场。 |
| 延迟追加分支 | writer 写完完整行后**不立即 close、延迟 ≥1s 再追加垃圾字节然后 close**：reader 必须把它当作同一帧流的多余字节而在 EOF 终校验时拒绝（防"先到即用"竞态）。验收 A-GO 专列此分支。 |
| 零字节两形态（v11 分列，均等到截止） | 零字节阶段 read 返回 **0（EOF）＝当前无 writer**（从未连接或已 close）；read 返回 **EAGAIN＝有 writer 在场但暂无数据**。两者都继续等到 deadline，唯一例外是收帧后的 EOF 触发终校验。收据分别记录两形态出现次数与时序。 |
| 截止时间 | 宿主交付窗口＝T9c 通过后 ≤5s（open+write+close）。容器 deadline＝start+20s：其间持续容忍 EAGAIN/read=0；到点仍未凑成完整单帧 ⇒ `SUPERVISION_ABORTED_NO_GO` exit 1。宿主交付前被杀 ⇒ 容器侧自然走该超时路径。 |
| 一次性消费 | 交付＝write 后 close（EOF 终结流）。管道字节一经 reader 读完即消耗；事后重读按「零字节两形态」行与「双方非阻塞等待」行的状态机处理（read=0/EAGAIN 均等到截止），任何形态都取不回第二份 GO；实测值入收据。 |
| 不换 inode | **已绑定候选（gen.json state=BOUND）的通道禁止 unlink/rename/mkfifo 重建**——inode 自 create 起至终态归档不变。换代次＝**新 GEN-ID 新目录**，绝不原地换件；旧代目录只读保留至 T11 归档移动。 |
| DELIVERED 留证 | 宿主 close 成功后落 `go/gen-<GEN-ID>/DELIVERED.json`（双 fsync）。**其语义仅为"宿主已把 GO 写入管道并关闭"**——不证明容器读到、更不证明放行；容器是否读到以 exec 事件流为准。"已写出、留证前"崩溃窗口见 §4f。 |

## 4f. 宿主退出后的恢复规则（v12，条款②重写）

**证据语义**：DELIVERED.json 只证明"宿主写出 GO 并 close"——不证明容器读到、
更不证明放行。**exec 事件流只回答一个问题：worker 是否启动过**；终态为
TIMEOUT 必须另有**独立截止证据**（入口主循环的 deadline 判定日志或 supervisor
自身超时收据），不得由"无 worker 事件＋时间流逝"反推。

**两段流程严格分离：查找（lookup）≠ 回收（reclamation）**

**同一互斥边界**：新入口起手与 recover-orphan 都在 `registry/<attempt>.flock`
的 LOCK_EX 内执行"检查代次记录 → 查询/核实 → 先持久写结果 → 再解除或维持
阻断"，二者不可能交错；阻断判定只读代次记录状态，因此**入口崩溃后无需任何
恢复动作先行，新的 stage-* 也会被挡住**。

1. **PREPARED 阶段查找**（gen.json 未 BOUND/container_id）：以 PREPARED 收据
   为基准按标签 `io.xiangrugu.attempt-gen=<GEN-ID>` 查询 ↔ 固定创建配置摘要
   （镜像 .Id、挂载面、entrypoint argv 哈希）核对。**单次零匹配只代表"当时
   未见候选"**——create 请求可能仍在 daemon 在途：
   - 无法排除在途（默认如此）⇒ **不回收任何东西**；阻断已由未 RESOLVED 的
     PREPARED 记录本身提供（上表），RECOVERY_PENDING 仅作恢复进度注记补写；
   - 待后续任一确证到达——出现带本 GEN 标签的容器（转核对/回收）、或
     daemon 可证 create 从未落地——按 §4f.4 先持久核实结果再解除阻断收尾。
2. **BOUND 后三元组核对**：仅当 gen.json state=BOUND 才使用完整容器 ID 做
   attempt+GEN-ID+container_id 核对；回收动作只允许针对**该确切容器**。
3. **异常处置（一律保留现场＋升级人工，禁止批量 stop/rm）**：
   - *多匹配*（同 GEN 标签 >1 容器）：**不得**仅凭标签批量 stop/rm——落
     INVALID_GEN_AMBIGUOUS 明细（各容器 inspect 全文快照）→ RECOVERY_PENDING
     → 人工裁决后方可逐个处置；
   - *配置不符*（标签命中但 inspect 与 PREPARED 固定配置摘要不一致）：同上
     保留现场升级，不自动回收；
   - *状态查询失败*（daemon 无响应/超时/unknown）：保持 RECOVERY_PENDING，
     **不写任何终态**，等待 daemon 恢复后重走查找。
4. **先核实落盘、后解除阻断（v11 顺序纪律）**：核实结论（容器最终状态快照＋
   处置动作清单）先以独立收据 `gen-<GEN-ID>.RESOLVED.json` 双 fsync 持久落盘，
   **之后**才允许改写代次状态/清除注记/恢复重试资格/补终态。若中断恰落在
   "核实已完成、RESOLVED 未写完"之间：重启方在同一 flock 内重做核实（幂等），
   见 404/exited 即可安全补写 RESOLVED——**核实与收尾之间不存在半程放行窗**。
5. **终态纪律**：无论 DELIVERED 是否存在，只有**确认确切候选已 stopped 或已
   删除**（inspect State.Status∈{exited,dead} 或对象 404 可复核）后才补终态；
   unknown/查询失败 ⇒ 代次保持未 RESOLVED＝阻断维持，绝不猜测性收尾。
6. attempt 保持已消费（T9b 之后无回退）；**任何恢复分支都不补发 GO、不重发
   start**。
7. **start/create 请求计数主证据**＝入口发起 Docker 请求处的先记账日志
   （`START_REQUEST cid=<id12> ts=…`，先记账后发起，fsync）；docker events 仅
   作容器状态佐证，不作计数依据。

## 4g. 统一锁序与收尾顺序（v14，条款①②）

一套规则覆盖 Stage A/B 正常收尾、T9a 可重试拒绝与恢复路径：

1. **锁与获取顺序**：两把常驻 flock——`registry/stage-a.flock`（A）与
   `registry/<attempt>.flock`（B）。**固定顺序只能 A→B**：stage-a 起手取 A；
   凡要读写本 attempt 的代次记录（PREPARED/gen.json/RESOLVED/消费记录）必须
   在已持 A 后加取 B；stage-b/recover-orphan 只取 B。任何路径禁止先 B 后 A
   （防死锁由顺序而非超时保证）。锁文件永不删除。
2. **收尾五步固定序（所有路径一致）**：worker/候选进程终止或回收动作完成 →
   **核实确切候选状态**（inspect∈{exited,dead} 或 404 可复核）→ **写本代
   `gen-<GEN-ID>.RESOLVED.json`**（按第 3 条发布程序：临时件含尾标一次
   写齐→文件 fsync→rename→父目录 fsync）→
   更新消费记录/终态或 refusals（双 fsync）→ 释锁。T9a 静态拒绝同样执行
   第 2、3 步后才算"可重试"；正常 Stage A（T5 后）与 Stage B（T11）亦然。
3. **RESOLVED 发布程序（v14 定式）**：①在 root 独占临时件**一次性写完最终
   内容与属主/mode**（含 `published:true` 尾标——尾标是内容的一部分，先于
   rename 就位）；②文件 fsync；③原子 rename 到 `gen-<GEN-ID>.RESOLVED.json`；
   ④fsync 目标父目录。**双同步之后不再改写尾标或触碰该 inode**。读取端判
   "内容完整"＝json.loads 全量解析＋GEN-ID/attempt 双字段匹配＋尾标在案；
   这只证明字节完整，**生效一律走第 4 条重入确认**。缺失（ENOENT）、截断、
   解析失败、绑定不一致（GEN-ID/attempt 对不上本代次）⇒ 无效＝阻断维持，
   恢复方换新临时件按本条整体重写（不在旧 inode 上修补）。不存在"部分有效"。
4. **重入判定（一条规则，不推断上一进程如何退出）**：新入口持 B 锁的起手
   检查对**同一代次**只看三样东西——RESOLVED 本身 ＋ 该路径要求的收尾记录
   （stage-b＝消费记录终态；T9a 拒绝径＝refusals；stage-a＝Stage A 成功/失败
   收据）：
   - **缺失、损坏或绑定不一致** ⇒ 返回 `recovery_pending`，由恢复路径补齐
     （恢复按 §4f/§4g.2 核实→重写发布→落收尾记录）；
   - **记录齐全在场** ⇒ 入口也不得直接放行：须按本提案既定流程**重新确认
     候选状态**（inspect∈{exited,dead} 或 404 可复核；未回收者先走 §4f 回收）
     **并对所需文件与父目录各补一次 fsync**（幂等，不区分是谁、以何种方式
     写下的这些件——规则不依赖对上一次退出的任何推断）；
   - **核实或补同步任一失败**（daemon 查询失败、fsync EIO 等）⇒ 保持阻断；
   - **全部成功后**，才回到原有消费/重试规则决定能否继续：消费记录已是终态
     ⇒ `attempt_consumed` 立拒；T9a 拒绝径且记录齐备 ⇒ 允许修正重试进入
     T9b；正常收尾径 ⇒ 新 attempt 照常。
5. **中断语义**：崩溃落在"核实完成→RESOLVED 发布①~④→收尾记录"任一点，
   重启方都汇入第 4 条同一条重入规则处理，无需分辨窗口性质；期间 stage-*
   起手检查一律先 `recovery_pending`/重入确认，不存在半程放行。

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
1. `id xrgp01op` 无 docker 组；socket EACCES；`sudo -l -U xrgp01op` 恰**四条**
   固定入口（verify-inbox / stage-a / stage-b / recover-orphan），白名单中
   **不含** xrg-authz-publish；`sudo -l -U <授权人>` 仅 xrg-authz-publish 一条。
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
  该 container ID 无 stop/rm/inspect-set 调用、其 go/gen-<GEN-ID>/ 与
  run-authz/gen-<GEN-ID>/ 字节前后摘要不变（audit/exec 日志双证）。
- **A-T9a-2 静态配置拒绝（v13 统一收尾条件）**：注入 `.Mounts` 或 HostConfig
  与 plan/C 不符 ⇒ rm 容器、**flock 释放而锁文件仍在**（ls 证据）、无消费
  记录。**重试资格非即时且条件齐备**：仅 RESOLVED 在场不够——refusals 收据
  必须已释锁前持久（§4g.2），二者任一未落而再发 stage-b ⇒ `recovery_pending`
  拒；对确切候选完成回收、RESOLVED 双 fsync、refusals 双 fsync 三者齐备后，
  修正重试才成功进入 T9b。断言该序列中 create/start 计数仍为 1/0。
- **A-T9b 后已消费（拆分②）**：双 fsync 完成后注入任意失败（start 超时、
  读回不符、终态更新崩溃）→ 一律不得回到可重试态：stage-b 再发起立拒，
  终态只能经恢复路径补记，消费记录 fd+目录双同步痕迹入收据。
- **A-T9b 半写/同步失败**：kill 于 write 中途 → 重启 stage-b 读到截断 JSON
  ⇒ `consumed_record_corrupt` 拒绝且无自动覆盖（人工裁决标记文件生成）；
  注入父目录 fsync 失败（模拟 EIO）⇒ 不发 start、半成品 unlink、可重试。
- **A-T9c 等待机制三态（条款①，主证据＝按候选身份关联的进程事件流）**：
  注入 ① 四项 cgroup 任一读回不符、② 入口在轮询中被 SIGKILL、③ 读回预算
  超时。**主证据**：start 请求发出**之前**即启用 exec/fork 采集器（事件含
  comm/pid/ts/cgroup）：**先全量留存早期事件**（候选 cgroup 只在启动后才
  出现，无法预先按 ID 过滤），BOUND 容器 ID 到手后按实际出现的
  `docker-<完整ID>.scope` 身份对已留存与后续事件做关联归组；三态各自的
  该 scope 归组结果须仅含 PID1 supervisor 与白名单预检进程——即便
  task_control 瞬时启动
  也必被捕获，不依赖时间线推断。**允许已声明预检进程**：事件流中除 PID1
  supervisor 外仅可出现白名单项（supervisor 自身 fork 的 check_limits/ionice
  查询子进程，comm 与父链预先登记于 `declared_preflight.json`）；worker
  判定以 task_control 的 exec 事件为准，白名单外的任何 exec 即判该态失败。
  **事件流仅作 worker 启动与否的记录**；恢复分支涉及 TIMEOUT 的终态一律
  另附独立截止证据（§4f），不得由"无事件＋时间流逝"反推。
  采集器随收据输出 `capture_status`
  （armed_at 早于 start 请求时间戳、events_seen、dropped 计数）；**dropped>0
  或 arm 迟于 start ⇒ 该态验收判无效重跑**。辅助证据（不作唯一依据）：源
  访问审计（audit -w ＋ fanotify 零命中）、output/ 无 task_control 产物。
  ②另证 PID1 至 deadline 打印 SUPERVISION_ABORTED_NO_GO exit 1。
  **正常对照**：同采集器下一次成功放行运行须看到 worker exec 事件（证明
  采集面确实可见 worker）＋GO 交付时间戳晚于四项 cgroup 读回与 nice/ionice
  自报通过时间戳，收据逐项列读回原文。
- **A-GO 语义（§4e 逐项实测入收据）**：①通道在 create 前已存在、路径按
  GEN-ID 固定且 mount-plan 含之；②**读权验收以实际只读挂载后的容器内
  `/control/go` 为准**：由候选自身（USER 10001）执行 stat＋NONBLOCK open＋
  零字节探测，把 uid/gid/mode/errno 写入容器收据（无 userns-remap 前提另附
  docker info 留证）；宿主侧 `setpriv --reuid 10001 --regid 10001` 检查仅作
  补充。操作员身份 open(FIFO) EACCES、对目录内文件写/替换/unlink 全拒；
  ③帧状态机形态各留实测且**分别实测零字节两形态**：(a) **无 writer**
  （从未 open 或已 close）⇒ read 返回 **0（EOF）**，reader 必须继续等到
  deadline 后按截止拒绝，**不得提前退出**；(b) **writer 已连接但未写入**
  ⇒ read 返回 **EAGAIN**，同样持续等到 deadline，不得提前退出；(c) 正常
  交付——EOF 终校验通过唯一帧；(d) 事后重读——同 (a) 语义等满截止；新
  writer open 无 reader 得 ENXIO——**ENXIO 仅记录于无 reader 的写端**。
  收据分列 (a)(b) 各自的 errno 序列与持续时长；③b **延迟追加分支**：writer 写完完整
  行后 ≥1s 再追加垃圾字节然后 close ⇒ reader 必须在 EOF 终校验以"附加字节/
  行数≠1"拒绝，不得先到即用；③c 截断帧（半行后 close）同样拒绝；④**inode 稳定性**：BOUND 前后及交付全程
  `stat go/gen-<GEN-ID>/go` 的 st_ino 不变，任何 unlink/rename 尝试 EACCES；
  换代演练走新 GEN 目录而非原地换件；⑤nonce 由 confirmed_sha‖GEN-ID‖attempt
  重算匹配，伪造/多行/截断行均 exit 1；⑥通道无任何反向数据面（strace 记录
  容器侧 write 调用为 0）。
- **A-T8~T10 中断恢复（条款②）**：
  ① *ID 未落盘·查找有果*：create 响应已回、kill 于 BOUND 前 → 按标签↔
     PREPARED 配置核对命中唯一容器 → 仅对该容器 stop→rm、补记
     INVALID_PRESTART；此后 stage-b 立拒（与 §4c/§4f 同口径）。
  ② *start 响应丢失，原入口仍存活*：恢复调用得 `holder_alive` 只报告退出，
     主循环不受扰继续收敛终态。
  ③ *start 响应丢失，原入口已退出且未放行*：恢复 stop→rm、补记
     INVALID_START_UNCONFIRMED；断言恢复路径日志无 GO 写、无 start 请求。
     **start 计数主证据＝入口发起 Docker 请求处的先记账日志**（§4f.7，grep
     计数 ≤1），docker events 仅佐证容器状态轨迹。
  ③b *交付后留证前宿主退出（§4f 不可确定窗口）*：kill 于 write(GO)+close
     之后、DELIVERED.json 落盘之前 → 恢复必须按"可能已放行"处理：确认
     确切候选 stopped/deleted 后才补 INVALID_DELIVERY_UNVERIFIED；exec
     事件流只附作"worker 是否启动"记录，不作终态推断依据；attempt 保持
     已消费，后续 stage-b 立拒。
  ③c *DELIVERED 已落盘但候选仍运行（v10 点名）*：write+close+DELIVERED
     双 fsync 完成后 kill 入口，inspect＝running → 恢复不得以 DELIVERED
     推断 worker 状态：stop→观察 exited→rm，**确认停止/删除后**才补终态；
     若判 TIMEOUT 必须附独立截止证据（deadline 判定日志/超时收据），不得由
     "无事件＋时间流逝"反推；不补 GO、不重发 start。
  ③d *create 响应丢失且首次查询为零（v11 口径）*：kill create 响应路径后
     首查标签零匹配 → 断言恢复**不做任何回收**；阻断来自**未 RESOLVED 的
     PREPARED 记录本身**（recover-orphan 尚未运行时亦然，RECOVERY_PENDING
     仅是进度注记）→ stage-a/b 再发起均得 `recovery_pending` 拒绝；随后注入
     延迟到达的候选（模拟在途 create 落地）→ 二次查找命中转 ① 流程，按
     §4f.4 先写 RESOLVED 再解除阻断；或 daemon 可证从未落地 → 同样先
     RESOLVED 后收尾。两分支都验证"单次零匹配≠收尾依据"。
  ③e *多匹配与异常保留现场（v10 收紧）*：同 GEN 标签造两个容器 → 断言
     **无任何批量 stop/rm 调用**（audit/exec 日志）、INVALID_GEN_AMBIGUOUS
     含两份 inspect 全文快照、PENDING 挂起待人工；配置不符（改 stub 镜像
     .Id 使标签命中而摘要不符）同样保留升级；daemon 查询超时 → 保持
     RECOVERY_PENDING、零终态写入。
  ④ *flock 互斥双向（与 recovery_pending 严格分案，v13）*：本项只测**持锁
     期间的并发竞争**——stage-b 持锁期 recover-orphan LOCK_NB 拿不到立退
     `busy`；恢复持锁期 stage-b 同样立退 `busy`（两侧各验一次，锁文件始终
     存在不被删；此时代次记录可能正被合法持有者推进，**不产生也不消费
     recovery_pending**）。原入口退出后的 `recovery_pending` 拒绝属 ⑤/⑥ 案，
     断言两案的返回码与日志标记不同源（busy≠recovery_pending）。
  ⑤ *create 已发出、T9b 未落盘时崩溃→先重发 stage-b、后调恢复（v12 主故障点）*：
     kill 于 START_REQUEST/CREATE_REQUEST 先记账之后、ATTEMPT_CONSUMED 写入
     之前，**两个子态各演练一次**——(a) PREPARED 已落盘但 gen.json 未 BOUND；
     (b) gen.json 已 BOUND 但消费记录尚未落盘。两态断言：**ATTEMPT_CONSUMED
     与 RECOVERY_PENDING 均不存在**（ls 证据），阻断仅来自未 RESOLVED 的代次
     记录；**不跑恢复**直接 `sudo xrg-p01-run stage-b` ⇒ 持锁后起手检查得
     `recovery_pending` 拒且**无任何新增 create/start 请求**（CREATE_*/START_*
     先记账日志行数不变＋docker events 无新建/启容器事件双证）；随后调用
     recover-orphan 正常收敛（按 §4f.1/§4f.2 定位、核实、RESOLVED、终态）。
  ⑥ *核实已完成、收尾记录未写完时再次中断（v14 五窗，汇入同一条重入规则）*：
     分别在 kill 于 (a) 核实完成、RESOLVED 未出现；(b) RESOLVED 临时件已
     存在但 rename 未完成；(c) **正式件已可见、内容与尾标完整，父目录 fsync
     尚未完成或结果不明**；(d) RESOLVED 齐全、该路径收尾记录（终态/refusals/
     Stage A 收据）未落；(e) **所有记录均已可见、最后一次同步结果未知**
     （stub 使 fsync 返回值不可考）——五个窗口注入，重启方一律走 §4g.4 同
     一条规则，不做退出方式推断。
     (e) 专项：先重发 stage-b ⇒ 入口在 B 锁内重确认候选＋补同步，**注入补
     同步失败**（fsync EIO stub）⇒ 断言保持阻断、返回 recovery_pending、
     **零新增 create/start**（先记账日志行数不变＋events 双证）；随后修复
     stub 令补同步成功：T9a 拒绝径 ⇒ 修正重试才获准进入 T9b；已消费 attempt
     （终态在案）⇒ 依旧 `attempt_consumed` 立拒——两条分支各出一收据。
     另设对照：**正常收尾（T11 五步齐备）后的下一次入口调用**按既定规则
     继续（新 attempt 放行；同 attempt 重放拒绝），证明重入规则不惩罚善终。
     断言 (b)(c) 中缺失/截断/无尾标/绑定不一致件被读取端直接判无效（ls＋
     解析记录入收据）；五窗全程无新增 create/start。
  ⑦ *统一锁序与收尾（§4g，v12 新增）*：静态检查＋运行实验双证——锁定获取
     顺序仅 A→B（stage-a 触代次记录时加取 B；无先 B 后 A 路径）；Stage A
     正常收尾、Stage B T11、T9a 可重试拒绝三条路径的收据均含 §4g.2 五步齐备
     （候选核实快照→RESOLVED 双 fsync→终态/refusals→释锁）；T9a 拒绝后
     RESOLVED 生效前的 stage-b 重试必得 recovery_pending。
- **A-AUTHZ（条款③）**：
  ① 发布全流程实走通：**非 root 授权人**在 .staging（0770+sticky）确可
     O_EXCL 建件(0600)（getuid≠0 断言入收据）→ fsync →
     `sudo xrg-authz-publish <uuid>`——程序从**调用者的**暂存件读取并做
     schema 校验（非法内容拒绝且不产生正式件）；在 root 独占 .publish-tmp
     新 inode 内先固定字节/root:xrgauthz/0400 双同步，再 NOREPLACE rename
     ＋authz 父目录同步；原件呈现 root:xrgauthz 0400。
  ② 否决性四连：**第二次发布 EEXIST** 留证；**发布中断**（kill 于 tmp 成形
     后、rename 前 ⇒ 正式路径仍 ENOENT 可重发；kill 于 rename 后、父目录
     同步前 ⇒ 幂等补同步成功且摘要一致）；**操作员调用 publish 被拒**
     （sudo -l 不含该命令的 runas 尝试 EPERM＋authz/ 遍历 EACCES 双证）；
     **暂存件后续变化不影响原件**（发布后改写/删除 .staging 件，原件 sha256
     前后不变——不同 inode 证明）；操作员对 .staging 连目录都不可进入。
  ③ 同代绑定：交错预检演练——stage-a(GEN-A) 与 stage-b(GEN-B) 各绑各的
     gen-/go/ 目录与标签互不覆盖；**容器内 UID 10001 实读本代副本全文
     sha256 == 本代 gen.json confirmed == 宿主门记录**三方一致入收据；
     Stage A 首读前就绪由两段正向收据证明：**PREPARED（create 前，含副本与
     gen.json 摘要）＋BOUND（start 前）**，不用 mtime 反向断言；BOUND 的
     container_id 与 inspect Labels 的 attempt-gen 一致（读回/放行/恢复三处
     共验同一绑定）。
  ④ 操作员破坏面：xrgp01op 对 authz/、.staging/、run-authz/gen-*、go/ 的
     写/删/rename/chmod 全 EACCES/EPERM（audit 留痕）。

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
