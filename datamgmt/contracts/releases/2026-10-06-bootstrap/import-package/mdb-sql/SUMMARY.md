# 第 4/6 块 · MDB 与 SQL 包（SUMMARY）

基线 git ef90b64；inventory sha256=fb5e6b334b898d62… 断言一致；32 宿主 python3 stdlib 流式只读；**SQL 未对任何库执行；本轮未安装依赖；源件只读零触**。

## 三计数
- 核心成员 **7**（MDB 5 + SQL 2；完整链+sha 绑定 inventory 精确对账）
- 已枚举对象 **39** = SQL 表 **34**（全量 CREATE TABLE 解析，异常 0）+ MDB 文件级 **5**（头探针；表/字段枚举=GAP 不臆造）
- 已映射对象（提案）**34**（SQL 表→目标类型提案，PROPOSED_NOT_AUTHORIZED/ready_for_import=false）；MDB 表映射 0（待读取器）

## SQL 面
- china_chron/china_chron.sql：方言 **mysql**（证据 {"mysql_dump_banner": 1}）；表 1；INSERT 语句 677（行估算 677，口径注记在证）；载体 INSERT statements；编码 utf-8-sig（BOM True，替换字符 0（定位行 []））；DROP 0/LOCK 0
- tgaz_bak_2018.sql：方言 **mysql**（证据 {"mysql_dump_banner": 1, "backtick_identifiers": 136, "engine:InnoDB": 32, "charset:utf8": 33, "engine:MyISAM": 1}）；表 33；INSERT 语句 136（行估算 983236，口径注记在证）；载体 INSERT statements；编码 utf-8（BOM False，替换字符 5（定位行 [326]））；DROP 38/LOCK 66

## MDB 面（工具缺口）
- 5 件头级确证（JET magic/签名/版本字节/页大小版本推导/128 字节 hexdump 逐字），sha 全匹配 inventory。
- **V4 direct member sha differs from zip-wrapped copies: TWO distinct byte versions registered separately; the two zip-wrapped copies (access_database/ and shapefiles/) share one sha = mirror pair, merge deferred to block 6**
- 逐件不可读原因+所需工具（mdbtools=1.0.0+dfsg-1.1 候选提案，本轮不装）+隔离恢复路径在 evidence-gaps。
- 编码/二进制/NULL/精度面：MDB 需目录读取器后逐列断言，本轮不臆测。

## 相关成员处置（exactly-once）
3 内层容器 ZIP structural；Thumbs.db 非数据排除→块5；cbdb sqlite3 块1既有（78表736列）不重映射；china_chron.xls 块2既有；txt/README documentation。

## 缺口与批准面
缺口 **6**（MDB 工具缺口×5；编码损失风险）；全部提案待茶香/Codex 批准；MDB 读取器安装需另批。
