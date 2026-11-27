# 第二阶段待办与 secret 提供方式（本盒不创建任何生产对象或凭据）

基线 `15d1e2a`（本盒交付提交）｜装载运行时固定 `a5d12b13ad87b74fea5e8e7b2fb8a2c901bbad9e`

## 0. 现状（只读实测，未做任何变更）
- 32 宿主机 `/run/secrets/`：**不存在**
- `xiangrugu-dev` 容器 `/run/secrets/`：**不存在**
- 生产 `pg32b`：`cbdb` schema 数 **0**、`xrg_loader` 角色数 **0**、目标表 **NULL**
- 未创建任何 schema / 角色 / secret；未连生产库；未写库

## 1. 第二阶段待办（按依赖顺序）

| # | 事项 | 谁决定 | 前置 |
|---|---|---|---|
| 1 | Codex 明确放行第二阶段 | Codex | — |
| 2 | 茶香转发放行 + 确认沿用既有单表授权 | 茶香 | 1 |
| 3 | 创建 `xrg_loader` 角色（最小权限，见 §2） | 茶香授权后执行 | 2 |
| 4 | 创建 `cbdb` schema（或由装载时 `CREATE SCHEMA IF NOT EXISTS` 建） | 同上 | 3 |
| 5 | 提供装载 secret（见 §3） | 茶香 / 运维 | 2 |
| 6 | 按交付命令执行步骤 2（单事务装载） | 执行方 | 3,4,5 |
| 7 | 核对 COMMIT/ROLLBACK 报告与值比对 | 执行方 + 复核 | 6 |

**步骤 4 只有一种可行做法（本盒依代码实测更正）**：由 DBA **预先**创建 `cbdb` schema，
`xrg_loader` 只拿 `USAGE`/`CREATE`。

原先本文写过"两种做法，(b) 让装载时自建、需库级 CREATE，代码两条都支持"——**这是错的，已删**。
代码依据（`cbdb_social_addr_loader.py` L227-235）：
```python
is_formal = expected.get("execution_branch") == "real"
if is_formal:
    rows = _rows_csv(session.query_csv("SELECT to_regnamespace('%s') IS NOT NULL" % TARGET_SCHEMA))
    if not (rows and rows[0] and rows[0][0] == "t"):
        raise LoaderGateError("prerequisite_schema_missing", TARGET_SCHEMA)
check_target_absent(session)
return _load_and_verify(..., create_schema=not is_formal, ...)
```
即 **formal 分支强制 schema 必须已存在，且 `create_schema=False`**——它既不会自建，
也过不了那道门。注释还写明了理由：若允许装载器建 schema，"no CREATE on the database"
这个最小权限声明就成了摆设。所以做法 (b) 不仅多余，而且与门禁互斥；
`GRANT CREATE ON DATABASE xiangrugu TO xrg_loader;` **一律不给**。

## 2. `xrg_loader` 最小权限（依代码实测推导）
`cbdb_social_addr_entry.py` L195 强制 `current_user == xrg_loader`；L197 起拒绝 superuser
与角色覆盖（`SET ROLE`）。装载体只需：

```sql
-- 角色本身
CREATE ROLE xrg_loader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
-- 连接与最小权限
GRANT CONNECT ON DATABASE xiangrugu TO xrg_loader;
GRANT USAGE, CREATE ON SCHEMA cbdb TO xrg_loader;
-- Gate B2 必需（本盒补，原方案漏项）：marker 在 public，不在装载目标 schema 内
GRANT SELECT ON public.xrg_instance_marker TO xrg_loader;
```
**marker SELECT 为何必需**（`cbdb_social_addr_entry.py` Gate B2，L167/L170/L176 三次访问）：
```sql
SELECT (to_regclass('public.xrg_instance_marker') IS NOT NULL)::int  -- 缺 -> marker_table_missing
SELECT count(*) FROM public.xrg_instance_marker                      -- 0 -> marker_empty; >1 -> marker_multiple_rows
SELECT instance_id FROM public.xrg_instance_marker                   -- != fingerprint -> marker_value_mismatch
```
⚠️ 一个真实缺口：**Gate C（entry L202-203）只检查目标 schema 的 `USAGE,CREATE`，
没有检查对 `public.xrg_instance_marker` 的 SELECT**。因此漏授不会在预检阶段被发现，
而是等 psql 会话建立后才在 Gate B2 抛 permission denied——fail-closed 不会误放行，
但会打断装载并留下半程证据。建议纳入 preflight（跟进项 F3）。

**不需要**：superuser、CREATEDB、CREATEROLE、对 `pg32` 的任何权限、`pg32b` 其他库的权限。
**不需要** `CREATE EXTENSION postgis`——那是 `first_batch_loader.py` L164 的**另一条装载路径**
（`create_prerequisites=True`），B 批单表走 `cbdb_social_addr_loader.py`，不经过该分支。

## 3. secret 提供方式（供放行时核对，本盒不创建）
runner 从**环境变量** `XNG_LOAD_PASSWORD` 取密码，代码注释明写
`set XNG_LOAD_PASSWORD (never on the command line)`
（`cbdb_social_addr_runner.py` L502-506）。

交付命令现有形态：
```sh
test -r /run/secrets/xrg_loader_password \
  || { echo "SECRET_NOT_PRESENT_ON_HOST_32: ..."; exit 1; }
export XNG_LOAD_PASSWORD="$(cat /run/secrets/xrg_loader_password)"
```
但注意：该 `export` 与 `cat` **在宿主机执行**，而 `docker exec ... -e XNG_LOAD_PASSWORD`
透传的正是宿主侧这个变量。所以 secret 需要落在**宿主机**的 `/run/secrets/xrg_loader_password`。

