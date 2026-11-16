# INSTALL-CHANGES-32 —— p01 最小权限入口：32 安装变更清单 / 校验 / 回退

> 依据：静态定稿提案 v14（commit `20d8219`）；实现工件：本目录 `p01-entry/`。
> 本轮 DSH **不登录 32**（凭据缺失，见 ACCESS-32.md 顶部现状；方案 A/C 已被
> 茶香明令禁止——不新增 root SSH 密钥、不试其他凭据、不由 Codex 代跑）。
> 本文是**给管理员的执行清单**：安装前状态核对 → 变更逐项 → sudoers 校验 →
> 每项变更保留原状的核对与回退依据。全部为新增文件/片段，无覆盖既有配置。

## 0. 变更总览（32 上实际改动的路径）

| # | 路径 | 动作 | 属主:组 mode | 内容来源 |
|---|------|------|--------------|----------|
| C1 | `/usr/local/bin/xrg-p01-entry-python` | 新增 | root:root 0755 | `p01-entry/xrg_p01_entry.py` 加 shebang `#!/usr/bin/python3` |
| C2 | `/usr/local/bin/xrg-p01-run` | 新增 | root:root 0755 | `p01-entry/xrg-p01-run` 原样 |
| C3 | `/usr/local/bin/xrg-authz-publish` | 新增 | root:root 0755 | `p01-entry/xrg-authz-publish` 原样 |
| C4 | `/etc/sudoers.d/xrg-p01-op` | 新增片段 | root:root 0440 | §3 白名单（操作员恰四入口；stage-b 带/不带可选 `--roots-pin` 拆两条同形条目，语义仍是四入口） |
| C5 | `/etc/sudoers.d/xrg-p01-authz` | 新增片段 | root:root 0440 | §3 白名单（授权人仅 publish） |
| C6 | 用户 `xrgp01op`（系统账号，无密码登录） | 新增 | — | §1 |
| C7 | 组 `xrgauthz`（成员＝具名授权人） | 新增 | — | §1 |
| C8 | `/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a/` 分区树 | 新增骨架 | 逐项见 §2 | §2 分区表 |
| C9 | `/usr/local/lib/xrg-p01/go_gated_supervisor.py` | 新增 | root:root 0644 | `p01-entry/go_gated_supervisor.py`（核验后由入口按 gen 复制进 run-input，容器内字节即此件） |
| C10 | `/usr/local/bin/xrg-p01-fixture-run` | 新增（仅人工夹具期） | root:root 0755 | §3b 夹具隔离包装；夹具验收完成后删除 |
| C11 | `/usr/local/lib/xrg-p01/go_gated_overlay.py` | 新增 | root:root 0644 | `p01-entry/go_gated_overlay.py`：真实链 stage-b 以 `runpy.run_module('go_gated_overlay')` 启动门控监督器；垫片把绑定目录注册为包并链接镜像内产品包路径，使 `go_gated_supervisor.py` 的相对导入按 v14 交付语义生效。入口在 create 前核验该文件存在（`supervisor_overlay_missing`） |

其余一律不动：sshd、authorized_keys、docker daemon 配置、pg32/pg32b、快照/NAS 挂载、systemd 单元。

## 1. 账号与组

```bash
getent passwd xrgp01op || useradd --system --no-create-home --shell /usr/sbin/nologin xrgp01op
getent group xrgauthz || groupadd xrgauthz
# 授权人由茶香指定并加入；DSH 不假设成员：
# usermod -aG xrgauthz <授权人用户名>
id xrgp01op    # 断言：无任何 docker 组成员资格（v14 §1.1、§6 基础项 1）
```

## 2. 运行根分区骨架（v14 §2；创建时逐项记录原状）

```bash
ROOT=/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a
install -d -m 0755 -o root -g root            "$ROOT"
install -d -m 0777 -o root -g xrgp01op        "$ROOT/inbox"        # 操作员可上传区
install -d -m 0755 -o root -g root           "$ROOT/run-input"     # 固化区：操作员零写权
install -d -m 0750 -o root -g xrgauthz       "$ROOT/authz"
install -d -m 4770 -o root -g xrgauthz       "$ROOT/authz/.staging"     # 0770+S_ISVTX
install -d -m 0700 -o root -g root           "$ROOT/authz/.publish-tmp"
install -d -m 0755 -o root -g root           "$ROOT/run-authz"
install -d -m 0750 -o root -g root           "$ROOT/go"
install -d -m 0755 -o root -g root           "$ROOT/pins"
install -d -m 0755 -o root -g root           "$ROOT/registry"
install -d -m 0755 -o root -g root           "$ROOT/output"
install -d -m 0755 -o root -g root           "$ROOT/receipts"
```

