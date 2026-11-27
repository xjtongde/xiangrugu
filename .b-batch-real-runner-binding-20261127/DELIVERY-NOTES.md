# 交付说明（交 Codex 独立验收）

**状态：PARTIAL — 部分完成，明确标注未决项。不是"放行就绪"。**

---

## 交付前必须知道的三项未决（请先读这一段）

> 本节于 `20261127` 复验后逐条重标。复验提交 `de3517f`（代码）/ `90bec08`（证据）；
> 真跑主机 32，计时起点 `2026-11-27T14:34:57Z`。报告见
> `.b-batch-phase1-verify-20261127/report.json`。

**(a) 单测：已执行 —— 解除。**
32 恢复后真跑，**99 passed / 0 failed / exit 0**
（entry 43 + loader 21 + runner 35）。日志：`.b-batch-phase1-verify-20261127/pytest-full.log`。
⚠️ 数字更正：此前"既有 77 + 新增 23 = 100"的说法不成立。23 项是 runner 测试的**完整数**
（`7af6208` 引入）且**替代**了原 13 项，不是追加；故本轮之前实际总数是 87 而非 100。
演进链：13(`58e93e3`) → 19(`91746fe`) → 23(`7af6208`) → 30(本轮加 7 条隔离端点反例) → 35(再加 5 条替身 host 反例)。
首次真跑还暴露 4 处**测试自身**缺陷（产品代码正确），已分别修复于
`97c583b` / `9aaa6a9` / `de3517f`。

**(b) `_PRODUCTION_CONTAINER_ID`：已现场核实 —— 解除。**
32 上只读实测四项，**全部与固定值一致，未触发停报**：
- `pg32b` 全容器 ID = `3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc`（与常量一致）
- `docker port pg32b` → `5432/tcp -> 0.0.0.0:5433`（外部 5433 → 内部 5432）
- `public.xrg_instance_marker` 值 == 容器全 ID（实例绑定自洽）
- 会话内 `show port` = 5432；`server_version` = 18.6；`current_database()` = `xiangrugu`

该四元组应作为 phase2 交付件的**对照基准**保留：此后若任一值变化即可报警。
"为让 phase2 通过而改动该常量"的风险因此有了基线锚点。**改动仍需新的授权引用。**

**(c) 正式命令端到端：仍未执行 —— 唯一未决项。**
步骤 1（只读预检）已实跑 `exit=0 / 15 项 / closure=16`，本轮复验再次通过。
**步骤 2 仍未执行**：正式命令 `phase2-production` 无端到端实测。
本轮新增的是**隔离**端到端（`xrg-v-iso` 替身，见下），不是正式端到端——两者路径不同，
隔离通过不能推出正式可执行。另需注意：正式分支要求预建 `xrg_loader` 角色与 `cbdb` schema，
本轮只读核对确认二者在生产**尚不存在**。

---

## 本轮新增：隔离端到端实测（`xrg-v-iso` 替身）

首次把交付命令真正递给下游并跑完整个「装载 → 回读 → 回滚」闭环：

| 用例 | 结果 | 关键证据 |
|---|---|---|
| P1 正向装载 | **COMMITTED** exit 0 | rows **3859** |
| N7 回读不符 → 整表回滚 | **REFUSED** exit 2 | `row_count_mismatch`；probe `{present:false, residue:0}`；独立 `to_regclass` = TABLE_ABSENT |
| P3 恢复装载 | **COMMITTED** exit 0 | rows 3859 |
| 正式值比对（独立 psql 读回，非 payload） | **`comparison_equal`** | 源/目标同 `2cb8c354…07579`；3859/3859；缺失 0 多余 0；`target_fields` 42449 = 3859×11 |
| 正式端点只读预检 | **PASSED** 15/15 | 未连接 |

替身条件：`--network none`、无端口发布、源件只读挂载、库名 `xiangrugu_iso`（隔离实例不得
看到生产库名）。载荷 3859 行 / 417981 字节 / sha256 `5ca84bdc…`。跑毕已销毁，残留容器 0。

---

## ⚠️ 本轮真跑暴露的交付工件缺陷（4 + 1 处，均已修复）

这些是**静态审查十二轮都未发现**的问题，性质高于文档瑕疵：

1. **两份 scope 一份都进不了 entry。** 补正盒为区分正式/隔离把 `mode` 写成
   `production-write` / `isolated-test`，而 entry Gate A **硬性要求 `mode="execution-candidate"`**。
   mode 值本身合法、注释自洽、字段齐全——只有递进 Gate A 才炸。
   已改回 `execution-candidate`，改用 `scope_class=formal|isolated` 区分。
