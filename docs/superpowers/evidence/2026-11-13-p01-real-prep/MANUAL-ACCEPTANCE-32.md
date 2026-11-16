# MANUAL-ACCEPTANCE-32 —— 32 主机人工夹具验收手册（p01 最小权限入口）

> 依据 v14 §6；全部使用**人工合成夹具**，不触碰 NAS、真实快照、数据库、镜像
> 发布与真实任务卡（`real-p01-20261113-a` 保持 CLOSED）。夹具轮以
> `XRG_P01_FIXTURE=1` + 独立 `XRG_P01_ROOT` 运行：入口在真实模式下会硬拒
> Stage B（`real_stage_b_locked`），保证本手册不可能误触真实执行。
> 前置：INSTALL-CHANGES-32.md 已完成且 `visudo -c -q` 通过。**夹具轮一律经
`sudo -u xrgp01op sudo xrg-p01-fixture-run …`（INSTALL §3b 的隔离别名）执
行，绝不使用正式 `/usr/local/bin/xrg-p01-run`——程序内部门会双向拒绝误配
（正式程序见 `XRG_P01_FIXTURE` 即拒；夹具程序见非夹具模式即拒），本手册每
条命令都因此天然不可能触碰真实面。**

## 0. 夹具环境（一次性，root shell）

```bash
AC=/opt/mydocker/xiangrugu/deploy/docs/superpowers/evidence/2026-11-13-p01-real-prep/p01-entry
AROOT=/var/tmp/xrg-p01-acceptance            # 夹具运行根，与真实根完全分离
ASCOPE=/var/tmp/xrg-p01-acceptance-scope     # 假 cgroup 读回目录
rm -rf "$AROOT" "$ASCOPE"; mkdir -p "$AROOT/inbox/source-green-v1" "$ASCOPE"
# 48 个合成文件 + INPUTS.sha256 == pins 清单（P==B 门可用真件演示）
for i in $(seq -w 0 47); do printf 'synthetic fixture payload %s\n' "$i" \
  > "$AROOT/inbox/source-green-v1/file-$i.dat"; done
( cd "$AROOT/inbox/source-green-v1" && sha256sum file-*.dat > INPUTS.sha256 )
mkdir -p "$AROOT/pins" && cp "$AROOT/inbox/source-green-v1/INPUTS.sha256" \
     "$AROOT/pins/INPUTS.admin.sha256"
# 假 scope：值必须等于卡片口径（cpu 半核 / 768MiB / swap 0 / pids 128）
printf '50000 100000\n' > "$ASCOPE/cpu.max"
printf '805306368\n'    > "$ASCOPE/memory.max"
printf '0\n'            > "$ASCOPE/memory.swap.max"
printf '128\n'          > "$ASCOPE/pids.max"
export XRG_P01_FIXTURE=1 XRG_P01_ROOT="$AROOT" \
       XRG_P01_CGROUP_BASE="$ASCOPE" XRG_P01_SCOPE_NAME="" \
       XRG_P01_DOCKER="$AC/stub-docker.sh" \
       XRG_P01_STUB_STATE="$AROOT/../stub-state" PYTHONPATH="$AC"
```

操作员命令一律 `sudo -u xrgp01op sudo xrg-p01-fixture-run …` 形态由验收
主持人代打，或直接在 xrgp01op 会话中执行（§3b 夹具白名单即被测对象；正式
四条白名单留待 GITEA 定稿后的 32 正式安装轮按 INSTALL §3 断言）。授权人命令用其本人
账号 + `%xrgauthz`。每条命令的 stdout/stderr 都 tee 到
`$AROOT/../evidence/<用例>.log`——这就是逐项机器可读收据的人间副本；
结构化收据本身在 `$AROOT/receipts/`。

## 1. 正常路径先行（v14 T1→T11）

```bash
sudo xrg-p01-fixture-run verify-inbox         # T2：P==B、48 字节门、固化 run-input
```

