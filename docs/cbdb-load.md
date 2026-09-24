# cbdb-load.md —— 哈佛资料装数方案（首批 → pg32b）

> **卷首令与边界**：用户令链——"哈佛的资料怎么入到pg里？"（问路）→"那就装上吧"（装载器，已执行＝pg32b.md §11）→**"36故障，你在32主机上搞"（2026-09-24，本方案之令）**。装数对象由 pg36 改判 **pg32b**（36 故障候恢复；恢复后迁移/同步另议，见差异项⑦）。本文档只做装数方案与执行记录；备份调度/落盘＝另派 agent（pg36.md 卷首令不改）；数据落盘纪律：数据只入 pg32b 库与 32 容器临时区（用毕即删），本工作区零数据副本。

## §0 事实基座（指针，不复述）

- 数据家底/四问裁决史/清洗规则/索引账：`docs/features.md` F-13＋`docs/cbdb.md` §9（**坐标污染、`0` 哨兵、同名锚定、官方索引 ≈307 条**）。
- 货位与通路实测：`docs/pg32b.md` §10（32 本地镜像盘 `/mnt/nas-mirror/61/workmetadata/` 全货在位；`cbdb_20260919.sqlite3` sha 前缀 `bde1bb8e…` 与官方全同）＋§11（装载器 gdal-bin 3.13.2 已就位，驱动 Shapefile〔含 `.shp.zip` 直读〕/CSV/PostGIS 实测在列）。
- 本轮核货新增事实（2026-09-24 只读，32 实测）：
  - `cbdb-project/` 内**无现成 PG DDL/脚本**（find 全空）→ 建表与索引 DDL 权威源＝**sqlite_master 本身**（改写迁移）。
  - 镜像盘 sqlite 复验：tables=**78**、BIOG_MAIN=**661,969**、ADDR_CODES=**30,157**（与官方账全同）。
  - 三小件 `.tab` **实为 TSV**：制表符分隔＋全字段双引号；全元文/书院带 UTF-8 BOM（`utf-8-sig` 读），传教士无 BOM；表头即列名（书院件含中文列名与经纬度列，末列后有多余制表符→空列名须清洗）。
  - V6 三件皆 zip 内整包 shapefile（shp/shx/dbf/prj[+cpg/qpj]）；家中 `chgis-v6/SHA256SUMS.txt` 有县点/府点 utf_wgs84 zip 之 sha256，`VERIFICATION.md` 记**县点＝10,522 条**（对账标答）。
  - Hartwell 29302＝两 zip 共 **5,333 件**之多图层年代包（v1_2002/v5_2010）→ **缓办**（差异项①）。
  - 32 宿主无 unzip；容器有 python3？——容器无需：解压不需要（ogr2ogr `/vsizip/` 直读）；宿主 python3.11 带 sqlite3/csv 模块。
- **装数工作集已立（2026-09-24 用户令"把我们要用的数据copy一份到usedata/harvard下……原来那些就当是下载的原数据备份"；落点经用户确认＝`/mnt/wd61workmetadata/usedata/harvard/`）**：首批数据 7 件＋随附 6 件共 **13 件/594MB** 拷入（32 从本地镜像盘读→写 NAS，单程网络）；核验三重全过——**sha256 双端全同**、府/县点与家中 `SHA256SUMS.txt` 全同（`48f6a50b…`/`3b431d2e…`）、sqlite＝官方 `bde1bb8e…`；本机侧实测 `sha256sum -c` **13/13 OK**；README 出生纸＋SHA256SUMS 在目录。**原树（cbdb-project/harvard-full/chgis-v6）自此降级＝原数据备份（只读，不用于装数）**；32 镜像脚本实核为 `rsync -a --delete` 纯镜像语义→**写必落 NAS 侧方持久**（落点判定依据），每日 12:00 同步后 32 可本地读 `/mnt/nas-mirror/61/workmetadata/usedata/harvard/`（装数优先本地镜像读）。

## §1 目标与角色

