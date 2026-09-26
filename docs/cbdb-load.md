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

**缓办（第二批，候另令）——四条明细**（2026-09-25 用户令"你应该一字不差的写到里面的"照录入账；此前本节只有一行简述、四条展开只在对话未入账——账目疏漏就此补齐。对话原文照录，仅时间指代词换算为绝对日期/节号）：

1. **Hartwell 29302 —— CHGIS 的"年代切片大包"**：Robert M. Hartwell 是 CBDB/CHGIS 的创始人（cbdb.md §源流），Dataverse 上编号 29302 的这份货＝**两个 zip、共 5,333 个文件**的多图层年代包（v1_2002／v5_2010 两代版本），把中国历史政区按年代一层层切开。**缓办原因**：首批三件（府面/府点/县点）是单文件单层、拿来就装；这个包 5,333 件、图层命名规律得先研读，工程量完全不同级。**在 32 镜像盘 harvard-full 里，本地已有，无需下载。**
2. **ADDR_XY —— CBDB 的"今地坐标表"**：官方 2024-02 档案件里有一张 `ADDR_XY`（每个地址点的现代经纬度），0919 快车道版把它裁掉了（cbdb.md §9.2 在账的缺项之一）。**用处**：人物/地点直接落图。**两个注记**：账上早写明"可由 CHGIS_PT_ID 桥绕过"——而这座桥已于首批执行时（2026-09-25）建通（join 命中 7,125）；且该表坐标有已知污染，用时须剔。**在 2024-02 档案件里，本地已有**（索引 DDL 就是从它抽的）。
3. **ZZZ —— 官方"预连接宽表"族（处置：不装——2026-09-25 用户口径"我们不需要"＋下述实证）**：官方为自家 Access 查询界面预先 join 好的大宽表（免写关联、查询快）。0919 版没有；**2024-02 档案件里也没有**（§13 之 370 条官方索引 no-table 清单可证）——官方把它单独打包在 HF 快车道仓根 `latest_ZZZ_tables.7z`（215MB），这是四样里唯一本地没有、要装须另下载的。**指南实证补记（2026-09-25，《User's Guide》§6 "Denormalized Tables"＋查询章，全文在案）**：ZZZ＝官方对基础表的**反规范化（denormalized）**派生表——基础关系表只存 ID 码，ZZZ 预 join 多表把码填成名字（人名/地名/官名/类型描述），官方原话用途＝"simplify the process of writing queries"（Access Query Designer 写多表 join 费劲之补丁）；指南自证派生例：`ZZZ_BIOG_ADDR_DATA`＝`BIOG_MAIN＋ADDR_CODES＋BIOG_ADDR_CODES` 拼成。**零新数据**——78 表全在我库，任何 ZZZ 表一条 `CREATE VIEW` 可重建；PG 中 join 毫秒级（§13 性能探针实证），其存在理由整体蒸发。**"蓝图"亦无须下载**：官方 11 表配方清单已全量提取在此，将来建视图照此即可——ZZZ_ALT_NAME_DATA（填异名类型）／ZZZ_BIOG_ADDR_DATA（填地址＋地址类型）／ZZZ_BIOG_MAIN（填年号＋族裔）／ZZZ_BIOG_NAME_OFFICE（姓氏↔差遣官名，供检索）／ZZZ_BIOG_TEXT_DATA（填人名＋角色＋文本数据）／ZZZ_ENTRY_DATA（填人名＋入仕类别）／ZZZ_KIN_BIOG_ADDR（亲属关系＋索引地）／ZZZ_NONKIN_BIOG_ADDR（社会关系＋索引地）／ZZZ_POSTED_TO_ADDR_DATA（填人名＋官名＋地址）／ZZZ_POSTED_TO_OFFICE_DATA（填人名＋官职信息）／ZZZ_STATUS_DATA（填人名＋身分描述）。
4. **CHGIS 其余层 —— V5/V6 家族没装完的部分**（**2026-09-25 实勘修正**：本条原文记"县面（cnty_pgn）、1911/1820 层都在本地 chgis-v6 树里"——实勘推翻：**chgis-v6 树实际只有首批已装三件＋数据字典＋纪年表**（China_Periods_ReignDates.zip）；**V6 官方从未发布时序县面**；县面与 1911/1820 层实在 harvard-full `doi_10_7910/DVN/M7WEFY`＝**CHGIS V5 树**（含 EULA/README/shapefile 文档），清单实测：
   - **v5_1911 族**：**cnty_pgn（县面——本地全库存唯一历史县面，清末快照）**、cnty_pts、pref_pgn/pts、prov_pgn/pts、**twn_pts（乡镇点）**；
   - **v5_1820 族**：cnty_pts、pref_pgn/pts、prov_pgn/pts、twn_pts、coast_lin（海岸线）、coded_rvr_lin（河流）、lks_pgn（湖泊）——清帝国标准底图要素齐全；
   - 其余：v4_time_prov_pgn/pts（**省级时序面**）、v5_1926_prov_pgn、v5_1997_prov_pgn、**v5_1990_citas_cnty_pgn/pref_pgn（1990 CITAS 县/府面）**、**v5_dem（地形高程）**、v5_gns_*（各省现代地名集，仅 GBK）、v5_ChinaW_pts、Manshu_200K_index、v5_2009_tibet_twns；
   - 主要层皆有 GBK/UTF 双变体（UTF 可用，编码裁定同首批差异项⑤；coast_lin/gns 等少数仅 GBK）。

**四条皆不装的功能损失（2026-09-25 答用户问"如果我不装你说的四项，会缺少什么功能"，实勘后入账）**：
- **已具备不受影响**：CBDB 全部人物/亲属/社会关系/仕宦/入仕/身分/文本/机构关系查询（562 万行＋321 索引，速度已证）；**府级**历史 GIS（时序府面落点判府、府界变迁）；县点（县治位置）；桥坐标 7,125 地址落图；三小件全部功能。
- **损失①（最重）县级边界面**：只能判"点落哪府"、**不能判"落哪县"**——县级密度图、书院/人物籍贯的县级归属、府内精细定位皆不可做；县面仅有 1911 快照（v5_1911_cnty_pgn）与 1990 CITAS 两个断面可补，无时序县面（V6 官方就没出）。
- **损失②标准年代底图**：1820/1911 快照层缺位——V6 时序面虽可按 beg_yr/end_yr 属性过滤出任意年断面，但**无乡镇点（twn_pts）、无河流/湖泊/海岸线底图要素**；做"清帝国 1820 标准图"式底图须装 V5 族。
- **损失③坐标覆盖面**：桥余 3,871 地址＋无 chgis_pt_id 的 19,161 地址（30,157−10,996）暂无坐标；ADDR_XY（②）是官方另一坐标源（须剔污染），装 V5 县点/镇点层亦可救回 3,871 中一部分。
- **损失④（清单外新见，随实勘记）**：无 DEM＝无地形分析；无 GNS＝无现代地名对照；无省级时序面＝省级聚合分析须由府面自并。
- **≈零损失两项**：ZZZ（③）——PG 建视图即替代；Hartwell 29302（①）——v1_2002/v5_2010 年代包与 M7WEFY V5 族功能大幅重叠，仅旧文献复现/版本存档需要。
- **决策参考**：四项中真正补功能缺口的是 ④CHGIS V5 族（县面/底图/镇点）与 ②ADDR_XY（坐标补面）；①③可长期不装。货全在 32 镜像盘，随时可装、不装不腐。

**装上增益与开发支撑（2026-09-25 答用户问"装了我们会多出什么功能来，为以后开发项目能提供什么帮助与信息"，摘要入账；与上块"不装损失"互为表里，不复述）**：
- **④V5 族（价值最大）**：1911 县面＋1990 CITAS→**点能判县**、县/府/今三期对比、县级填色与密度图、人物籍贯县级归属；1820/1911 底图族（省/府/县点＋**乡镇点**＋河流/湖泊/海岸线）→**省—府—县—镇四级聚落体系**＋历史地图平台标准底图＋**漕运/经济史专题**（水系＋镇点＝网络节点—通道）；v4_time_prov→省级长时段聚合；v5_dem→地形因子（迁徙约束/选址/配准）；GNS→古今地名对照（检索消歧底表）。
- **②ADDR_XY**：可落图地址自桥通 7,125 扩至约 2 万+（污染剔除法 cbdb.md §9 在账）——人物分布/迁徙轨迹/带地理锚点之关系网络图覆盖率翻倍级。
- **①Hartwell 29302**：除版本存档外独门用处＝5,333 件**逐年切片**系政区演变**逐年动画/时间轴播放器**之现成素材（V6 时序层须自按属性过滤）。
- **③ZZZ**：已升级为"**不装**"处置（见上第 3 条）——蓝图（11 表配方清单）已从官方指南提取入账，**连结构都不必读**，将来建视图照账面清单写 SQL 即可。
- **全栈图景（未来项目底座）**：现有 CBDB 562 万行＋府级空间栈，补县/镇/水文/地形/坐标面后即凑齐——(1)人物空间化（点→面→网）；(2)历史地图平台（四期底图＋四级下钻）；(3)量化历史（县级/省级×地形因子）；(4)知识图谱/家谱（人—地—机构＋GNS 桥）；(5)专题史（漕运/经济/城市）。
- **成本**：货全在 32 镜像盘；装法＝首批已验证管线（ogr2ogr/COPY），每层分钟级；V5 主要层 UTF 变体齐，仅 coast_lin/gns 少数仅 GBK（`SHAPE_ENCODING` 转码法首批已实证）。**建议组合**：④＋②（高价值）；①看是否做时间轴展示；③**已定不装**（蓝图已入账）。**仍候另令。**

