# 写前现场与前置（生产首次写入，Codex 已放行）

## 写前基线（与复核人快照逐项一致）
```
pg32b container Id = 3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc
cbdb schema count  = 0        → 本盒按 formal 要求创建
目标表             = ABSENT   → 未动，装载产生
xrg_loader         = 0        → 本盒按最小权限创建
marker instance_id = 3d93fc77…c1fc  == 容器 Id ✅
端口映射           = 5432/tcp -> 0.0.0.0:5433（未改）
```

## 已创建的生产对象（仅本盒必需三项）
| 对象 | 内容 |
|---|---|
| schema | `cbdb`，AUTHORIZATION postgres |
| role | `xrg_loader` LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT |
| grants | `CONNECT ON DATABASE xiangrugu`；`USAGE, CREATE ON SCHEMA cbdb`；`SELECT ON public.xrg_instance_marker` |
| secret | `/run/secrets/xrg_loader_password`，`0400 root:root`，46 字节随机值 |

**明确不给**：库级 `CREATE ON DATABASE`。依据 loader L227-235——formal 分支
`create_schema = not is_formal` = **False**，且先查 `to_regnamespace('cbdb') IS NOT NULL`，
缺则 `prerequisite_schema_missing`。所以生产装载不需要、也不应有库级 CREATE。
实测确认 `has_database_privilege('xrg_loader','xiangrugu','CREATE') = f`。

## 🔴 差点重犯上一盒的错：口令被静默设成 NULL
第一次建角色用
`SELECT format('… PASSWORD %L', current_setting('pwpw', true))` —— 而 **`pwpw` 这个 GUC 我从未设置**。
`current_setting(..., true)` 对不存在的自定义 GUC 返回 NULL，于是生成的是
`CREATE ROLE xrg_loader … PASSWORD NULL`，**psql 退出码 0、`ALTER/CREATE ROLE` 成功**，
但角色实际没有口令。表现是外部 `FATAL: password authentication failed`，
极易误判成网络或 pg_hba 问题。

定位过程（不是靠猜）：
```
select current_setting('pwpw', true) is null  -> t          ← 根因确认
select rolpassword::text from pg_authid where rolname='xrg_loader' -> 空
    ↑ 注意这行不能单独作证据：同查询里 pg_monitor 也是空，属超级用户可见性限制
真正决定性的只有：以 xrg_loader 经 TCP:5433 实际认证 -> AUTH_EXIT=2 失败
```
修正后（口令经 stdin 喂给 `psql -f -`，不进 argv）：
```
$ psql -h pg32b -p 5433 -U xrg_loader -d xiangrugu -tAc "select current_user, current_database()"
xrg_loader|xiangrugu
AUTH_EXIT=0
```
**教训重复出现两次了**：`CREATE/ALTER ROLE … PASSWORD NULL` 与上盒 `DO $$ … current_setting`
都是"语句成功但值是空的"。凡是涉及凭据的设置，必须用**真实认证一次**来收尾验证，
不能只看 SQL 退出码。建议入纪律。

## 凭据处理合规性
- 生成：`secrets.token_urlsafe(30)`，宿主 `/run/secrets/xrg_loader_password`，`chmod 0400`
- 传给 psql：`docker exec -i pg32b psql … -f - < /tmp/alter.sql`（文件用完即删）
- 传给 runner：`docker exec -e XNG_LOAD_PASSWORD`（只传变量名，值由容器内 `cat` 得出）
- **未出现在**：任何 `docker exec`/`psql` 的 argv、git、日志、证据文件
- 临时 SQL 文件 `/tmp/alter.sql`、`/tmp/fixpw.sh` 均已删除并复核不存在

## 只读确认（候选容器内，正式装载前）
```
current_user / current_database = xrg_loader / xiangrugu     ✅ 批准库
SHOW port                       = 5432                        ✅ = IN_SESSION_PORT
inet_server_addr()              = 172.29.0.2/32               ✅ = pg32b 在该网络的地址
marker                          = 3d93fc77…c1fc = 容器 Id      ✅
target table                    = ABSENT                       ✅
server_version                  = 18.6 (Debian 18.6-1.pgdg12+2) ✅ startswith("18")
```

## 载荷身份复核（正式装载前，容器命名空间外亦一致）
```
bytes  = 417981        ✅
sha256 = 5ca84bdc9bb4d28f4be0922e86d6f60d9ad5e3f487b7fc63c117bc2de1f968ff  ✅
lines  = 3859          ✅（LF-only，每条记录终止；与生成器 "\n".join(rows)+"\n" 口径一致）
```
