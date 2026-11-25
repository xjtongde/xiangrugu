# 首批七项正式执行与回退步骤（候选 runbook，未授权执行）

**正式目标唯一**：`pg32b:5433/xiangrugu`。本 runbook 描述未来经批准后的正式执行；本轮仅隔离测试。

## A. 先决条件（分开授权，非装载器默认动作）
1. 在 pg32b:5433 创建数据库 `xiangrugu`（CREATE DATABASE；另批授权；不得触碰 pg32 与 cbdb/cbdb_reh）。
2. 在 xiangrugu 内 `CREATE EXTENSION postgis`（镜像 pg32b-full:18-pgdg 已含 PostGIS 3）。
3. `CREATE SCHEMA harv; CREATE SCHEMA chgis`。
4. 执行前备份：若 xiangrugu 已有对象，`pg_dump` 全库至受控目录并记 sha（R0 式）。
装载器对先决**只核验不代建**：缺 postgis/schema → prerequisite_missing 拒写。

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