**"可补桥余 3,871"释义（附）**：桥验证的实测账：`addr_codes` 里 10,996 个非空 `chgis_pt_id`，对已装两层命中 7,125（府点 997＋县点 6,128），**剩下 3,871 个指向的 ID 不在已装层里**——它们多半指向④里没装的层（县面/1911/1820 点集）或①的年代包。**把其余层装上，这 3,871 个就能继续对上号——这就叫"补桥"。**

原简述余项不在四条内者：**扩展补数据**（PostGIS 扩展侧，候需求）；原简述之"1911/1820 层；V6 西安80/GBK 变体"已并入④。**编码/坐标裁定＝UTF-8＋WGS84**（与 CBDB 坐标同系好 join；差异项⑤）。

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
- **CBDB《User's Guide》全文已抓到**（M. Fuller 修订版，**153 页**；harvard 直连 403 系服务器端反爬→改经 wayback 存档取 PDF、`pdftotext` 转文。**版本注记（2026-09-25 补正）**：初录误标"rev. 2021-10"——扉页修订日期因字体编码在文本层丢失，PDF 元数据实测生成日 **2023-10-06**（Acrobat PDFMaker 17），据此补正为"2023-10 生成之修订版"；本件 8,531,184 B、sha256 `cab7d155…`，暂存开发机 /tmp（易失，正式归宿候用户令）。**NAS 另有官方 2018 版**：`harvard-full/doi_10_7910/DVN/P8U8RC/CBDB_Users_Guide_2018.pdf`（5,478,089 B、sha256 `bd1c7461…`，与 CBDB_aw_20180831 Access 包同树）。**改钉补正（2026-09-26，用户问"最新版是哪一年的"→实勘＋用户令"以实事为依据"）**：指南最新版实为**官方 2025-05 Access 包内自带**——`harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_bi_20250520_Build20250604.7z`（320,251,527 B、sha256 `dd053635…`）内 `HelpFiles/CBDB Users Guide.pdf`＝**160 页**、9,268,565 B、sha256 `3b703c8e…`、pdfinfo CreationDate **2025-05-19**（扉页修订日期与 2023 版同病文字层丢失——"Revised Version . May , "——元数据与包名 bi_20250520 互证）；同包中文版 `CBDB Users Guide CH.pdf`＝142 页、2017-01-26 生成——**中文版止于 2017，此后只更英文**。包内 HelpFiles 九件尺寸与开发机解包树 `/tmp/cbdbdoc`（2026-09-23 解，**已删——2026-09-26 用户令"tmp下的文档不保留"**）逐件核对全同。**改钉零页码债实证**：账内指南引用 grep 穷举＝**页码/行号级 0 条**（原"钉 2023 版"系伞式声明、从未有实际引用挂靠），全部引用为章节级＋全文级；2025 版复核**五点全健在**：§6 "Denormalized Tables" 在、原话 "simplify the process of writing queries" 一字同、§2③ 十一表配方逐名验证（各表 1–9 次提及）、派生例原句 "(BIOG_MAIN, ADDR_CODES, BIOG_ADDR_CODES)" 一字同、PostgreSQL/PostGIS/MySQL 命中 0＋CHGIS_PT_ID 命中 0（**两条负证在最新版上反而加强**）。据此**本文档一切指南引用（章节级＋全文级）改钉 2025-05 版（NAS 官方包内自带）**；2023 wayback 版降为过程记录（§2③ 配方当初提取源；其 /tmp 暂存件**查实已不在**〔2026-09-26 实勘〕，**归宿事结案**——2026-09-26 用户令"tmp下的文档不保留"，引用既已改钉 NAS 官方包内 2025-05 版，wayback 件无归宿需求））：官方支持面＝序言原话 **Access（主制式）＋SQLite（"for quantitative researchers and Mac users"）**；另有历史附录《CBDB SQL Server Version》（CBDB_SS，SQL Server Express 平台，系绕 Access 文件大小限制之产物）；**全文检索 PostgreSQL/PostGIS/MySQL 命中＝0**——"官方无入 PG 指引"系全文实证，非推断。
- **含义**：CBDB→PG 无官方成例可循，本管线属自建——§7 对账验收七项即安全网（官方无指引处，以可复核对账代之）。

### 12.3 社区同类经验

- **sqlite→PG 大路工具＝pgloader**（Neon/Netbird/Render 三家迁移指南一致推荐）；其 Debian bookworm 有官方包。**本案不用**，理由：装它＝32 宿主系统改动（超实例边界须另令）；本管线 python3 标准库零新装、且类型映射/BLOB 十六进制/NULL 语义全可控。**备选地位记录在案**（若 78 表管道遇阻可裁启用）。
- 社区踩坑清单（open-webui 迁移讨论等）：类型亲和性（sqlite 动态类型→PG 静态）、BLOB、标识符大小写、布尔表示——**本方案 §4.2 映射表逐条已覆盖**（INTEGER→bigint／BLOB→bytea hex／不引号全小写／无布尔列）。
- **CBDB 专向入库项目：检索未见现成开源管线**（学术侧有 CBDB 关系库论文与 R/Python 访问包，皆非 PG 迁移）——与 12.2 互证。
- CHGIS→PostGIS **官方手册对照（PostGIS 3.6 Manual 第 4 章 §4.7 "Loading Spatial Data"，全文已抓）**：官方内建装载法两条——①SQL 语句（WKT/WKB 经 `psql -f`）②**shp2pgsql 装载器**（关键旗标：`-D` dump 格式＝COPY 快速模式，官方原话 "Use this for very large data sets"；`-I` 建 GiST；`-W` DBF→UTF8 编码转换；`-s` 指定 SRID；`-e` 逐句事务）。本方案之 **ogr2ogr＝GDAL 项目官方工具**（与 shp2pgsql 同属 PostGIS 生态、内部同走 COPY），功能覆盖上述要点：`.prj` 自动带 SRID 4326（≈`-s`）、GiST 自建（≈`-I`）、UTF-8 变体＋`SHAPE_ENCODING`（≈`-W` 且从根上免转换）、`/vsizip/` 直读 zip（shp2pgsql 所无）。**差异记录**：若须严格按手册原生工具，可加装 PGDG `postgis` 装载器包（F-13 ③(a) 候选，与 gdal-bin 同批可加）——默认不变（ogr2ogr 已本机实证三驱动在列）。编码历史坑（PostGIS 邮件列表 2011 年 shp2pgsql 客户端编码旧案）→本案 UTF-8 变体从根绕开 GBK。

### 12.4 调研出处（引用为外部资料，内容以原文为准）

- PostgreSQL 18 官方文档 §14.4 Populating a Database：postgresql.org/docs/current/populate.html（经 web.archive 存档实抓全文）
- PostGIS 3.6 官方手册第 4 章 §4.7（Loading Spatial Data）：postgis.net/docs/manual-3.6/using_postgis_dbmanagement.html（curl 实抓全文切片）
- CBDB《User's Guide》（Fuller 修订版，153 页，PDF 生成 2023-10-06——初录"rev. 2021-10"系误标已补正，见 §12.2 版本注记）：harvard 直连 403（服务器端反爬）→经 web.archive.org/web/20240914131845 取 PDF 全文、本机 `pdftotext` 转文检索（临时文件仅在 /tmp，不入工作区；归宿已结案——2026-09-26 用户令"tmp下的文档不保留"，件已删/查实不在，引用改钉 NAS 官方包内 2025-05 版）；**最新版＝NAS 官方 2025-05 包内自带 160 页版（sha256 `3b703c8e…`，§12.2 改钉补正——账内指南引用已改钉该版）**
- CBDB 官方 HF 数据卡：huggingface.co/datasets/cbdb/cbdb-sqlite（实抓）
- 社区迁移指南：render.com《How to migrate from SQLite to PostgreSQL》、docs.netbird.io（pgloader 路）、github.com/open-webui/open-webui Discussion #21609（踩坑清单）
- 编码旧案：lists.osgeo.org pipermail postgis-devel #1303
- CBDB 学术描述：OpenHumanitiesData《CBDB: A Relational Database for Prosopographical Research of Pre-Modern China》（2022）

## §13 执行记录（2026-09-24 23:44 开工令"同意，另外你要考虑到32主机的压力"→23:48–00:24 施工，历时约 36 分钟＝预算 2.5h 之 24%；全程 ssh heredoc、顺序单流零并行、宿主侧进程 nice/ionice 全程）

**Step 0 复核＋基线（23:48）**：pg32b healthy、cbdb 库无（＝全新建）；`/` 余 195G、镜像盘余 829G、data 56M；货七件点名 OK＋`sha256sum -c` **13/13 成功 0 失败**；压力基线＝loadavg **0.11**／avail 5.5G／PSI-cpu some 0.57／PSI-io some 4.04／pg32 healthy＋canary `select 1` **0.092s**；**compose ＋`cpu_shares: 512`**（`config -q` 过→`up -d` 秒级重建→healthy、shares=512 实测；生产容器默认 1024＝争抢时 2:1 让路；pg32 实测 CpuShares=0 即默认 1024）。

**Step 1 建库**：`CREATE DATABASE cbdb ENCODING 'UTF8' TEMPLATE template0`＋`CREATE EXTENSION postgis`（**3.6.4**）＋`CREATE SCHEMA chgis`；实测 `cbdb UTF8 en_US.utf8`；实例 datname 四项（postgres/template0/template1/cbdb——无野库）。