授权发布三步（§3，仅授权人）。按 INSTALL §3b 安装夹具隔离副本与正式
publish（两者都是新增文件，回退见 INSTALL §5 C10/C3 行）：

```bash
install -m 0755 -o root -g root $AC/xrg_p01_entry.py /usr/local/bin/xrg-p01-fixture-python
printf '#!/bin/bash\nexport XRG_P01_PROGRAM=fixture\nexec /usr/local/bin/xrg-p01-fixture-python "$@"\n' \
  > /tmp/xrg-p01-fixture-run
install -m 0755 -o root -g root /tmp/xrg-p01-fixture-run /usr/local/bin/xrg-p01-fixture-run
install -m 0755 -o root -g root $AC/xrg_p01_entry.py  /usr/local/bin/xrg-p01-entry-python
install -m 0755 -o root -g root $AC/xrg-authz-publish /usr/local/bin/xrg-authz-publish
# 夹具白名单片段 /etc/sudoers.d/xrg-p01-op-fixture 已由 INSTALL §3b 落盘
```

授权人建暂存件（O_EXCL，五键按 `authorization.template.json`；绑定卡片
SHA `41bd0ecf…` + attempt `real-p01-20261113-a`），随后：

```bash
U=$(uuidgen | tr 'A-Z' 'a-z')
umask 022
python3 - "$U" "$AROOT" <<'PY'
import json, os, sys
u, root = sys.argv[1], sys.argv[2]
doc = {
  "version": 1,
  "status": "AUTHORIZED_REAL_P01_SINGLE_ATTEMPT",
  "attempt_id": "real-p01-20261113-a",
  "task_card_sha256": "41bd0ecfb8b9cf6081909f60e27780c40fd5d7bf3019847a77905a4f61fc0b69",
  "one_attempt_only": True,
  "granted_by": "茶香",
}
path = f"{root}/authz/.staging/{u}.json"
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(json.dumps(doc, sort_keys=True) + "\n"); f.flush(); os.fsync(f.fileno())
print("staged", path)
PY
sudo xrg-authz-publish "$U"                   # PUBLISHED；二次同 uuid ⇒ EEXIST
```

（五键 schema 与 `../authorization.template.json` 一致：version / status /
attempt_id / task_card_sha256 / one_attempt_only+granted_by；入口逐项等值
校验，任何不符在写原件前拒绝。）

两段执行（夹具 docker = stub，容器不落真实镜像）：

```bash
sudo xrg-p01-fixture-run stage-a --stage-a-suffix fa        # STAGE_A_COMPLETED gen=<G1>
sudo xrg-p01-fixture-run stage-b --stage-b-suffix fb --mat-suffix fa \
     --request-pin <64hex> --approval-pin <64hex>           # STAGE_B_COMPLETED gen=<G2>
```

语法负例（同轮必测，退出码 3、零 docker 请求）：后缀含大写/斜杠/空格、
pin 非 64 位小写十六进制、`--key=value` 连写、verify-inbox/recover-orphan
带任何参数——四种均 `REFUSED usage`，且发生在取锁之前（journal 无该次
LOCK 事件）。

断言（脚本化亦可，主持人逐项看 receipts/）：`run-input/VERIFIED.sha256`、
`authz/authorization.json` mode 0400 root:xrgauthz、`run-authz/gen-G2/`
BOUND→RESOLVED(published:true)、`go/gen-G2/go` FIFO inode 全程不变、
`receipts/go-gate-*.json` 含 nonce 与 copy SHA、consumed=COMPLETED。

## 2. 四项关键行为（每项独立全新 AROOT，先清 `.suite` 式重放）

### ① 宿主核验实际 cgroup 后才发 GO

```bash
sed -i 's/^50000 100000$/25000 100000/' "$ASCOPE/cpu.max"   # 改一个字节
sudo xrg-p01-fixture-run stage-b ...                                  # ⇒ REFUSED readback_timeout
```

