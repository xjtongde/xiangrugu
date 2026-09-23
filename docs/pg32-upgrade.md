# pg32-upgrade.md —— pg32 升级方案（全功能 PostgreSQL 镜像）

> **状态**：方案成文（2026-09-23，用户令"制作 pg32 升级方案"）。**执行待开工口令（R-01）**——本文是实施方案，不是实施记录。
> **前置账目**：`docs/features.md` F-13（CBDB／CHGIS 入 PostgreSQL 数据底座）；用户口径两条均已入账 F-13：**单实例优先**、**依赖只取官方源（PGDG）**。
> **范围**：仅升级 32 主机（lx03）上的 `pg32` 实例为"PG18 最新小版本＋官方源全功能扩展集"的自建镜像。**不含** CBDB／CHGIS 数据导入（属 F-13 后续步骤，另行口令）；**不含**同机其他容器。

## §1 官方资料核对（2026-09-23 实测，十项全过）

| # | 我们的理解 | 官方出处（当日实fetch） | 结果 |
|---|---|---|---|
| 1 | PGDG 是 PostgreSQL 官方推荐的 apt 源，且与系统补丁管理集成 | postgresql.org/download/linux/debian/ 原文 *"This repository will integrate with your normal systems and patch management"* | ✅ |
| 2 | 小版本升级（18.4→18.6）**不改内部存储格式**，直接换二进制即可，无需 pg_upgrade／dump-restore；**回退亦安全** | postgresql.org/docs/current/upgrading.html 原文 *"Minor releases never change the internal storage format and are always compatible with earlier and later minor releases"* | ✅ |
| 3 | PostGIS 3.6 有配 PG18 的官方源包 | PGDG bookworm-pgdg 索引：`postgresql-18-postgis-3`＝**3.6.4+dfsg-2.pgdg12+1**（另有 `-scripts`） | ✅ |
| 4 | contrib 扩展**已并入主包**，无独立包 | PGDG 索引 `postgresql-contrib-18` **不存在**（grep 计数 0）；主包 `postgresql-18`＝18.6-1.pgdg12+2；pg32 实测裸镜像即有 `pg_trgm`／`hstore` 等 | ✅ |
| 5 | 扩展**按库启用**：装包只是把文件放上磁盘，`CREATE EXTENSION` 才生效于当前库 | postgresql.org/docs/current/sql-createextension.html 原文 *"CREATE EXTENSION loads a new extension into the current database"* | ✅ |
| 6 | PostGIS 二进制升级后须逐库 `ALTER EXTENSION postgis UPDATE;` | postgis.net/docs/postgis_installation.html 原文 | ✅ |
| 7 | `pg_stat_statements` 必须写入 `shared_preload_libraries`，改此项须重启 | postgresql.org/docs/current/pgstatstatements.html 原文 | ✅ |
| 8 | `pg_cron` 同样需 preload | citusdata/pg_cron README（PGDG 发行的官方项目仓） | ✅ |
| 9 | 官方 PG18 镜像数据目录约定：`VOLUME /var/lib/postgresql`、`ENV PGDATA /var/lib/postgresql/18/docker` | docker-library/postgres `18/bookworm/Dockerfile` L191–192 | ✅ **与 pg32 现有挂载一致**（升级不会误初始化空集群） |
| 10 | 中文分词扩展不在官方源 → 按用户口径**不装** | PGDG 索引实测 `pg_bigm`／`zhparser`／`pgroonga` 源内无；替代＝应用层分词存 `tsvector` 走核心 FTS | ✅ |

**补正一处细节**（非推翻）：官方镜像构建时把 PG 二进制**钉在镜像构建时点的小版本**（Dockerfile 用 `postgresql-$PG_MAJOR=$PG_VERSION`）——所以"拿到 18.6"靠的是**升级当日重新 pull 基础镜像**，本方案流程天然满足；若届时基础镜像已走到 18.7，**照走**（同一逻辑，小版本向后兼容），以实际为准并记录。

## §2 现状快照（2026-09-23 实测；权威展开＝F-13 实勘行）