**Step 2 腿 A（78 表）**：
- DDL＝sqlite_master＋pragma table_info 生成（§4.2 映射落地：INTEGER→bigint／TEXT→text／VARCHAR(n)→varchar(n)／REAL→double precision／NUMERIC→numeric／BLOB→bytea；无任何约束），78 表 **736 列**，特殊须引号标识符＝**0**（保留字表零命中）；sqlite 以 `mode=ro&immutable=1` URI 只读直开 NAS cifs 件（网络文件系统锁规避）。
- **事件①（自制，当批即决）**：首版 `ident()` 正则只放行小写→全大写表名被加引号保大小写，`\copy`（折叠小写）报表不存在，ON_ERROR_STOP 即停——**零数据入库**（\copy 原子），78 表全 DROP 重建（普通名直通不引号，任 PG 折叠小写）；复证：表名小写实测、biog_main 55 列全小写、空流 canary `COPY 0` 正常。
- COPY 循环：python3 标准库管道（TSV；NULL→`\N`、BLOB→`\\x`hex、`\t\n\r\\` 转义、NUL 保险丝、float 用 repr 保往返）→`docker exec -i psql -Atc "\copy … FROM STDIN"` 逐表；**78/78 表成功、146 秒**。
- **三方对账：sqlite count＝＝COPY count＝＝PG count，78/78 表零差异，三方总数全同＝5,623,075**（＝cbdb.md §9 官方总行数逐位全同）。大表实录：BIOG_SOURCE_DATA 1,254,135／BIOG_MAIN 661,969（＝家中账参证）／POSTED_TO_OFFICE_DATA 591,518／POSTING_DATA 591,487／KIN_DATA 562,711／POSTED_TO_ADDR_DATA 465,284／BIOG_ADDR_DATA 461,637／ENTRY_DATA 264,975／ALTNAME_DATA 208,828／ASSOC_DATA 190,048／ADDR_CODES 30,157（＝参证）；空表 3（admin_cat_code_type_rel／admin_cat_types／social_institution_altname_data——**源库本空非装失**）。全表行数清单＝审计件 copy-counts.tsv（已随 §13 归档后清理，再生法＝本节管线）。
- 索引：源＝**官方 2024-02 档案件**（镜像盘 `harvard-full/doi_10_7910/DVN/PAGGQS/CBDB_20240208_sqlite.db` **只读取 schema**——0919 活库直出件天生无显式索引即账载"370→0"缺项，§4"实测条数为准"条款触发；非数据装载，原树备份语义未破）；解析：方括号标识符＋CRLF 归一、COLLATE NOCASE 剥除、名 63 字节截断＋去重。
  - **账目吻合**：官方 **370**＝**可套用 308**＋no-table **46**（ADDRESSES 6／SOCIAL_INSTITUTION_CODES_CONVERSION 4／OFFICE_TYPE_TREE_backup 4／DATABASE_LINK_DATA 4／TMP_INDEX_YEAR 3／TablesFields 3／ADDR_XY 3／FormLabels 2／ForeignKeys 2／DATABASE_LINK_CODES 2／CBDB_NAME_LIST 2／APPOINTMENT_TYPE_CODES 2／ADDR_PLACE_DATA 2／PLACE_CODES 1／OFFICE_CODES_CONVERSION 1／CopyTables 系 5）＋col-drift **16**（ASSOC_CODE_TYPE_REL_PrimaryKey・ASSOC_CODE_TYPE_REL_type_id・ASSOC_TYPES_PrimaryKey・ASSOC_TYPES_type_id＝c_assoc_type_id×4；ENTRY_DATA_c_nianhao_id；EVENTS_ADDR_PrimaryKey・EVENTS_ADDR_c_event_record_id・EVENTS_DATA_c_event_record_id＝c_event_record_id×3；EXTANT_CODES_c_extant_hd_code；OFFICE_TYPE_TREE_c_office_tts_id；POSTED_TO_OFFICE_DATA×2＝c_appt_type_code；TEXT_CODES×4＝c_pub_country/c_pub_dy/c_pub_nh_code/c_pub_range_code——**与 cbdb.md 在账漂移例逐字互证**）＋complex **0**。**308 vs 账载 307 差 1**（apply/no-table 口径边界；本批 308 条经表在＋列在机械校验后方采用，更稳）。跳过 62 条＝**人工复核清单全列如上，无静默丢**（验收②）。
  - **事件②**：官方索引名带空格（`[ALTNAME_DATA_Primary Key]`，Access 血统）→首跑 PG 语法错即停（已写 6 条）；修＝名消毒（非法字符→下划线，3 条）＋全量 `IF NOT EXISTS` 幂等重放（6 条 NOTICE skip 实测，无重复建）。
  - FK 补建 **6** 条（`c_*id` 未被官方索引首列覆盖之机械推定）：assoc_data.c_tertiary_personid／assoc_data.c_assoc_claimer_id／biog_main.c_index_year_source_id／entry_data.c_entry_nh_id／**merged_person_data.c_personid／merged_person_data.c_merged_from_personid**（后二＝0919 新表官方索引全缺，推定正好补上）。
  - 执行：单会话 `SET maintenance_work_mem='256MB'`（压力令降档）＋314 条顺序，**36 秒**；`max_wal_size` **1GB→4GB（SHOW 前后实测）→RESET 复原 1GB 实测**；`ANALYZE` 7 秒；**pg_indexes：public＝315**（308＋6＋postgis 自带 `spatial_ref_sys_srid_idx` 1）**＋chgis＝6**（GiST 3＋ogc_fid PK 3）。
- 腿 A 毕库 1,459MB；闸门复测 loadavg 1.56（全程峰值 1.87＜阈 4.0）、pg32 canary 0.089s（基线 0.092 零劣化）。

**Step 3 腿 B（CHGIS 三层）**：docker cp 三 zip→容器 /tmp→`ogrinfo -so -al /vsizip/` 探明＝**pref_pgn 3,830 Polygon／pref_pts 5,226 Point／cnty_pts 10,522 Point**、三层皆 EPSG:4326；ogr2ogr 顺序×3（`-nln chgis.v6_* -lco GEOMETRY_NAME=geom -lco PRECISION=NO --config SHAPE_ENCODING UTF-8`、容器内 nice）。
- **事件③**：pref_pgn 首跑败——层申报 Polygon 而含 MultiPolygon 要素（时间切片多部件面），PG typmod 拒、COPY 原子回滚（**建表都未留下**）；修＝**`-nlt MULTIPOLYGON`**（忠实升型无损）重跑 2 秒成。
- 对账：**三层行数＝＝ogrinfo 要素数（5,226／10,522／3,830），县点＝家中账标答 10,522 逐位全同**；geometry_columns 实测三层 srid=4326（POINT/POINT/MULTIPOLYGON）；GiST 三键在；**中文零乱码**（"定羌军／保德军／保德州""辽州/州""沁州/州"实录）；容器 /tmp 三 zip `rm`（零残留实测）。

**Step 4 腿 C（三小件）**：python csv（utf-8-sig／tab／双引号）→全 text DDL（**中文列名 53 个带引号原样入库**）→`\copy` 管道；**quan_yuan_wen_index 5 列 40,199 行／academies_2957 54 列 2,957 行（行数＝表名自证）／missionary_writings 11 列 1,033 行——三表 src＝＝COPY＝＝PG 零差异**；样本"城南書院｜宋紹興三十一年（1161）｜長沙"零乱码；空字段＝空串保真（不判 NULL，§6 口径落地注记）。**事件④**：首版脚本 stdin 关闭后调 communicate() 踩闭合文件——修写法＋三表 DROP→CREATE 幂等重跑（首跑仅建 1 空壳表，零数据残留）。

**Step 5 验收七项（全过）**：
- ① 腿 A 78/78 三方零差异＋总数 5,623,075 ✓
- ② 索引三数吻合：370＝308＋46＋16＋0；PG 侧 315＋6 实测；人工复核清单 62 条全列 ✓
- ③ 腿 B 三层对账＋标答 10,522＋GiST 三键＋中文无恙 ✓
- ④ 腿 C 三表对账 ✓
- ⑤ **桥验证两发**：(a) `addr_codes.chgis_pt_id`（非空非零 **10,996**/30,157）↔`v6_pref_pts.sys_id`＝**997**、↔`v6_cnty_pts.sys_id`＝**6,128**、**两层并 7,125（64.8%）**——主靶县点；余 3,871 指向未装层/时间片 ID（第二批可观察；两侧 bigint 同型直 join，官方索引 `addr_codes_chgis_pt_id` 现成）。**事件⑤**：首试误加 `::text` cast 报 text=bigint——复跑修正。(b) `ST_Within` 三点实弹（**腿 C text→float→腿 B geometry 跨腿桥**）："歷山書院｜濮州 (115.50,35.67)→**濮州**"语义直中、"濂溪書院｜合州→重庆府,重庆路"、"靈谷書院｜貴溪→信州,饶州,广信府等"；**x=经度/y=纬度实证**（hit_xy>0、hit_yx=0）；多命中＝时间切片面叠加（CHGIS 时序模型正常）；补发 addr_codes.x_coord/y_coord 三点："滿城→保定府""土默特右旗→承德州,朝阳府等""遼陽市→奉天府"（辽阳例与账载坐标污染提示相符——地理结论仍须按 cbdb.md 剔污染点，**引擎无恙**）。
- ⑥ 对账总表＝本节 ✓
- ⑦ 零触碰复核：pg32b datname 四项无野库；**pg32 healthy 全程＋canary 0.092→0.089s 零劣化**（闸门五测）；**36 不可达（ssh Connection timed out 实测）＝零触碰天然成立**；postgres 库未动 ✓。

**性能探针（加测）**：cbdb.md 在账之 sqlite 时代"60 秒未出"同款相关 exists（addr_codes×biog_addr_data＝30,157×461,637）→**本库 0.124 秒出 8,434**（约 500 倍，索引效力实证）。

**压力防护实录（§8 六条全兑现）**：峰值 loadavg **1.87**／阈 4.0 未触；收工 0.03；pg32 canary 零劣化；cpu_shares 512 生效；nice/ionice 全程；顺序单流；夜间窗口 23:48–00:24。**宿主生产零感知。**