放行时的最小做法（三选一，由茶香/运维决定，本盒不执行）：
- (a) 宿主机建 `/run/secrets/xrg_loader_password`，权限 `0400 root:root`
- (b) 挂载到容器并由命令改读容器内路径（需同步改命令与检查）
- (c) 由运维在放行窗口内以 `systemd-run --pipe` 或受控 shell 注入环境变量，不落盘

**无论哪种**：不得出现在命令行参数、不得进 git、不得写进任何证据文件。
🔴 **并且严禁 `set -x`（shell trace）**：a04 用假值演示过，一旦开启执行轨迹，
`export XNG_LOAD_PASSWORD="$(cat /run/secrets/…)"` 会把口令明文打进 trace/stderr，
进而可能被收进原始输出类证据文件。放行窗口内如需调试，只在**不含该 export 的行段**开 `-x`，
或先 `set +x` 再取值。同理不要把该变量写进 `docker exec` 的命令行（只传变量名 `-e NAME`）。
现有命令的 `test -r` 前置检查会在缺失时以
`SECRET_NOT_PRESENT_ON_HOST_32` 退出 1，**不会静默降级**。

## 4. 本盒遗留的已知差异（不影响本盒验收，放行前宜处置）
- `git archive a5d12b1` 会连带导出 3 个 `.b-batch-*` 目录，其中
  `.b-batch-real-runner-binding-20261127/preflight.py` 是历史版本 `63f2738a…`，
  与交付件 `8be2202b…` 不同（缺载荷断言）。步骤 1 读的是 `$WORK` 那份，故不受影响；
  已在 `COMMAND-FORMAL.txt` 步骤 1 前加显著警示。

## 5. 恢复快照（本盒新增；此前全文 0 命中「备份/快照/恢复/rollback」）

复核人指出得对：原文只写了事务级 `ROLLBACK`，**不覆盖 COMMIT 之后的撤回**。
代码依据——`cbdb_social_addr_loader.py` L9 与 L333 的 `session.rollback()` 都在
COMMIT 之前；L411/L414 是 `BEGIN`/`COMMIT`。全仓 grep `DROP TABLE` 在 loader/runner 中
**0 命中**，即**没有任何 post-COMMIT 回退路径**。一旦提交成功，撤回只能靠外部快照。

### 5.1 当前生产基线（实测，只读）
```
xiangrugu schemas: chgis, harv, information_schema, pg_catalog, pg_toast, public
cbdb schema：不存在
to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr') = ABSENT
public.xrg_instance_marker：已存在，恰好 1 行，值 3d93fc77…c1fc
                            == docker inspect pg32b Id == scope.instance_fingerprint ✅
server_version：18.6 (Debian 18.6-1.pgdg12+2)
```
**恢复目标因此很干净**：回到"cbdb schema 与本表均不存在"，属**对象级撤销**而非数据还原。

### 5.2 快照位置与校验方式（放行时创建；本盒未写任何东西）
| 层 | 位置 | 内容 | 校验 |
|---|---|---|---|
| S1 结构基线 | `/opt/mydocker/xiangrugu/data/var/b-batch/pre-load-ddl.sql` | `pg_dump -n cbdb --schema-only xiangrugu`（当前应为空对象集） | sha256 入记录；文件应仅含注释头 |
| S2 目录快照 | `…/pre-load-catalog.json` | `pg_namespace` 列表、`to_regclass` 结果、相关 `pg_roles` 行 | 可与本文 §5.1 逐项比对 |
| S3 源侧证书（已存在） | `/opt/mydocker/xiangrugu/data/var/snapshots/2026-10-07-bootstrap.{json,prepared,copied,checked}.json` | 权威源快照证书链 | 直接引用，不新建 |
| S4 装载后终态 | `…/post-load-*.sql/json` | 同 S1/S2 形态 | 用于 diff 出本次净变更 |

S3 已实际存在（4 件，uid 10001），是既有证据链的一部分。

### 5.3 恢复验证方法（机器判定，非叙述）
回退后必须逐条断言回到基线，全部期望值来自 §5.1 实测：
```sql
-- R1 目标表消失
select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='cbdb' and c.relname='cbdb__social_u5f_institution_u5f_addr';   -- 期望 0
-- R2 若 cbdb 为本次新建则须撤销
select count(*) from pg_namespace where nspname='cbdb';                          -- 期望 0
-- R3 cbdb 内无残留对象（类型/序列/约束/遗留表）
select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='cbdb';                                                         -- 期望 0
-- R4 无关 schema 未被波及
select string_agg(nspname,',' order by nspname) from pg_namespace;
-- 期望 chgis,harv,information_schema,pg_catalog,pg_toast,public
-- R5 marker 未被改动（它是实例身份锚点）
select instance_id from public.xrg_instance_marker;                              -- 期望 3d93fc77…c1fc
```
进程层配套证据：runner evidence json 的 `outcome` 与退出码
（`0 COMMITTED` / `2 REFUSED` / `3 ERROR(已回滚)` / `4 PREFLIGHT_FAILED`）。
REFUSED/PREFLIGHT_FAILED 两条路径**发生在写入之前**，无需外部恢复；
只有 COMMITTED 后的撤回才依赖 S1–S4。

**可复用的既有实证**：`.b-batch-phase1-verify-20261127/evidence/N7_rollback.json`
记录了隔离实例中"回滚后表不存在"。本轮 16 模块摘要仍 16 MATCH / mismatch 0，运行时未变，
故该结论可迁移，无需重跑。

⚠️ **恢复验证方法本身仍是"待实测"**：本盒零写入、零 DROP、零恢复动作，
R1–R5 是为放行准备的断言清单，其可行性依据是 N7 隔离实证 + 当前基线为空。