- 装数目标：**pg32b**（192.168.3.32:5433，容器内本地 trust 通道执行，无需密码面）。
- 新库：**`cbdb`**（UTF8/template0/集群默认 en_US.utf8 collate——与 pg36 同款）。
- 角色注记：pg32b 由"备份/恢复演练台"**兼营装数靶机**（36 故障期用户口令改判）；演练台本义不废——库成后即天然活备份副本，36 恢复后可 `pg_dump→pg_restore` 反向迁移或双轨，届时另议（差异项⑦）。

## §2 装载清单（首批）与缓办项

| 腿 | 货 | 源路径（**装数工作集** `/mnt/wd61workmetadata/usedata/harvard/` 下；32 每日 12:00 同步后本地镜像 `/mnt/nas-mirror/61/workmetadata/usedata/harvard/` 同款，装数优先本地读） | 落点 |
|---|---|---|---|
| A | CBDB 0919 全 78 表（5,623,075 行账载） | `cbdb/cbdb_20260919.sqlite3` | `cbdb` 库 `public`（标识符不引号→小写，如 `biog_main`） |
| B1 | V6 时序府面（政区多边形） | `chgis/v6_time_pref_pgn_utf_wgs84.zip`（29.7MB，DOI I0Q7SM） | `chgis.v6_pref_pgn` |
| B2 | V6 时序府点 | `chgis/v6_time_pref_pts_utf_wgs84.zip`（0.3MB，DOI WW1PD6） | `chgis.v6_pref_pts` |
| B3 | V6 时序县点 | `chgis/v6_time_cnty_pts_utf_wgs84.zip`（0.5MB，DOI Q9VOF5，标答 10,522 条） | `chgis.v6_cnty_pts` |
| C1 | 全元文索引（TSV，5 列） | `tab/Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab`（DOI HTGBQ3） | `public.quan_yuan_wen_index` |
| C2 | 2957 书院（TSV，约 12 列含经纬度） | `tab/ACADEMY_Data.tab`（DOI J6XRIV） | `public.academies_2957` |
| C3 | 传教士著作（TSV，10 列） | `tab/writings of the 19c missionaries in China.tab`（DOI CE4ZNG） | `public.missionary_writings` |

**缓办（第二批，候另令）**：Hartwell v1/v5（多图层年代包，图层命名规律须先研读）；ADDR_XY/ZZZ 补数据；1911/1820 层；V6 西安80/GBK 变体；扩展补数据。**编码/坐标裁定＝UTF-8＋WGS84**（与 CBDB 坐标同系好 join；差异项⑤）。

## §3 通路（三个零）

**零传输**（货全在 32 本地盘）、**零解包**（ogr2ogr `/vsizip/` 直读 zip）、**零中间落盘**（腿 A/C 管道直灌；腿 B 仅 zip 暂入容器 `/tmp`，用毕 `rm`）。执行机＝32（ssh），本机只发令记账不碰数据。

## §4 腿 A：CBDB 78 表（sqlite→PG）

1. **建库**：`docker exec pg32b psql -U postgres -c "CREATE DATABASE cbdb ENCODING 'UTF8' TEMPLATE template0"`；库内 `CREATE EXTENSION postgis; CREATE SCHEMA chgis;`（postgis 为腿 B 所需；address_standardizer 首批不建，按需另裁）。
2. **DDL 迁移**（宿主 python3 读 `sqlite_master` → 生成 PG DDL → `docker exec -i psql -v ON_ERROR_STOP=1`）：
   - 类型映射（保守忠实）：`INTEGER→bigint`；`TEXT/CLOB→text`；`VARCHAR(n)/CHAR(n)→varchar(n)/char(n)`；`REAL/FLOA/DOUB→double precision`；`NUME/DEC→numeric`；`BLOB→bytea`；无声明→`text`。
   - **不加 PK/FK/UNIQUE 约束**（sqlite 原本无约束＝原样保真，cbdb.md §9.4）；行内 `PRIMARY KEY/AUTOINCREMENT` 字样剥除。
   - 标识符一律不加引号（全库小写化，与官方 PG 移植惯例一致）。
