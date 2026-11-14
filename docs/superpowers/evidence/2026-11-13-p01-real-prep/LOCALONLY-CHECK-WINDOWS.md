# stage-real.ps1 本地入口 —— Windows 校验步骤与实测状态

> as_of 2026-11-14（v2，对应提案评审后的脚本修订）。回答两件事：**Windows 隔离
> 检出里怎么复核**，以及**这一轮到底测没测过**。全程离线，不触 32。

## 1. 入口语义（脚本已实现）

三个互斥模式：

```powershell
# [Windows PowerShell 5] 在本目录（隔离检出内）：

# (a) 仅本地校验：权威清单只读消费；成功后临时目录已被 finally 删除才打印
powershell -ExecutionPolicy Bypass -File stage-real.ps1 -LocalOnly
#   → LOCAL-ONLY STAGING CHECK PASSED: 48 files verified …（退出码 0）

# (b) 独立重钉入口（唯一能改写两份 pin 清单的路径；完成即返回，绝不进传输段）
powershell -ExecutionPolicy Bypass -File stage-real.ps1 -RegeneratePins
#   → PINS REGENERATED LOCALLY from 48 staged files; no archive, no ssh/scp.

# (c) 默认传输模式：两份已提交清单均只读消费（清单不符直接抛错），随后 tar+ssh/scp
```

结构性保证（静态可核，与 OS 无关）：
- `-LocalOnly` / `-RegeneratePins` 用 `return` 结束于 try 块内 ⇒ **finally 先删
  本轮创建的临时 packet 目录，成功行后打印**；任何异常同样经 finally 清理并
  非零退出。只有本轮创建且属瞬态模式的目录会被删除；传输模式 `packet-real/`
  按原设计保留供操作员查验。
- 全部 `& ssh` / `& scp` / tar 调用点都在两个本地入口的 `return` 之后；
  默认路径不再写 `packet-inputs-real.sha256` / `packet-files-real.txt`
  （旧 `$env:XRG_REGENERATE_INPUTS` 通道已废除）。

## 2. Windows 复核步骤（获批操作员执行，全程离线，约 3 分钟）

1. `git clone <gitea> xrg-win-check && cd xrg-win-check && git checkout <本分支 SHA>`
2. `cd docs\superpowers\evidence\2026-11-13-p01-real-prep`
3. **正例**：`powershell -ExecutionPolicy Bypass -File stage-real.ps1 -LocalOnly`
   → 断言①输出恰为一行 `LOCAL-ONLY STAGING CHECK PASSED: 48 files …`；
   → 断言②`$LASTEXITCODE -eq 0`；
   → 断言③`Get-ChildItem -Directory -Filter 'packet-local-check-*'` 为空（无残留）；
   → 断言④`git status --porcelain` 为空（未动 pin/清单/归档）。
4. **CRLF 负例**：复制任一 staged 工具到临时副本不可行（清单只读），改为在克隆树内
   `git config core.autocrlf true; git checkout -- .` 使某文本件带 CRLF，或直接
   `(Get-Item ..\..\..\..\datamgmt\config\roots.yaml)` 注入——最简做法：
   `Add-Content -Path (Join-Path $PWD '..\..\..\..\docs\superpowers\evidence\2026-11-13-request-reader-integration\verification.json') -Value ''`
   再跑 `-LocalOnly` → 断言⑤抛出 `Staged byte mismatch (CRLF or drift): …`、
   退出码非 0、断言⑥仍无 `packet-local-check-*` 残留；随后 `git checkout -- .` 还原。
5. **无网络断言**：两步运行期间无需改名系统二进制；以结果为准——
   断言⑦进程内无对 192.168.3.32 的连接（可选：`Get-NetTCPConnection` 抽查或
   防火墙日志），且脚本源码中网络调用点均位于本地入口 return 之后（§1）。
6. 收尾：`Remove-Item ..\..\.. -Recurse`（删除整个克隆树即可，无他物残留）。

## 3. 本轮实测状态

- DSH 会话主机为 Linux，无 PowerShell/pwsh ⇒ **Windows 原生 `-LocalOnly` /
  `-RegeneratePins` 实测 = 待办**（按指令如实标记，不谎报）。
- 等价逻辑已在 Linux 替身验证（detached worktree @HEAD，同一提交字节 + 同一
  权威清单只读门，模拟 try/finally 流程）：
  - 正例：**48/48，mismatch=0**，临时目录清理后不存在残留；
  - CRLF 负例（对夹具输入注入 `\r\n` 后重建）：门捕获
    `metadata/runtime-verification.json` 失配并判失败（对应 ps1 throw → 非零退出），
    同样无临时目录残留；
  - 两次运行前后 `packet-inputs-real.sha256` / `packet-files-real.txt` 摘要不变
    （本地入口零写入得证）；全程未调用 ssh/scp/tar。
  - 结构断言（网络调用点均位于两个本地入口 return 之后、括号/圆括号平衡）
    静态复核通过。
  替身脚本非 PowerShell 本体 ⇒ Windows 原生实测仍为待办。
