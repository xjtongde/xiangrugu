# pg32b.md —— 32 主机新建 pg32b 实例施工方案（备份／恢复演练台）

> **状态**：**已执行（2026-09-24，"同意"令）——pg32b 建成、装后核查九项全过，执行记录＝§9**。
> **用户令链**（裁决依据，照录不改写）：F-14 诉求"我想pg在35上也装一个" → "你看一下32，33，35那个更适合？" → "36上的那个镜像可以直接用吧？" → **"好，那就听你的建议在32机上装吧。"**（2026-09-24）——主机＝32 已裁；建议技术路线（复用 pg36 镜像／save-load 传输／让口 5433／参数缩配／新凭据）即照此成案，出入之处全数列 §7 差异项候裁。
> **职责边界**（沿 pg36.md 卷首令）：本档只管**安装与装后核查**。备份文件的生成调度、端口／homelab 仓登记＝另派 agent（§8）。
> **定位**：第三实例＝**备份／恢复演练台**（"另一个专门备份用"口径的具体化——用户如另有定位，口令时一并明示）。

---

## §0 事实基座（指针引用，R-04 不复述）

- **镜像**＝36 之 `pg36-full:18-pgdg`：PG **18.6**＋PostGIS **3.6.4**＋21 包全表与 address-standardizer 裁减裁决 → `docs/pg36.md` §13 ＋ codemap §2"36 之 pg36 实例"行。
- **复用核证**（amd64／基座 bookworm 全配／save-load 定案／复用≠照抄四件）→ F-14"镜像复用核证"条。
- **32 实况**（i7-6567U／RAM 可用 5.5G／`/` 余 196G＋nas-mirror 大盘 829G／时区两文件正常**无 B-02**／nginx32 unhealthy 观察项）→ codemap §2"第三实例选型三机实勘"行。
- **pg32 本尊**（不动一字）：`0.0.0.0:5432`、网络 `postgres_pg_net`、数据 `/opt/mydocker/postgres/data/postgres`——2026-09-24 实测账。

## §1 冲突排查（本批只读实测，2026-09-24）

| 项 | 实测 |
|---|---|
| 端口 5433 | **空闲**（在用端口 22/80/111/443/5432/5678/8002/8081/8181/9100/9443） |
| 容器名 `pg32b`／`pg32-backup` | 空闲 |
| 目录 `/opt/mydocker/pg32b`／`postgres-b` | 空闲 |
| 网络 `postgres_pg_net` | **pg32 在用**——本案不加入、不自同名，新建独立 bridge `pg32b_default` |
| 36↔32 ssh | **互不能直连**（host key 未建立——属系统配置，不建、不动）→ 传输走**本机管道中转**（§3），本机零落盘 |

## §2 七要素草案（落盘 `/opt/mydocker/pg32b/`＝compose＋.env＋README 三件）

> **前向注（执行时勘正）**：以下草案 YAML **漏 `env_file:` 行**（compose 之 `.env` 仅变量替换、不注入容器环境）——首起即退、无副作用，修正后 6s healthy；**实盘件已含 `env_file: [ .env ]`**，全过程见 §9 执行记录。

**docker-compose.yml**：

```yaml
name: pg32b
services:
  pg32b:
    image: pg32b-full:18-pgdg          # 传输后 retag，见 §3
    container_name: pg32b
    restart: unless-stopped
    ports:
      - "0.0.0.0:5433:5432"            # 让口：5432 系 pg32 生产口
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./data/postgres:/var/lib/postgresql
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro # 标准 §9 全规格——32 无 B-02，此行可全须照挂（与 pg36 唯一挂载差）
    shm_size: 128mb
    command:
      - postgres
      - -c
      - shared_preload_libraries=pg_stat_statements
      - -c
      - shared_buffers=512MB           # §7③ 缩配（pg36 的 1GB 系按 15G RAM 配，32 让着现有服务）
      - -c
      - work_mem=8MB
      - -c
      - maintenance_work_mem=128MB
      - -c
      - effective_cache_size=2GB
      - -c
      - max_connections=50
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: json-file
      options: { max-size: "50m", max-file: "5" }
    networks: [pg32b_default]
networks:
  pg32b_default: {}
```

**`.env`**（32 上现算 `openssl rand -hex 16`，chmod 600；**明文不出 32、不落任何日志／台账／对话**——pg36 纪律原样）：`POSTGRES_USER=postgres`／`POSTGRES_DB=postgres`／`POSTGRES_PASSWORD=<现算>`。

