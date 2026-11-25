# A 批 14 件处置落账与 B 批划界 · lead 记录（30 分钟盒）

- 起表 2026-11-25 18:22:22 UTC，硬停 18:52:22。基线 fe38f3ace463045c743fc208c7d0585c0a0878d5。茶香授权原文存 a-batch-approval-20261125.txt。**只提交候选规则/证据/进度；不冻结新合同、不更新 deploy、不改权限服务、零 DB**。lead 执行收口（a02 起始失败惯例接管披露），a03 独立复核。

## 1. 12 空间伴生件候选登记（非独立装载成员）
- 逐件完整归档链/物理序号/大小/SHA-256/关联目标入 a-batch-candidate-rules.json；**14/14 对 inventory.json 逐件 sha+size 全等**。
- 角色按 approved-spatial-binding-context：cpg=编码声明/prj=CRS/qpj=附加 CRS 候选/shp=主几何/shx=几何索引；README(m002704)/ru.htm(m002711)=溯源文档（business_reading_approved=False，关联两目标）。
- **身份注记**：候选 m002709/m002717=清单 SHP 成员；首批同名合同规则绑 m002706/m002714 DBF（已验收规则保持不变，候选 ID a1-* 唯一无撞）。

## 2. 两条 NON_TABULAR
- **m004860**：仅内层 Thumbs.db 精确链 [KML/CHGIS_v4_1911_KML.zip, V4_1911_KML_metadata/Thumbs.db] 序号 [5,11]，24576B c68ef43f…；原件保留，**不扩展外层 ZIP/其他子件**，不因 OLE 当 XLS。
- **m007903** harvard/SHA256SUMS：溯源账本保留，**附既有 13/13 校验记录**（assertions.yaml ledger=harvard/SHA256SUMS 13 条全 matched，提取入 m007903-checksum-13of13.json 含源文件 sha）。
- 两条零目标表、零新增校验例外。

## 3. 独立对账
- 候选恰 14；**合同 ba8118fb/清单 fb5e6b33 容器正式重算不变**；实际未覆盖仍 **7995**（候选 CANDIDATE_NOT_ADOPTED 未接入）；**接入后预计 7981（8004−23）单列**。

## 4. B 批最小可装载候选（只划界不装载）
- **m007906 cbdb_20260919.sqlite3**（586268672B bde1bb8e…）：**78 已验证表组**（2026-10-09 sqlite-structure+sqlite-types 双证据，catalog/详情/表元数据完整，sqlite 3.40.1）；**business_rows_read=0/values_verified=false/import_approved=false**。
- 源侧期望：结构/类型目录已验，业务值期望未生成未批准。缺失批准：独立值读取器/列编码目标映射/源侧值期望/新冻结合同/新写库授权原文（88f4f1ac 不可复用）/Codex 放行。
- **首个阻断：业务值读取未实施未批准，结构证据不构成装载授权**。m007905 json 伴生件另裁不入清单。

## 首个剩余缺口
候选 14 件接入正式账需新合同冻结授权（本盒不冻结）；B 批首个阻断=CBDB 业务值读取未批准。