P-list 权威：`$ROOT/pins/INPUTS.admin.sha256`（root:root 0644）由管理员从
已验收字节放置（当前值 SHA-256 = `6235c356…` 口径的 roots pin 另卡；48 文件
清单以任务卡附注为准），操作员对该文件零写权。

## 3. sudoers 片段（先落临时文件，visudo -cf 通过再启用）

`/tmp/xrg-p01-op`：

```text
Defaults!/usr/local/bin/xrg-p01-run env_reset
Cmnd_Alias XRG_P01_OP = /usr/local/bin/xrg-p01-run verify-inbox, \
                        /usr/local/bin/xrg-p01-run stage-a --stage-a-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-], \
                        /usr/local/bin/xrg-p01-run stage-b --stage-b-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --mat-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --request-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f] --approval-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f], \
                        /usr/local/bin/xrg-p01-run stage-b --stage-b-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --mat-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --request-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f] --approval-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f] --roots-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f], \
                        /usr/local/bin/xrg-p01-run recover-orphan
xrgp01op ALL=(root) NOPASSWD: XRG_P01_OP
```

`/tmp/xrg-p01-authz`：

```text
Defaults!/usr/local/bin/xrg-authz-publish env_reset
%xrgauthz ALL=(root) NOPASSWD: /usr/local/bin/xrg-authz-publish [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]
```

校验与启用（任一失败即停，不落盘）：

```bash
visudo -cf /tmp/xrg-p01-op && visudo -cf /tmp/xrg-p01-authz
install -m 0440 -o root -g root /tmp/xrg-p01-op   /etc/sudoers.d/xrg-p01-op
install -m 0440 -o root -g root /tmp/xrg-p01-authz /etc/sudoers.d/xrg-p01-authz
visudo -c -q                     # 全量 sudoers 仍有效
sudo -l -U xrgp01op              # 断言：恰四入口（verify-inbox/stage-a/stage-b/recover-orphan；
                                   #   stage-b 的两条 roots-pin 变体算同一入口），不含 xrg-authz-publish（v14 §6 基础项 1）
sudo -l -U <授权人>              # 断言：仅 xrg-authz-publish 一条
```

说明（v14 §1.2「白名单钉到完整 argv」的落地方式）：

- sudoers 的通配符不是正则：`*` 匹配任意串（含空格），单类 `[0-9a-f]` 只
  匹配一个字符。因此 64 位 pin 必须逐字符展开为 64 个 `[0-9a-f]` 类才能
  精确锁定长度与字符集（上面的片段即完整展开，可直接 `visudo -cf`）。
- 后缀逐字符展开为 41 个类（1–41 字符，首字符 `[a-z0-9]`，其余
  `[a-z0-9_-]`），与程序内 `SUFFIX_RE = [a-z0-9][a-z0-9_-]{0,40}` 完全同形。
  pin 逐字符展开为恰 64 个 `[0-9a-f]` 类，与 `PIN64_RE` 同形。程序侧仍在
  取锁与任何 docker 调用之前先行校验，越界即 `Refused(usage)` 退出码 3；
  **白名单与程序语法互为镜像，双保险。**
- `--roots-pin` 是可选旗标，故 stage-b 拆成两条逐字条目（带/不带均可，
  程序仍强制其值等于 ROOTS_SHA）。
- publish 行把参数钉死为规范 36 字符 uuid 形状（8-4-4-4-12，逐字符类展
  开）；程序侧再验完整 uuid 形态、暂存件所有权与 no-follow 读取（§1.3）。
  注意 sudoers 通配符不是正则：`*` 匹配任意串（含空格），单类只匹配一个
  字符，因此全部长度/字符集约束都必须像上面这样逐字符展开。
- 若管理员希望零通配，可改为无参四条＋操作员手输完整命令的等价方案，语
  义不变。