**README.md**：版本全表（抄自镜像 label 之 21 包）、**来源注记**（本镜像＝36 `pg36-full:18-pgdg` 同字节拷贝，label 系 `pg36.*` 冠名如实保留——镜像 label 构建时 baked、retag 不改，故来源与角色以本 README＋compose 注释为记载处）、传输与回滚法、凭据位置纪律。

## §3 传输与 retag（唯一动镜像的两步）

1. `ssh root@36 'docker save pg36-full:18-pgdg' | ssh root@32 'docker load'`（经本机管道直通，两端皆已实测可达；**本机不落盘**）。
2. 32 上：`docker tag pg36-full:18-pgdg pg32b-full:18-pgdg` → `docker rmi pg36-full:18-pgdg`（32 只留 32 冠名版；36 原件系拷贝非移动，分毫不动）。

## §4 施工步骤（Step 0–5）

| 步 | 内容 | 通过判据 |
|---|---|---|
| 0 | 冲突复核（§1 各项现场再查一遍，防勘察→施工间隔漂移） | 全空 |
| 1 | 传输＋retag（§3） | 32 `docker images` 见 `pg32b-full:18-pgdg`，digest 与 36 端核对全同 |
| 2 | 落盘 `/opt/mydocker/pg32b/` 三件套（.env 现算 600） | 文件就位、密码未出 32 |
| 3 | `docker compose up -d` | healthy（pg36 实证 t≈15s；首起 initdb 仅在**新空目录**，与 pg32 数据零接触——挂载路径已在 §1 核死） |
| 4 | 装后核查（§5） | 全过 |
| 5 | 收口记账＋交接素材（连接法 `host=192.168.3.32 port=5433`／凭据位置，供另派备份 agent 取用） | 三账齐、log 落 |

## §5 装后核查清单

1. `SELECT version()`＝**18.6**（与 pg36 全同版本——演练台同构之证）。
2. 冒烟库建→`CREATE EXTENSION postgis;`→`CREATE EXTENSION address_standardizer;`（验移植后镜像完整性含裁减遗留态）→删库。
3. **双口对答**：5432 仍答 18.4（pg32 无恙）、5433 答 18.6（pg32b）——版本成对即端口归属铁证。
4. 远程连通：32 宿主经容器外 IP:5433 psql 正反两测（法照 pg36 §8 Step 5；无密码负向须被拒）。
5. 参数逐条 `SHOW` 对照 §2 表。
6. 时区：容器内 `date` 与 32 宿主一致（全规格挂载首次实挂）。
7. healthcheck 绿／restart 策略／shm／日志四轮转在位。
8. **现有服务影响排查**：pg32 及 graphrag/chainlit/n8n/calibre/portainer 健康态与勘察基线逐项对照；`ss -tln`＝基线**＋5433** 恰一行增量；`df` 无异常。
9. homelab 标准 §13 清单逐项过（TZ／挂载／命名／网络／healthcheck／日志／restart／端口等）。

## §6 回滚

`docker compose down` → 删 `./data`（新库无生产数据可言）→ `docker rmi pg32b-full:18-pgdg` → 删 `/opt/mydocker/pg32b/`——**全程 pg32 与既有容器零接触**，回滚不留痕。

## §7 差异项／待裁清单（默认＝照本案；口令时一并裁）

| # | 项 | 本案取定 | 备注 |
|---|---|---|---|
| ① | 命名 | 容器 `pg32b`／镜像 `pg32b-full`／目录 `/opt/mydocker/pg32b`／网络 `pg32b_default` | 不满意即改名再建（b＝backup） |
| ② | 端口 | **5433**（5432 系 pg32 让不得） | |
| ③ | 参数缩配 | 512MB／8MB／128MB／2GB／50 conn | 系"与 pg36 有意不同"——32 内存让着现有七容器 |
| ④ | 同构策略 | 全功能镜像＋preload 照 pg36——**验货台的意义即在同构**，勿嫌"备份机何必" | 若用户明说要裸镜像另议，本案不推荐 |
| ⑤ | 时区挂载 | `/etc/timezone` 行**全规格照挂**（与 pg36 的 §11⑤ 裁决相反相成：32 无此坑，据实即挂） | |
| ⑥ | label 冠名 | `pg36.*` 原样随镜像（retag 改不了 label），来源记 README＋compose 注释 | 非疏漏，系镜像机制如实 |

## §8 边界（本案不做）

dump 的生成与调度／备份文件落盘（NAS／nas-mirror 大盘）／端口与实例进 homelab 仓登记／pg36 装数联动（F-13 另议）——均另派或另案。

---