**观察⑤（非本批故障，如实记）**：`pg_reload_conf()` 触发 LOG "configuration file … contains errors; unaffected changes were applied"（×2）——reload 实弹定位：镜像 conf 文件里 max_connections/shared_buffers 等 restart-needed 参数为初始默认值、运行值系 entrypoint 命令行所给，**任何 reload 皆触发此 LOG＝镜像 entrypoint 固有怪癖，无害**（本批 max_wal_size 1→4→1GB 每步 SHOW 实测生效）；pg32 同血统潜伏（从未 reload，log 0 命中）；pg36 同构，候恢复后核。

**事件账总（六起，全自制全决全披露；库 log 10 条 ERROR/LOG 全数归因，零数据完整性问题）**：①ident 保大小写→重建 DDL；②索引名带空格→消毒＋IF NOT EXISTS；③Polygon/MultiPolygon→`-nlt`；④python I/O 写法→修＋幂等重跑；⑤查询级猜错两处（name_chn 列名、::text cast）→重跑；⑥＝观察⑤（LOG 级）。

**收尾与现状**：容器 /tmp 清空；宿主 `/tmp/pg32b-load`（DDL/对账/报告小件审计物，无数据本体）入账后已 rm（再生法＝本节管线）；**cbdb 库 1,543MB、84 用户表（public 81＋chgis 3；另工具自带辅表 2——`public.spatial_ref_sys`＝PostGIS 自带、`ogr_system_tables.metadata`＝GDAL/ogr2ogr 自带，pg_tables 非目录总计 86 实测归位）、索引 321、总行数 5,623,075＋19,578＋44,189＝5,686,842**。第二批挂账不变：Hartwell 29302（5,333 文件）、ADDR_XY/ZZZ、CHGIS 其余层（可补桥余 3,871）——**四条明细唯一展开＝§2 缓办段**。

---

**状态：首批、第二批均已执行完毕——首批（2026-09-25 00:24 验收七项全过，记录＝§13）；第二批 v2 全量装载（2026-09-25 22:59 开工令"同意"→2026-09-26 02:50 验收八项全过，含编码大事件六轮修复，记录＝§15）。挂账余项仅 §2 之①版本堆（存档不装）③ZZZ（定案不装）两条既定裁决。**

---


## §14 第二批成案 v2 · 全量装载案（2026-09-25 用户"能装尽装"令修订；**v1〔f452374/d91997b〕作废**——v1 按"用处大小"挑选〔Hartwell 拆研读缓装／DEM 条件跳／v5_time 跳装／范围限四挂账项〕，经用户纠正为下述三铁律）

### 14.0 立案依据（用户令照录，不改写）

> *"我的意思是人家给我们的，肯定是有目的。我们自己不要在这里胡想八想的。除了象ZZZ这样重复的东西，我们肯定不装，如果不是。能装的肯定要装上啊。只有装上了我们才知道用这些东西干什么啊？所以要搞清楚我们有什么？"*

**三铁律**：①**能装尽装**——不预判用处，装上才知道干什么用；②**唯实证重复不装**——凡跳装必附 sha/内容级证据入账（ZZZ 型＝派生可重建、编码变体、格式重打包、时序旧快照四类）；③**先搞清楚有什么**——65 树全量点验＝14.1 总账，货单封盘。

### 14.1 我们有什么 · harvard-full 65 树全量点验总账（2026-09-25 只读实测：逐树件数/字节/扩展名分布＋datasets.tsv 标题；处置＝本案裁定）

| 类别 | 树（DOI 尾号·标题·规模） | 处置 |
|---|---|---|
| **已装（首批⑦件）** | I0Q7SM/WW1PD6/Q9VOF5＝V6 时序府面/府点/县点；HTGBQ3/J6XRIV/CE4ZNG＝三小件 | 在库 |
| **CHGIS 官方家族** | M7WEFY＝V5 树 101zip/431MB；HHVVHX＝**v6_1911 七层 UTF**；ST5KKM＝**v6_1820 八层 UTF**；T27RQO＝v6_citas90 三层（仅 GBK）；0P89R9/2K4FHX＝V6 1911/1820 之 GBK 编码变体；SB8ZTM＝**V6 明代驿路站网 2 层**；SC7AOU＝纪年表；E1FHML＝**DEM 官方三包**（ARCGIS/QGIS-2/QGIS-3_REVISED 各 63MB）；ZZKZ6U/HIMIVE/PDGOZ0＝**V2/V3/V4 历代矢量**（239/343/608MB）；JX4KSQ＝V3 关系库 MDB 66MB；WEJMB6＝V5 KMZ 24 件（展示打包）；SNCEAU/6CHSR7/FDLFJ3＝字典/README/EULA（文档） | **装**（KMZ 与文档除外：KMZ 核层名重复即不装；文档存档） |
| **哈佛专题矢量/表格** | 29302＝Hartwell（v5_2010 **352 shp 层**＋v1_2002 353 层＋408 MapInfo）；VJHPVK＝茶马古道 3 层；2CVTR0＝德川日本 4 层；H3OB28＝TGAZ（单件 zip 待探）；W6PFXR＝藏传寺院；WP1ASG＝藏族乡镇；PRCLTU＝藏区地名对照 xls；3KAHBT＝谭其骧图集索引；PJ8D45＝ArcChina 图幅索引；I4UIKV＝GNS 特征码表；5RUXK8＝明卫所；VAYEUZ＝BGIS 2006；25413＝DCW 世界底图；J5U79Z＝天然气管道 2013；JIISNB＝高铁 2016；KUFJTG＝北京古迹；H4WVUP＝北京 1875；Z24KTH＝中瑞考察；23340＝新中国全图；MI56KU＝工作坊资料；EOH3FV＝**1999 县级人口表**；SK7KGK＝**国标 GBT-2260-91 码表**（tab×2） | **装**（各包 Step 0 探内后按固定规则落表） |
| **历史地图系列（探后裁）** | ABPR9F/E7HDYD/ELTD3L/G9RKCW/LVYYZC/RXP4AA＝普尔热瓦尔斯基/柯兹洛夫/波德布尼等六套（9–367MB）；AZYI17＝俄藏目录；JJMYV7＝报告；23336＝**黑龙江省图集 2.18GB** | zip 内**带地理配准**（prj/jgw/tfw/GeoTIFF）→ postgis_raster 装；**纯扫描** → 存档不入（差异项③） |
| **软件/模型（非数据）** | BWIBNL＝LoGaRT-BERT 1.9GB；16PSZE＝韩文罗马化 pth 105MB；IWOK2X/MZANN5＝pdf/gif 文档 | 不装（无可装性，非挑拣） |
| **CBDB 版本堆（差异项①）** | PAGGQS＝2024-02 sqlite（**ADDR_XY 之源，抽表装**）＋Access 7z×9；F6BBOF/2UFYFG/GNPNON/P8U8RC/SHMDGU＝2017–2019+ 历代 Access 快照 | **存档不装库**——同一库之时序旧快照（皆旧于已装 0919），装＝五套过期 500 万行；MDB 解包须另装工具。**要装另案候令** |

### 14.2 货单与目标表（腿 D–L；schema 三分＝差异项④：`chgis`＝CHGIS 家族〔含 Hartwell/明驿路〕、`harv`＝其余专题、`public`＝CBDB 族＋通用码表）

- **腿 D1·V6 现行代 18 层**→`chgis.v6_*`：1820 族 8（cnty_pts/coded_rvr_lin/lks_pgn/pref_pgn/pref_pts/prov_pgn/prov_pts/twn_pts，ST5KKM）＋1911 族 7（cnty_pgn/cnty_pts/pref_pgn/pref_pts/prov_pgn/prov_pts/twn_pts，HHVVHX）＋citas90 3（cnty_pgn/pref_pgn/prov_pgn，T27RQO **GBK 转码**）。
- **腿 D2·V5 代 24 层**→`chgis.v5_*`/`v4_*`：M7WEFY utf 件——1820 族 9（含 coast_lin 单变体，DBF 编码先探）＋1911 族 7＋v4_time_prov 2＋1926/1997 prov 2＋v5_1990_citas 2＋ChinaW_pts＋tibet_twns＋PhysiogMacroregions（utf 版；0.2MB 非 utf 版内容对验后定）＋SMR＋Manshu 索引。
- **腿 D3·v5_time 三层**：主版（utf/gbk 各一之 utf）装；**`-1/-2` 与 gbk 变体内容级对验**（要素数＋字段表＋抽行）——同→跳装留证；异→装为 `…_r1/_r2` 变体表并入账（差异项⑧）。
- **腿 D4·gns 30 省（GBK）**→ 并单表 `chgis.v5_gns`（`-sql` 加 prov 列逐省 append）。
- **腿 E·ADDR_XY**→`public.addr_xy`（19,249 行×6 列已实测；腿 A 管道；`0` 哨兵照装原样＋统计入账，联动 cbdb.md §9.2/9.5）。
- **腿 F·纪年表**→`chgis.china_chron`（SC7AOU `china_chron.ZIP`；与 chgis-v6 树 `China_Periods_ReignDates.zip` sha/内容对验，装一次；sql 方言不合则走 CSV/txt 腿 C 管道）。
- **腿 G·DEM**→`CREATE EXTENSION postgis_raster`（**实测 available 3.6.4 未装，一条 SQL 即通，无需动镜像**）；四包对验（E1FHML×3＋M7WEFY v5_dem 80.7MB）取最新修订（候选 QGIS-3_REVISED）→`raster2pgsql -C` →`chgis.dem`；hillshade/ovr＝ST_HillShade 可派生（ZZZ 型）不装留证。
- **腿 H·Hartwell**：v5_2010 **352 层→8 张归并表** `chgis.hartwell_{cnty(78),pref(77),jin(58),circ(51),indp(37),liao(19),prov(17),chin(15)}`——每表＋`yr`（741–1900 六年份）＋`src_file` 列，`ogr2ogr -append` 归并（列差自动 ADD COLUMN）；对账＝每层型源要素和==并表 count。**v1_2002（353 层＋408 MapInfo）**：抽 10 层与 v5 对验要素数/属性＋研读 `Hartwell_Reprojection_Info_28sep10.pdf`——**纯重投影派生（ZZZ 型）→不装留证；有实差→装为 `chgis.hartwell_v1_*` 八表**；MapInfo TAB＝shp 同层换格式，抽验后不装留证。
- **腿 I·专题矢量批**→`harv.*`（SB8ZTM 明驿路 2 层标题系 V6→归 `chgis.ming_routes_2016/ming_stations_2016`）：茶马 3（major/minor/nodes）、德川 4（doo/dmyo_pts/dmyo_pgn/kuni）、TGAZ（探内定法）、藏区 3（monasteries/townships/placenames_xwalk）、谭图索引、ArcChina 索引、GNS 码表、明卫所、BGIS、DCW、气管道、高铁、北京古迹、北京 1875、中瑞考察、新中国全图、工作坊 tab——**规则固定：包内每 shp 落一表，表名＝源名小写去日期尾**；非空间表格走腿 C。
- **腿 J·表格批**→`public.*`：`china_pop_1999`（xls→CSV）、`gbt2260_91`（tab×2 各一表）。
- **腿 K·历代矢量 V2/V3/V4**：三 zip 探层清单→全装 `chgis.v2_*/v3_*/v4_*`（D3 同款对验规则）；**JX4KSQ V3 MDB**：探容器 GDAL MDB 驱动——有则腿 A 变体管道装 `chgis.v3db_*`；无则记录（不为它重建镜像，要装驱动另令）。
- **腿 L·栅格地图（探后裁）**：六套俄藏/黑龙江图集/北京 1875 等——带配准→`harv.ras_*`（raster2pgsql）；纯扫描→存档记录（差异项③）。