### 3b. 人工夹具入口与正式入口的部署隔离（v14 §6 前置）

夹具轮（`XRG_P01_FIXTURE=1` + 独立 `XRG_P01_ROOT`）**不得**借用正式白名
单路径跑同一份可写环境。程序侧已有硬门：正式程序检测到 `XRG_P01_FIXTURE`
即 `Refused(usage)`，夹具程序（`XRG_P01_PROGRAM=fixture`）检测到非夹具模
式同样拒启——两侧互斥，误配不会静默降级。部署办法：

```bash
# 夹具专用解释器副本（与正式 C1 同字节、不同文件名 ⇒ argv[0] 可区分）
install -m 0755 -o root -g root p01-entry/xrg_p01_entry.py \
        /usr/local/bin/xrg-p01-fixture-python
printf '#!/bin/bash\nexport XRG_P01_PROGRAM=fixture\nexec /usr/local/bin/xrg-p01-fixture-python "$@"\n' \
        > /tmp/xrg-p01-fixture-run
install -m 0755 -o root -g root /tmp/xrg-p01-fixture-run /usr/local/bin/xrg-p01-fixture-run
```

`/tmp/xrg-p01-op-fixture`（临时片段，夹具验收完随 C10 一并删除）：

```text
Defaults!/usr/local/bin/xrg-p01-fixture-run env_reset
xrgp01op ALL=(root) NOPASSWD: /usr/local/bin/xrg-p01-fixture-run verify-inbox, \
    /usr/local/bin/xrg-p01-fixture-run stage-a --stage-a-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-], \
    /usr/local/bin/xrg-p01-fixture-run stage-b --stage-b-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --mat-suffix [a-z0-9][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-][a-z0-9_-] --request-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f] --approval-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f], \
    /usr/local/bin/xrg-p01-fixture-run recover-orphan
%xrgauthz ALL=(root) NOPASSWD: /usr/local/bin/xrg-authz-publish [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f-][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]
```

要点：夹具片段与 §3 语法逐字同形，仅程序名换成 fixture 专用副本——白名
单按路径隔离，正式 `/usr/local/bin/xrg-p01-run` 全程只服务真实模式；程序
内部门（`XRG_P01_PROGRAM` ↔ `XRG_P01_FIXTURE` 互斥校验）保证即使环境误配
也不会让夹具 argv 落到正式程序或反向。publish 仍走正式 C3 程序：它不触碰
容器面，且 §3 的调用者属主门与 no-follow 读取在两种根下是同一实现。夹具
期间正式根（真实 `$ROOT`）零写入由 MANUAL §4 清理断言兜底。

### 3c. 真实 Docker 候选链的运行事实（38 实测后补，v14 §4e/§8）

以下四条是 38 上用演练镜像跑通 materialize + go_gated_supervisor 全链后固化的部署约束，32 安装时必须逐条对照：

1. **GO 帧不过 bind 面**。docker daemon 拒绝把 FIFO（文件或含 FIFO 的目录）作为 bind 源；`/control` 又是只读绑定。因此 stage-b 容器内由 argv 预lude 在私有 tmpfs `/gochan`（`size=65536,mode=1777`，与既有 `/tmp` 挂载同姿态）上创建一次性 FIFO，宿主经 `docker exec -i … cat > /gochan/go` 写入恰好一帧 `GO <nonce>\n` 后关闭。§4e 的两阶段读取状态机、一次性语义与 DELIVERED.json 审计字节不变；`--network none` 全程保留，不存在任何 socket 面。
2. **lease 走文件级绑定并在宿主原地更新**。目录绑定会永久遮蔽 create 之后写入的 lease inode，故 `/control/lease` 单独绑定宿主 `go/gen-<GEN>/lease`；宿主喂样进程（MonitorFeeder）只做 truncate+write 保 inode 更新，绝不 rename。样本恰 9 行（read_lease 契约），间隔默认 10 s < 25 s 新鲜度窗。
3. **证据面须在 create 前整树移交**。监督器在 `/data/var/run` 以写独占文件（limits.json 等）起步，run-real.sh 的 `chown -R 10001:10001` 义务由入口 `_chown_tree` 承担：stage-a/stage-b 均在 create 前对 `$ROOT/output/gen-<GEN>` 整树 chown+chmod；32 上 root 执行时即真实 chown。
4. **GO 前的宿主核验顺序**：四项 cgroup 实读回 → 等到 `/data/var/run/limits.json` 出现（监督器写完 nice/ionice 才落此件）→ 进程级 nice==19 且 ionice∈{idle,none} 快照（宿主 procfs 不可见时经 `docker exec` 读容器自身 procfs，判定范围限定为 cmdline 含监督器的进程）→ 全部通过才允许投递 GO；任一失败 ⇒ stop+rm+RESOLVED+INVALID_READBACK，GO 永不写出。收据 `receipts/priority-audit-<GEN>.json`。

