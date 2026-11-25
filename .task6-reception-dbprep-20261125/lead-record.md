# 装载器受控接收与目标库准备 · lead 记录（30 分钟盒）

- 起表 2026-11-25 14:58:15 UTC，硬停 15:28:15。来件固定 e1de476a21f11f0dba2720ab2748fa61aaba45d2。授权受控接收+仅在 pg32b:5433 新建 xiangrugu 与批准先决。**首批七表装载另批；本盒不建七业务表/不 COPY/不改镜像/不重启服务**。lead 执行（a02 起始失败惯例接管披露）。

## 1. 受控接收
- deploy 现状：9178 件，pre-manifest sha 474d1113…==R48 接收后清单（期间未动）。变更范围 f546783..e1de476 恰 47 件。
- **R1 恢复快照**：reception-20261125/R1.tgz sha **2935ce3acc90bbe2895a94cc0bf840f711543a3f7248ad74ac14e69a8761fa3e**（10369 条目）；**恢复验证 R1_RESTORE_VERIFY_OK**（解至 /tmp/r1check sha256sum -c 9178 全合后清）。
- 接收：38 认证 clone `git archive e1de476` 直管 32（incoming tar sha c50a767a…）→overlay deploy→post 9225 件（+47，0 删，deploy-only 7079 保留）。**逐件 git blob sha1 绑定：变更 47/47 + 全树 2146/2146，BAD 0**。
- 接收未改现役服务（dev StartedAt/RestartCount 不变）。
- **runbook 校准**：A5 标记四态+恰一行+独立指纹；A6 装载角色仅 SELECT 标记；只读先决检查器用法；F 节实际版本 e1de476+入口 run_production_load+检查器实跑记录。

## 2. 目标库准备（pg32b:5433）
- **5433==pg32b 独立确认**：docker ports 0.0.0.0:5433->5432/tcp；Id 3d93fc7741f6…healthy。
- xiangrugu 存在性查：**count 0 不存在**→准创建。
- 创建：CREATE DATABASE xiangrugu；postgis；harv/chgis；marker 表+**恰一行值=pg32b Id**；xiangrugu_loader NOLOGIN+USAGE public+**仅 SELECT 标记**（SET ROLE 实测可读）。
- pg_database 前后：仅增 xiangrugu；**cbdb/cbdb_reh 未触；pg32 未连**。
- **受控件先决检查**（deploy prereq_check.py，同会话只读）：六查全 True **exit 0**。
- **七业务表 to_regclass 全空（count 0）**；COPY 未执行。

## 3. 边界
ready_for_import=false/7995 保持；M=2 不提交不触碰；镜像/服务未改未重启。

## 首个剩余缺口
首批七表装载授权事件（独立写库批准 approval_class=real+real_authority_ref，绑七目标）另批；其后按校准 runbook 执行。

## a03 复核收口
- **R54 终报 PASS（15:02 UTC 盒内）**：接收 47/47 blob 逐字节+PATHSETS_EQUAL；**R1 独立解包重验 9178/0 mismatch**；先决检查自跑 exit 0+双负例 exit 2；marker 恰一行==独立核实 Id；七业务表 0+库净面（仅 spatial_ref_sys+marker）；loader 角色 NOLOGIN 仅 SELECT；旧库表计数 90/81 只读未动；服务无重启镜像未改；runbook A5/A6/F 逐码一致。
- 本盒无试装容器（目标库准备为批准持久态）；a03 临时件自清在案。