### 14.3 方法（全部首批已证管线＋两条新命令级工具）

腿 B 原样（docker cp→ogr2ogr `/vsizip/` 直读→GiST 自建→rm）；腿 A 原样（python sqlite 只读→COPY）；腿 C 原样（分隔文本→COPY）；**新增仅**：`raster2pgsql`（gdal-bin 自带，腿 G/L）＋`CREATE EXTENSION postgis_raster`。GBK 件一律 `SHAPE_ENCODING=GBK` 转 UTF-8 入（编码裁定承差异项⑤UTF-8＋WGS84；SRID 逐层探 .prj，非 4326 者 `-t_srs` 重投影并记差异）。全部 `ON_ERROR_STOP=1`、顺序单流、对账不平即停。**Step 0＝探测清单一次跑完**（各包内容物/编码/prj/TGAZ/MDB 驱动/重复对验），产出生成**最终层清单**后按单循环装——探测结果入账 §15，不再有案外新货。

### 14.4 对账与验收（全过方收口）

1. **逐层三方对账总表**（脚本生成：源要素数==ogr2ogr 报数==PG count，全层零差；预计 100–500 层行）；
2. ADDR_XY 三方对账（sqlite 19,249==COPY==PG）＋哨兵/污染统计；
3. Hartwell 每并表 count==该层型 352 分之源要素和；
4. 中文抽验（GBK 转码层全覆盖抽 3 行，乱码＝0）；
5. GiST 清点==矢量表数；DEM 行数/范围/取值抽验；
6. **桥补 3,871 试 join**（探索项：V6 1911/1820 及新装点层全试，V5/V6 id 制式异同如实入账）；
7. 空间复测三例：1911 县面判县（书院样）＋DEM 取值＋明驿路样查；
8. 压力门禁（loadavg＞4.0 或 pg32 不健康即暂停）。

### 14.5 压力防护与排期（承首批六措施）

顺序单流零并行；`nice -n 19`＋`ionice -c3`；`cpu_shares: 512` 在位；步骤间门禁；`max_wal_size` 不动（总行数预计远小于首批 562 万）；**拆两个夜间窗**：批 2a＝Step 0 探测＋腿 D/E/F/G（预算 ≤2h），批 2b＝腿 H/I/J/K/L（预算 ≤2.5h），批间复核 pg32 金丝雀。

### 14.6 工作量估算 v2（答"这个工作量大吗？"）

货≈2.6GB 可装件（除软件/版本堆/文档）；装载动作≈**100–500 层跑**（脚本循环，单层秒–分钟级）；**机器时间 1–3 小时、两个夜间窗**；全程（探测/对验/对账/记账）≈**两晚**。较 v1（1–1.5h）变大系范围按您令扩至全量；**无未知深水区**——Hartwell 已解为 352→8 并表，余皆带 if-then 裁定规则的探测项。

### 14.7 差异项（默认皆按本案，"同意"即照此，可逐条改裁）

① CBDB 版本堆五套＝**存档不装**（时序旧快照；要装另案）；② Hartwell v1_2002＝**对验后定**（纯重投影派生→不装留证）；③ 纯扫描地图＝**存档不入 raster**（带配准则装）；④ schema 三分 chgis/harv/public；⑤ 编码变体只装一份（UTF 优先，仅 GBK 者转码装）；⑥ 格式重打包（KMZ/MapInfo/合并包）核证后不装；⑦ hillshade 派生不装；⑧ `-1/-2` 变体内容对验后定装否；⑨ 数据源直读 32 镜像盘 harvard-full（第二批货不在 usedata 工作集；要扩围拷贝请改裁）；⑩ MDB 驱动缺则 V3 关系库记录缓装（不重建镜像）。

### 14.8 回滚与账目联动

回滚：本批新表逐张 DROP／`DROP SCHEMA harv CASCADE`／`DROP EXTENSION postgis_raster`（首批产物与 cbdb 库本体不动）；最坏 chgis 整 schema 重建后按 §5 重装首批三层（工作集在 NAS）。账目联动（执行批内）：§15 执行记录；pg32b.md §12 补第二批段；features F-13 状态行；codemap usedata/instance/harvard-full 行补注；cbdb.md §9.2（ADDR_XY 落地＋哨兵统计）复核义务兑现；log 收口。

---

## §15 第二批执行记录（2026-09-25 22:59 开工令"同意"〔周五夜窗口〕→2026-09-26 02:50 收工，历时约 3 小时 51 分；全程 ssh heredoc、顺序单流零并行、`nice -n 19 ionice -c3`＋loadavg<4.0 门禁〔30s 轮询〕、pg32 生产零感知）

**开工基线**：pg32 canary `select 1`＝1、loadavg 0.42、宿主 `/` 余 192G；执行工作区＝宿主 `/tmp/pg32b-load2/`（脚本 22 支＋对账总账 `recon_b2a.tsv`＋hash 去重登记 `hashreg.json`；**已入账后 rm**，审计件 36 件/576KB 收 `ops/harvard/load-b2/`，再生法＝本节＋脚本原件）。对账唯一权威＝recon TSV（终态 1,757 行），非 stdout 流水。

**批 2a（腿 D/E/F/G，脚本 b2a/b2a2）**：
- **D1** V6 全量 18 层（1820/1911 省市县镇点面全 set＋coded_rvr＋1926/1997 省面等）；**D2** V5 26 层（1820/1911 全 set、tibet_twns、SMR、chinaw、physiog 等）；**D3** v5_time 时序变体；**D4** gns 30 省并表 130,665。
- **E** ADDR_XY：sqlite→COPY→`public.addr_xy` **19,249**（三方一致；哨兵：零坐标 **7,793**／非零 **11,456**／`c_source_reference` 非空 **6,722**；列＝c_addr_id,x_coord,y_coord,c_source_reference,c_source_id,c_notes——cbdb.md §9.2 剔污染口径落地）。
- **F** 纪年三件：china_chron **677** 行（20 实列名硬编码）／major_china_periods **52**／fields xls **21**。
- **G** DEM：`chgis_dem.tif` 内嵌用户自定义 `Xian_1980_GK_Zone_19` ENGCRS（GDAL 不可解析，原点 15,781,037/6,567,324 米）→ 从 23340 图集 aux.xml 提取**规范 WKT**（False_Easting 19,500,000／Central_Meridian 111／Xian_1980 椭球）→ `gdalwarp -s_srs wkt -t_srs EPSG:4326 -r bilinear` → `raster2pgsql -C -I -M -t 128x128` → `chgis.dem` **3,358 瓦片 srid=4326，Int16 真高程**；**历山书院 (115.50,35.67) 取值＝54.0m** ✓（与首批 ST_Within"濮州"同点互证）。
- **事件①raster2pgsql 缺失**：镜像无此件（`/usr/lib/postgresql/18/bin/` 亦无）——Debian 拆在 `postgis` 独立包（无 apt 候选至 `apt-get update`）→ `apt-get download postgis && dpkg-deb -x` 提取 → `/usr/local/bin/raster2pgsql`（RELEASE 3.6.4、ldd 净）。G 腿初版只查 rc（无 pipefail 管道吞错）→ 加 `rc!=0 or ntiles==0 → exit` 补强。
- **事件②psql 辅助函数引号制式**：shell 单引号误用 SQL 式 `''` 转义 → `extname='postgis_raster'` 校验查询被截断（扩展实已装成而报"安装失败"）→ 改 `'\''`，六支脚本统一。

