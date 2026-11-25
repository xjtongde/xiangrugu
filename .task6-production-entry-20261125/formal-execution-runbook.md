# 首批七项正式执行与回退步骤（候选 runbook，未授权执行）

**正式目标唯一**：`pg32b:5433/xiangrugu`。本 runbook 描述未来经批准后的正式执行；本轮仅隔离测试。

## A. 先决条件（分开授权，非装载器默认动作）
1. 在 pg32b:5433 创建数据库 `xiangrugu`（CREATE DATABASE；另批授权；不得触碰 pg32 与 cbdb/cbdb_reh）。
2. 在 xiangrugu 内 `CREATE EXTENSION postgis`（镜像 pg32b-full:18-pgdg 已含 PostGIS 3）。
3. `CREATE SCHEMA harv; CREATE SCHEMA chgis`。
4. 执行前备份：若 xiangrugu 已有对象，`pg_dump` 全库至受控目录并记 sha（R0 式）。
5. **实例标记（R53 补正规则）**：`public.xrg_instance_marker(instance_id text PRIMARY KEY)` **恰一行**，值=带外独立核实的实例 Id（docker inspect pg32b 全号）。装载器同会话四态核验：缺表→marker_table_missing / 空→marker_empty / 多行→marker_multiple_rows / 错值→marker_value_mismatch，均 BEGIN 前拒。cbdb/cbdb_reh 可见不拒（正向身份证明）。
6. **装载角色仅读取标记**：`xiangrugu_loader`（NOLOGIN）仅 GRANT USAGE ON SCHEMA public + GRANT SELECT ON public.xrg_instance_marker；不授业务表写权限（装载写权限随首批写库批准另授）。
装载器对先决**只核验不代建**：缺 postgis/schema → prerequisite_missing 拒写。
**只读先决检查器**：`.task6-production-entry-20261125/prereq_check.py <container> <dbname> <expected_instance_id>`（exit 0/2，六查：库可连/postgis/schema×2/标记表在/恰一行/值合）。

## B. 批准链（独立于合同评审）
1. 茶香独立**首批写库批准事件**（approval_class=real，real_authority_ref 指向该事件）。
2. 范围合同 production-scope：write_approval 四面 + 正式端点 {host pg32b, port 5433, dbname xiangrugu}；五摘要锚重算绑定（合同 canonical ba8118fb/清单 fb5e6b33/两核销证据/七目标身份）。
3. 全量 ready_for_import=false 与 7995 未覆盖保持——首批批准不翻转全量门。

## C. 执行（同一会话）
1. 连接 pg32b:5433/xiangrugu（psql -h 192.168.3.32 -p 5433 -U <user> -d xiangrugu）。
2. `run_production_load`：写批准门→摘要重算门→**同一 DDL 会话内**核验 current_database()/port/inet_server_addr/server_version/postmaster_start/库面（cbdb/pg32b 可见即拒）→先决核验→七目标 to_regclass 全空（已存在即拒，绝不覆盖）。
3. 单事务：BEGIN→七表 DDL（无 IF NOT EXISTS）+COPY→事务内全量回读（47725 行/列元/七 attr+两 geom 摘要/63 组 74 额外/rownum 序）→全合 COMMIT，否则 ROLLBACK。
4. 提交后独立回读复核（另会话）+机器可读证据落 Gitea。

## D. 回退
- **事务内失败**：自动 ROLLBACK，零残留（DDL 同事务回滚），可直接干净重试（重跑全门）。
- **提交后回退**（另批授权）：经 Id/名核实的七表 `DROP TABLE harv.<t>…; DROP TABLE chgis.<t>…`（恰七张，不触他物）；或 restore 执行前 pg_dump。回退后核验 to_regclass 全空+库面不变。
- 任何阶段不修改源件、不触 pg32/cbdb/cbdb_reh、不改镜像服务。

## E. 本轮隔离测试映射
临时唯一名容器（--network none）POSTGRES_DB=xiangrugu，先决预建（A2/A3 等价），test 审批+test 端点声明；注入回读失败证整批回滚零残留干净重试；反例证错库/错端口/缺审批/漂移/目标已存在/先决缺失均拒写。

## F. 实际运行版本与入口记录（2026-11-25 受控接收盒）
- **接收版本**：e1de476a21f11f0dba2720ab2748fa61aaba45d2（deploy 全树 2146/2146 git blob 逐字节绑定，变更 47/47）。
- **正式入口**：`xiangrugu_datamgmt.production_entry.run_production_load(session, scope, contract, payloads, expected, artifacts, contract_parse_fn)`（单次正式解析驱动；证据恰 NUL+CHGIS；标记四态；同会话身份）。
- **先决检查器实际运行**：deploy 受控件 `.task6-production-entry-20261125/prereq_check.py pg32b xiangrugu <pg32b Id>` → 六查全 True exit 0（2026-11-25 14:59 UTC）。
- **目标库准备已执行**（本盒授权）：xiangrugu 新建 + PostGIS + harv/chgis + marker 恰一行（值=pg32b Id 3d93fc7741f6…）+ xiangrugu_loader 只读标记。**七业务表未建、COPY 未执行**——首批装载另批。
