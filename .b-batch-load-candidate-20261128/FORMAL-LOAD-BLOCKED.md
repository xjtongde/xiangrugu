# 正式单表装载：门禁与项目事实互斥（BLOCKED）

基线 `da73ed4`｜运行时 `a5d12b1`｜镜像 `xrg-load-candidate@sha256:2af4d796…8c8c58`
本盒按硬纪律：**一次尝试、不重试、不绕过、零写入**。

## 一、装载结果（原始）
```
outcome    = REFUSED
error_code = production_database_visible
detail     = cbdb
LOAD_EXIT  = 2
SCRIPT_RC  = 2
```
**零写入已确认**：`to_regclass(目标表) = ABSENT`、`cbdb` schema 内对象数 0。
门禁在 `check_instance_identity`（L222），早于 `check_target_absent`（L233）与 DDL（L249）。

## 二、根因：库名黑名单被用于 schema 名冲突

`cbdb_social_addr_loader.py` L148-155：
```python
dbs = str(observed.get("databases", ""))
names = {n.strip() for n in dbs.split(",") if n.strip()}   # pg_database 的【库名】集合
forbidden = ("pg32b", "cbdb", "cbdb_reh")
if not (branch == "real"):
    forbidden = forbidden + ("xiangrugu",)
for f in forbidden:
    if f in names:                                          # 库名集合里找 schema 名
        raise LoaderGateError("production_database_visible", f)
```
生产实际库列表：`cbdb, cbdb_reh, postgres, template0, template1, xiangrugu`。

本批目标 `cbdb` 是 `xiangrugu` 库内的**schema**，而 `cbdb` / `cbdb_reh` 是 pg32b 上**既有的两个数据库**
（AGENTS.md：「现有 pg32b/cbdb、pg32b/cbdb_reh 保留，仅供观察」）。

**用库名集合去匹配一个 schema 名的黑名单** —— 只要实例存在同名库就必然误杀。

## 三、真相比"两处同源缺陷"更严重：同仓相反断言

`production_entry.py`（已按 **R52 修正**）明确写着 legacy 库可见是**允许**的：
```
L8   - Positive instance identity: legacy databases cbdb/cbdb_reh MAY be visible
     (they exist on the real pg32b); the correct target still passes.
L47  LEGACY_DATABASES = ("cbdb", "cbdb_reh")
L186 "legacy_databases_visible": [d for d in LEGACY_DATABASES if d in dbs.split(",")]
```
而 `cbdb_social_addr_loader.py` L150：`forbidden = ("pg32b", "cbdb", "cbdb_reh")` —— 只要可见就拒。

**同一仓库里两个模块对同一事实给出相反断言。** 且 loader 是从
`first_batch_loader.check_instance_identity`（L70-71 同样写 `if "cbdb" in ...`）
**fork 时把错误语义一起复制过来的**。

→ **修复方向不是调 expected 文件，而是把 R52 语义回灌 loader、并消除 fork 副本。**
否则下一张表、下一个 batch 会踩同一个坑。

（本节判断由 a04 第十盒独立发现，lead 已核实属实。）

## 三之二、这不是偶发，是结构性互斥
```
branch=real  forbidden=(pg32b, cbdb, cbdb_reh)      hits=[cbdb, cbdb_reh] -> REFUSED
branch=test  forbidden=(...+ xiangrugu)             hits=[cbdb, cbdb_reh, xiangrugu] -> REFUSED
```
即：**在 `cbdb` / `cbdb_reh` 库存在的实例上，formal 分支 100% 必然被拒绝**，
而这两个库按 AGENTS.md **必须保留**。门禁与项目事实互斥，formal 装载在此实现下不可能成功。

同一函数后半段处理是对的（`_without_target_db` 对 formal 分支做了 target-aware 排除），
**只有前面这段黑名单没有做**。`names` 是 set，全等匹配而非子串，这点本身严谨——缺陷纯粹在名单语义。

## 四、为什么隔离六项全过却卡在这里
隔离替身是新建实例，`pg_database` 只有 `postgres/template0/template1/xiangrugu_iso`，
**不含 cbdb**，且走 `branch=test`。所以隔离测不出该冲突。

**方法教训（a02 自述，采纳）：隔离替身必须复刻生产的库名集合，
否则名单类冲突一律结构性漏检。**

## 五、残余风险：expected 与生产不匹配（同源缺陷的另一面）
`formal-expected.json` 的 `instance_identity.databases = postgres,template0,template1`，
**不含生产实际存在的 `cbdb`/`cbdb_reh`/`xiangrugu`**。
即使绕过黑名单，下一步 `databases` 键比对（L162-166，经 `_without_target_db` 去 `xiangrugu`）
仍会因 `cbdb`/`cbdb_reh` 不在 expected 中而报 `instance_identity_mismatch`。
**即 expected 工件本身也需要随生产库名集合更新**——这与 L148 是同一处语义缺陷的两面。