**批 2b 腿 H（Hartwell 29302，脚本 b2b1）**：容器侧批量普查（fc＋geomtype→`hw_meta.tsv`）→ 按（年代 type×几何类 pts/lin/pgn）分组，**352 层并 9 表**：chin_pgn 14 层 9,402（36 列）／chin_pts 1 层 957／circ_pgn 51 层 315／cnty_pgn 78 层 8,146（38 列）／indp_pgn 37 层 155／jin_pgn 58 层 923／liao_pgn 19 层 437／pref_pgn 77 层 1,145／prov_pgn 17 层 17 ＝ **21,497 要素**；逐层 `-sql "SELECT *, {yr} AS yr, '{stem}' AS src_file"`（年代切片＋源文件谱系入行）、SHAPE_ENCODING=BIG5、`-nlt PROMOTE_TO_MULTI`、`-t_srs EPSG:4326`、首层 `-overwrite` 余 `-append`；逐表对账 src 和==PG count 全过；**BIG5→UTF8 繁体实证：藍關鎮／二曲鎮／堯渡鎮（capital_ch CJK 行 8,065/8,146）**；v1_2002＝SKIP_DERIV（纯重投影派生，§14 差异项②兑现）。
- **事件③**：初版仅按 type 分组 → `v5_1080_chin_difang` 系 MultiPoint 混入面组 → typmod 拒 → DROP 半成品表、改 (type×几何类) 重分组＋PROMOTE_TO_MULTI → 全过。

**批 2b 腿 I（专题 21 项，脚本 b2b2/b2b2j 前半）**：ming_routes **1,043**／ming_stations **1,000**（yznm_ch 云南府/杨林净）；teahorse 5+37+212（4610→4326）；jp_toku 9+206+206+69；ming_garrisons 375；bgis **18,938**（GBK→UTF8：崇明寺/三亚市佛教协会）；dcw_asia_contour **186,130**；china_gas 自动拆表 171+72（长表名＝GDAL 自动分段）；hsr 79+748；beijing_sites 82；kozlov utf8 层 2,351；poddubnyi 555；przh 嵌套 zip 四组 374/59/111/155（1871–1888 俄测图，EPSG:4024→4326）；W6PFXR 寺院四并表 2,926+356+2,436+204；WP1ASG＝SKIP_DUP（933==933 字节哈希实证）；PJ8D45 v3+v4 图幅索引 77+77；SKIP_FMT 留证 14 行。
- **事件④嵌套 zip**：zip 内含子目录前缀成员 → GDAL `/vsizip` 零层可列 → 改宿主解出 shapefile 六件套（.shp/.dbf/.shx/.prj/.cpg/.qpj）＋docker cp 整目录装载；首修误成 `name.shp.shp` 双扩展（selm 留 .shp）→ `[:-4]` 剥除；随附 `.cpg` 同目录即被 GDAL 尊重（enc=None 让位）——przh/russ 诸层 UTF-8 赖此保全；`*images*` zip 自 findzips 排除（LVYYZC 子串误配 ru_images）。

**批 2b 腿 J＋TGAZ（脚本 b2b2j）**：china_pop_1999_county **2,361**／thdl_tibet_adm_areas 166／gb_91_codes 3,389／**谭其骧 tan names1 36,780＋names2 38,500**／ngia 631／nima 641／workshop2001_index 29；TGAZ mysqldump→**33 表**（spelling 245,042／part_of 83,400／placename=present_loc=mv_pn_srch×3 各 82,117／v6_id 82,858／v5_id 77,769／snote 25,655／alt_name3 18,540…约 105 万行；ins==pg 33/33 全过；空表 6 保留如实；视图 5 SKIP_VIEW）。
- **事件⑤谭图 GBK**：tan_gbk 件所有严格解码（含 gb18030）皆失败 → 兜底法＝`gb18030(replace)` 与 `utf-8(replace)` 比 CJK 字符数 → gb18030 胜且 **U+FFFD 零丢失**（样本实证：也儿的石河｜元朝｜水）。
- **事件⑥TGAZ 解析**：mysqldump 之 CREATE TABLE 跨多行 → 单行正则碎裂 → 改块累加器状态机。

**批 2b 腿 K（V2/V3/V4 档案，脚本 b2b3）**：向量 **107 层**（V2 37＋V3 25＋V4 45：russ 七套 CP1251 4024→4326〔Пекин/Гу-бей-кэу〕、1820/1911 全 set〔v2_1911_twn 151,254 行级、v4_1911_twn 38,599〕、dcw contour 92,626＋rds 27,256＋rvr 213,880、time 层 Krasovsky `-a_srs` 注记〔无 datum 移位，假定入账〕、citas90 三编码变体）＋**MDB 关系库 36 表**（v2db 11：main 36,529/gisinfo 38,179/partof 31,834/source_notes 2,524/xtra×7；v3db 12：main 49,255/gis_info 52,465/part_of 53,122/preceded_by 7,692…；v4db 13：main 58,399…）＋gns v4 并表 **126,566**（29 内层 zip，4610 米制→4326）＋xlsx 10 件（含 chinaw_master_beta）；**哈希去重 12 层 SKIP_DUP**（V3 内嵌 v2_* 字节级同份，hashreg.json 实证）；JX4KSQ SKIP_FMT（MDB 已装）。
- **事件⑦MDB 管线**：容器 mdbtools 之 `mdb-schema` backend "postgresql"＝**Invalid backend type** → 改全文本列 CSV 管线（mdb-tables/mdb-export UTF-8→CREATE TABLE 全 text→COPY）；kozlov jpg 元数据 cp1251 致 UnicodeDecodeError 0xa8 → subprocess `errors='replace'`。
- **事件⑧chgis_v2_database.ZIP NO_LAYER**：zip 内系 MDB 非 shp → 分类窥探：无 .shp 之 zip 将内层 .mdb/.xls(x) 路由 others 管线（ROUTED 19 行），否则 SKIP_FMT；basename 去重（V4 MDB 多路径三次误装→修）。

**批 2b 腿 L（栅格）＋两轮修（脚本 b2b3 L 段/b2b3fix/b2b3fix2）**：
- 首装：peking_1875（bretschneider 1875 北京）**275 瓦片 4326** ✓；atlas×3／v2_dem×6／gtopo30 首装 **srid=0 病**；worldfile TIF 误 SKIP_NOGEO；v3 DemTopo30 误 NORASTER。
- **事件⑨raster srid=0**：epsg 提取正则 `ID\["EPSG",(\d+)\]` 抓 gdalinfo 全文，误中 **DATUM/UNIT 之 ID**（7049=Xian80 datum、9014、6610）而非 CRS → 正确检测＝`gdalsrsinfo -o epsg`；度像素无 SRS 者 `-s 4326` 赋标（**datum 按 WGS84 假定入账**）；米制 Xian80-GK19 者以规范 WKT warp→4326。
- **事件⑩worldfile 漏抽**：`.tifw` 拼写不在解包过滤器 → 16 个 TIF 误判无配准 → 补抽并造 `.tfw`/`.tifw` 双拼写＋gdalinfo `Pixel Size` 实证 → 16/16 全落（度制 worldfile：pdb2 900 瓦／Ca1884_partial 380／ABPR9F map1-3 380/360/380／LVYYZC map1-11 320–425，全部 `-s 4326`）。
- fix2 轮：**事件⑪GDAL 对含旋转项之 worldfile 只打 `GeoTransform =` 不打 `Pixel Size =`** → 检测字符串两度误判（atlas jgw 大旋转项＝扫描件歪斜；DemTopo30 微旋转项 5.4e-7）→ 检测改 `GeoTransform|Pixel Size`；atlas 三页补抽 .jgw＋PAM 自定义投影退化为 ENGCRS 不可 warp → `gdalwarp -s_srs xian80_gk19.wkt` 显式 → **1926 图集 01 全国页 220 瓦 ext 62.8–143.6E/14.5–57.0N、11 长江中下游 176 瓦 111.4–120.4E/24.2–30.1N、13 160 瓦 106.9–116.1E/24.5–30.2N（extent 与页题吻合）**；DemTopo30 3,948 瓦 60–149.1E/10–60N；v2_dem 六瓦 567–858 瓦；gtopo30 → warp `-r near` **6,095 瓦** ext 42.3,7.1–174.7,67.8（README 自述 "reprojected to Gauss Kruger Xian 1980 Zone 19"＝证据；**Byte RGB 可视化底图，非高程**）。纯扫描图存档不装（SKIP_NOGEO 终态 55，§14 差异项③兑现）。

