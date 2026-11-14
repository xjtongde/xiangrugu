# 提案 v2（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**（替代 v1/0032ca4 版）。本轮与既往各轮均未登录或修改
> 32；真实任务卡 `real-p01-20261113-a` 保持 CLOSED。任何落地须先获总指挥批准。
> v1 被否要点：操作账号进 docker 组＝等价近似 root，且直接触达 Docker socket。
> ｜as_of 2026-11-14

## 1. 设计原则（v2 硬约束）

1. **操作账号不属于 docker 组，不接触 `/var/run/docker.sock`**，也不得持有可
   间接调用 docker/podman/systemctl-docker 的任何 sudo 条目。
2. 容器启动能力**只存在于管理员控制的固定任务入口**：一个不可被操作者参数化
   任意命令的受控触发器，而非通用 shell 通道。
3. 固定入口在启动前**逐项绑定核验**：attempt、镜像摘要、输入清单、允许的挂载
   表、资源限制——任一不符即拒启，且不落任何部分状态。
4. **真实执行继续经过独立授权门**：`authorization.json`（操作员人工独占放置，
   绑定卡片 SHA + attempt）仍是容器内 worker 的第一道字节门；本入口不复制、
   不缓存、不绕过它。
5. pg32 生产实例零暴露：入口不加载任何指向 pg32 的路径/变量；快照挂载源以
   ro bind 由入口内部拼装，操作者无从指定源路径的能力。

## 2. 组件与职责

| 组件 | 属主/权限 | 职责 |
|---|---|---|
| `/usr/local/bin/xrg-p01-run` | root:root 0755，目录 0755 root | 固定任务入口脚本：全部常量硬编码（attempt=`real-p01-20261113-a`、IMAGE=`sha256:8f89956…`、digest 钉定的 run-real.sh），启动前跑 §3 绑定核验，然后经 systemd-run 以专用 uid 拉起容器 |
| sudoers 条目 | `/etc/sudoers.d/xrg-p01` 0440 | 仅一行：`xrgp01op ALL=(root) NOPASSWD: /usr/local/bin/xrg-p01-run stage-a, xrgp01op ALL=(root) NOPASSWD: /usr/local/bin/xrg-p01-run stage-b` ——白名单到**完整 argv**，无通配 |
| `xrg-p01-verify`（同一脚本子命令） | root 0755 | 只读复核模式：对既有运行根出收据，不启动容器 |
| 运行根 | ACL：`xrgp01op` rwx + 10001 rwx；父目录仅 --x | staging 上传落点与证据树；操作者可放件/收证，不能改入口 |
| 镜像 | daemon 侧预拉取，按 repo@digest 引用 | 入口只用 `IMAGE@sha256:…` 全摘要引用；摘要不符拒启 |

操作者流程不变的部分：Windows `stage-real.ps1` → scp 至运行根（仍走既有传输
账户或改由 `xrgp01op` sftp，仅运行根 ACL 内）→ `sudo /usr/local/bin/xrg-p01-run
stage-a|stage-b` → 事后从运行根收取收据。

## 3. 固定入口的启动前绑定核验（全部通过才允许创建容器）

1. **attempt 绑定**：argv 只接受 `stage-a` / `stage-b` 两个子命令；attempt id、
   运行根路径、超时（1800/1830s）为脚本内常量，与环境无关。
2. **镜像摘要**：`docker image inspect --format '{{index .RepoDigests 0}}'` 必须
   逐字等于常量 `sha256:8f899568909671131b14cc1c06afeef93d6ef1eef7d5d0a1b18c3bf287bd0a0a`；
   禁止 `latest`/tag 回退；缺失即拒（不自动 pull）。
3. **输入清单**：对 `$remote/source-green-v1` 执行 `sha256sum -c INPUTS.sha256`
   （权威 48 项清单随包钉入），任一行失败即拒；随后核对 task-card.closed.json
   字节 = `41bd0ecf…`、review = `a7c2c5bd…`、roots = `6235c356…`。
4. **允许的挂载**：入口生成的 docker 命令行写死后逐项断言于自身记录文件
   `mount-plan.txt`（快照源仅 `/mnt/wd61workmetadata/usedata@ro → /data/imports/usedata/<SNAPSHOT_ID>`、
   证据根 rw、其余全 ro/cap-drop ALL/network none/read-only rootfs），启动后
   `docker inspect .Mounts` 与 plan 逐条比对，不符立即 stop 并保留现场。
5. **资源限制**：cpu.max 50000 100000、memory 768MiB、swap=mem、pids 128、
   nice19/ionice idle 以 cgroup 文件读回值断言（同已验收演练口径）。
6. **独立授权门**：Stage A/B worker 容器内首步仍校验 `authorization.json`
   （status/attempt/task_card_sha256/one_attempt_only/granted_by），缺失或绑定
   不符 → 退出 2，早于任何源读取。入口本身不读该文件内容，只保证路径挂载。
7. **单次 attempt**：入口检查登记文件（O_EXCL）；已存在即拒绝第二次启动，
   与 RUNBOOK「一次 attempt」纪律一致。

## 4. 明确不做

- 不给 `xrgp01op` docker 组、socket 访问、通用 docker CLI sudo、systemctl 权。
- 不提供任意命令/任意挂载/任意镜像的入口参数面（两个固定子命令之外无接口）。
- 不在 32 直接编辑 Git 内容；入口脚本本体随交付包经 Windows staging 审阅后
  由**管理员**安装（cp+chmod+visudo -cf），操作者无安装能力。
- authorization.json 放置仍纯人工（install -m 600 独占创建），不经任何自动化。

## 5. 验收条件（获批后的实施轮，逐项出机器可读收据）

1. `id xrgp01op` 不含 docker 组；`ls -l /var/run/docker.sock` 属组不含该用户；
   `sudo -l -U xrgp01op` 输出恰为两条固定 argv 白名单，无其它条目。
2. 以 `xrgp01op` 直接 `docker ps` / 打开 socket → EACCES，留 audit 记录。
3. 篡改演练（在隔离副本根）：错镜像摘要 / 删一行 INPUTS / 加一条挂载 / 换
   attempt id → 四种情形入口均拒启且退出码非 0、无容器创建、登记文件不消耗。
4. refuse-no-authorization 走查：无 authorization.json 时 `stage-a` 到达容器内
   拒绝路径（退出 2），证明独立授权门未被入口旁路。
5. 正常演练：`stage-a` 全程产物与现 RUNBOOK R2 预期一致；`stage-b` 仅在执行
   轮（茶香授权后）由总指挥现场监督下启用。
6. 回退验证：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01
   /usr/local/bin/xrg-p01-run; setfacl -b <运行根>` 后系统回到现状，无残留。

## 6. 残余风险

- root 通道（sshd root 登录）仍存在——那是**管理员侧**安装/审计通道，操作者
  日常执行不再使用；是否进一步收紧（禁 root 密码/限源 IP）列为后续裁决项。
- 入口脚本自身的完整性依赖 root:root 0755 + 交付包摘要钉定；建议实施轮把
  `xrg-p01-run` 的 sha256 也写入任务卡附注，供 verify-real.sh 复核。
