# 两件空间对象隔离装载与全量回读 · lead 记录（30 分钟盒）

- 起表 17:44:47 UTC，硬停 18:14:47。基线 f10bfea（M=2 完好）。茶香明确授权。a02 起始即失败→lead 接管（披露）。
- 实施链：
  1. **PostGIS 能力核**：本地 postgres:18-bookworm 无 PostGIS（extension 目录 grep 空）；pg32b-full:18-pgdg 含 postgis-3.so+postgis.control（docker run --rm --network none 只读镜像核 exit 0）；**实际镜像 Id sha256:d562e43664f996da0e4208b375c00c111a543d996475188d852e9189b2a8cd05==RepoDigest 记录**。以该镜像建全新隔离容器——pg32b 实例/数据未触。
  2. **唯一身份**：容器名 xiangrugu-trial-spatial2-20261123-174708-b6e61aa3（时间戳+uuid 本次生成）；创建后 docker inspect 核实容器 ID d71bca328f57797012b692b9855fce1976ef0ae37dbd33eb40b3ec59ed3f7ca0 与 name；--network none 无宿主端口；**无固定名预删**；清理仅按本次容器 ID（复核后 17:55:30 docker rm -f <ID> 留证 cleanup_execution）。
  3. **固定名强删移除**：trial_text5.py 与 trial_load_m004812.py 启动前 docker rm -f 固定名逻辑同步移除（name collision fail closed；a03 grep 0/0 核）。
  4. 32 快照只读 1884route.zip（sha 39f505c1…）；两件各自核对（SHP 字节同 109d74b1 也分开）：两份 DBF 身份 0b4b86cb/eb9dfed2+cpg sha；逐件 pre-write 门（组件 sha+59 行+deleted 0+blankN 0+对齐+**数值重建==raw**+attr/geom 源侧 sha==期望）全 PASS 才写入。
  5. 已批类型 DDL：text×7（nullable YES，nullable_approved DDL 面）+numeric(19,5)×2（LAT/LONG）+bigint×3（POS_CERT/DATE_CERT/DATE_）+geom geometry(Point,4326) NOT NULL+__src_rownum bigint PK；CREATE EXTENSION postgis→**3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1**。
  6. **原始 X/Y hex EWKB 装载**（01+0x20000001+SRID 4326 LE+原始 X/Y LE 字节，无十进制转换）；COPY exit 0×2。
  7. 全量回读：59×2；meta 全合（data_type+udt_name geometry/int8/numeric+is_nullable）；null 行 0；rownum [1,59]；attr-geom 对齐；dup attr 0/xy 0；**ST_X/Y float8→pack('<d') 逐点原始 LE 字节 match True×2**；geom POINT/2/4326 全合。
  8. **数值列按已核宽度标度重建源字段文本**（numeric(19,5)→Decimal '.5f' rjust 19；bigint(16,0)→int rjust 16）==raw 双向核；复算 attr XRGVALUE-v1==**3519649f663f8a6d/a2ad2d24ff4cae8c**；几何复算 XRGGEOM-v1==**ff7081a0013d721f/3c6067845a7938e8**；**四摘要逐件全等**；合计 118。
  9. SP2_EXIT=0 stderr 0B TRIAL_SPATIAL2_PASS first_difference None。
  10. **方案来源提交==接收前实际回退锚统一**（f10bfea；三锚同一完整锚）；审批表增 trial_spatial2_result 单列（以临时试装为终点）；approval-table ddd15933d2622447/生成器 4a194e1615cecf35 双跑全等。
  11. 回归：五套 141 passed REG_EXIT=0 stderr 0B（src 零改写）。
- a03 R43 一期（四摘要目标+15 列框架+重建方案+隔离核预置）PASS；R43b 二期独立逐表回读（自写 sp2stream.py/sp2dup.sh/sp2meta.sh 零复用 lead 码，META/COL/DUP/SP_EXIT 全 0）：15 列 format_type+is_nullable 逐项==/59×2/null 0/rownum 1|59|59/dup 0/0/对齐 True/attr lpad 宽度标度重建 24634/24214B sha✓/geom ST_AsEWKB hex 通道原始字节直取 1530B sha✓/**四摘要全等 PASS**/field_count 767×2；容器 ID 逐字==TE/镜像 Id==RepoDigest/NetworkMode none/Ports 空/PGDATA 新匿名卷/postmaster.pid mtime 17:47:12Z 盒起后全新；固定名强删 grep 0/0；方案 f10bfea 4/4 token/AT ddd15933/生成器双跑全等；范围 rollup+src diff 空/M=2。诊断披露：a03 三轮 SP_EXIT=1 系 SQL 引号转义面（f-string 内嵌引号与%优先级），改拼接法一次通过，非交付缺陷。
- cleanup 时机沿 R42 补正策略：保留至复核完成后按 ID 即刻销毁（a03 观察容器仍 Up 系复核窗口，预期）。
- 边界：pg32/pg32b/deploy/正式落盘不在本轮；rollup 19 件不动；原 inventory/五块不动；M=2 未触；候选生产名未批（显式临时表名）。
- 三态区分：**试装通过**（本盒，以临时试装为终点）≠**正式合同接入**≠**生产装载授权**。
- 首个剩余缺口：promotion 步骤 1「32 受控接收转正」。