**验收八项初轮（b2acc）→ 编码大事件暴露**：④中文抽验见 `é¸å·`（＝霸州）、⑦a 1911 县面返 "Pu Zhou|æ¿®å·"——**系统性双重编码**。
- **病理**：批 2 装载函数 D1/D2/D3/K/I 诸腿多传 enc=None（未设 SHAPE_ENCODING）→ GDAL 依 dbf LDID（多 0x57=ANSI）按 **ISO-8859-1** 猜解 → UTF-8 源字节被 latin1→UTF-8 双重编码入库。首批显式 `--config SHAPE_ENCODING UTF-8` 故无恙。
- **检测演进（如实记）**：首轮扫 `[À-ÿ]{2}`（U+00C0–00FF）仅中 14 列——**漏检**：UTF-8 三字节汉字之 latin1 像＝E6 系字符＋**C1 控制段（U+0080–009F）**＋A0–BF 段字符（"æ¿®å·"之 ¿®· 皆出界、连排被打断）→ 二轮 `[\u0080-\u00FF]{2}` 全 Latin-1 补充块扫 3,760 列 → **中伤 820 表列**。
- **分诊四路**：REPAIR_U8（latin1 型伤）117 表／REPAIR_1251（poddubnyi：CP1251 被当 latin1，`áåç èìåíè`＝без имени）／RELOAD（kozlov：UTF-8 源被 AUTO 误判强制 GBK，`斜械蟹`＝Пекин；gns：见下）／**LEGIT 源自带 11 表不动**（public.biog_main 2 行法籍传教士名"Hubert-Franççoi Schraven"、addr_codes 1 行、ethnicity_tribe_codes "Hü'üshin" 转写、merged_person_data 1 行、tgaz_snote 14 行〔中文注记＋西文引注〕、tgaz_alt_name3/present_loc〔Wade-Giles ü 合法〕、MDB source_notes 3/3/7 行西文引注、bgis bldg_mt_en "Buddhist nun's (庵)" 混排）。
- **修复法（工程决策）**：ISO-8859-1 系 256 字节**全映射**（字节↔U+00XX 双射）→ `convert_from(convert_to(col,'LATIN1'),'UTF8')`＝**无损可逆修复**，免重装；守卫模式 `[\u00C2-\u00F4][\u0080-\u00BF]`（UTF-8 lead＋continuation 签名；合法 ü 单字符/西文重音不误伤）。批量 UPDATE **780 列/2,344,643 行**全过；24 列整句回滚报 invalid byte——**源 dbf 字段宽度截断多字节字符**（如 E7A5 缺第三字节）→ plpgsql 逐行＋裁尾重试（`left(v,len−k)`,k=0..2）**修 138,524 行／360 行源截断不可逆**（残伤 3 列如实入账：v2_time_cnty_pts.ch_orig 339＋pgn 20＋v4_1911_twn_pts.name_py 1）。poddubnyi 修 `convert_from(convert_to(…,'LATIN1'),'WIN1251')`（**PG 编码名系 WIN1251 非 CP1251，首试报错**）1,111 行→без имени/Цза-ра-ла ✓。
- **修复后抽验（全净）**：霸州/仁本宗、濮州（⑦a 空间复测）、萧县/归善县、漠河/塔河、崇明寺、Пекин/Гу-бей-кэу、без имени/Бор-нуру、元朝｜水、云南府/杨林、伦珠寺/拉康寺、古宫/白塔寺、蝦夷地/北陸道、内藤義概/ないとうよしむね（汉字假名双列）、澎湖厅/双城厅、万善寺/东山寺、北京市轄縣、Mendong Gömpa。
- **kozlov 重装事件（如实记）**：首重装把**宿主路径** `/mnt/nas-mirror/…` 传给容器内 ogr2ogr → 容器不见 → **静默未装**（old==new==2351 系假象，验证语句崩溃前未暴露）→ docker cp 入容器＋`--config SHAPE_ENCODING UTF-8` 强制（zip 内 cpg='UTF-8' 在而 GDAL 未采、LDID=0）真装 → 2,351/2,351 行西里尔 ✓。**教训：old==new 不等于成功，容器内命令须验容器侧可见路径。**
- **gns 误标事件（字节实证）**：`v5_gns_*_gbk.zip` 原始字节 `48 73 FC 61 6E`＝"Hs\xFCan"——**ü 系 latin1 单字节 0xFC，文件名 `_gbk` 为误标**；CNTY_CH 等中文列实测全空 → v5_gns 以默认 enc（latin1 直通）重装 **130,665** ✓（ü 行 3,912：T'ai-yü-chen/Shuang-ch'üan-chen）。**v4_gns 不同**：原始字节 `ED B8 C9 BD CF D8`＝真 GBK 中文 → SHAPE_ENCODING=GBK＋`-t_srs EPSG:4326`（源 4610 米制）重装 **126,566** ✓；同列混编（GBK 中文＋latin1 ü）→ GBK 装载把 ü＋其后 ASCII 字符吞成 **GBK 用户区杂字**（FC61→黙、FC6E→黱、F66C→鰈＝öl、DC64→躣＝Üd——Wade-Giles 变音 äëïöüÄÖÜ 系 latin1 C0–FF 单字节）→ 系统化逆映射：distinct 非 ASCII 字符→`encode(ch,'GBK')` 前缀 C0–FF 且尾字节 40–7E 者→`chr(lead)+chr(trail)`，**83 映射清洗 1,183 处**（Sakya Gömpa/Pembar Gömpa ✓）；真汉字（GB2312 尾≥A1）不动——**v4 真中文本在 CNTY_CH 列**（措勤县/边坝县/萨迦县，GBK 装载本就正确；FIX4 账"CJK 行 1140"实为用户区杂字非汉字，勘正）；残杂字 **2 行**（lead<C0：燛rsha/Ør縨u＝GNS 九〇年代转写源自带退化，**不造数据**，如实入账）。
- **gns CRS 误判与勘正（如实记）**：v5_gns 重装漏 `-t_srs` → srid=2333 米制；列 typmod `geometry(Point,2333)` 拒 UPDATE → 误判"prj 与数据不合、实为 2327"→ `ST_SetSRID(geom,2327)` 强转后**安徽落 129–131°E（错）**→ spatial_ref_sys 实证：**2333＝`+lon_0=111 +x_0=19500000` 本就是 6 度带 19 真解（FE 19.5M/CM 111），2327＝13 带（CM 75/FE 13.5M）——原 .prj 无错、我判错** → 逆变换 `ST_Transform(geom,2327)` 还原米制 → `ST_SetSRID(…,2333)` → `ALTER TYPE geometry(Geometry,4326) USING ST_Transform(…)`（typmod 一并解）→ ext **74.2–135.0E/18.2–53.5N 与 v4_gns 逐位互证**、安徽带 114.90–119.62 全同、西藏样 Lhazhong@86.67,32.05／Kugka Lhai@88.33,31.98 合理 ✓。
- **tbrc FFFD 溯源**：DB 10 行 U+FFFD；源 dbf `Tibet_Monasteries_UTF8_v1_20120702.dbf` 字节探查 EF BF BD **恰 10 次**——源自带、装载零丢失 ✓。
- **工具级教训汇总（如实记）**：①宿主路径入容器＝静默失败；②`-sql "…'{pv}'…"` 内层单引号顶破 bash -c 外层单引号（`Unrecognized field name beijing`）→ 改 ALTER＋UPDATE 补 prov 列；③ssh 管道无 pipefail → tee 吞 python 崩溃（b2fix2 exit 0 而 traceback）→ 此后全程 `set -o pipefail`；④重装未带 `-lco GEOMETRY_NAME=geom` → 列名 wkb_geometry（kozlov 例，后 RENAME 归位＋GiST 复证）；⑤检测字符串必先验 GDAL 输出形态（Pixel Size vs GeoTransform、[À-ÿ] vs [\u0080-\u00FF] 两度漏判）。

**验收八项终态（b2acc2＋b2post，全过）**：
- **①对账总账**：recon 1,757 行；终态 **OK 282＋REPAIRED 8＋AS_IS 3＋SPLIT_OK 1＋ROUTED 5**＋SKIP 族（**SKIP_DUP 110**〔字节哈希同份实证〕／**SKIP_FMT 186**〔MapInfo〔镜像无 MITAB 驱动〕/KMZ 重打包/纯图档等——存档留证〕／**SKIP_ENC 65**〔编码变体只装一份〕／**SKIP_NOGEO 55**〔纯扫描无配准——存档〕／SKIP_VIEW 5〔TGAZ 视图可随时重建〕／DERIV/COORDVAR/GEOMONLY/VAR/NOWORLD/NORASTER 各 1–2）；FAIL 4 行**皆被后续修复行取代**（hartwell_chin＝事件③半成品已 DROP〔实存=0 实证〕；FIX/FIX2 gns 3 行被 FIX4/FIX9 取代）＋NO_LAYER/NORASTER/SKIP_NOWORLD 各 1 亦被后续 OK 行取代——**未解决终态为零，无一静默丢**。
- **②ADDR_XY**：19,249／哨兵 7,793 零／11,456 非零／6,722 有 source_ref ✓。
- **③Hartwell**：九表合计 **21,497 == H 腿 src 和** 逐位全同 ✓。
- **④编码族抽验十六项全净**（BIG5 藍關鎮〔capital_ch CJK 8,065〕／UTF-8 霸州濮州萧县归善县／GBK 漠河崇明寺／CP1251 Пекин без имени／gb18030 元朝｜水／TGAZ written_form 霸州新河縣密云縣／MDB Chengde Fu／纪年 秦｜秦 简繁双列／明驿 云南府杨林／gns Gömpa＋ü 3,912 行／tbrc 伦珠寺＋源生 FFFD 10 行／jp 内藤義概＋假名）；U+FFFD 零（除 tbrc 源生 10 行）、latin1 伤零。
- **⑤GiST/栅格清点**：GiST **221**（chgis 162＋harv 59）＝向量 **192** 表＋栅格 **29** 表严丝合缝；带型账：**chgis.dem＝16BSI Int16 真高程**；gtopo30/v3_dem_topo30＝8BUI×3 **Byte RGB 可视化底图**（同点取值 48/48＝通道值非高程，高程真值唯 chgis.dem）；v2_dem 六瓦＝8BUI Byte（中心值 140/76/50/0/204/50）。
- **⑥桥补 3,871 探索项（成败皆如实记）**：批 2 D1 重载 v6 两点层后桥余基数变为 **2,649**（首批口径 3,871 中 1,222 个新命中 v6 层）；以全部 sys_id/v5_id/v6_id 列试 join → **去重命中 1,494**＝ChinaW 三载体 1,449（v5_chinaw_pts〔shp〕/chinaw_master_beta〔xls〕/harv.chinaw_pts——**同内容三份、字节级去重防不了跨格式重复**，如实记）＋时序层 45（v5_time_cnty 112/v4_1911_cnty 67/pref 24/twn 10/v4_time 27/v3_time_prov 5/v5_smr_subr 30，去重后并 1,494）；**余 1,155 仍未对上**（推测指向 Hartwell 制式 ID 或年代包外时间片——探索项入账，不追加）。
- **⑦空间复测三例**：a) 历山书院 (115.50,35.67)→`v5_1911_cnty_pgn` ST_Intersects＝**Pu Zhou｜濮州**（拼音汉字双列同中，与首批互证）；b) DEM 同点 **chgis.dem＝54m**（与首批逐位同）、gtopo30/v3＝48（Byte 通道值）、atlas 11 页范围内取值 141、v2 瓦片中心 0–204；c) 明驿路：三站（云南府/杨林/寻甸）→最近路线 KNN＝**0.00km**——驿站在驿路上，语义直中。
- **⑧压力门禁**：全程 nice/ionice＋门禁，抽测 loadavg 0.37–0.55 未近阈 4.0；**pg32 canary＝1 恒、生产零感知**（docker stats：pg32 cpu 0.02–8.87% 瞬时/mem 66–70MiB；pg32b 峰值 mem 2.5G/7.3G）；收工后磁盘余 189G。
- **VACUUM ANALYZE**（234 万行 UPDATE 后）：52 秒。