- 宿主 lx03（192.168.3.32）：Debian 12／4 核／7G（可用 5G）；`/dev/sdb1` 余 **196G**
- `pg32`：镜像 `postgres:18-bookworm`（2026-08-10 拉取，**18.4**），端口 **5432**，数据目录宿主 `/opt/mydocker/postgres/data/postgres`（395M）→ 容器 `/var/lib/postgresql`；compose 在 `/opt/mydocker/postgres/`（`.env` 含凭据，**不入本仓**）
- 现有库：`nbdc`(112M)／`nbdc_test`／`n8n`／`chainlit`／`home_graphrag_chainlit`；已装扩展仅 `plpgsql`
- 同机 live 服务共用此实例：n8n(:5678)／chainlit(:8002)／graphrag(:9100)／calibre／portainer／nginx——**升级窗口会闪数十秒**

## §3 目标态

- **镜像**：自建 **`pg32-full:18.6-pgdg`**（tag 名可改）＝ `FROM postgres:18-bookworm` ＋ PGDG 扩展集（§4），**在 32 本地 build**
- **实例**：单实例不变——端口 5432、挂载、`env_file`、restart 策略、healthcheck **全部保持**
- **preload 最小集**：`pg_stat_statements`（`pg_cron` 装了但**不预加载**，将来真要定时任务再改）
- **扩展**：全部装入镜像、**一律不启用**；建 `cbdb` 库时按需 `CREATE EXTENSION postgis` 等（属 F-13 装数步骤，不在本方案）

## §4 Dockerfile（审稿用草案）

```dockerfile
# pg32-full —— PG18 ＋ PGDG 官方源全功能集
# 口径：只取官方源；钉 PG 大版本（18），扩展版本随 PGDG 浮动（官方源保证配套）
FROM postgres:18-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
      postgresql-18-postgis-3 postgresql-18-postgis-3-scripts \
      postgresql-18-pgrouting postgresql-18-h3 postgresql-18-address-standardizer \
      postgresql-18-pgvector postgresql-18-rum postgresql-18-pg-ivm postgresql-18-hypopg \
      postgresql-18-cron postgresql-18-repack postgresql-18-partman postgresql-18-pgaudit \
      postgresql-18-wal2json postgresql-18-pg-stat-kcache \
      postgresql-18-mysql-fdw postgresql-plpython3-18 postgresql-18-pgtap \
      postgresql-18-pglogical postgresql-18-decoderbufs \
   && rm -rf /var/lib/apt/lists/*
```

注：
- **不钉扩展版本**——PGDG 会清旧版包，钉死会致日后构建失败；配套性由官方源保证（§1 核对 1）
- `pointcloud` **不装**（本项目无点云用途；要用再加一行）
- `pgdg.list` 基础镜像已自带（pg32 容器内实测在位），**无需配置任何第三方源**
- 体积预估：基座 629MB → **约 1.2GB**（PostGIS 拖 GEOS／PROJ／GDAL；预估值，build 时实测）

## §5 实施步骤（开工口令当日，严格按序）

**Step 0 预检（只读，~5 min）**
1. `docker pull postgres:18-bookworm` → `docker image inspect`：核 `Env.PGDATA`＝`/var/lib/postgresql/18/docker`、`Volumes` 含 `/var/lib/postgresql`（§1 核对 9）；**记录实际小版本与旧镜像 digest（回滚锚点）**
2. 记录基线：`select version()`；`\l` 库列表与大小；每库抽 1–2 张表 `count(*)`
3. `df -h /opt`；确认 compose 文件与 `.env` 位置

**Step 1 构建镜像（32 上，~5–15 min 视网络）**
1. §4 Dockerfile 落 `/opt/mydocker/postgres/Dockerfile`
2. `docker build -t pg32-full:18.6-pgdg /opt/mydocker/postgres/`
3. 冒烟（不碰现有容器）：`docker run --rm pg32-full:18.6-pgdg postgres --version` → 18.6；`docker run --rm --entrypoint ls pg32-full:18.6-pgdg /usr/share/postgresql/18/extension/ | grep -c postgis` → >0

