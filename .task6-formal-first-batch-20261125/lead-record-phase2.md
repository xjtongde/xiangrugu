# 第二阶段·首批七表正式装载 lead 记录（Codex 明确放行，30 分钟盒）

- 起表 2026-11-25 17:48:55 UTC，硬停 18:18:55。固定来件 **4c2eb31ce218404cc3b385b340873f2d3e1baca1**（==分支头==ls-remote）。按茶香既有真实写库授权（审批原文 sha 88f4f1ac…钉死）执行；lead 执行（a02 起始失败惯例接管披露），a03 独立复核。

## 1. 恢复快照先行（生成+验证后才接收）
- deploy 现状 9225 件，pre 聚合 sha e1bc754fda2cccd9…；快照 **deploy-recovery-phase2-20261125-174902.tgz**（96,076,519 B），**sha256 59617d83c6bd583128d99ee3e5539d12d148bcc38ad20a643783180c09a78a73**；解包回读清单 cmp 全等 **RESTORE_VERIFY_OK**。

## 2. 受控接收固定来件
- git archive 4c2eb31 单跳管道（tar sha 8e9070c61eb2423b…）→staging；**件单对 git ls-tree 全等 2175 件**；关键五件 sha 对 git show 全等（contracts 94a1e564/entry/fbl/正式命令/审批原文）；staging 聚合 61574edc3e9e3065…。
- **overlay 接收保全历史证据**：deploy 内 7079 件 docs/superpowers 历史证据不在 git 树（e1de476 git 2146+7079=9225），只覆盖/新增 git 2175 件，不删历史件。接收后 **2175/2175 git 路径 sha 全等 BAD 0**，总 9254 件，post 聚合 45044e2b46fe1d6b…；EXTRA_PRESERVED 7079。phase2-reception.json 在账。

## 3. 最小授权（唯一生产权限变更）
- 5433 外部路径（scram，密码运行时 env 无值传递）：**GRANT USAGE, CREATE ON SCHEMA harv, chgis TO xiangrugu_loader**（xiangrugu 内）GRANT_EXIT=0。
- face 前：harv false,false|chgis false,false|marker true,false|旧库 default×2 → 后：**true,true|true,true|marker true,false（只读保持）|旧库 default×2（原样）**。无其他权限变更。

## 4. --real 正式装载（从已核验 deploy 根，默认受控解析源）
- 命令：`cd /opt/mydocker/xiangrugu/deploy && python3 .task6-formal-first-batch-20261125/formal_first_batch.py --real --port 5433 --instance-id 3d93fc7741f6… --password-container pg32b --approval-ref .task6-formal-first-batch-20261125/real-write-approval-20261125.txt --out …/formal-real-ev.json`
- 前置自动核：审批 sha==88f4f1ac ✓/pg32b Id+映射 ✓/解析绑定 deploy src 46 件 mismatch 0 ✓/probe xiangrugu|5432|172.29.0.2 ✓/同会话 current_user==xiangrugu_loader ✓/标记四态+七表 absent ✓。
- **REAL_EXIT=0，FIRST_BATCH_TRIAL_LOAD_PASS，committed=True，transaction=single，total 47725**。
- 逐表：m008002 2957/m008003 40199（**63 组 74 额外行保留**）/m008004 1033/m004812 29/m006642 3389/m002709 59/m002717 59；七 attr 全等；两空间 **EWKB 5262fe45…×2 全等**+geom/XY/meta 全等；gates 10。

## 5. 提交后 lead 独立回读（新只读连接 5433）
- 计数 **2957|40199|1033|29|3389|59|59**（=47725）；owner DISTINCT==xiangrugu_loader；marker 恰 1 行==pg32b Id 不变；cbdb/cbdb_reh datacl default|default 不变。**无差异，未触发停报条款；未删表/覆盖/重跑。**

## 边界
源件只读；pg32/cbdb/cbdb_reh 零触；镜像/服务不改不重启；ready_for_import=false 全量保持；7995 未覆盖保持；M=2 不提交。a03 全量独立回读进行中。
