# 首批七对象合同结构扩展 · lead 记录（30 分钟盒）

- 起表 18:18:26 UTC，硬停 18:48:26。基线 450d68dd86a8ad594ecf13ad3e6d3f007f9b9c7a。授权面=DSH 候选分支合同模型/发布 schema/测试/证据；构建测试只在 32 隔离环境。lead 收口，a03 独立复核。

## 实施
1. **contracts.py 最小扩展（+117 行）**：
   - `ColumnMapping`：ordinal（一基）/source_column/target_column/pg_type（正则 `text|bigint|numeric(p,s)`）/nullable/source_width_bytes/source_decimals；numeric 宽度标度必须==声明精度标度（矛盾拒）；非 numeric 禁非零 decimals。
   - `DerivedRownum`：`__src_rownum`/bigint/nullable False/one_based_physical_source_row 全 Literal 固定语义（偏离即解析拒）。
   - `DuplicateReconciliation`：键=值列全集排除 __src_rownum；expected_groups/expected_extra_rows/count_includes_duplicates=True；算术矛盾拒（0 组禁非 0 超出；每组至少 1 超出）。
   - `GeometryExpectation`：Point/2D/srid≥1/XRGGEOM-v1/expected_sha256 Digest/coordinate_storage=preserve_original_ieee754_xy_no_swap_or_transform 全固定或受约束。
   - `ObjectTarget` 四新字段**全可选（None 默认）→既有合同按原规则解析不变**；列映射一致性 model_validator（ordinal 连续自 1/源列与目标列各自唯一/rownum 碰撞拒）。
   - **`validate_first_batch_seven` 单列校验**（独立于通用解析）：必须 draft 未冻结/恰七 rule（m002709/m002717/m004812/m006642/m008002/m008003/m008004）/IMPORT/单 target/columns+derived_rownum+duplicate_reconciliation 必填且列非空/expected_count+sha 必填/重复口径不超 expected_count/空间必带几何且 SRID==已批 4326/文本禁带几何。**缺字段或矛盾→ContractError 拒绝**。
2. **发布 schema 再生**：容器内 `contract_schema()`（model_json_schema）→ config/contract.schema.json（15276B，sha b8c4888836ead52b…，indent=2/sort_keys/尾 NL）；`test_published_schema_matches_runtime_model` 通过（schema==运行模型）。
3. **未冻结七对象候选**（build_candidate.py stdlib 构造，预检待批表→合同文档）：
   - candidate-contract.json：status draft/review None/release_id 2026-11-23-first-batch-seven-candidate/inventory_sha256 fb5e6b33…（原清单绑定）。
   - 文本五件：selector=源文件路径；expected=源 raw sha+size；columns 自 value_columns（column_key→target_name/text/nullable False）；encodings 逐列 codec（m008002/m008003 utf-8-sig，余 utf-8）；dup m008003 **63 组/74 超出**，余 0/0。
   - 空间两件：**规则 expected 选各自 DBF 成员**（0b4b86cb…/eb9dfed2…@16937B，selector zip+成员 chain+物理 ordinal）→各自来源身份入合同；columns 自 spatial-attributes-approved（original_name→target_name/text|numeric(19,5)|bigint/nullable_approved/宽 19 标 5、宽 16 标 0）；geometry Point/2/4326/XRGGEOM-v1 sha ff7081a0…/3c606784…/preserve。
   - **candidate-validation-report.json：total_expected_rows 47725==47607+118 ✓；七项 all_match True**（名称/映射/行数/attr sha==已批期望==试装回读/geom sha==源侧/DBF 身份/重复口径逐项对账预检待批表）。
4. **测试**（tests/unit/test_contract_extension.py，19 例）：既有 fixture 原样解析（新字段 None）/schema==模型/候选正例（47725/63/74/几何/身份互异）/16 反例全拒（三缺字段/空间缺几何/文本带几何/SRID 4327/frozen/缺 rule/重复超 count/ordinal 断序/目标重名/numeric 宽度矛盾/重复算术矛盾/rownum nullable 偏离/维数 3/空列）。
5. **32 隔离运行**（xiangrugu-dev 容器 /tmp/ce 全新树；PYTHONPATH 前置新 src——容器 editable 安装指向 /workspace 旧包，首跑 ImportError 后修正；tar 补 datamgmt/contracts 测试 ROOT 依赖；roots.yaml 宿主路径配置不入测试树沿 r5 配方）：
   - **六套回归 R6_EXIT=0 stderr 0B：160 passed**（141 既有五套+19 新）r6.out 在证据目录。
   - 全量 tests/unit：158 failed/1228 passed/8 skipped——失败系环境性（scratch_path 等宿主路径依赖）；**同环境基线对照**（基线 contracts.py+schema、删新测试）失败集 diff 判定见补记。
6. 边界：不接收 deploy/不切服务/不冻结合同/不写库；源件只读；工作树保全（M=2 未触）；rollup/原 inventory/五块零改写。

## 交付差异清单
- datamgmt/src/xiangrugu_datamgmt/contracts.py（+117）
- datamgmt/config/contract.schema.json（+229，再生）
- datamgmt/tests/unit/test_contract_extension.py（新增 19 例）
- .task6-contract-extension-20261123/（build_candidate.py/candidate-contract.json/candidate-validation-report.json/r6.out/lead-record.md/a03-cross-evidence.txt）

## 通过后动作
提交茶香审批首批七项正式名称与映射（候选已备，未冻结）。
## 基线对照补记（环境性失败证明）
- 同环境（/tmp/ceb，基线 450d68d contracts.py+schema，删新测试）全量：**BASE_FULL_EXIT=1，158 failed/1209 passed/8 skipped**。
- 扩展侧全量：158 failed/1228 passed/8 skipped。**FAILED 集合排序 diff 空（FAILURE_SETS_IDENTICAL）**——158 失败全部基线既有环境性（scratch_path 宿主路径依赖等），扩展零回归；通过数 1209→1228 恰+19 新测试。
- 官方回归口径=六套 R6_EXIT=0 stderr 0B 160 passed（沿 r5 配方）。