## §9 执行记录（2026-09-24，开工＝用户令"同意"承接"在32机上装吧"）

> 差异项六条（§7）全数默认照案（用户"同意"）。

- **Step 0 冲突复核**（防漂移）：5433 空闲／`pg32b` 名空闲／`/opt/mydocker/pg32b` 目录空闲／网络空闲／镜像名两端无冲突；基线快照留存（11 容器态、端口 13 条、pg32 healthy、`/` 余 196G）。
- **Step 1 镜像移植**：`ssh 36 docker save | ssh 32 docker load` 经本机管道直通**12.5 秒**、本机零落盘；**指纹两端全同 `sha256:06ad5ef6a527…`**；32 上 retag `pg32b-full:18-pgdg` 后原名删净（`docker images` 无杂 tag）；**36 原件核实无恙**（拷贝非移动）。
- **Step 2 落盘**：`/opt/mydocker/pg32b/{docker-compose.yml, .env, README.md}`；`.env` 密码 32 现算（32 hex 位）600、**明文零外落**；compose 校验过。
- **执行偏差一处（草案自身缺陷，如实记）**：§2 草案 YAML **漏 `env_file:` 行**——compose 之 `.env` 仅作变量替换、不注入容器环境，官方镜像缺 `POSTGRES_PASSWORD` 拒绝初始化即退（日志实证 `You must specify POSTGRES_PASSWORD…`；**副作用零**：未及 initdb、数据目录未触）。修正＝compose 补 `env_file: [ .env ]` 重建 → **6 秒 healthy**、initdb 正常首跑。续修 README 一处小疵（首写时块重定向只及末行，重写后 32 行全表 21 包齐）。§2 草案处已补前向注。
- **Step 3 起容器**：healthy t=6s；数据目录 `…/data/postgres/18/docker` `drwx------` UID 999（PGDATA 约定与 §1 镜像账吻合；宿主 passwd 恰占 999 名"dnsmasq"系显示映射非异常）。
- **Step 4 装后核查（§5 九项全过）**：① `version()`＝**PG 18.6 (Debian 18.6-1.pgdg12+2)** 与 pg36 全同；② 冒烟库建→`postgis=3.6.4`＋`address_standardizer=3.6.4` 启用成（**移植后镜像完整性＋裁减遗留态复验通过**）→删库净；③ 参数九条逐一 `SHOW` 合案（512MB/8MB/128MB/2GB/50conn/preload pg_stat_statements/UTF8）；④ 时区＝标准 §9 **全规格三挂载实挂核验**（binds 三行含 `/etc/timezone:ro`；容器内外 `date` 逐秒一致、`Asia/Shanghai`——与 pg36 相反相成：32 无 B-02 据实全挂）；⑤ pg_hba 末行 `host all all all scram-sha-256`；⑥ 远程**负向**无密码拒（`fe_sendauth: no password supplied`）；⑦ 远程**正向**借 pg32 客户端（32→5433）答 **18.6**——版本差异即应答者系 pg32b 之铁证（32 本机 5432 系 pg32=18.4）；⑧ 运行时＝restart unless-stopped／shm 128mb／json-file 50m×5／healthcheck pg_isready／端口 `0.0.0.0:5433:5432`；⑨ **现有服务零影响**：基线 11 容器态逐项未漂移（pg32 healthy 依旧、nginx32 维持原 unhealthy 观察项）、`ss -tln`＝基线**＋5433 恰一行**、pg32b 空闲 79.3MiB／CPU 0.09%、`/` 用量仅＋~1G（镜像）。
- **Step 5 收口**：本节＋三账联登（codemap §2 实例行＋§1.2 树、index 条目→已执行、F-14→已建成）；**交接素材（供另派备份 agent）**：连接法 `192.168.3.32:5433`（scram）／凭据＝32 `/opt/mydocker/pg32b/.env`（600，明文未出 32）／镜像 label 系 `pg36.*` 冠名如实（§7⑥）／回滚三步见 README。
- **边界自检**：32 改动仅 `/opt/mydocker/pg32b/` 一处＋其容器/镜像/网络，pg32 与其网络/数据**零接触**；36 全程只读（save/inspect）原件原服务无恙；本机零落盘零安装；标准 §13 清单逐项过（端口登记项归另派 agent，同 pg36 口径）。

---

## §10 完备性复勘（2026-09-24 建成后台次批，用户令"就pg32b这个库，查一下还缺少什么"；**全程只读**）

