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
| C4 | `/etc/sudoers.d/xrg-p01-op` | 新增片段 | root:root 0440 | §3 白名单（操作员恰四条） |
| C5 | `/etc/sudoers.d/xrg-p01-authz` | 新增片段 | root:root 0440 | §3 白名单（授权人仅 publish） |
| C6 | 用户 `xrgp01op`（系统账号，无密码登录） | 新增 | — | §1 |
| C7 | 组 `xrgauthz`（成员＝具名授权人） | 新增 | — | §1 |
| C8 | `/opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a/` 分区树 | 新增骨架 | 逐项见 §2 | §2 分区表 |
| C9 | `/usr/local/lib/xrg-p01/go_gated_supervisor.py` | 新增 | root:root 0644 | `p01-entry/go_gated_supervisor.py`（核验后由入口按 gen 复制进 run-input，容器内字节即此件） |

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
                        /usr/local/bin/xrg-p01-run stage-a --stage-a-suffix [A-Za-z0-9][A-Za-z0-9._-], \
                        /usr/local/bin/xrg-p01-run stage-b --stage-b-suffix [A-Za-z0-9][A-Za-z0-9._-] --mat-suffix [A-Za-z0-9][A-Za-z0-9._-] --request-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f] --approval-pin [0-9a-f][0-9a-f][0-9a-f][0-9a-f], \
                        /usr/local/bin/xrg-p01-run recover-orphan
xrgp01op ALL=(root) NOPASSWD: XRG_P01_OP
```

`/tmp/xrg-p01-authz`：

```text
Defaults!/usr/local/bin/xrg-authz-publish env_reset
%xrgauthz ALL=(root) NOPASSWD: /usr/local/bin/xrg-authz-publish *[0-9a-f-]
```

校验与启用（任一失败即停，不落盘）：

```bash
visudo -cf /tmp/xrg-p01-op && visudo -cf /tmp/xrg-p01-authz
install -m 0440 -o root -g root /tmp/xrg-p01-op   /etc/sudoers.d/xrg-p01-op
install -m 0440 -o root -g root /tmp/xrg-p01-authz /etc/sudoers.d/xrg-p01-authz
visudo -c -q                     # 全量 sudoers 仍有效
sudo -l -U xrgp01op              # 断言：恰四条，不含 xrg-authz-publish（v14 §6 基础项 1）
sudo -l -U <授权人>              # 断言：仅 xrg-authz-publish 一条
```

说明：四段式 pin 正则把完整 argv 钉死到固定程序（v14 §1.2「白名单钉到完整
argv」）；后缀字符集限 `[A-Za-z0-9._-]` 防 shell 元字符。publish 行的参数
模式只允许十六进制 uuid 形态。若管理员希望更严，可改为无通配的四条逐字
条目＋现场人工输入完整命令，语义不变。

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
| C2/C3/C1/C9 程序 | `rm /usr/local/bin/xrg-p01-run /usr/local/bin/xrg-authz-publish /usr/local/bin/xrg-p01-entry-python /usr/local/lib/xrg-p01/go_gated_supervisor.py` | `ls -l` 无残留 |
| C6/C7 账号组 | `userdel xrgp01op; groupdel xrgauthz`（仅当第 4 节证明原本不存在） | `getent` 空 |
| C8 运行根 | 人工验收未消耗 attempt 时可 `rm -rf $ROOT`；一旦 `pins/ATTEMPT_CONSUMED.json` 存在，**保留全树作证据**，只撤入口（上一行）——删除运行根需茶香另行裁决 | consumed 文件是否存在的记录 |

回退后重跑第 4 节采集命令，diff 应只剩预期消失项。

## 6. 部署方式（项目既有同步流程）

Gitea 分支 `dsh/p01-real-prep-20261113` → 32 侧 `/opt/mydocker/xiangrugu/deploy`
既有受控同步（AGENTS.md §3：远端不形成未回传 Git 的独立修改）。本目录工件
随分支同步到达后，由管理员按 §2–§3 从 deploy 副本安装到系统路径；DSH 提供
每个文件的 SHA-256（见交付回报），管理员安装时逐一比对。