**装了什么/为什么没装总账（§14.4 验收⑥兑现）**：装＝OK 282 目标＋REPAIRED 8＋AS_IS 3（向量 192 表、栅格 29 表、MDB 36 表、TGAZ 33 表、纪年/码表/xlsx 若干）；不装＝五类留证：SKIP_DUP 110（字节同份）／SKIP_FMT 186（格式不可装：MapInfo 无 MITAB 驱动、KMZ 重打包核证、纯图档等）／SKIP_ENC 65（编码变体一份制）／SKIP_NOGEO 55（纯扫描存档）／SKIP_VIEW 5＋零星裁决 7——**每一跳过皆有 recon 行**。

**清点（第二批毕库态）**：cbdb 库 **4,770MB**（首批 1,543→＋3,227MB）；用户表 **394**（chgis **211**＋harv **97**＋public **86**；另 ogr_system_tables 1＝pg_tables 非目录总计 395）；总行 **≈8,580,012**（首批 5,686,842→＋2,893,170）；GiST 221；扩展 postgis 3.6.4＋**postgis_raster 3.6.4（本批新建）**；最大表序：biog_source_data 1,254,135／biog_main 661,969／…／tgaz_spelling 245,042／v4_dcw_rvr_lin 213,880（新增层跻身前十二）。

**收尾**：审计件（recon_b2a.tsv 1,757 行＋脚本 22 支＋关键输出，共 36 件/576KB）收 `ops/harvard/load-b2/`（运维工作区，依 .gitignore 政策不入仓）；宿主 `/tmp/pg32b-load2`（1.3G，内含 ras/hw5/iext 等**外部数据解包副本——N-01 必删**）入账后已 rm；容器 /tmp 清空（7.1G→0）；§2 缓办段四条对账：②Hartwell ✓本批装、④CHGIS 其余层＋ADDR_XY ✓本批装、①版本堆仍存档不装、③ZZZ 仍不装——**第二批挂账清零**。36 仍不可达（缓办，非本批范围）。（**2026-09-26 补正续**：① 用户令"tmp下的文档不保留"——开发机 /tmp 指南系物件全删（`cbdbdoc` 解包树 23M／`cbdbp`／`cbdbt` 官网调研暂存／`g2025.txt`；wayback 2023 版件查实已不在；并行会话之 wiki 工作目录不在此列、未动）；② 答用户问"导入 pg32b 的数据用了哪个位置的源数据，都有记录吗"——recon src 列系文件基名、完整路径此前散于 §15 腿级叙述与脚本源码，现补全**`src_paths.tsv` 源文件映射表**入审计件：每 recon 行→NAS 实存源逐文件展开，1,757 行**未解析 0／异常多命中 0**（解析形态：文件级 1,472／外层 zip 级 233〔成员在 zip 内，inner 列注成员链〕／嵌套 zip 级 17〔如 `ZZKZ6U/CHGIS_V2.zip⊃v2_dem_nw_one.zip⊃nw_one.tif`〕／DOI 目录级 25〔描述性/多件引用〕／多档案级 1／修复验收行 5；DOI 消歧取自 b2*.py 脚本硬编码证据，生成器 `resolve_src.py` 同存可复跑）；源根两处＝32 镜像盘 `/mnt/nas-mirror/61/workmetadata/`（harvard-full DOI 树＋chgis-v6）＝开发机侧 `/mnt/wd61workmetadata/` 同一 61 共享；审计件现共 **38 件/864KB**。）（**2026-09-26 补正续2**：③ 承用户问"用的是 /mnt/wd61workmetadata/ 下哪些目录的数据"——src_paths.tsv 机械汇总出**目录级账**并把 harvard-full 65 树＋顶层目录全部对完，存 **`tree_coverage.tsv` 源覆盖审计表**入审计件（67 行：**第二批用 42 树/目录**〔41 DOI 树＋顶层 chgis-v6/，1,754 条 recon 行挂其下——前五 PDGOZ0 572 行/ZZKZ6U 356/HIMIVE 337/H3OB28 114/M7WEFY 83〕、**首批工作集 1**〔usedata/harvard/：cbdb/ 2 件 sqlite＋chgis/ 3 件 time zip＋tab/ 3 件＝7 件数据，另 PAGGQS/CBDB_20240208_sqlite.db 只读取 schema〕、**未触碰 24 树**逐一分类给实证）；④ 未触碰 24 树分类（各经实证）：**版本堆 5**（GNPNON/P8U8RC/F6BBOF/2UFYFG/SHMDGU——§2① 裁决存档不装）、**软件 2**（BWIBNL LoGaRT 权重／16PSZE 韩文罗马化转换器——工具非数据）、**文档树 7**（JJMYV7/AZYI17/MZANN5/IWOK2X/SNCEAU/FDLFJ3/6CHSR7——PDF/GIF 书目、论文、EULA、README、字典类）、**同内容已装 7**（I0Q7SM/WW1PD6/Q9VOF5 V6 时序三树之 utf_wgs84.zip 与 usedata/harvard/chgis/ 同名件 sha256 **字节全同三连**〔`d3aa9f39…`/`48f6a50b…`/`3b431d2e…`〕＝首批腿 B 已装；HTGBQ3/J6XRIV/CE4ZNG＝首批腿 C usedata/harvard/tab/ 三 .tab 原件之源树〔40,199/2,957/1,033 行已装〕；SC7AOU china_chron.ZIP＝F 腿源 chgis-v6/China_Periods_ReignDates.zip 之子集——5 同名成员 4 字节全同〔txt sha `4d41c5ec…` 同〕、唯 china_chron.xls 为格式变体而其 txt 已装 677 行）、**编码变体 2**（0P89R9＝1911 GBK／2K4FHX＝1820 GBK 孪生树——utf 版 HHVVHX/ST5KKM 已装、依编码变体一份制不重装；原 recon 对此二树无留证行＝账目小疵，tree_coverage.tsv 该行即留证）；⑤ **新缺口挂账（R-02）**：**TI8DFI「Multilingual Feature Type Crosswalk」**（多语言〔中/日/维等〕特征类型对照表）——含 ADL_FTT_V2.zip 80,559B／feat_class_xwalk_080502.zip 99,018B／xwalk_2004.zip 135,288B 三数据 zip＋PDF 一件——**§14 v2 货单未覆盖、第二批未装**；依"能装尽装"口径属真缺口，**补装候用户令**；审计件现共 **39 件/872KB**；人读摘要表＝**`docs/data-sources.md`**〔同日用户令开设、index.md 已登记——一页说清源文件→库位／来历与内容／对应规则，数字全部机械汇总自本批审计件＋库内实测〕。）（**2026-09-27 补正续3**：用户裁决（原话）"**不行。/mnt/nas-mirror 这个目录我们的项目不能用。我建立它的目的就是为了在32上备份nas的内容。**"——**nas-mirror＝用户自建之 32 本地 NAS 备份区，项目读写皆禁**（裁决权威展开＝`docs/codemap.md` §2"32 本地备份盘"专行）。史实不改写：两批装载实跑确曾读镜像盘侧（§10/§12/§14/§15 及 b2*.py 22 支脚本硬编码路径＝审计留证），**装载产物有效性不受影响**——镜像盘与直挂系字节级同一份数据（文件数 16,822＝同、纯文件字节和 21,492,791,579＝同、rsync 干跑零差异，2026-09-27 实测）；**项目从未写镜像盘**（工作集拷贝＝镜像盘读→NAS 写单程）。**此后任何装载/补装（含挂账中之 TI8DFI）/复核一律读 32 直挂 `/mnt/wd61workmetadata/`**（容器侧搬运法不变＝docker cp，kozlov 事件教训仍适用：容器内命令须验容器侧可见路径）；本文 §2"装数优先本地镜像读"与 §14 差异项⑨"直读镜像盘"两处旧表述作废（原文不改、前向注记于此）。）

**事件账总（十一件＋教训五条，全自制全决全披露；库内数据完整性零遗留——唯三处源生缺陷如实入账：360 行 dbf 截断、2 行 GNS 转写退化、10 行 tbrc 源生 FFFD）**：①raster2pgsql 缺失→Debian 包提取；②psql 引号制式→`'\''` 统一；③Hartwell 混组→type×几何类重分组；④嵌套 zip→解包＋docker cp＋cpg 尊重；⑤谭图解码→gb18030(replace) CJK 计数比较；⑥TGAZ 多行 DDL→块累加器；⑦mdb-schema 无效→全文本列 CSV 管线；⑧MDB zip 误配→分类窥探＋basename 去重；⑨raster srid=0→gdalsrsinfo 实证＋规范 WKT warp；⑩worldfile 漏抽→双拼写补抽；⑪**编码大事件**（820 列中伤→修复 2,483,167 行〔780 列批量＋24 列逐行〕＋kozlov 重装＋gns 双表重装/清洗＋CRS 误判自纠）。教训五条见上"工具级教训汇总"。