3. **COPY 灌注**：逐表 `python3（sqlite SELECT * → COPY text 格式：NULL→\N，\、制表、换行转义，BLOB→\x十六进制）| docker exec -i pg32b psql -U postgres -d cbdb -v ON_ERROR_STOP=1 -c "\copy <表> FROM STDIN"`。
4. **对账 A**：逐表 `count(*)` 双侧比对（78/78 全同方过）＋总行数对 5,623,075（以实测为准，差则逐表定位）。
5. **索引**：sqlite `CREATE INDEX` 语句全量迁移（实测条数为准，账载 ≈307）；`COLLATE NOCASE` 剥除、表达式索引逐条核 PG 兼容性——**不兼容者列人工复核清单入报告，不静默丢**；索引段前依 PG 官方 §14.4.5/6 调参：会话级 `SET maintenance_work_mem='256MB'`（**压力防护降档，原案 512MB——2026-09-24 用户令"要考虑到32主机的压力"**；不动配置文件）＋ `ALTER SYSTEM SET max_wal_size='4GB'; SELECT pg_reload_conf();`（**2026-09-24 依官方建议补入**，见 §12；**兼为减压项**——检查点更少＝共享 `/` 盘 I/O 更平滑，pg32 数据同盘；pg32b 专库无生产流量、盘余 196G，临时抬高安全），索引毕 `ALTER SYSTEM RESET max_wal_size; SELECT pg_reload_conf();` 复原（前后 `SHOW max_wal_size` 实测记录）；补建＝官方索引未覆盖的 FK 命名列（`c_*id` 类）经目测后补，清单入报告；毕 `ANALYZE`。

## §5 腿 B：CHGIS 空间三件（shapefile→PostGIS）

1. **对账前置**：工作集自检 `sha256sum -c SHA256SUMS`（13 件；拷入时已核**双端全同**＋府/县点与家中账全同＋府面实测 `d3aa9f39…` 在案）。
2. **暂入容器**：`docker cp` 三 zip → `pg32b:/tmp/`（用毕删）。
3. **核货**：`docker exec pg32b ogrinfo -so -al /vsizip/tmp/<zip>/<shp>` → 记录各层要素数/列名（**认 ID 列**：与 `addr_codes.chgis_pt_id` 对接之用）/几何类型/SRID（应 4326）。
4. **灌注**（每层一条）：`docker exec pg32b ogr2ogr -f PostgreSQL "PG:dbname=cbdb user=postgres" /vsizip/tmp/<zip>/<shp> -nln chgis.<表名> -lco GEOMETRY_NAME=geom -lco PRECISION=NO --config SHAPE_ENCODING UTF-8`——SRID 自 `.prj` 带入；**GiST 空间索引 ogr2ogr 默认自建**（`SPATIAL_INDEX=YES`），毕 `\di chgis.*` 核实在案。
5. **对账 B**：各层 `SELECT count(*)` vs ogrinfo 要素数；县点对 `VERIFICATION.md` 标答 **10,522**；中文抽一行肉眼核无 mojibake。
6. **清场**：`docker exec pg32b rm /tmp/v6_*.zip`。

## §6 腿 C：三小件（TSV→text 表）

python3 `csv`（`utf-8-sig`、delimiter=`\t`、quotechar=`"`）读表头→生成 DDL（**全列 text**＝原样保真，类型化后置视图层；**全部列名加双引号**保中文/括号原样；清洗空列名——书院件表头尾部多余制表符）→建表→流式 `\copy … FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', QUOTE '"', HEADER)`（BOM 由 utf-8-sig 在 python 侧剥除，数据流经管道重发）。对账：行数 vs `wc -l`−1（表头）。

## §7 对账与验收（全过方收口）

① 腿 A 78/78 表行数全同＋总数对上账；② 索引创建数/跳过数/人工复核清单三数吻合；③ 腿 B 三层要素数对上＋县点 10,522＋GiST 在＋中文无恙；④ 腿 C 三表行数对上；⑤ **桥验证两发**：`addr_codes.chgis_pt_id ↔ chgis.v6_pref_pts.<ID列>` join 命中率报告；取 3 个坐标非零人物点 `ST_Within(点, chgis.v6_pref_pgn.geom)` 返府名（坐标列位置依 cbdb.md §9 实认）；⑥ 对账总表落本文档 §执行记录；⑦ `postgres` 库与 pg32/36 零触碰复核。

