# pg32b.md —— pg32b 实例事实卡

> **状态：现行**｜as_of **2026-09-30**（本卡全部数字系本日**活体现算**，非转录）
> 本卡只记**实例事实**。库内数据之合格性 → `datamgmt/config/roots.yaml` 之 `target.known_nonconformance`；缺陷 → `docs/bugs.md`。

## 一、实例

| 项 | 值（2026-09-30 现算） |
|---|---|
| 主机 | **192.168.3.32**（i7-6567U；RAM 总 7G／可用 5G；`/` 233G 总、**余 189G**；loadavg 1.09） |
| 容器 | **`pg32b`**，`Up (healthy)` |
| 镜像 | **`pg32b-full:18-pgdg`**（＝36 之 `pg36-full:18-pgdg` **同字节拷贝后 retag**，故镜像 label 仍系 `pg36.*` 冠名，如实保留） |
| 端口 | **`0.0.0.0:5433 → 5432`**（5432 系同机生产 `pg32` 之口，故让口） |
| 版本 | PostgreSQL **18.6**（`server_version_num=180006`，Debian 18.6-1.pgdg12+2） |
| 数据目录 | 宿主 `/opt/mydocker/pg32b/data/postgres` → 容器 `/var/lib/postgresql`（bind mount，**本地盘非 NAS**） |
| 时区挂载 | `/etc/localtime`、`/etc/timezone` 皆正常（**32 主机无 B-02**） |
| 关键参数 | `shared_buffers=512MB`（**缩配**：pg36 之 1GB 系按 15G RAM 配，32 让着现有服务）；`maintenance_work_mem=128MB`；`max_wal_size=1024MB`；`wal_level=replica`；`max_connections=50` |
| 同机邻居 | `pg32`（生产，`postgres:18-bookworm`，5432，healthy）；另有 nginx32（unhealthy 观察项）／n8n／chainlit／graphrag |

⚠ **共实例告警**：`pg32b` 与**生产 `pg32` 同在 32 主机** → 任何装载/验证须 `nice`／`ionice`，且 **loadavg<4.0 门禁**（`roots.yaml` 已载）。

## 二、库 `cbdb`（现况）

| 项 | 值 |
|---|---|
| 库大小 | **4,771 MB** |
| 用户表 | **395**（关系数 399＝395 表＋4 个视图/物化视图类对象） |
| schema | `public`、`chgis`、`harv`、`ogr_system_tables` |
| 扩展 | `plpgsql 1.0`、**`postgis 3.6.4`**、**`postgis_raster 3.6.4`** |
| ⚠ **pgvector** | 镜像内**含 pgvector 0.8.6**，但 `cbdb` 库**未创建该扩展**（`pg_extension` 无 `vector`）→ 向量检索层（F-04）启用前须先 `CREATE EXTENSION vector` |
| 行数 | **唯一权威＝`datamgmt/config/roots.yaml`** 之 `target.current_state`（`count(*)` 与 pg_stat 两口径并存，差 221，口径候裁） |
| 合格性 | **未知**：仅 `chgis.v4_gns` 一表做过值级对账（结果 2,288 值不合格＝B-11）；`v5_gns.geom`／`v4_gns.geom` 已非源值（**B-15**）；**其余 397 关系未知** |
| 备份 | ⚠ **现无任何 `cbdb` 库 dump**（备份调度归另派 agent；`import-plan.md` P-1 前置条件） |

## 三、访问式

```bash
ssh 192.168.3.32 "docker exec -i pg32b psql -U postgres -d cbdb -At -F'|'" <<'SQL'
select ...;
SQL
```

⚠ **引号纪律**：SQL 内字符串一律用**单引号**；`psql` 的 `-At -F'|'` 之外**不要再套双引号**（双引号在 PG 里是标识符定界符，`"template0"` 会报 `column does not exist`）。

## 四、职责边界

- **本档只管实例事实**。库内数据之对错归 `docs/bugs.md`（我方）与 `docs/cbdb.md` 登记册（源生）。
- **dump／备份文件生成调度、端口与 homelab 仓登记＝另派 agent**（2026-09-23 用户令："备份的部分不用你管"）。
- 建成过程、compose 全文、装后核查九项之叙事**已删**（2026-09-30 用户令）；可 `git show 75ecd77:docs/pg32b.md` 取回。建成日＝**2026-09-24**，核查九项全过，6 秒 healthy。

## 五、并行重建之余量（2026-09-30 现算，供 `import-plan.md` §10 阶段四之裁）

| 项 | 余量 | 判定 |
|---|---|---|
| 磁盘 `/` | **189G 可用**；`cbdb` 仅 4,771 MB | ✅ **在同实例并行装一个新库名（如 `cbdb_v3`）余量充足**（需 ~10G 级） |
| RAM | 可用 5G；`shared_buffers` 512MB | ✅ 可跑，但须 `nice`／`ionice` 且守 loadavg<4.0 |
| 当前负载 | loadavg 1.09 | ✅ 低于门禁 |

⇒ **`import-plan.md` 自审第①项（建议不删库、改并行装新库）之磁盘前提已核实成立。**
