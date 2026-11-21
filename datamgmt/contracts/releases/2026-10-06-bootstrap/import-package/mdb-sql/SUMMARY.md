# 第 4/6 块 · MDB 与 SQL 包（SUMMARY）

基线 git ef90b64；inventory sha256=fb5e6b334b898d62… 断言一致；32 宿主 python3 stdlib 流式只读；**SQL 未对任何库执行；本轮未安装依赖；源件只读零触**。

## 三计数
- 核心成员 **7**（MDB 5 + SQL 2；完整链+sha 绑定 inventory 精确对账）
- 已枚举对象 **96** = SQL 表 **34**（全量 CREATE TABLE 解析，异常 0）+ MDB 文件级 **5**（头探针；表/字段枚举=GAP 不臆造）
- 已映射对象（提案）**96**（SQL 表→目标类型提案，PROPOSED_NOT_AUTHORIZED/ready_for_import=false）；MDB 表映射 0（待读取器）

## SQL 面
- china_chron/china_chron.sql：方言 **mysql**（证据 {"mysql_dump_banner": 1}）；表 1；INSERT 语句 677（行估算 677，口径注记在证）；载体 INSERT statements；编码 utf-8-sig（BOM True，替换字符 0（定位行 []））；DROP 0/LOCK 0
- tgaz_bak_2018.sql：方言 **mysql**（证据 {"mysql_dump_banner": 1, "backtick_identifiers": 136, "engine:InnoDB": 32, "charset:utf8": 33, "engine:MyISAM": 1}）；表 33；INSERT 语句 136（行估算 983236，口径注记在证）；载体 INSERT statements；编码 utf-8（BOM False，替换字符 5（定位行 [326]））；DROP 38/LOCK 66

## MDB 面（茶香授权候选镜像，本轮读通）
- 镜像 xiangrugu:runtime-mdbtools-20261120-a Id sha256:74e022830b3b16ab1…（mdbtools=1.0.0+dfsg-1.1；4 deb 离线闭包 --network none 构建；requirements-apt.lock mdbtools 段）；mdb-tables/mdb-schema v1.0.0 预检通过；容器无网络/无凭据/无 socket，快照 :ro，仅本轮隔离目录解包，未进 pg32/pg32b。
- **5/5 读通**（全 JET4）：内部表 **62**（按源 sha 去重 49；逻辑 schema 族 36=v3 12+v4 13+v2 11；V4 两版本字节异但 schema/表/行数输出全同，镜像对分别登记来源）；行数合计 876453；schema/count/export 错误文件全 0 字节；表清单 vs schema 解析对称差空；sha+成员序号全断言==inventory。
- 编码：mdb-schema 头部声明 UTF-8 输出（JET4 目录 UTF-16LE 转换，原始码页语义留值合同）；NULL：mdb-schema 不暴露 NOT NULL⇒导入合同目录级核验；精度：Text(n) 逐字、Numeric 精度/标度目录级待核；二进制：OLE Object/Binary→bytea 提案逐件标记。
- **V4 direct member sha differs from zip-wrapped copies: TWO distinct byte versions registered separately; the two zip-wrapped copies (access_database/ and shapefiles/) share one sha = mirror pair, merge deferred to block 6**
- 读不出表/字段：本轮 **0 项**（若有逐项在 object table_enumeration.unreadable_tables_or_fields）；全量值导出/编码规范化/NULL 语义/二进制字节忠实合同留导入阶段。


## geom 二进制字面量提取（原始字节全程，a02 交付 lead/a03 核验）
- tgaz `geom` 表：**INSERT 1 条/记录 1**（三途径互证：语句扫描/全文件 1432 行交叉扫描/DDL AUTO_INCREMENT=2）；可验证 **1/1**，首个无法验证位置 **null**。
- 两层证据：raw_literal 33B（转义 \0、\\）vs decoded_payload 25B；MySQL 内部格式 4B LE SRID=0 + WKB LE Point (115.31562, 38.94772)，consumed==len 精确闭合；SRID 0⇒CRS unresolved 不推断。
- 零替换字符参与生成、源 SQL 未执行；证据 .mdb-sql-block4-20261120/geom/（sha 入 mapping_doc.geom_extraction）。

## 相关成员处置（exactly-once）
3 内层容器 ZIP structural；Thumbs.db 非数据排除→块5；cbdb sqlite3 块1既有（78表736列）不重映射；china_chron.xls 块2既有；txt/README documentation。

## 缺口与批准面
缺口 **6**（MDB 工具缺口×5；编码损失风险）；全部提案待茶香/Codex 批准；MDB 读取器安装需另批。