## §8 执行步骤（开工口令后依序）

**主机压力防护六条（2026-09-24 用户开工令附加约束"要考虑到32主机的压力"——32 系 2C4T 小机且跑生产 pg32/n8n 等 11 容器）**：① 全程**顺序单流零并行**（COPY 逐表、索引逐条、ogr2ogr 逐层，不开第二连接）；② 宿主侧进程一律 `nice -n 19`＋`ionice -c3`（空闲类），容器内 ogr2ogr 以 `nice -n 19` 起跑；③ compose 给 pg32b 加 **`cpu_shares: 512`**（生产容器默认 1024——CPU 争抢时 pg32b 自动让路，空闲时不限速；实例配置变更记 pg32b.md）；④ maintenance_work_mem 降档 **256MB**（§4.5）；⑤ **压力闸门**：Step 0 取基线（loadavg／PSI／pg32 healthy＋canary 查询计时／free），**每个大步之间复测——1 分钟 loadavg＞4.0 持续、或 pg32 非 healthy、或 canary 显著劣化 → 立即暂停**，恢复方续；⑥ 夜间窗口执行（开工即 23 时后），预算换稳：**总时长 ≤2.5h**。

- **Step 0** 复核：pg32b healthy、`cbdb` 库不存在（全新建）、盘余量（data 现 55M，预算 +≤5G）、货位点名（§2 七件于 usedata/harvard 逐一 stat＋`sha256sum -c` 13 件全过）＋**压力基线**（防护条⑤）＋compose 加 cpu_shares（防护条③，`config -q` 过→`up -d` 重建秒级→healthy 复证）。
- **Step 1** 建库＋扩展＋schema（§4.1）。
- **Step 2** 腿 A：DDL→COPY→对账→索引→ANALYZE（§4.2–5；2C4T 预算：灌注 ≈10 分钟、索引 ≈15–40 分钟）。
- **Step 3** 腿 B：sha→cp→ogrinfo→ogr2ogr×3→对账→清场（§5）。
- **Step 4** 腿 C：判头已在案（TSV）→DDL→灌→对账（§6）。
- **Step 5** 桥验证＋对账总表＋验收七项（§7）。
- **Step 6** 收口记账：本文档 §执行记录＋F-13 状态推进＋codemap＋log＋push。
- 每步失败即停：`ON_ERROR_STOP=1` 全线生效；任何对账不平→停在该步排查，不带病前行。

## §9 差异项（候裁清单——默认皆按本案，口令时可逐条改裁）

1. **首批范围**＝CBDB 全量＋V6 三件＋三小件；**Hartwell 缓办**（5,333 件多图层包须先研读）。
2. **库构**＝新库 `cbdb`；CBDB 表入 `public`（小写名），空间三层入 `chgis` schema；仅建 postgis 扩展。
3. **保真**＝无 PK/FK/UNIQUE、不清洗、腿 C 全列 text；清洗视图后置（cbdb.md §9 规则已备）。
4. **索引**＝sqlite 官方索引全量迁移＋FK 命名列目测补建；不兼容句进人工清单不静默丢。
5. **编码/坐标**＝UTF-8＋WGS84（EPSG:4326）；GBK/西安80 变体不入。
6. **腿 B 暂存法**＝zip `docker cp` 入容器 `/tmp` 用毕即删（**不动 compose/挂载**，实例配置零变更）。
7. **角色**＝pg32b 兼营装数靶机；36 恢复后迁移/双轨**另议不在本批**。
8. **资源与压力防护**＝会话级 maintenance_work_mem **256MB**（用户压力令降档，原 512MB；配置文件不动）＋compose `cpu_shares: 512`＋全程 nice/ionice＋顺序单流零并行＋步间压力闸门（loadavg＞4 或 pg32 非 healthy 即停）＋夜间窗口；总时长预算 **≤2.5h**（换速保压，§8 防护六条）。
9. **用户面**＝仍 postgres 超户（POSTGRES_USER 改名窗依旧候裁，F-13 在册）。

