# A 批冻结候选与 B 批证据归并 · lead 记录（30 分钟盒）

- 起表 2026-11-25 18:37:45 UTC，硬停 19:07:45。基线 29d7437a5b781b06671a5f69b36e9badcf870111。茶香授权原文 a-batch-freeze-approval-20261125.txt（sha 8f988a202ca6054e…）；review 记录本次审批（前次 review 存 approval-context.json）。**本轮只生成候选，正式接收/写库另批；不更新 deploy、不改权限服务、零 DB；首批审批 88f4f1ac 不复用 B 批**。lead 收口（a02 起始失败惯例接管披露），a03 独立复核。

## 1. A 批冻结候选（23 规则）
- abatch-frozen-candidate.json = 原 9 规则（7 数据+2 核销）**逐字节深等保留** + 14 条 a1-* NON_TABULAR 新规则（零业务目标、validator none）；**两例外深等不变、零新例外**；inventory_sha256 字段不变；原合同/原清单文件 git diff 空（字节保留）。
- **新合同摘要 fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e**（原 ba8118fb 不动）。
- **32 隔离 dev 重生两例外证据**（writeoff_driver 复用，源件只读 cat R-07）：nul raw 900d98c6/chgis raw 694c101f 互等；证据 contract_sha256 绑新摘要；**派生核销复核 closed 3/exactly3 True/complete_false 保持/derived [unmatched_member]/ready False**。
- **候选未覆盖 7981**（coverage 8004/matched 23/unmatched 7981，uncovered-members.txt 7981 行）；**现行未覆盖仍 7995**（候选未接入）；全量 ready=false。

## 2. B 批口径修正+逐表证据归并（b-batch-table-evidence.json）
- **口径修正**：首版 business_rows_read=0 仅指 2026-10-09 structure 观察轮；CBDB 导入包已生成 **68/78 表源侧值期望**（canary 3 已批准+small 55 draft 326 列/76392 cells+medium 10 draft 156 列/5430382 cells），逐表 expected_rows/expected_sha256/field_count/证据文件 sha 全列。
- **剩余 10 表/235 列单列**（ALTNAME_DATA 12/ASSOC_DATA 42/BIOG_ADDR_DATA 29/BIOG_MAIN 55/BIOG_SOURCE_DATA 10/ENTRY_DATA 28/KIN_DATA 11/POSTED_TO_ADDR_DATA 8/POSTED_TO_OFFICE_DATA 34/POSTING_DATA 6；large 组资源冲突 1GiB>64MiB，不开新大组读取）。
- **36 声明-only 列单列**（SOURCE_DECLARATION_ONLY，PROPOSED_NOT_AUTHORIZED 未升级；observed 700）。
- **3 表 value-canary 最小批核对**：ADMIN_CAT_TYPES（0 行 05afdf0d…）/SOCIAL_INSTITUTION_ADDR（3859 行 2cb8c354…）/SOCIAL_INSTITUTION_ALTNAME_CODES（1 行 4e8d5f51…）；目标候选 cbdb.cbdb__admin_u5f_cat_u5f_types / cbdb__social_u5f_institution_u5f_addr / cbdb__social_u5f_institution_u5f_altname_u5f_codes。
- **关键发现**：value-canary≠types-canary（仅 ALTNAME_CODES 重叠）；**三表含 5 个声明-only 列**（ADMIN_CAT_TYPES 全 4 列+ALTNAME_CODES c_notes）——类型批准缺口；仅 SOCIAL_INSTITUTION_ADDR 全列 observed。
- 缺失批准：声明-only 列升级/目标映射（碰撞检查未完成）/nullability/值合同冻结/新冻结合同/新写库授权原文/Codex 放行。**首个装载器缺口：PG 生产装载器未实现（production_adapter_implemented=false，importer/load.py 仅 staging 原型禁直跑）**。

## 首个剩余缺口
A 批候选正式接收另批；B 批最小批须先闭类型/映射/值合同批准链+实现 PG 装载器。
