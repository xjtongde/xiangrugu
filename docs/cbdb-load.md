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
- **CBDB《User's Guide》全文已抓到**（M. Fuller 修订版，**153 页**；harvard 直连 403 系服务器端反爬→改经 wayback 存档取 PDF、`pdftotext` 转文。**版本注记（2026-09-25 补正）**：初录误标"rev. 2021-10"——扉页修订日期因字体编码在文本层丢失，PDF 元数据实测生成日 **2023-10-06**（Acrobat PDFMaker 17），据此补正为"2023-10 生成之修订版"；本件 8,531,184 B、sha256 `cab7d155…`，暂存开发机 /tmp（易失，正式归宿候用户令）。**NAS 另有官方 2018 版**：`harvard-full/doi_10_7910/DVN/P8U8RC/CBDB_Users_Guide_2018.pdf`（5,478,089 B、sha256 `bd1c7461…`，与 CBDB_aw_20180831 Access 包同树）——**本文档一切页码/行号引用皆钉 2023 修订版**，与 2018 版不通用）：官方支持面＝序言原话 **Access（主制式）＋SQLite（"for quantitative researchers and Mac users"）**；另有历史附录《CBDB SQL Server Version》（CBDB_SS，SQL Server Express 平台，系绕 Access 文件大小限制之产物）；**全文检索 PostgreSQL/PostGIS/MySQL 命中＝0**——"官方无入 PG 指引"系全文实证，非推断。
- **含义**：CBDB→PG 无官方成例可循，本管线属自建——§7 对账验收七项即安全网（官方无指引处，以可复核对账代之）。

### 12.3 社区同类经验

- **sqlite→PG 大路工具＝pgloader**（Neon/Netbird/Render 三家迁移指南一致推荐）；其 Debian bookworm 有官方包。**本案不用**，理由：装它＝32 宿主系统改动（超实例边界须另令）；本管线 python3 标准库零新装、且类型映射/BLOB 十六进制/NULL 语义全可控。**备选地位记录在案**（若 78 表管道遇阻可裁启用）。
- 社区踩坑清单（open-webui 迁移讨论等）：类型亲和性（sqlite 动态类型→PG 静态）、BLOB、标识符大小写、布尔表示——**本方案 §4.2 映射表逐条已覆盖**（INTEGER→bigint／BLOB→bytea hex／不引号全小写／无布尔列）。
- **CBDB 专向入库项目：检索未见现成开源管线**（学术侧有 CBDB 关系库论文与 R/Python 访问包，皆非 PG 迁移）——与 12.2 互证。
- CHGIS→PostGIS **官方手册对照（PostGIS 3.6 Manual 第 4 章 §4.7 "Loading Spatial Data"，全文已抓）**：官方内建装载法两条——①SQL 语句（WKT/WKB 经 `psql -f`）②**shp2pgsql 装载器**（关键旗标：`-D` dump 格式＝COPY 快速模式，官方原话 "Use this for very large data sets"；`-I` 建 GiST；`-W` DBF→UTF8 编码转换；`-s` 指定 SRID；`-e` 逐句事务）。本方案之 **ogr2ogr＝GDAL 项目官方工具**（与 shp2pgsql 同属 PostGIS 生态、内部同走 COPY），功能覆盖上述要点：`.prj` 自动带 SRID 4326（≈`-s`）、GiST 自建（≈`-I`）、UTF-8 变体＋`SHAPE_ENCODING`（≈`-W` 且从根上免转换）、`/vsizip/` 直读 zip（shp2pgsql 所无）。**差异记录**：若须严格按手册原生工具，可加装 PGDG `postgis` 装载器包（F-13 ③(a) 候选，与 gdal-bin 同批可加）——默认不变（ogr2ogr 已本机实证三驱动在列）。编码历史坑（PostGIS 邮件列表 2011 年 shp2pgsql 客户端编码旧案）→本案 UTF-8 变体从根绕开 GBK。

### 12.4 调研出处（引用为外部资料，内容以原文为准）

