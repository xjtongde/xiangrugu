# 三、恢复快照（方案 + 只读核验；**未执行任何写操作或恢复**）

## 先说清"要恢复的是什么"
本批装载是 `CREATE TABLE cbdb.cbdb__social_u5f_institution_u5f_addr` + COPY 3859 行。
**当前生产基线（实测）**：
```
xiangrugu 内 schema：chgis, harv, information_schema, pg_catalog, pg_toast, public
cbdb schema：**不存在**
to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr') = ABSENT
```
所以恢复目标很干净：**回到"cbdb schema 与本表都不存在"的状态**。
这比"备份一张已有数据的表"容易证明得多——不需要数据级还原，只需要对象级撤销。

## 快照位置与校验方式（建议，未创建）
| 层 | 位置 | 内容 | 校验 |
|---|---|---|---|
| S1 结构基线 | `/opt/mydocker/xiangrugu/data/var/b-batch/pre-load-ddl.sql` | `pg_dump --schema-only -n cbdb -t 'cbdb.*' xiangrugu` 的输出（当前应为空对象集） | sha256 记录在案；文件应仅含注释头 |
| S2 目录快照 | `.../pre-load-catalog.json` | `to_regclass` 结果、`pg_namespace` 列表、`pg_roles` 相关行 | 逐字段可与本文比对 |
| S3 源侧既有件 | `/opt/mydocker/xiangrugu/data/var/snapshots/2026-10-07-bootstrap.*.json` | 已存在的源快照证书（prepared/copied/checked/.json） | 不新建，仅引用 |

S3 已实际存在（4 个文件，uid 10001，10月7日），是权威源的快照证书链，可直接引用。
S1/S2 **尚未创建**——它们属于放行时动作，本盒按边界不写任何东西。

## 恢复验证方法（可机器判定）
装载后若需回退，验证不是"我跑过 DROP 了"，而是**逐项断言回到基线**：
```sql
-- R1: 表必须消失
select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='cbdb' and c.relname='cbdb__social_u5f_institution_u5f_addr';   -- 期望 0
-- R2: schema 若为本次新建，须一并撤销
select count(*) from pg_namespace where nspname='cbdb';                          -- 期望 0
-- R3: 不得留下残留类型/序列/约束
select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='cbdb';                                                         -- 期望 0
-- R4: 无关对象未被波及
select string_agg(nspname,',' order by nspname) from pg_namespace;
-- 期望 chgis,harv,information_schema,pg_catalog,pg_toast,public
```
外加进程层证据：runner 的 evidence json 里 `outcome=ERROR(已回滚)` 且退出码 3
（`EXIT_ERROR`），以及回滚后表不存在的独立查询输出。

**这条路径已有隔离实证可复用**：`.b-batch-phase1-verify-20261127/evidence/N7_rollback.json`
记录了隔离实例中"回滚后表不存在"的实测。16 模块摘要本轮复核仍为 16 MATCH / mismatch 0，
故该结论对当前运行时成立，无需重跑。

## 实际退出码与首个差异（本盒）
本盒所有命令均为只读探测，**没有**装载类退出码可报。实报的是：

| 动作 | 命令要点 | 退出码 |
|---|---|---|
| dev 容器内 TCP 探测 | `socket.create_connection(("172.29.0.2",5432))` | 失败 `[Errno 101] Network is unreachable` |
| 一次性探针容器 → `pg32b:5433` | 容器网络内 connect | 失败 `ConnectionRefusedError [Errno 111]` |
| 同上 → `pg32b:5432` | 容器网络内 connect | **成功**，startup packet 回 `b'R'`（PostgreSQL Authentication） |
| `psql -U postgres -d xiangrugu -tAc "show port"` | 经 docker exec 进 pg32b | 0，输出 `5432` |
| marker 值比对 | `select instance_id …` vs scope | 0，两侧同为 `3d93fc77…c1fc` ✅ |
| 角色检查 | `select rolcanlogin from pg_roles where rolname='xrg_loader'` | 返回 **0 行**（角色不存在） |

**首个差异（D1）**：scope 声明的连接端点 `pg32b:5433` 在容器网络内不存在——5433 只是
宿主机发布端口（`5432/tcp -> 0.0.0.0:5433`）。原交付命令的步骤 2 因此在容器内不可执行。

**第二个差异（D2）**：代码要求的装载角色 `xrg_loader` 在生产不存在；存在的是
`xiangrugu_loader` 且 `rolcanlogin=false`。即便解决 D1，Gate C 也会以
`load_role_mismatch` 拒绝，而实际更早一步——连会话都建不起来。

**第三个差异（D3）**：`cbdb` schema 不存在（这是预期的前置缺失，非缺陷），
但 marker 表已在 `public` 且值正确——说明前置工作做了一半。

## 明确标注
**恢复验证方法：待实测。** 我没有对生产做任何写入、DROP 或恢复动作，
上面的 R1–R4 是为放行准备的断言清单，其可行性依据是隔离实例的 N7 实证 + 当前基线为空。
