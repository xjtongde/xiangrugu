# ACCESS-32 —— DSH 自行执行登录方案（供茶香裁决）

## 现状（已实测）

本机＝宿主 38。从 38 直连 `root@192.168.3.32`：本地各私钥与经 35/37 跳转均 `Permission denied (publickey,password)`；36 不可达。故**当前 DSH 无法自行在 32 上执行任何命令**，前两轮代跑均由 Windows/Codex 承担传输与调用。以下方案任选其一即可让 DSH 直接执行本 RUNBOOK（R0 拒绝验证、Stage A/B、复核与收据采集）。

## 方案 A（推荐）：专用密钥直挂 32 root

- **账号**：`root@192.168.3.32`（既有运行协议全部以 root 进行：docker、chown 10001、cgroup 读取、flock 锁文件属主）。
- **凭据**：DSH 新生成一次性 ed25519 密钥对（仅存 38 `~/.ssh/id_ed25519_dsh32_p01*`），提交公钥给持有 32 shell 的一方。
- **配置变更（32 上一行）**：向 `/root/.ssh/authorized_keys` **追加**（绝不覆盖）带来源限制的条目：
  `command=null,from="192.168.3.38" ssh-ed25519 AAAA… dsh-p01-real-20261113-a`
  （不加 restricted command——runner 需要 docker/mkdir/sha256sum/findmnt 等原生命令；来源 IP 限制是唯一新增约束。）
- **权限范围（纪律约定＋脚本自限）**：仅在 `ROOT=/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a` 与 `source-green-v1` 内创建/读写；只读挂载快照；docker 仅限 label `io.xiangrugu.synthetic-run=<本轮后缀>` 的精确名容器；不触碰 pg32/pg32b/dev 容器内部、不改服务、不动别名。以上由 run-real.sh/verify-real.sh 的路径与身份门强制，非口头承诺。
- **风险**：root 通道技术上可及整机；缓解＝from 源限制＋单轮专用密钥＋用后即撤。
- **撤销**：删除该 authorized_keys 行即完全失效（一行 diff 可审计）；同时删除 38 私钥。生命周期建议：授权窗口内有效，收据验收后当日撤销。

## 方案 B：最小权限专用账号 + docker 组

- **账号**：新建 `dsh-operator`（无密码登录，仅密钥）。
- **配置变更**：建用户＋加入 `docker` 组＋对 `/opt/mydocker/xiangrugu/data/var` 设 ACL（rwx 于 batch-runner-real-* 前缀）＋`/usr/local/bin` 放固定 runner 包装脚本。
- **诚实说明**：`docker` 组事实上等价 root（容器挂载逃逸面），最小化收益有限；且 chown 10001、锁文件属主需额外 sudoers 条目，改动面反而更大、更偏离既有协议。**不推荐**。

## 方案 C：维持 Windows/Codex 代跑（零新增权限）

沿用已验证两轮的流程：DSH 交付 staging/传输脚本与清单，Codex 执行并回传收据。**无需任何 32 配置变更**；代价是每轮多一次人工中转与时延。若茶香不愿开任何新通道，此为默认路径。

## 待裁决要点

1. 选择 A / B / C（或指定第四方持钥人执行 A 的追加操作）。
2. 若选 A：谁在 32 上执行那一行 authorized_keys 追加（需 32 现有 root 通道持有者）。
3. 密钥生命周期确认：A 方案下"授权窗口内存活、验收后当日撤销"是否成立。
4. 无论何种通道，**Stage B 启动仍需茶香对卡片 `41bd0ecf…` 的具名授权先行**——访问权限不等于执行授权，两者独立裁决。