- PostgreSQL 18 官方文档 §14.4 Populating a Database：postgresql.org/docs/current/populate.html（经 web.archive 存档实抓全文）
- PostGIS 3.6 官方手册第 4 章 §4.7（Loading Spatial Data）：postgis.net/docs/manual-3.6/using_postgis_dbmanagement.html（curl 实抓全文切片）
- CBDB《User's Guide》（Fuller 修订版，153 页，PDF 生成 2023-10-06——初录"rev. 2021-10"系误标已补正，见 §12.2 版本注记）：harvard 直连 403（服务器端反爬）→经 web.archive.org/web/20240914131845 取 PDF 全文、本机 `pdftotext` 转文检索（临时文件仅在 /tmp，不入工作区；正式归宿候用户令）
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

**状态：首批已执行完毕（2026-09-25 00:24 验收七项全过，执行记录＝§13）；第二批已成案＝§14，候"同意"开工。**

---

## §14 第二批成案（2026-09-25 用户令"把余下的装上去。这个工作量大吗？"→ 装前实勘毕、成案候令）

### 14.0 实勘新事实（本批依据，全部只读实测于 32 镜像盘）

- **M7WEFY＝CHGIS V5 树全量 101 zip**：其中 UTF 可用层约 24 个；`v5_time_pref_pgn/pref_pts/cnty_pts` 系 **V5 代时序层（V6 前身，已装 V6 等价件——跳装不重复）**；GBK 变体、合并包（`v5_1820_utf.zip`/`v5_1911_utf.zip`）、`-1/-2` 重复产物皆不另装。
- **v5_dem.zip＝GeoTIFF 栅格**（`chgis_dem.tif`＋hillshade＋ovr/aux，80.7MB）——**非矢量**，装入需 `postgis_raster` 扩展（pg32b 有无待探测，见差异项①）。
- **gns_*＝30 省现代地名集，仅 GBK，合计仅 10MB**（比预想小两个量级）——`SHAPE_ENCODING` 转码可装。
- **Hartwell 29302 实勘定性**：v1_2002 包 2,866 条目＝shapefile＋**MapInfo（.MAP/.TAB）混装**；v5_2010 包 2,467 条目＝**逐年切片**（`v5_0741_…`—`v5_1900_…`，每层 shp/shx/dbf/prj/xml 五件套，实际约 400 个年×图层）——直接装＝数百张表，**须先设计归并策略（合并表＋年份列），拆为独立研读案**（见 14.2 丁）。
- **ADDR_XY（2024-02 sqlite 只读实测）**：**19,249 行×6 列**（c_addr_id INTEGER/x_coord FLOAT/y_coord FLOAT/c_source_reference CHAR(255)/c_source_id INTEGER/c_notes CHAR）；样本首行即 x=y=0.0——**`0` 哨兵实在**（cbdb.md §9.5 清洗规则适用；照装原样＋哨兵/污染统计入账，不在库内改数）。
- **China_Periods_ReignDates.zip**：内含 `china_chron.sql`＋`china_chron.txt`＋CSV＋README——**现成朝代/年号纪年对照表**（意外小丰收，随批装入）。
- 新见层（前清单未列）：`v5_PhysiogMacroregions_pgn_utf`（自然地理大区面 5.7MB）、`v5_SMR_pgn_utf`（6.3MB）、`Manshu_200K_index_SHP`（满洲 20 万图幅索引）。

### 14.1 范围裁定（四挂账项处置）

| 挂账项 | 本批处置 | 理由 |
|---|---|---|
| ④CHGIS V5 族 | **装**（腿 D，24 层＋gns 并表） | 用户令"余下的装上去"；全部本地、管线已证 |
| ②ADDR_XY | **装**（腿 E，19,249 行） | 同上；腿 A 管线复用 |
| 纪年表 china_chron | **装**（腿 F，随批） | 实勘新见、极小、补年号检索短板 |
| DEM 栅格 | **探测后定**（差异项①） | 需 postgis_raster；无则另令 |
| ①Hartwell 29302 | **本批不装，拆研读子案**（14.2 丁） | 400 层/MapInfo 混装，须先定归并策略——装进去是几百张表，非"余下的一层" |
| ③ZZZ | **不装**（已定案，§2③） | 零新数据，蓝图已入账 |