- **箱内健全**：设置全合案（UTF8／scram／`listen *`／wal_level=replica／hot_standby=on／max_wal_senders=10／shared_buffers 512MB 实测＝65536×8kB）；pg_hba 八线清（远端一律 scram）；角色仅 postgres 超户（干净）；容器内客户端四件套 **18.6 全在**（pg_dump/pg_restore/pg_basebackup/pgbench——演练无需外出借件）；`pg_available_extensions` 81 项、34 点名逐项命中（唯 partman 实名 `pg_partman` 系查询笔误非缺）；数据目录 56M 新净。**日志 4 条 ERROR 系我方核查查询的引号笔误自伤，非服务器病**（如实记）。
- **通路实测意外已通**：32 有 cron `/opt/mirror-nas.sh`（每日 12:00＋@reboot）把 NAS 镜像到本地大盘 `/mnt/nas-mirror/61/workmetadata/`——**`cbdb_20260919.sqlite3` sha256 前缀 `bde1bb8e…` 与官方/家中构建全同（586,485,760 字节分毫不差）**、`harvard-full` 374 文件全目在（目录时 2026-09-23 23:05）、`chgis-v6` 在。**故 CBDB 灌入腿在 32 本机＝零缺口**（python3.11 带 sqlite3 模块＋容器内 psql `\copy` stdin，工具链齐）。
- **真缺口三条**：① **shapefile 装载器两无**——镜像内与 32 宿主均无 shp2pgsql/ogr2ogr（与 pg36 同源同像同缺）→ CHGIS 空间腿无入口；补法＝重建加 `gdal-bin`（PGDG 官方源）——**注意联动**：若欲保"与 pg36 同构"，36 镜像亦须同日加建（否则台⊃厂一步之遥，亦可接受）；② **pg_hba 无远端复制行**——仅当备份架构取"流式物理备库"时才是缺口（wal_level/hot_standby/senders 皆已就绪，只欠一行＋pg36 端配套）；属备份 agent 架构裁决；③ **无目标库**（仅 postgres）——恢复/直灌时 `--create` 即成，运行态非缺陷。
- **备注**：archive_mode=off（若需连续 WAL 归档，属备份 agent 架构裁决项）；`pointcloud` 未装（"全功能"候选清单在列但 21 包终选未含，pg36 同——于史地数据用途非缺）。

---

## §11 装载器补装执行记录（2026-09-24，用户令"那就装上吧"）

- **范围裁定**：只动 pg32b（用户前令"现在不要考虑pg36"）；**36 的同构联动同建挂起候另令**（F-13 ③(a) 于 36 侧同款适用）——谱系自此分叉一层，README＋codemap 已注记。
- **方法＝增量层重建**（基座 21 包不重拉）：`docker tag 06ad5ef6a527 pg32b-base:18-pgdg` 钉基座锚（防同名 tag 自叠层）→ `Dockerfile`：`FROM pg32b-base:18-pgdg` ＋ `apt-get install --no-install-recommends gdal-bin`（PGDG 官方源浮动，政策同 21 包）＋ `LABEL pg32b.loader` 来源注记 → compose 增 `build: context: .`（部署目录自包含可重建）→ `.dockerignore` 排除 `.env/data/README`（**凭据不入构建上下文**）。
- **执行与核查（九点全过）**：build 成功——实装 **gdal-bin 3.13.2+dfsg-1.pgdg12+1**（与 F-13 探查之 PGDG 候选版本逐字全同）；`up -d` → **healthy t=6s**；新镜像 `d562e436…`＝基座＋1 层、**增量仅 +42MB**（"libgdal 已随 postgis 在基座"预判兑现）；`ogr2ogr --version`＝**GDAL 3.13.2 "Iowa City"**；驱动三件套实测在列——**ESRI Shapefile（rw＋uv，含 `.shp.zip` 直读，免先解包）**／CSV／**PostgreSQL/PostGIS（rw）**＝**§10 真缺口①销案，CHGIS 空间腿入口已通**；服务器面分毫未变（18.6／available 81 项／仅 plpgsql／shared_buffers 512MB／datadir 55M／TZ 逐秒一致／基座 label `pg36.*` 原样完整）；`shp2pgsql` 仍无（gdal-bin 单件政策——ogr2ogr 足覆，如需另裁）。
- **观察注记（非本批所致，如实记不猜因）**：收尾核验时 **36 不可达**（ping 100% 丢包＋ssh No route to host，22:22 实测两度）；本批对 36 **零写操作**（仅 17:10 只读 save/inspect，当时核实无恙）；pg36 运行态**待 36 恢复后核验**，核验项＝`docker inspect pg36` healthy＋`pg36-full` ID 仍 `06ad5ef6…`。