## 六、处置选项（均需茶香/Codex 授权，本盒不自行改）
| | 做法 | 评价 |
|---|---|---|
| **A** | 修 `check_instance_identity`：黑名单改为「本次批准实例上已知可共存」的显式白名单/目标感知；并加反例测试（含同名库的替身 → formal 通过、isolated 仍拒） | 根治，但动 `a5d12b1` → 重 PIN + 全量重验 |
| B | 目标 schema 改名 | 动已批准的表限定名与契约，不可取 |
| C | 删/改名生产 `cbdb` 库 | **AGENTS.md 明令须另获明确同意**，禁止 |
| D | scope 声明已知库名单供豁免 | 量级同 A |

**lead 倾向 A**，但需授权：它会改动固定运行时 `a5d12b1`，触发重 PIN、重验 99 单测、
重跑全部隔离证据。这不是执行方能自行决定的。

## 七、生产侧前置已就绪（a02 建成，保持现状未回滚）
- schema `cbdb`（AUTHORIZATION postgres）
- role `xrg_loader` LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT
- grants：`CONNECT ON DATABASE xiangrugu` / `USAGE,CREATE ON SCHEMA cbdb` / `SELECT ON public.xrg_instance_marker`
- 实测 `has_database_privilege('xrg_loader','xiangrugu','CREATE') = f`（formal 不需要库级 CREATE，与代码 L227-232 一致）
- secret `/run/secrets/xrg_loader_password` 0400 root:root 46B，口令不进 argv/git/日志/证据
- 只读确认全绿：`xrg_loader|xiangrugu`、`SHOW port=5432`、`inet_server_addr=172.29.0.2`、
  marker=`3d93fc77…`、目标表 ABSENT、server_version 18.6
- 载荷复核：417981 B / 3859 行 / `5ca84bdc…`

**这些前置对象在生产上已存在**，属本盒已发生的变更，需在交接说明中列明。

## 八、凭据陷阱第二次出现（建议入纪律）
a02 首次建角色用 `current_setting('pwpw', true)` 而该 GUC 从未设置 →
`format('%L')` 生成 `PASSWORD NULL` → `CREATE ROLE` **退出码 0 成功**，但角色无口令，
外部表现是 `FATAL: password authentication failed`，极易误判成网络/pg_hba 问题。

**建议纪律：凡涉及凭据的设置，必须用一次真实认证收尾验证，SQL 退出码不构成证据。**
（同类已踩两次：上盒 `DO $$ … current_setting`、本盒 GUC 未设）

另：`select rolpassword from pg_authid` 返回空**不能单独当证据**（`pg_monitor` 同样为空，
是可见性限制），决定性证据只有真实 TCP 认证。

## 九、恢复快照（lead 建立，a04 复核后收窄口径）
位置：`/opt/mydocker/xiangrugu/data/var/pre-load-snapshot-20261128/`
```
namespaces.txt / roles.txt / tables.txt / dbacl.txt / marker.txt   (41 行, 总 sha256 bffb67b0…)
schema-before.sql  (304 行, sha256 9bb69ef9…)
RECOVERY-CHECK.sh  (R1-R4 判定断言)
```
摘要核对：`schema-before.sql` = `9bb69ef9…`（304 行）、五个 txt 合计 41 行，均与 lead 报一致（a04 逐个复算）。

**可恢复性演练**（lead 执行）：临时库 `restore_drill` 用 `schema-before.sql` 恢复 →
0 错误 → 3 个 schema、13 张表与基线一致 → 演练库已销毁。
（a04 无法复现该演练——临时库已销毁，记为「只读他人输出，未独立验证」。）

### ⚠ 口径必须收窄（a04 第十盒指出，已采纳）
本快照 **只保证恢复结构，不保证恢复数据**：
- `schema-before.sql` 是 `--schema-only` dump，**`COPY` 计数 = 0**（实测），无任何行数据
- `tables.txt` 只有表名，无行数
- `RECOVERY-CHECK.sh` 的 **R4 是弱断言**：只断言 `chgis`/`harv`/`public` 三个 schema **存在**，
  不验其中 13 张表还在、行数未变。装载若意外动了既有表，R4 照样 PASS。

对本盒判断**够用**（本次只新增一张表，formal 分支 DDL 只建 `cbdb.*`），
但"恢复快照可恢复"这一说法**必须收窄为"可恢复结构"**。
R4 应改为逐表比对 `count(*)`（a04 建议，未实施——本盒不改代码）。