断言：`grep START_REQUEST $AROOT/receipts/docker-requests.log` 计数不含新增
stage-b start；无 go-gate 收据；consumed=INVALID_READBACK；恢复后 worker
从未启动的证据链完整。**还原 cpu.max 后重跑必过**（证明门是读回而非猜测）。

### ② 读回失败 / 入口退出 / 等待超时 ⇒ worker 从未启动

三种注入各一轮：
- 读回失败＝上一段；
- 入口退出：`XRG_P01_FAULT=consumed_pre_start` 令入口在消费记录落盘后、
  start 请求发出前崩溃，随后 `sudo xrg-p01-fixture-run recover-orphan`；
- 等待超时：`XRG_P01_STUB_GO_DEADLINE=6` 且故意不发 GO（夹具 reader 等待
  预算内零投递）。

共同断言：`receipts/go-gate-*.json` 不存在（worker 未越过 GO 门）、
runner 侧 `SUPERVISION_ABORTED_NO_GO`、恢复结果 `cleared` 且
**docker-requests.log 行数在恢复前后逐字节相同**（零重发）。

### ③ 首次 start 前消费记录已持久化，恢复不会重发

```bash
stat -c '%y %s' $AROOT/pins/ATTEMPT_CONSUMED.json
grep -n "CONSUMED_STATE\|START_REQUEST" $AROOT/receipts/entry-journal.jsonl
```

断言：journal 中该 gen 的 CONSUMED_STATE 事件行号 **早于** START_REQUEST
行号（实现里两者之间就是双 fsync）；对已 consumed 的 attempt 再发
stage-b ⇒ `attempt_consumed` 拒绝且不产生任何 docker 调用（requests 日志
行数不变）。

### ④ 授权人独占发布；UID 10001 读同字节副本；操作员不可替换原件/副本

```bash
# 非成员（操作员身份）直接 sudo publish ⇒ sudo 层拒绝（不在其 Cmnd_Alias）
sudo -u xrgp01op sudo xrg-authz-publish whatever   # 预期 sudo: not in sudoers
# 原件写探针（操作员）：touch $AROOT/authz/authorization.json ⇒ EACCES
# 副本写探针（操作员）：echo x >> $AROOT/run-authz/gen-*/authorization.json ⇒ EACCES
# UID 10001 等价面：夹具 runner（模拟容器内 uid）在 go-gate 收据中回显
#   authorization_copy_sha256 == authz 原件 sha256 == 发布时 sha
sha256sum $AROOT/authz/authorization.json
python3 -c "import json,glob;print(json.load(open(glob.glob('$AROOT/receipts/go-gate-*.json')[0]))['authorization_copy_sha256'])"
# 发布后再改 staging 文件 ⇒ 原件逐字节不变（§3 反替换）
```

断言：三项 SHA 全等；操作员的写/删/rename/chmod 全 EACCES/EPERM；
publish 二次 EEXIST；`.staging` sticky 下同组他人文件不可 unlink。

## 3. v14 验收⑥：收尾中断与同步失败窗口

`XRG_P01_FAULT` 逐个注入并观察（每例后跑 recover-orphan 再比对请求日志）：

| 窗口 | 注入 | 预期 |
|------|------|------|
| (b) 消费记录 dir-fsync 崩 | `consumed_dir_fsync` | 记录字节保留、零 start 发出；恢复 inspect-only → INVALID_START_UNCONFIRMED，**绝不 rm/stop 未启动候选**（人工可见） |
| (c) 记录后 start 前崩 | `consumed_pre_start` | 同上；重发被 attempt_consumed 拒 |
| (d) RESOLVED 发布 rename 前崩 | `rename_publish` | pending_gens 捕获，恢复按 §4g.2 五步补发布 |
| (e) 终态更新 fsync 未知 | `terminal_update` | ENTRY_CRASHED；恢复 reentry_verified_and_resynced；无 resend |
| 发布器 fsync×2 | `publish_file_fsync` / `publish_parent_fsync` | 原件未生成，staging 保留可重试；无半原件 |