### 14.2 货单与目标表（腿 D/E/F）

**甲·1820 族（9 层，UTF 除 coast_lin）**→ schema `chgis`，表名从源：
`v5_1820_cnty_pts`／`v5_1820_coded_rvr_lin`（河流）／`v5_1820_lks_pgn`（湖泊）／`v5_1820_pref_pgn`／`v5_1820_pref_pts`／`v5_1820_prov_pgn`／`v5_1820_prov_pts`／`v5_1820_twn_pts`（乡镇点）／`v5_1820_coast_lin`（单变体，装载时先探 DBF 编码，GBK 则 `SHAPE_ENCODING=GBK` 转 UTF-8 入）。

**乙·1911 族（7 层，UTF）**：`v5_1911_cnty_pgn`（**本批头号货——唯一历史县面**）／`v5_1911_cnty_pts`／`v5_1911_pref_pgn`／`v5_1911_pref_pts`／`v5_1911_prov_pgn`／`v5_1911_prov_pts`／`v5_1911_twn_pts`。

**丙·省级/专题/杂项（11 层）**：`v4_time_prov_pgn`／`v4_time_prov_pts`（省时序）／`v5_1926_prov_pgn`／`v5_1997_prov_pgn`／`v5_1990_citas_cnty_pgn`／`v5_1990_citas_pref_pgn`／`v5_ChinaW_pts`／`v5_2009_tibet_twns`／`v5_PhysiogMacroregions_pgn`／`v5_SMR_pgn`／`manshu_200k_index`。

**丁·gns 30 省（GBK）→ 并一张表** `chgis.v5_gns`（加 `prov` 列标省名，`-sql "SELECT *, '<省>' AS prov FROM <层>"` 逐省 append；比 30 张碎表好用）。

**戊·ADDR_XY** → `public.addr_xy`（CBDB 数据归 public；腿 A python 管道：sqlite 只读 URI→COPY text，哨兵/NULL/浮点规则同首批 §4）。

**己·china_chron** → `chgis.china_chron`（先读 `china_chron.sql`/`README` 定方言与列义，优先 CSV/txt 走腿 C 管道；.sql 若系 Access/MySQL 方言则弃用只取数据）。

**庚·Hartwell 研读子案（不装只研）**：产出＝命名规律表（年份×图层×制式三轴）＋归并装载策略建议（预计"合并表＋年份列＋层型列"约 4–6 张表方案）＋工作量重估——**成文挂账，装载候再令**。

### 14.3 方法与通路

- 腿 D＝首批腿 B 原样复用：宿主 `docker cp` zip 入容器 `/tmp`→`ogr2ogr -f PostgreSQL`（`/vsizip/` 直读、`-nlt` 按实测几何型、`-lco GEOMETRY_NAME=geom -lco FID=sys_id`、`PG_USE_COPY=YES`）→GiST 索引 ogr2ogr 自建→用毕 `rm`。SRID 逐层探 `.prj`（预期皆 4326＝首批裁定 WGS84；若有非 4326 层，`-t_srs EPSG:4326` 重投影并记差异）。
- 腿 E＝首批腿 A 原样复用（python sqlite3 只读→psql COPY，`\N`/转义/浮点 repr 规则全同）。
- 腿 F＝腿 C 管道（分隔文本→COPY）。
- 全部 `ON_ERROR_STOP=1`、顺序单流、任何对账不平即停（家规同首批）。

### 14.4 对账与验收（全过方收口）

