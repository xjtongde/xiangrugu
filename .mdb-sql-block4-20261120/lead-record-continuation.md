# 第 4/6 块续盒 · lead 运行记录（2026-11-21，MDBTools 茶香授权）

基线 8b5846603f865721b900f39100ae875b65222ce4；盒 14:06:30Z–14:36:30Z（30 分钟）。
分工：lead=锁定/构建/预检/解包/MDB 枚举/集成；a02=geom 原始字节提取（**本轮存活完成**）；a03=ROUND 14 独立双面复核。

## 镜像与锁定
- 标签 xiangrugu:runtime-mdbtools-20261120-a（独立标签，别名零触）
- **Id sha256:74e022830b3b16ab18847d43c98d7b2fde042da7ae40a3841febee5c29000399**
- labels revision=8b58466…/mdbtools=1.0.0+dfsg-1.1/purpose=mdb-readonly-inventory
- 锁定：datamgmt/requirements-apt.lock **mdbtools 段 4 deb**（libglib2.0-0=2.74.6-2+deb12u9/libmdb3=1.0.0+dfsg-1.1/libmdbsql3=1.0.0+dfsg-1.1/mdbtools=1.0.0+dfsg-1.1 sha fb95badaff6e4aee…；来源 ftp.us.debian.org bookworm/main amd64）；deb 实物 32 build-candidates/runtime-mdbtools-20261120-a/debs/
- 构建：datamgmt/Dockerfile.mdbtools-candidate，**--network none 离线成功**（闭包完整实证）；基座 python@sha256:4b4c524dc3dc…
- 预检：mdb-tables v1.0.0 / mdb-schema v1.0.0 ✅；全套二进制在位（mdb-count/export/header/json/prop/queries/sql/ver…）
- 纪律：读件容器 --network none、无 DB 凭据、无 Docker socket、快照 :ro、仅本轮隔离目录解包、未进 pg32/pg32b、宿主软件零改、不写库、源件零触。

## 解包与枚举（32:/opt/mydocker/xiangrugu/mdb-verify-20261120/）
extract_mdb.py（本目录）按完整链+成员序号流式解包，sha256 全量断言==inventory：
| case | 链 | ordinals | sha | 表 | 行数 | 错误 |
|---|---|---|---|---|---|---|
| v3_himive | HIMIVE/V3_Data_Archive.zip!access_dbase/v3_chgis_dbase.ZIP!v3_chgis_database.mdb | [76,0] | 68853b49… | 12 | 170479 | 0 |
| v4_direct | PDGOZ0/V4_Data_Archive.zip!access_database/v4_chgis_dbase.mdb | [2] | a2cc4039… | 13 | 198606 | 0 |
| v4_access_zip | 同!access_database/v4_chgis_dbase.zip!v4_chgis_dbase.mdb | [3,0] | 04be983d… | 13 | 198606 | 0 |
| v4_shapefiles_zip | 同!shapefiles/v4_chgis_dbase.zip!v4_chgis_dbase.mdb | [109,0] | 04be983d… | 13 | 198606 | 0 |
| v2_zzkz6u | ZZKZ6U/CHGIS_V2.zip!access_dbase/chgis_v2_database.ZIP!chgis_v2_database.mdb | [0,0] | 4a9bd1bc… | 11 | 110156 | 0 |

**5/5 读通，全 JET4**；内部表 62 实例（按源 sha 去重 49=4 版本；**V4 直接 vs 包裹字节异但 schema/tables/rowcounts 输出全同——lead diff 实证，差异在非 schema 页**；逻辑 schema 族 36）；schema/count/export 错误文件全 0 字节；读不出表/字段 0 项。镜像对分别登记来源，合并留块 6。
证据回仓 .mdb-sql-block4-20261120/mdb/<case>/{tables,schema,rowcounts,ver}.txt+*.err+sample_*.csv+extraction_evidence.json。

## geom 提取（a02 交付，lead/a03 核验）
tgaz_bak_2018.sql 原始字节全程（zipfile 二进制流，sha 4c6db692…==inventory 断言）：**INSERT INTO geom 1 条/记录 1**（三途径互证：语句扫描/全文件 1432 行交叉扫描/DDL AUTO_INCREMENT=2）；CREATE TABLE geom 5 列逐字（id/placename_id/**g geometry NOT NULL**/src enum/updated_on；MyISAM utf8）；raw_literal **33B**（转义 \0、\\）vs decoded_payload **25B** sha cfe2b8d4…；MySQL 内部格式 **4B LE SRID=0 + WKB LE Point (115.31562, 38.94772)**，consumed==len 精确闭合⇒valid；**可验证 1/1，首个无法验证位置 null**；零替换字符参与、SQL 未执行、exit 0/0。证据 .mdb-sql-block4-20261120/geom/{geom_extract.py,geom-extraction.json,deliverable-summary.json}。SRID 0⇒CRS unresolved 不推断。

## 集成（生成器证据驱动）
build_mdb_sql_package.py 增：MDB_EV 装载（mdb_evidence/ 传输件==仓内 .mdb-sql-block4-20261120/mdb/）+parse_mdb_schema（CREATE TABLE [t]/[col] Type(n) 逐字）+MDB_TYPE_MAP 目标提案（Text→varchar(n)/Memo→text/Long Integer→integer/Integer→smallint/Single→real/Double→double precision/Numeric→numeric/DateTime→timestamp/Bit→boolean/OLE Object|Binary→bytea）+62 mdb_table 提案+文件对象 table_enumeration 块+GEOM 引用+缺口 RESOLVED 态。
过程缺陷披露：首跑 f-string 表达式内 `{{}}` 误为含 dict 集合字面量⇒TypeError exit 1/1（run5/6 日志在证），修正 `{}` 后 exit 0/0；distinct 口径首版误标"按内容去重 49"⇒正名"按源 sha 去重"+逻辑 36 注记。
**真双跑 exit 0/0 字节一致（run7-10）；SQL 34 提案 byte-identical 保留（任务要求）；sid 101 唯一**。
终态产物 sha：members 9a859420…（不变）/om **b56889f17f183b0e…**/gaps **a6ed3537db5855e7…**/SUMMARY **e818e3d9d9e106ab…**。
计数：成员 7/枚举 96（SQL34+MDB62）/映射提案 96/缺口 6（5 RESOLVED+1 encoding_loss_risk 含 geom 提取状态注记）。

## 剩余缺口
①MDB 全量值导出/编码规范化（JET4 UTF-16LE→UTF-8 转换语义）/NULL 目录级核验/二进制字节忠实合同——导入阶段；②tgaz geom 导入值合同（提取已验证）；③96 提案批准面；④V4 镜像合并+候选镜像/apt 锁转正——块 6；⑤其余块 3 余留（899 批准/v5 合同/CRS 源级）。