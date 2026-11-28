# B 批正式装载（重设口令后的一次机会）——REFUSED，已停报未重试

基线 `97efcb4`｜运行时 `a5d12b1`（原版）｜镜像 `xrg-load-candidate@sha256:2af4d79…`｜30 分钟盒

## 结论先说
```
LOAD_EXIT=2   outcome=REFUSED
refusal.error_code = session_eof
refusal.detail     = session_eof: ERROR:  permission denied for database xiangrugu
```
**零写入**（事后实测 target ABSENT、`cbdb` schema 内对象数 0）。按硬纪律**未重跑、未覆盖、未删表**。

## 🔴 首个差异：交付命令的执行容器根本没有 psql
第一次尝试连不上数据库，直接崩在进程启动：
```
LOAD_EXIT=1
FileNotFoundError: [Errno 2] No such file or directory: 'psql'
  at cbdb_social_addr_loader.py:354  subprocess.Popen(cmd_prefix + [...])
```
根因：`.b-batch-real-runner-binding-20261127/COMMAND-FORMAL.txt` 步骤 2 用的是
`docker exec … xiangrugu-dev`，而 **`xiangrugu-dev` 容器里没有 psql**（实测
`which psql` → `NO_PSQL_IN_DEV`）。有 psql 的是候选镜像
（`/usr/bin/psql`，18.7）。也就是说这条交付命令**在它指定的容器里永远跑不起来**，
与门禁逻辑无关。我改用授权候选镜像执行（见下"我的处置"）。

## 第二次尝试（唯一一次真正触库）：权限被拒
用 `xrg-load-candidate@sha256:2af4d79…` + `--network host --add-host pg32b:127.0.0.1`，
`PYTHONPATH` 指向 `code5/xrg-batch/datamgmt/src`。先确认加载的确实是**原版**码：
```
resolved: /data/var/b-batch/code5/xrg-batch/.../cbdb_social_addr_loader.py
digest  : 8969a7e69c13159a…   == git show a5d12b1:… ✅
含修复标志 instance_marker_verified? False          ← 确认是修复前的原版
```
（这一步很关键：候选镜像 `site-packages` 里也装了一份包，不核就会误跑修复版。）

### 逐条复现门禁查询 —— 全部通过
```
SELECT current_database()                       => xiangrugu
SHOW server_version                             => 18.6 (Debian 18.6-1.pgdg12+2)
inet_server_addr()                              => 172.29.0.2/32      ← 原件写的是 127.0.0.1/32
SHOW port                                       => 5432
to_regclass('public.xrg_instance_marker')       => 1
string_agg(datname…) FROM pg_database           => postgres,template0,template1,xiangrugu
has_schema_privilege('xrg_loader','cbdb','USAGE,CREATE') => 1
```
所以：**原 R52 误拒确实消失了**（legacy 两库已删，`forbidden` 不再命中），
身份三要素也对得上。装载死在了后面的 DDL。

### 定位过程（逐个 CREATE 试探）
```
CREATE SCHEMA cbdb_probe_a02        => ERROR: permission denied for database xiangrugu
CREATE TABLE  cbdb.zzz_probe(i int) => 成功
CREATE INDEX  zz ON cbdb.zzz_probe  => 成功
CREATE VIEW   cbdb.zzv              => 成功
CREATE TABLE  public.zzz_probe      => ERROR: permission denied for schema public
```
即角色能在 `cbdb` 里建表，但**没有库级 CREATE**，因此建不了新 schema。

### 根因：这是本仓已登记但未修的缺陷 D3
`a5d12b1` 的 `run_single_table` 正确地把 `create_schema=not is_formal` 传下去，
注释还专门写明理由（L225-227）：
> "the load must never create it, or the declared least-privilege surface
> (no CREATE on the database) would be a fiction."

但 `_load_and_verify` L256 实际调用的是 **`session.execute(ddl_for(target))`——没带这个参数**。
`ddl_for` 默认 `create_schema=True`，于是 formal 分支照样发出
`CREATE SCHEMA IF NOT EXISTS cbdb; CREATE TABLE …`。
因为用了 `IF NOT EXISTS` 且 `cbdb` 已存在，正常情况下它只是无害地跳过；
可 **`psql -v ON_ERROR_STOP=1` 下权限错误会中止整个会话**，进程随即退出，
runner 只能报出 `session_eof` 而不是一个干净的 gate code。
（`cbdb` 不存在时更糟：它会试图真的去建 schema。）

**最小修法（一行，属代码改动，本盒边界内不做）**：L256 改为
`session.execute(ddl_for(target, create_schema=create_schema))`。
注意这与上一盒修的是**不同**的问题：上一盒是 formal 身份判断误拒（已在 `9b39319`/`dab4305` 修好），
这次是 DDL 生成漏传参数。**我不擅自改代码，也不申请额外授权。**

## 本次做的偏差与记录
| 项 | 原件 | 本次 | 依据 |
|---|---|---|---|
| expected `instance_identity.inet_server_addr` | `127.0.0.1/32` | **`172.29.0.2/32`** | 你要求实测后只改运行副本 |
| 其余所有键 | — | 逐字段断言与原件完全一致 | 脚本交叉核对通过 |
| 执行容器 | `xiangrugu-dev`（无 psql） | 授权候选镜像 | 首个差异，见上 |
| 合同/授权文本/载荷/其他身份锚 | — | **未改** | 符合任务书 |

```
formal-expected 原件 sha256    43f7705fd0bff6e7c2d605dbab664d104500d94d67ced1c2cc4bc42ed6afa2b8  ✅ 与批准值一致
formal-expected 运行副本 sha256 0a756a6aee80c783891f85d5b39cc1a40b0982e48b30ca8f5405b408c9d078d2  （仅改一字段）
```

## 授权范围内的前置工作（已完成并留证）
1. `/run/secrets/xrg_loader_password`：宿主 32 上新建，`400 root:root`，44 B，由
   `secrets.token_urlsafe(32)` 直写文件；**未进命令行 / shell 历史 / 日志 / Git / 回报正文**。
2. 重设现有 `xrg_loader` 口令：`\getenv PW PW` + `ALTER ROLE xrg_loader PASSWORD :'PW';`
   写在 0400 脚本里经 stdin 喂给 psql，用完 `rm`。未新建角色/schema，未改 pg_hba，未改 deploy。
   （前两次尝试 `\getenv` 少写第二个参数，报 `missing required argument`，已改正。）
3. **真实认证验证**（吸取"退出码 0 但口令静默为空"的教训）：从候选容器以
   `xrg_loader` 走 TCP 登录 `pg32b:5433/xiangrugu` → `xrg_loader|xiangrugu`，`AUTH_EXIT=0`。
4. 预检 `preflight.py`（批准件 `8be2202b…`，取自 HEAD `97efcb4`）
   → `{"outcome":"PASSED","failure":null,"checks":17}`，`PREFLIGHT_RC=0`。
   ⚠ 顺带发现：`a5d12b1` 树里那份 preflight 摘要为 `63f2738a…`，**不是批准件**，我没用它。
5. 载荷复核：`5ca84bdc9bb4d28f…` / 417981 B / 3859 行，三项全对。

## 探针残留自查
探测期间建的临时对象已全部清理并复测：`cbdb` 对象数 **0**、`%probe%` schema 数 **0**、
目标表 ABSENT。生产库集合仍为 `postgres,template0,template1,xiangrugu`。

## 时间盒
约 28 分钟，未超。用时主要花在：定位 dev 容器无 psql、以及逐条 CREATE 试探缩小权限面。
