# 二、最小权限方案（**只交方案，未执行任何 GRANT/CREATE**）

## 现状实测（pg32b 内只读查询；未连 pg32）
```
xiangrugu db 存在：      cbdb | cbdb_reh | postgres | template0 | template1 | xiangrugu
server_version:          18.6 (Debian 18.6-1.pgdg12+2)     ← 满足 Gate B1 的 startswith("18")
xiangrugu 内 schema：    chgis, harv, information_schema, pg_catalog, pg_toast, public
cbdb schema：            **不存在**（count=0）
public.xrg_instance_marker：**已存在**，1 行，值 = 3d93fc7741f6…c1fc
                           == docker inspect pg32b 的 Id == scope.instance_fingerprint ✅
角色：                   xiangrugu_loader | rolcanlogin=f | rolsuper=f | haspw=f
                         **xrg_loader 不存在**
xiangrugu_loader → marker SELECT：t（已有）
xiangrugu_loader → public CREATE： f
```

## 🔴 阻塞性发现：装载角色名不一致
代码里 `LOAD_ROLE = "xrg_loader"`（entry L54），Gate C 硬校验
`if role != LOAD_ROLE: raise LoaderGateError("load_role_mismatch", role)`（L195-196）。
生产实例里存在的角色叫 **`xiangrugu_loader`**，且 **`rolcanlogin = false`**。

两个独立问题：
1. **名字不匹配** → 即便连上了，Gate C 会以 `load_role_mismatch` 拒绝。
2. **不能登录** → `rolcanlogin=f`，psql 根本建不起会话，到不了 Gate C。

所以"给 `xrg_loader` 授权"这件事**目前无从谈起**——该角色不存在。要么新建 `xrg_loader`，
要么改代码用 `xiangrugu_loader` 并给它开 LOGIN。**两者都需要 DBA + 茶香决定，我不自行处理。**

## 你新增的那条要求：确认代码是否真需要 marker SELECT
**确认：确实需要，而且是硬门禁。** 依据：
- `cbdb_social_addr_entry.py` L166-177：Gate B2 三次访问该表
  - `to_regclass('public.xrg_instance_marker') IS NOT NULL` → 缺则 `marker_table_missing`
  - `count(*)` → 0 行 `marker_empty`，>1 行 `marker_multiple_rows`
  - `SELECT instance_id …` → 与 `scope.instance_fingerprint` 比，不等则 `marker_value_mismatch`
  - 再与 `ep.container_id` 比，不等则 `marker_container_binding_mismatch`
- `production_entry.py` L161-164 有同样的门
- 都在**装载会话所在事务内**执行，即装载角色必须有权读它

⚠️ 但注意一个设计问题：marker 在 **`public`** schema，而装载目标是 **`cbdb`**。
Gate C 只检查了目标 schema 的 `USAGE,CREATE`（L202-203），**没有检查对 public.marker 的 SELECT**。
也就是说：如果 DBA 忘了授 marker SELECT，运行不会在预检阶段被拦下，而是跑到 Gate B2
才抛 `permission_denied`——那时 psql 会话已经建立。建议把这项纳入预检（见文末 F3）。

## 方案（DBA 在 xiangrugu 内执行；本盒未执行）
```sql
-- 0) 先解决角色：二选一，需茶香裁决
--   A. 新建与代码同名的角色（推荐，不动固定运行时 a5d12b1）
CREATE ROLE xrg_loader LOGIN PASSWORD :'***';   -- 密码经 secret 注入，不写在脚本里
--   B. 复用既有角色：ALTER ROLE xiangrugu_loader LOGIN; 并把代码 LOAD_ROLE 改掉
--      ——这会动 a5d12b1 固定运行时，需重新 PIN 与重批，代价大

-- 1) DBA 预建目标 schema
CREATE SCHEMA IF NOT EXISTS cbdb AUTHORIZATION postgres;

-- 2) 最小授权（三条，正好对应门禁所需）
GRANT CONNECT ON DATABASE xiangrugu TO xrg_loader;
GRANT USAGE, CREATE ON SCHEMA cbdb TO xrg_loader;
GRANT SELECT ON public.xrg_instance_marker TO xrg_loader;   -- Gate B2 必需
```
**不给**的权限及理由：
- 不给 `public` 的 CREATE/USAGE（装载只写 cbdb；marker 只需 SELECT）
- 不给超user（Gate C 明确拒绝 `rolsuper=true`）
- 不给 `pg_read_all_data` 等宽泛角色
- 不给 DDL 于 public：装载器只应在 cbdb 内建表

**授权后的自检 SQL（可机器判定，全部应返回 t）**
```sql
select has_database_privilege('xrg_loader','xiangrugu','CONNECT');
select has_schema_privilege('xrg_loader','cbdb','USAGE'),
       has_schema_privilege('xrg_loader','cbdb','CREATE');
select has_table_privilege('xrg_loader','public.xrg_instance_marker','SELECT');
select rolcanlogin, rolsuper from pg_roles where rolname='xrg_loader';
```

## secret 的受控提供方式（**本盒未创建、未伪造**）
实测确认：**32 宿主机与 dev 容器内均无 `/run/secrets/`**（复核人结论一致）。
命令里那条 `SECRET_NOT_PRESENT_ON_HOST_32` 检查会正确地以 exit 1 停下——这是应有行为。

约定（供放行时执行，非现在）：
1. DBA 建角色时用占位口令，实际口令由茶香侧生成，**不进 git、不进命令行**
2. 落到宿主 32 的 `/run/secrets/xrg_loader_password`，`chmod 0400 root:root`
3. 正式命令在**宿主**上 `export XNG_LOAD_PASSWORD="$(cat …)"`，再用
   `docker exec -e XNG_LOAD_PASSWORD` 把**已导出的变量名**传进容器（值不上命令行，
   避免进入 ps 与 shell 历史）——这一步已在 COMMAND-FORMAL.txt 里写好
4. runner 侧：未提供口令时以 `load_password_not_supplied` 退出 4（runner L502-507），
   发生在构造 PsqlSession 之前，因此不会有半开会话
5. 装载完成后由茶香侧决定是否轮换/回收；本盒不做任何密钥操作

⚠️ 前提仍未满足：这条链路依赖第 1 步的角色先存在。当前既无 `xrg_loader`，
也无 secret 文件，两项都待 DBA/茶香。
