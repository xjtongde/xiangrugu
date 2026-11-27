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

**注意**：步骤 4 有两种做法——
- (a) 预先由 DBA 建 `cbdb` schema，`xrg_loader` 只给 `USAGE`/`CREATE`；
- (b) 让装载时 `CREATE SCHEMA IF NOT EXISTS` 自建，`xrg_loader` 需库级 `CREATE`。
代码两条都支持（`cbdb_social_addr_loader.py` 的 `create_schema` 分支）。**建议 (a)**，权限更小。

## 2. `xrg_loader` 最小权限（依代码实测推导）
`cbdb_social_addr_entry.py` L195 强制 `current_user == xrg_loader`；L197 起拒绝 superuser
与角色覆盖（`SET ROLE`）。装载体只需：

```sql
-- 角色本身
CREATE ROLE xrg_loader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
-- 连接与最小权限
GRANT CONNECT ON DATABASE xiangrugu TO xrg_loader;
GRANT USAGE, CREATE ON SCHEMA cbdb TO xrg_loader;   -- 做法 (a)
-- 若选做法 (b)：GRANT CREATE ON DATABASE xiangrugu TO xrg_loader;
```
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
现有命令的 `test -r` 前置检查会在缺失时以
`SECRET_NOT_PRESENT_ON_HOST_32` 退出 1，**不会静默降级**。

## 4. 本盒遗留的已知差异（不影响本盒验收，放行前宜处置）
- `git archive a5d12b1` 会连带导出 3 个 `.b-batch-*` 目录，其中
  `.b-batch-real-runner-binding-20261127/preflight.py` 是历史版本 `63f2738a…`，
  与交付件 `8be2202b…` 不同（缺载荷断言）。步骤 1 读的是 `$WORK` 那份，故不受影响；
  已在 `COMMAND-FORMAL.txt` 步骤 1 前加显著警示。