## 3b. v14 验收⑥(e)：补同步两分支实测收据（夹具轮必做）

用 local-suite 的两个专用用例产出机器可读收据，主持人逐项核对后归档：

```bash
# 分支一：T9a（未消费、无 start）半发布 ⇒ 注入恢复补同步成功 ⇒ 同参重试放行
python3 p01-entry/local-suite.py --only window_e_resync_success_t9a_retry_ok
# 断言映射：blocked_while_faulted=candidate_daemon_error（单次失败保持阻断）、
# post_retry_pending=[]（补同步成功后不再挂起）、retry_status=STAGE_B_COMPLETED、
# no_start_for_refusal_gen=true（被拒代从未 start）。

# 分支二：已消费 attempt 补同步成功 ⇒ 仍拒绝重发
python3 p01-entry/local-suite.py --only window_e_resync_success_consumed_still_refuses
# 断言映射：recovery=reentry_verified_and_resynced（补同步确实成功）、
# terminal_state=INVALID_DELIVERY_UNVERIFIED（消费记录已终态）、
# relaunch_refusal=attempt_consumed（成功补同步不洗白已消费 attempt）。
```

两条都绿再进 §4 清理；任一红 ⇒ §5 停止条件。38 侧本轮收据：
`.suite/SUMMARY.json` 同名两用例 + `.suite/window-e-*/runtime-root/receipts/`。

## 4. 人工资源清理（验收完成后）

```bash
rm -rf /var/tmp/xrg-p01-acceptance{,-scope} /var/tmp/stub-state
rm -f  "$AC/__pycache__" -r 2>/dev/null || true
# 夹具隔离副本与夹具白名单片段整体退场（INSTALL §5 C10 行）
rm -f /usr/local/bin/xrg-p01-fixture-run /usr/local/bin/xrg-p01-fixture-python \
      /etc/sudoers.d/xrg-p01-op-fixture
visudo -c -q
# 夹具不留进真实根：确认真实 $ROOT 未被本轮写过
ls -la /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a
```

清理断言：`find /opt/mydocker/xiangrugu/data/var/batch-runner-real-p01-20261113-a \
-maxdepth 0 -newer pre-install-*.txt` 为空（真实根零改动）；evidence/*.log
与 receipts/ 打包移交后才删除临时树。

## 4b. 身份与证据登记（实际操作员 / 授权人）

每轮验收开始前，主持人记录真实操作者身份并归档到 evidence 包（不入
`$ROOT`）：

```bash
{ date -Is
  echo "fixture-operator: $(id xrgp01op)"          # 实际敲命令的人本机账号
  echo "sudo-runner: $(logname 2>/dev/null || stat -c %U /proc/1)"
  echo "authorizer: <授权人本人账号> $(id -un)"     # 执行 publish 的自然人
  getent group xrgauthz                             # 组成员快照
  sudo -l -U xrgp01op                               # 白名单实况（应只见 fixture 四条）
  sudo -l                                           # 主持人自身权限快照
} | tee ../evidence/identities-$(date +%Y%m%dT%H%M%S).txt
```

断言：evidence 目录内每条命令日志的首行时间戳都能在该登记表找到对应自
然人；出现任何未登记身份的命令行 ⇒ 本轮作废重跑。38 侧本地证据同口径：
local-suite 的 SUMMARY.json + `.suite/<case>/runtime-root/receipts/` 即机
器可读收据；涉及 setpriv 的 uid 探针在无 root 的主机上如实标 SKIP（本机
无 sudo 栈/无法建系统账号时，禁止用 root 直跑冒充），该项在 32 正式安装
轮由管理员补测并回报。

## 5. 停止条件

任一关键项失败：**保留现场（不清理、不改写）**，采集 receipts/ 全量 +
docker-requests.log + journal，停在人工验收阶段回报茶香。Windows 原生
端到端验证单列状态另报（见交付回报第 4 节口径）。