2. **隔离门禁查错了对象。** 原门禁查 scope **声明**端点，但 entry 要求声明端点恒为
   `pg32b:5433`、隔离靠 `--connect-host/--connect-port` 改道。按声明检查会同时：
   禁掉 entry 强制的形态（导致隔离根本跑不了）+ 放过实际拨号到生产的运行。
   已改为检查**实际连接目标**。
3. **🔴 残留通路（a02 第 13 轮复核指出，本轮已收口）。** 上一条改完后仍只比
   `(host, port) == (pg32b, 5433)` 一对。但生产实例在**容器内也监听 5432**，
   故 `--connect-host pg32b --connect-port 5432` 会漏过——连接确实建立、会话确实开始。
   另：不传 `--connect-port` 时端口会**回落**到声明的生产端口。
   已改为要求 ① 显式给出 `--connect-port`（禁止回落）② host 必须落在替身白名单
   （回环地址或显式替身名）③ 生产主机名一律拒绝，与端口无关。
   新增 7 条反例覆盖 `{pg32b:5433, pg32b:5432, pg32b:5434, pg32:5432}`、非替身 host、
   缺省端口；并做变异测试确认：把加固退回旧逻辑后 `pg32b:5432` 用例立即失败。
   **替身 host 已由命名启发式改为白名单**（N1）：原 `startswith("xrg-")` / 含
   `standin`/`trial` 的规则会放过 `xrg-pg32b` 这类指向生产的别名。现只接受回环地址，
   或 scope 自身 `standin_hosts` 中声明的名字。新增 5 条 lookalike 反例，变异测试确认
   退回启发式后 4 条全部失败。
4. **模板缺必需绑定**（`bound_object_rule_ids`、`target` 等）→ `write_approval_not_bound_to_single_target`。
5. **隔离库名**用 `xiangrugu` 被 `production_database_visible` 拒。这是**正确的安全行为**，
   不是绕过对象：改名为 `xiangrugu_iso`。

**共同教训**：补正盒的正式/隔离分离改动此前从未真跑过，本轮是首次。
后续凡新增或改动交付工件（scope、expected、命令模板），至少要有一次把它真正递给
下游消费者的动作，哪怕下游是个 stub。

---

## 本盒完成的内容

| 项 | 状态 | 证据 |
|---|---|---|
| 正式/隔离 scope 与 expected 分离 | 完成 | 4 份文件；R1/R2 相位错配被拒 |
| 正式端点固定 + 连接前拒绝覆盖 | 完成 | 14 个拒绝码（8 formal + 4 isolated + 2 其他）；R4/R5/R6；拒绝点早于 `PsqlSession` |
| 已审授权摘要作为独立校验依据 | 完成 | 锚点写入 **runner 执行体**（不止预检工具）|
| 导出清单含 runner 自身 | 完成 | 传递闭包 16 模块；R8/R9/R13/R14 |
| 无占位符正式命令 | 完成 | `COMMAND-FORMAL.txt`，步骤 1 实跑通过 |
| 生产/隔离参数对照 | 完成 | `PARAMETER-MATRIX.md` |
| 只读预检 | 完成 | `preflight.py`，15 项，不连数据库 |
| 针对性反例 | 完成 | 14 条（工具层）+ 2 条（执行体层）+ 7 条（隔离端点，本轮新增）|

## 证据分层

- **执行体层**（2 份，`single-table-load-evidence.v1`）：`R10_runner`、`R_auth_runner`
  两份均为排他性证明——伪造件的摘要与声明值**完全相同**，自证检查本应全部通过，实际仍被硬编码锚点拒绝，且 evidence 无 `session` 键（从未建立连接）。
- **预检工具层**（16 份，`preflight.v1`）：14 条反例 + 2 条正向。

## 本盒未做

未更新 deploy、未改生产权限或服务、**未连接生产库**、未写正式库；M=2 未进入提交；授权原文 `4d250c8e…`（641B）逐字未动；`ready_for_import=false`。

## 下一步（32 恢复后）

1. 现场核实 `_PRODUCTION_CONTAINER_ID`
2. 跑 pytest：既有 77 + 本轮 23，结果写入报告
3. 隔离替身端到端 + vcmp 读库比对
4. 以上完成后转 PASS，再请 Codex 放行进入第二阶段

---

## 完整提交号

- 代码提交：`424ab2097891834642993049897008514db8018c`
- 交付 HEAD：见 Gitea `dsh/p01-real-prep-20261113` 分支最新提交