## §10 风险与回滚

- 回滚一句话：`DROP DATABASE cbdb`（新库独立，postgres 库/实例配置/pg32/36 零涉及）。
- 风险点：索引迁移语句兼容性（人工清单兜底）；`.dbf` 列宽截断为源数据固有（原样保真不修）；2C4T 索引时长（预算内，不并行加载）。

## §11 账目联动

F-13（装数四问之①③④由本方案差异项承接裁决；②靶机改判 32 记录于 F-13）；pg32b.md（实例权威不动，本批只写库不改实例）；codemap（树行＋执行后实例行推进）；bugs（无涉）；执行记录＝本文档 §13（开工后追加）。

## §12 官方与社区经验对照（2026-09-24 开工前调研，用户令"查一下官方对入新库有没有什么建议？或者网上有没有其它人有类似经验"）

### 12.1 PostgreSQL 官方《Populating a Database》（PG18 文档 §14.4）九条 vs 本方案

| # | 官方建议 | 本方案对照 | 判定 |
|---|---|---|---|
| 1 | 关 autocommit／单事务批量提交 | 逐表 `\copy` 单命令＝单事务，天然满足 | ✓ |
| 2 | **用 COPY 不用 INSERT**（大批量显著更快） | 腿 A/C 皆 `\copy … FROM STDIN` 管道；腿 B ogr2ogr PG 驱动内部即走 COPY | ✓ |
| 3 | **先去索引、灌完再建**（"对已有数据建索引快于逐行随灌随建"） | §4 顺序＝COPY→对账→索引，正是官方顺序 | ✓ |
| 4 | 去 FK 约束（百万行级触发器事件队列可溢出致败——官方原话"necessary, not just desirable"） | 保真策略本就不建 FK（差异项③）——**官方背书再加一层** | ✓ |
| 5 | 增大 maintenance_work_mem（利 CREATE INDEX，对 COPY 本身无益） | §4.5 会话级 **256MB**（原 512MB，用户压力令降档），恰只在索引段用 | ✓ |
| 6 | **增大 max_wal_size**（减少批量灌入的检查点次数） | **方案原缺→已修订补入 §4.5**（临时 4GB、毕即 RESET 复原、前后 SHOW 实测） | ✗→✓ 本批修订 |
| 7 | 禁 WAL 归档/流复制（wal_level=minimal 等，**须重启**，且废既有基础备份） | **有意不采纳**：须重启实例＋破坏将来物理备库预案＋archive_mode 本就 off＋600MB 级收益小——差异如实记 | 不采纳（有据） |
| 8 | 灌毕 ANALYZE | §4.5 末在案 | ✓ |
| 9 | pg_dump/pg_restore 恢复要点（`-j` 并行、`-1` 单事务之取舍、恢复后取新基础备份） | → **指针给将来 36 迁移腿与备份 agent**（本批不用） | 指针 |

**净结论：九条中七条本方案天然吻合、一条补入（max_wal_size）、一条有据不采纳（wal_level）——方案骨架与官方建议同向。**

### 12.2 CBDB 官方对"入 PG"的建议：**无（全文实证）**

- 官方 HuggingFace 仓 `cbdb/cbdb-sqlite` 数据卡实抓：只有**下载点**（latest＋history）与**许可 CC BY-NC-SA 4.0**（与本账旧记一致），无任何迁移/入库指引。
- **CBDB《User's Guide》全文已抓到**（M. Fuller，rev. 2021-10，**153 页**；harvard 直连 403 系服务器端反爬→改经 wayback 存档取 PDF、`pdftotext` 转文）：官方支持面＝序言原话 **Access（主制式）＋SQLite（"for quantitative researchers and Mac users"）**；另有历史附录《CBDB SQL Server Version》（CBDB_SS，SQL Server Express 平台，系绕 Access 文件大小限制之产物）；**全文检索 PostgreSQL/PostGIS/MySQL 命中＝0**——"官方无入 PG 指引"系全文实证，非推断。
- **含义**：CBDB→PG 无官方成例可循，本管线属自建——§7 对账验收七项即安全网（官方无指引处，以可复核对账代之）。