1. **逐层三方对账**：`ogrinfo -so` 源要素数 == ogr2ogr 报数 == `SELECT count(*)`，24＋1（gns 并表＝30 省总和）层全零差；
2. **ADDR_XY 三方对账**：sqlite 19,249 == COPY 报数 == PG count；另记 `x=0 AND y=0` 哨兵行数与 c_source_reference 非空数（数据质量账，联动 cbdb.md §9.2/9.5 复核义务）；
3. **中文抽验**：每层抽 3 行含汉字字段目检（重点 gns GBK 转码层与 coast_lin），乱码＝0；
4. **索引清点**：新增 GiST 数 == 层数（gns 并表 1 条）；
5. **桥补测试（探索项，不设承诺）**：余 3,871 个 chgis_pt_id 对新装 V5 点层 id 试 join——V6/V5 id 制式若不同则补桥不成，**如实记录**（成与不成都入账）；
6. **空间复测**：1911 县面 ST_Within 样点（书院 2 例：历山书院→濮州→**判县**）＋DEM 若装则栅格取值 1 例；
7. **压力验收**：全程 loadavg 峰值＜4.0、pg32 金丝雀无劣化（同首批门禁）。

### 14.5 压力防护（承首批六措施，量级更小）

顺序单流零并行；宿主侧 `nice -n 19`＋`ionice -c3`；`cpu_shares: 512` 已在位；步骤间压力门禁（loadavg＞4.0 或 pg32 不健康即暂停）；**max_wal_size 不动**（本批总量约 200MB zip、行数远小于首批，默认 1GB 足够——首批 4GB 临时循环不复用）；maintenance_work_mem 维持实例默认（小表无须抬）。

### 14.6 工作量估算（答用户问"这个工作量大吗？"）

**不大——首批的零头**：货约 200MB（首批 594MB）、预计总行数 <100 万（首批 562 万）、层数 55（24 矢量＋30 gns 并 1＋ADDR_XY＋china_chron±DEM）但**皆小件**（最大单层 24.8MB）；管线三段全部首批实证复用、零新工具（DEM 除外）。**机器时间估 <30 分钟，含探测/对账/记账全程约 1–1.5 小时**。深水仅两处且已拆出：Hartwell＝独立研读案（14.2 庚）；DEM＝探测后定（差异项①）。

### 14.7 差异项（默认皆按本案，"同意"即照此开工，可逐条改裁）

1. **DEM**：先探 pg32b 有无 `postgis_raster`——有则 `raster2pgsql` 装 `chgis.v5_dem`（仅 dem.tif，hillshade/ovr 系衍生物不装）；**无则本批跳过**（补装需 apt/镜像层＝另令，不为它重建镜像）；
2. **gns 并单表**（推荐）vs 30 张分表；
3. **Hartwell 拆研读子案不装**（推荐）vs 本批硬装（不推荐：约 400 层）；
4. **v5_time_* V5 代时序层跳装**（推荐，V6 等价件已在）vs 一并装（版本存档意义）；
5. PhysiogMacroregions/SMR/Manshu 三专题层**装**（推荐，皆小）vs 缓；
6. 编码/坐标裁定承首批：**UTF-8＋WGS84**，GBK 件转码入。

### 14.8 回滚与账目联动

- 回滚：本批新增表逐张 `DROP TABLE`（首批产物与 cbdb 库本体不动）；gns 并表 `TRUNCATE`；最坏 `DROP SCHEMA chgis CASCADE` 后按 §5 重装首批三层（工作集在 NAS）。
- 账目联动（执行批内完成）：本文件加 §15 执行记录；`docs/pg32b.md` §12 补第二批建成段；`docs/features.md` F-13 状态行更新；`docs/codemap.md` usedata/instance 行补注；`docs/cbdb.md` §9.2（ADDR_XY 落地→缺项转"已入库＋哨兵统计"）与 §9 复核义务兑现；`docs/log.md` 收口行。
- 数据源：**仍用 `usedata/harvard` 工作集？**——**否**：第二批货（V5 树/2024-02 sqlite/29302）不在工作集（当初只拷首批 7 件）。**默认直读 32 本地镜像盘 `nas-mirror/…/harvard-full`**（只读，与首批"零传输"同理）；若您要工作集扩围（拷 V5 树入 usedata）请改裁此条（多拷约 200MB，分钟级）。
