# 提案 v3（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（替代 v2/8f351fa）。本轮及既往各轮均未登录或修改
> 32；真实任务卡 `real-p01-20261113-a` 保持 CLOSED。落地须先获总指挥批准。
> v2 复核意见的落实点：①操作员上传区与运行输入/授权/登记/原始收据物理分离；
> ②固定入口只消费操作员不可替换的已核验副本；③宿主授权门+容器授权门双保留；
> ④挂载与 cgroup 核验相对源读取的时序写死；⑤镜像身份沿用已验收 `.Id` 口径；
> ⑥补输入替换/未授权/重复启动三项验收条件。｜as_of 2026-11-14

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

顺序即安全属性，编号步骤之间不得插入其他动作：

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
