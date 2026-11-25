# 首批七表验收入账记录（第 6/6 块后续盒）

- 基线 c28b9bbad7fca920f806f78ea73bd2282cb47a7a；起表 2026-11-25 18:10:22 UTC。**本盒零 DB 连接零写、不改 deploy/权限/服务**；ready_for_import=false 全量保持。

## 入账事实（已 COMMIT + Codex 独立只读验收）
- **装载**：2026-11-25 17:50:28 UTC，pg32b:5433/xiangrugu，单事务 **COMMITTED**（REAL_EXIT=0），总 **47725** 行；审批原文 sha 88f4f1acebbf0353…钉死验证；解析绑定受控 deploy src 46 件 mismatch 0。
- **Codex 独立只读验收**：a03 R58 终报 PASS（17:53 UTC）——快照 9225 件恢复验证 mismatch 0/接收 2175==git ls-tree/授权 face/全量回读 47725/七 attr/两 EWKB 5262fe452df361ff×2/63·74/owner/marker 不变/四不动。Codex 放行与验收经茶香转发在案（第 6/6 块第二阶段指令原文）。

## 七表（合同完整表名，逐表 COMMIT 结果）
| 合同 rule | 完整表名 | 行数 | attr | EWKB/geom | 重复 |
|---|---|---|---|---|---|
| m008002 | harv.harvard_u2f_tab__academy_u5f_data_u2e_tab | 2957 | ✓ | — | 0/0 |
| m008003 | harv.harvard_u2f_tab__index_u5f_of_u5f_the_u5f_complete_u5__300c7027 | 40199 | ✓ | — | **63 组/74 额外行保留** |
| m008004 | harv.harvard_u2f_tab__writings_u20_of_u20_the_u20_19c_u20___7866bf2d | 1033 | ✓ | — | 0/0 |
| m004812 | harv.harvard_u2d_full_u2f_doi_u5f_10_u5f_7910_u2f_dvn_u2f___1334a175 | 29 | ✓ | — | 0/0 |
| m006642 | chgis.harvard_u2d_full_u2f_doi_u5f_10_u5f_7910_u2f_dvn_u2f___9784b044 | 3389 | ✓ | — | 0/0 |
| m002709 | chgis.ca1884route_przh_1251 | 59 | ✓ | EWKB ✓ geom ✓ | 0/0 |
| m002717 | chgis.ca1884route_przh_utf8 | 59 | ✓ | EWKB ✓ geom ✓ | 0/0 |

- owner 全==xiangrugu_loader；marker 恰一行==pg32b Id 3d93fc7741f6…；旧库 cbdb/cbdb_reh ACL 原样。
- 证据：.task6-formal-first-batch-20261125/formal-real-ev.json、lead-record-phase2.md、a03-cross-evidence-phase2.txt；32:/opt/mydocker/xiangrugu/reception-20261125/（快照 sha 59617d83c6bd5831…）。
- Gitea：72143e525298932617c4854c0aef8311c76a3bcf（装载证据）→ c28b9bbad7fca920f806f78ea73bd2282cb47a7a（R58 收口）。

## 身份注记（防误读）
合同 rule_id m002709/m002717 绑定的是汇总账成员 **m002706/m002714（.dbf）**；汇总账 m002709/m002717 为 **.shp 主件**，其几何字节已随首批装载，但账面处置仍属 7995 未覆盖（伴生件待正式绑定）。被覆盖 9 成员=7 数据+2 核销（m000002 SHA256SUMS-b2 NUL/m007977 chgis SHA256SUMS.txt line4）。

## a03 独立复核收口
- **R59 终报 PASS（18:17 UTC 盒内）**：8004/9/7995 独立自算闭合；三分类 98/2/7895 抽样 20+ 件全中（signature 分布逐项全等，ole 17 精确）；两账 diff 4 件去向完整解释；入账事实面与 formal-real-ev 逐行互等；下一批提案与机器账 basis 逐字一致；快照/接收复验承接 R58 互洽；四不动保持。
- 首个缺口：**A 批 14 件（12 伴生+2 待裁定）需茶香裁定落账**；B 批须新冻结合同+新写库授权原文+Codex 放行。