### 12.3 社区同类经验

- **sqlite→PG 大路工具＝pgloader**（Neon/Netbird/Render 三家迁移指南一致推荐）；其 Debian bookworm 有官方包。**本案不用**，理由：装它＝32 宿主系统改动（超实例边界须另令）；本管线 python3 标准库零新装、且类型映射/BLOB 十六进制/NULL 语义全可控。**备选地位记录在案**（若 78 表管道遇阻可裁启用）。
- 社区踩坑清单（open-webui 迁移讨论等）：类型亲和性（sqlite 动态类型→PG 静态）、BLOB、标识符大小写、布尔表示——**本方案 §4.2 映射表逐条已覆盖**（INTEGER→bigint／BLOB→bytea hex／不引号全小写／无布尔列）。
- **CBDB 专向入库项目：检索未见现成开源管线**（学术侧有 CBDB 关系库论文与 R/Python 访问包，皆非 PG 迁移）——与 12.2 互证。
- CHGIS→PostGIS **官方手册对照（PostGIS 3.6 Manual 第 4 章 §4.7 "Loading Spatial Data"，全文已抓）**：官方内建装载法两条——①SQL 语句（WKT/WKB 经 `psql -f`）②**shp2pgsql 装载器**（关键旗标：`-D` dump 格式＝COPY 快速模式，官方原话 "Use this for very large data sets"；`-I` 建 GiST；`-W` DBF→UTF8 编码转换；`-s` 指定 SRID；`-e` 逐句事务）。本方案之 **ogr2ogr＝GDAL 项目官方工具**（与 shp2pgsql 同属 PostGIS 生态、内部同走 COPY），功能覆盖上述要点：`.prj` 自动带 SRID 4326（≈`-s`）、GiST 自建（≈`-I`）、UTF-8 变体＋`SHAPE_ENCODING`（≈`-W` 且从根上免转换）、`/vsizip/` 直读 zip（shp2pgsql 所无）。**差异记录**：若须严格按手册原生工具，可加装 PGDG `postgis` 装载器包（F-13 ③(a) 候选，与 gdal-bin 同批可加）——默认不变（ogr2ogr 已本机实证三驱动在列）。编码历史坑（PostGIS 邮件列表 2011 年 shp2pgsql 客户端编码旧案）→本案 UTF-8 变体从根绕开 GBK。

### 12.4 调研出处（引用为外部资料，内容以原文为准）

- PostgreSQL 18 官方文档 §14.4 Populating a Database：postgresql.org/docs/current/populate.html（经 web.archive 存档实抓全文）
- PostGIS 3.6 官方手册第 4 章 §4.7（Loading Spatial Data）：postgis.net/docs/manual-3.6/using_postgis_dbmanagement.html（curl 实抓全文切片）
- CBDB《User's Guide》（Fuller，rev. 2021-10，153 页）：harvard 直连 403（服务器端反爬）→经 web.archive.org/web/20240914131845 取 PDF 全文、本机 `pdftotext` 转文检索（临时文件仅在 /tmp，不入工作区）
- CBDB 官方 HF 数据卡：huggingface.co/datasets/cbdb/cbdb-sqlite（实抓）
- 社区迁移指南：render.com《How to migrate from SQLite to PostgreSQL》、docs.netbird.io（pgloader 路）、github.com/open-webui/open-webui Discussion #21609（踩坑清单）
- 编码旧案：lists.osgeo.org pipermail postgis-devel #1303
- CBDB 学术描述：OpenHumanitiesData《CBDB: A Relational Database for Prosopographical Research of Pre-Modern China》（2022）

## §13 执行记录（开工后追加）

---

**状态：方案已立，候开工口令（"同意"＝差异项九条默认全按本案）。**
