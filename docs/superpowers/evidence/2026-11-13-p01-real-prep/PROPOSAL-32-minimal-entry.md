# 提案（待审，未实施）：32 主机最小权限执行入口

> 状态：**仅方案提交评审**。本轮与既往各轮均未登录或修改 32；真实任务卡
> `real-p01-20261113-a` 保持 CLOSED。任何落地须先获总指挥批准。｜as_of 2026-11-14

## 1. 现状问题

当前 RUNBOOK 的全部远端步骤以 `root@192.168.3.32` 经 SSH 执行（staging 上传、
`bash run-real.sh …`、复核）。root 通道能力远超本 attempt 所需：可读写任意路径、
改系统配置、影响同机 pg32 生产实例——与"导入过程不得影响 pg32"的硬约束相悖。

## 2. 目标

把一次真实 Stage A/B 执行所需的宿主能力收缩到**单用途账户 + 白名单命令**，
其余全部维持 root 人工操作或禁止。

## 3. 方案（三层，任选其一起步，建议 A+B）

### A. 专用低权账户 `xrgp01op`（建议必选）
- `useradd -m -s /bin/bash xrgp01op`；SSH 仅密钥登录（`PasswordAuthentication no` 段内覆盖）。
- 属组仅 `docker`（容器以镜像 USER 10001:10001 运行，宿主侧无需 root shell 特权）。
- 目录 ACL：对运行根
  `/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a`
  授 `rwx`（setfacl），对其父目录仅 `--x`；对快照只读挂载源不加任何写权限。
- 效果：该账户能且仅能在该运行根内 staging/启动/收证；删除运行根、改
  `/etc`、动 pg32 均不可达。

### B. sudo 白名单（配合 A，替代整体 root 会话）
`/etc/sudoers.d/xrg-p01`（visudo -cf 校验后安装，文件模式 0440）：

```text
xrgp01op ALL=(root) NOPASSWD: /usr/bin/install -d -m 700 -o 10001 -g 10001 /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a*, \
             /usr/bin/setfacl -R -m u:10001:rwx /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a*, \
             /bin/chown 10001\:10001 /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a*
```

仅覆盖运行根预建/chown 两处既有 root 步骤；通配符限定在运行根前缀内。
run-real.sh 内部不含其它特权调用（已核对：docker/flock/mkdir/chmod 均在用户态）。

### C. systemd-run 资源围栏（可选增强）
以 `systemd-run --scope -p TasksMax=… -p MemoryMax=…` 包裹候选容器启动进程，
把卡片资源约束再钉一层宿主 cgroup。非必需（容器侧已有完整 posture），列为备选项。

## 4. 明确不做

- 不给 `xrgp01op` 任何 docker 之外的守护进程管理权；不装 agent/常驻服务。
- 不改 sshd 全局配置，仅 `Match User xrgp01op` 段收紧。
- 不在 32 上直接编辑 Git 内容（维持受控运行镜像单向同步纪律）。
- 授权放置 authorization.json 仍由操作员人工完成（600 独占创建），不经此入口。

## 5. 验收标准（获批后的实施轮）

1. `sudo -l -U xrgp01op` 输出与白名单逐字一致；
2. 以 `xrgp01op` 走一遍 refuse-no-authorization 模式（安全、无授权），RUNBOOK R0 全绿；
3. 试图越界（写运行根外路径、非白名单 sudo）被拒并留 audit 记录；
4. root 通道保留但仅用于审批后的实际 Stage B 单次启动（或按裁决完全切换）。

## 6. 风险与回退

- 风险：docker 组成员等价近似 root（既定事实，A 层无法消除；B/C 不扩大它）。
  若总指挥判定不可接受，则维持现状 root 人工执行，本提案作废即可，无残留。
- 回退：`userdel xrgp01op; rm /etc/sudoers.d/xrg-p01; setfacl -b <运行根>`。
