# stage-real.ps1 `-LocalOnly` —— Windows 校验步骤与实测状态

> as_of 2026-11-14。本文件回答两个问题：**怎么在 Windows 隔离检出里做纯本地
> 48 项校验**，以及**这一轮到底测没测过**。

## 1. 入口语义（脚本已实现）

```powershell
# [Windows PowerShell 5] 在隔离检出的本目录内：
powershell -ExecutionPolicy Bypass -File stage-real.ps1 -LocalOnly
```

- 构建 packet 到一次性目录 `packet-local-check-<8hex>/`；
- 用**已提交的权威清单** `packet-inputs-real.sha256`（48 项）逐字节门全部 staged 文件；
- **绝不**写 `packet-inputs-real.sha256` / `packet-files-real.txt`（重钉只存在于传输路径且需
  `$env:XRG_REGENERATE_INPUTS='1'`，代码位置在 `-LocalOnly` 的 `exit 0` 之后）；
- **绝不**创建 tar、**绝不**调用 ssh/scp（四个网络调用点全部位于 `exit 0` 之后，
  静态可核：`Select-String -Path stage-real.ps1 -Pattern '& (ssh|scp)'` 行号均晚于 exit 行）；
- 成功输出唯一一行：`LOCAL-ONLY STAGING CHECK PASSED: 48 files verified …`，随后删除临时目录并 `exit 0`；
  任何失败经 trap 清理临时目录后抛出非零退出。

摘要重生成与传输解耦：审阅者反复跑 `-LocalOnly` 无副作用；只有正式装包轮才走默认路径。

## 2. Windows 复核步骤（获批操作员执行，约 2 分钟，全程离线）

1. `git clone <gitea> xrg-win-check && cd xrg-win-check && git checkout <本分支 SHA>`
2. `cd docs\superpowers\evidence\2026-11-13-p01-real-prep`
3. 预置断网保险（可选但建议）：临时把 `%SystemRoot%\System32\OpenSSH\ssh.exe`、
   `scp.exe` 改名——若脚本有任何网络触达会立刻报错而非静默。
4. `powershell -ExecutionPolicy Bypass -File stage-real.ps1 -LocalOnly`
   → 预期恰好一行 `LOCAL-ONLY STAGING CHECK PASSED: 48 files …`，退出码 0。
5. 事后核验：`git status --porcelain` 必须为空（未写 pin/清单/归档）；
   目录中无 `packet-local-check-*` 残留；无 `packet-real/`、无 `packet-real.tar.gz`。
6. 负例抽查（证伪门有效性）：任选一个 staged 工具副本注入 CRLF 后再跑
   `-LocalOnly` → 预期 `Staged byte mismatch (CRLF or drift): <file>` 抛出。
7. 恢复第 3 步改名（若做过）。

## 3. 本轮实测状态

- **DSH 会话主机为 Linux，无 PowerShell/pwsh**（`command -v pwsh powershell` → 空）。
  ⇒ **Windows 原生 `-LocalOnly` 实测 = 待办**，按指令明确标记，不谎报。
- 已完成的等价验证（Linux 替身，逻辑逐段对齐 §1–§5 + 权威清单门）：
  在隔离检出（detached worktree @0032ca4）中以 Python 复刻同一 staging 集与
  同一提交清单做字节门：**48/48，mismatches=0，dropped=0**。
- 结构性保证（与操作系统无关，可静态复核）：所有 `& ssh` / `& scp` / pin 写入
  语句都排在 `-LocalOnly` 分支的 `exit 0` 之后——PowerShell 顺序执行模型下
  `-LocalOnly` 运行不可能触达它们。