**Step 2 备份（~3 min；备份目录默认 `/opt/mydocker/postgres/backup/`，落盘位置待用户确认）**
1. 在线逻辑备份：`docker exec pg32 pg_dumpall -U <user> > backup/pre-upgrade-$(date +%F).sql`
2. `docker compose stop`（**只停 pg32**）
3. 冷备：`tar czf backup/data-pre-upgrade-$(date +%F).tar.gz -C /opt/mydocker/postgres/data postgres`（395M）
4. `cp` compose.yml 与 `.env` 入 backup/

**Step 3 换镜像重启（停机 ~1–3 min）**
1. compose `image:` → `pg32-full:18.6-pgdg`
2. compose 加 `command: postgres -c shared_preload_libraries=pg_stat_statements`
3. `docker compose up -d`；`docker logs -f pg32` 至 ready——**若日志出现 initdb 字样＝数据目录没对上，立即停并走 §6 回滚**

**Step 4 验收清单（全过才收工；任一不过 → §6）**
- [ ] `select version();` → 18.6（或 Step 0 记录的实际小版本）
- [ ] `\l` → 五库齐全、大小与基线相符；抽样行数与基线相符
- [ ] n8n(:5678)／chainlit(:8002)／graphrag(:9100) HTTP 恢复
- [ ] PostGIS 冒烟：`create database _smoke;` → `\c _smoke` → `create extension postgis; select postgis_full_version(); create extension pg_stat_statements;` → `drop database _smoke;`
- [ ] `docker inspect pg32` → restart 策略／挂载／端口未变

**Step 5 收尾**
- 记账：log.md 一行＋F-13 状态行更新＋codemap §2 部署事实刷新（镜像名／版本／扩展集）
- 备份保留 7 天（或按用户指示处置）

## §6 回滚预案

| 场景 | 动作 | 数据风险 |
|---|---|---|
| 验收不过／服务异常 | compose `image:` 改回 `postgres:18-bookworm@sha256:<Step 0 记录的旧 digest>` → `up -d` | **无**——数据目录全程未动；小版本双向兼容（§1 核对 2） |
| 数据目录异常（极低概率） | 停 → 解 tar 冷备回原位 → 旧镜像起 | 恢复至冷备点，损失停机期间增量 |
| 构建失败（网络／源） | 重试或改时段；**旧容器未动，服务无感** | 无 |

## §7 风险与对策

| 风险 | 对策 |
|---|---|
| PGDATA／挂载不一致 → 误初始化空集群 | Step 0 inspect 核对；Step 3 盯日志见 `initdb` 即回滚 |
| preload 库缺失 → PG 起不来 | 最小集（仅 `pg_stat_statements`）；Step 1 已冒烟 |
| live 服务闪断 | 选低使用时段；停机 ~1–3 min，事先知晓 n8n／chainlit 使用方 |
| 构建时基础镜像已走到 18.7 | 照走（同逻辑），按实际记录（§1 补正） |
| 磁盘 | 镜像 ~1.2G＋备份 ~0.5G，余 196G 充足 |
| apt 源网络故障 | PGDG 走 https；失败重试，不涉及第三方源 |

## §8 验收标准（全过为成）

1. `version()` ＝ 18.6（或构建时实际小版本）
2. 五库及抽样数据与基线一致
3. 同机三 live 服务恢复访问
4. PostGIS 冒烟通过（`create extension postgis` ＋ `postgis_full_version()`）
5. 回滚锚点在案（旧镜像 digest 已记录、三份备份存在）

## §9 纪律边界

- 本方案**执行须用户开工口令**（R-01）；方案成文≠开工
- 32 上改动仅限：`/opt/mydocker/postgres/`（Dockerfile、compose、backup/）与 `pg32` 容器本身；**其他容器一概不碰**
- CBDB／CHGIS 装数**不在本方案**（F-13 后续步骤：入库范围／保真策略／索引策略届时另议）
- 备份落盘位置默认 `/opt/mydocker/postgres/backup/`（32 本盘）；如需他处，**由用户指定**（落盘纪律）
