# 第 4/6 块 MDB 与 SQL · lead 运行记录（2026-11-20 首个 30 分钟盒）

基线 ef90b64e908eaae315c0e1ba50b59b2eeb2985f0；盒 17:48:26Z–18:18:26Z。
过程披露：**a02 第五次早退（同型路由杂讯，未执行本轮任何工作），lead 接管全量生成器与解析**；a03 ROUND 13 独立核对不变。

## 运行
- 生成器 datamgmt/contracts/releases/2026-10-06-bootstrap/import-package/mdb-sql/build_mdb_sql_package.py（stdlib only，确定性，流式只读，**SQL 未对任何库执行，本轮未安装依赖，源件只读零触**）。
- 32 运行目录 /opt/mydocker/xiangrugu/build-candidates/mdb-sql-20261120/（inventory.json 传输副本 sha 断言 fb5e6b33…==仓内原件）。
- 命令：python3 -B build_mdb_sql_package.py（32 宿主 python3 3.11.2，快照 /opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap 只读）。
- 双跑纪律：run1/run2 exit 0/0 字节一致（r1.sha）；定位证据补全后 run3/run4 exit 0/0 字节一致（r3.sha==r4.sha），差分恰 om/gaps/SUMMARY 定位增量、members 不变、counts 恒等。日志 run1-4.log + r1.sha/r3.sha 在本目录。

## 产物 sha256（终态）
- members.json 9a8594205fe3d35650f92a2890d13dcd82de1de9c4892a834b5b87b9fd86c394
- object-mapping.json 820eff12ac528cf6234516796eb78269b41b3eaac0cd8554eee38565d3d6c157
- evidence-gaps.json 016740f16a8122924830a549cf95305c634f87e00de4fab34db7622355746be4
- SUMMARY.md bca41b5055e5f2f4c5e0c8580dc0c5de1286d7add97608655090db0ae710a864

## 计数
核心成员 **7**（MDB 5 + SQL 2）；已枚举对象 **39** = SQL 表 34（全量 CREATE TABLE 解析，异常 0）+ MDB 文件级 5（头探针）；已映射提案 **34**（SQL 表，PROPOSED_NOT_AUTHORIZED/ready_for_import=false）；MDB 表枚举 0（工具缺口）；缺口 **6**（MDB 目录读取器×5 + tgaz 编码损失×1）。

## SQL facts
- china_chron.sql（chgis-v6/China_Periods_ReignDates.zip!china_chron/）：MySQL dump；1 表 china_chron 20 列；677 INSERT/677 行；**utf-8-sig BOM**；0 替换字符；载体 INSERT。
- tgaz_bak_2018.sql（H3OB28/tgaz_bak_2018.zip!）：MySQL dump；**33 表**（InnoDB×32+MyISAM×1，charset utf8×33）；136 extended INSERT；行估算 ~983236（口径：每 INSERT 行 '),( ' 计数+1，字符串内含分隔符可致高估，精确计数待批准解析器）；utf-8 无 BOM；**5 替换字符全定位 line 326 单条 INSERT INTO `geom`——字符串字面量内 WKB 风格二进制几何载荷原始高位字节非 utf-8⇒字节忠实提取隔离恢复对象（gaps recovery_note）**。

## MDB facts（×5 全 JET4）
magic 00010000 / "Standard Jet DB" / version byte 0x14=1（JET4 Access 2000-2003）/ page 4096（版本推导注记）/ hexdump128 逐字在证；sha 流式全量复验==inventory。
- V3 v3_chgis_database.mdb 68853b49…（52195328B）
- V4 直接件 v4_chgis_dbase.mdb **a2cc4039…**（65896448B）≠ zip 包裹件 **04be983d…**×2（access_database/ 与 shapefiles/ 镜像对，块6合并）——**两版本分别注册**
- V2 chgis_v2_database.mdb 4a9bd1bc…（46702592B）
逐件不可读原因：锁定环境无 MDB 目录读取器（32 宿主与现有容器均无 mdbtools，实测）；所需工具 **mdbtools=1.0.0+dfsg-1.1**（32 apt-cache policy 候选，bookworm；锁定版本提案，本轮未装，待茶香批准）；隔离恢复路径：批准后 32 隔离临时目录 mdb-tables/mdb-export/mdb-schema 只读。

## 相关成员处置（exactly-once）
3 内层容器 ZIP structural；Thumbs.db（KML 内，OLE）Windows 缩略图缓存非数据库⇒排除注记留块5；harvard/cbdb/cbdb_20260919.sqlite3⇒块1既有（import-package/cbdb/ 78表736列）不重映射；china_chron.xls⇒块2既有；china_chron.txt/README_CHINA_CHRON.txt documentation。

## 首个阻塞
MDB 目录读取器工具缺口（5 件表/字段/值枚举待 mdbtools 或批准派生读取器；本轮不装）。