### 3d. 身份参数登记（真实链三个显式环境变量）

`XRG_P01_IMAGE_ID`（完整 `sha256:<64hex>` digest）、`XRG_P01_IMAGE_REF`（可解析到该 digest 的 repository[:tag]，create 位与门控探测共用；缺失即 `image_ref_missing` 拒绝）、`XRG_P01_SNAPSHOT_HOST`（真实快照根；未显式给出即拒绝——真实 Stage B 锁死条款保持）。三者覆盖固定常量时都会落 `receipts/image-identity-disclosure.json` 披露收据；38 上的演练值只属于演练，禁止出现在 32 的登记里。

## 4. 安装前状态核对（保留原状证据，回退依据）

在任何写入之前执行并把输出存到管理员本机（不入 `$ROOT`）：

```bash
PRE=$(date +%Y%m%dT%H%M%S)
{
  ls -ld /usr/local/bin/xrg-p01-run /usr/local/bin/xrg-authz-publish \
       /usr/local/bin/xrg-p01-entry-python /usr/local/lib/xrg-p01 \
       /etc/sudoers.d /etc/sudoers.d/xrg-p01-op /etc/sudoers.d/xrg-p01-authz \
       /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a 2>&1
  getent passwd xrgp01op; getent group xrgauthz
  sha256sum /etc/sudoers 2>/dev/null
  ls -la /etc/sudoers.d/
} | tee "pre-install-$PRE.txt"
cp -a /etc/sudoers.d "pre-sudoers-d-$PRE"   # 整目录原件备份
```

任何一项**已存在且非本次交付物** ⇒ 停止安装并回报冲突（不合并、不覆盖）。

## 5. 逐项回退（恢复到第 4 节记录的原状）

| 变更 | 回退 | 核对 |
|------|------|------|
| C4/C5 sudoers | `rm /etc/sudoers.d/xrg-p01-op /etc/sudoers.d/xrg-p01-authz` | `visudo -c -q`；`ls -la /etc/sudoers.d/` 与 pre 清单一致 |
| C2/C3/C1/C9/C10 程序 | `rm /usr/local/bin/xrg-p01-run /usr/local/bin/xrg-authz-publish /usr/local/bin/xrg-p01-entry-python /usr/local/bin/xrg-p01-fixture-run /usr/local/bin/xrg-p01-fixture-python /usr/local/lib/xrg-p01/go_gated_supervisor.py` | `ls -l` 无残留 |
| C10 夹具 sudoers | `rm /etc/sudoers.d/xrg-p01-op-fixture` | `visudo -c -q`；`ls -la /etc/sudoers.d/` 无 fixture 残留 |
| C6/C7 账号组 | `userdel xrgp01op; groupdel xrgauthz`（仅当第 4 节证明原本不存在） | `getent` 空 |
| C8 运行根 | 人工验收未消耗 attempt 时可 `rm -rf $ROOT`；一旦 `pins/ATTEMPT_CONSUMED.json` 存在，**保留全树作证据**，只撤入口（上一行）——删除运行根需茶香另行裁决 | consumed 文件是否存在的记录 |

回退后重跑第 4 节采集命令，diff 应只剩预期消失项。

## 6. 部署方式（项目既有同步流程）

Gitea 分支 `dsh/p01-real-prep-20261113` → 32 侧 `/opt/mydocker/xiangrugu/deploy`
既有受控同步（AGENTS.md §3：远端不形成未回传 Git 的独立修改）。本目录工件
随分支同步到达后，由管理员按 §2–§3 从 deploy 副本安装到系统路径；DSH 提供
每个文件的 SHA-256（见交付回报），管理员安装时逐一比对。
