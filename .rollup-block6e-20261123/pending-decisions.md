# 导入包合同草案 · 待审批决定表（lead 汇总，DRAFT_NOT_APPROVED）

基线 f54dd96。每项含：决定内容/具体影响/证据引用/关闭方式。所有决定权属茶香（Codex 独立验收），DSH 不预决。

## A · 包冻结级（不批则合同不能冻结）
| # | 决定 | 具体影响 | 证据 | 关闭方式 |
|---|---|---|---|---|
| A1 | NUL 126 兼容解析合同 | SHA256SUMS-b2 严格解析报 1 行格式错误；不批则含该账的核验流程无法机器闭合 | roots.yaml format_anomaly（固定摘要 900d98c6…）；historical-blockers ② | 茶香批准固定摘要下兼容解析合同，冻结入合同版本 |
| A2 | manifest-draft 整体批准 | 8004 成员四分类+1293 对象+1311 引用+产物 sha 成为装载基线 | manifest-draft.json（本盒） | 审批+git 锚冻结 |
| A3 | 命名草案整体批准 | 1208 候选名+39 统一名+schema_draft chgis/harv 二分成为目标名终态；83 既有+2 批准保留 | naming-draft b963ed2f；naming-scan 2e06c99e | 逐面批准或改名规则裁定 |
| A4 | 装载器合同（四面） | tabular/spatial/mdb/raster 读取与 PG 装载方法未批则任何批不可执行 | loader_contract_undecided 43；五块 read/load_method | 合同文本批准 |

## B · 镜像与配准级（影响目标表数与存储形态）
| # | 决定 | 具体影响 | 证据 | 关闭方式 |
|---|---|---|---|---|
| B1 | 孪生两案：共享存储认可+各建表或合一 | 合一则减 1 目标表（逻辑合并单列节给出减表名+逐来源追溯）；各建表则 2 表共享存储 | mirror-draft structured_case_group（两案/五对/十记录，内层 ZIP sha 69b5119f…一致） | 茶香裁定 |
| B2 | 377 同字节组主副本通则 | 共享存储字节+保留来源与逻辑对象为默认；主副本选择影响落盘形态 | mirror-draft 379 byte_identical 组 | 通则批准 |
| B3 | V4 mixed 版本对取舍 | 直接件 a2cc4039 vs 包裹件 04be983d 分立保留为默认；取舍影响 13 组×3 副本目标名 | mirror-draft v4_mdb；naming-draft 39 统一行 | 裁定 |
| B4 | Peking tfw 关联确认 | 六参数换算与内部 GT 全等已证；升级正式绑定或维持 casefold；**配准默认沿用现有 GT** | affine_reconciliation_this_box（six_item_identical=true） | 确认/维持裁定 |
| B5 | pdb2 配准取舍 | 三份 exact-stem tifw 本地绑定采用与否；V4 [159,6] UNRESOLVED_PENDING 处理（无 GT 无 wf） | mirror-draft pdb2 per_copy_evidence（wf sha 2904e190…） | 逐绑定裁定 |
| B6 | 批准 2 件候选名核准 | ca1884route_przh_1251/utf8+chgis schema 最终核准（原批准范围不动） | naming-draft approved_spatial；.shp ord[6]/[14] sha 109d74b1… | 核准 |
| B7 | LOCAL_CS 非 EPSG CRS 政策 | 影响空间装载 SRID 赋值 | pending crs_local_cs_non_epsg | 政策裁定 |

## C · 装载阻断级（不关闭则对应批不可装载）
| # | 决定/事件 | 具体影响 | 证据 | 关闭方式 |
|---|---|---|---|---|
| C1 | CBDB 10 表/235 列值验证授权 | 68/78 覆盖→78/78；CBDB ready_for_import=False 解除前置 | TODO L19/L54；cbdb 交付 | 授权+独立验证器执行+机器证据 |
| C2 | tabular 170 提案批准 | 170 对象入批 A；**789 系历史口径**（类目选择面 txt751+csv7+ods4+xlsx13+xls14），当前账成员处置{174,620,846}与提案{5,170}分记 | load-blockers 789 纠正节；tabular class_counts | 逐批批准 |
| C3 | spatial 899 提案+SRID 政策 | 899 对象入批 B | unapproved_mappings_spatial | 批准 |
| C4 | MDB/SQL 96 提案+值与 geom 合同 | 96 对象入批 C | unapproved_mappings_mdb | 批准+合同 |
| C5 | raster 43 装载合同+NoData 113 | 43 对象入批 D | loader_contract 43/NoData 113 | 合同+政策 |
| C6 | checksum_deferred 17 补跑授权 | 17 件源 sha 核验闭合 | load-blockers 逐件清单 | 授权+17/17 匹配或差异裁定 |
| C7 | WMF 12 读取工具 | 工具缺口关闭前 12 件不入装载批 | wmf_reader_tool_gap | 工具合同或豁免裁定 |
| C8 | v5 缺 DBF 1 | 源事实带账；装载形态裁定（仅 SHP 或补 DBF 来源） | v5_missing_dbf | 裁定 |

## D · 说明级（不阻断，带账即可）
- inventory 历史 issues 3：已裁定（EXCLUDED_BY_DECISION_2026-10-02/FORMAT_ANOMALY 引 A1/ASSOCIATED_BY_SHA_PATH_MISMATCH），原账 verbatim+complete=false 保留。
- PAGGQS 排除：决定引文+备份原件全 sha 5207eace…b9a7f 回溯证据在案，无需新决定（除非茶香推翻 2026-10-02 令）。
- 32 正式落盘/目标库创建/数据库写入：**另行授权**（拟案路径在 manifest-draft，PROPOSED_NOT_LANDED）。