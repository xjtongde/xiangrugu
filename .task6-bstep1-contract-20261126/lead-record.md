# B 批单表合同待批稿 + A 批账迁移方案 · lead 记录（30 分钟盒）

- 起表 2026-11-26T14:07:03Z；固定基线 `93964182c04f1edf94c94859f611728c68997eee`（本机 ls-remote 独立核对 == 本地 HEAD）。
- **本轮范围**：只出 B 批待批稿与 A 批迁移方案；**不冻结新合同、不重跑试装、不更新 deploy、不改权限或服务、不写数据库**。
- 复用：R62 隔离试装记录（`trial-pass.json`/`b-trial-record.json` 为同目录快照，原件在 `.task6-bbatch-addr-trial-20261125/`）、已批期望 `sqlite-value-canary.approved.json`、R61 冻结候选、正式清单、现行处置账、R59 三分类账。
- lead 执行收口；a03 独立复核待接。

## 流程披露
- 首次 `ssh 32`（`root@192.168.3.32` 直连形式）报 `Host key verification failed`；改用 `~/.ssh/config` 的 `32` 别名（独立 IdentityFile + known_hosts）后正常，全程只用该别名。属调用形式问题，非环境异常。
- 生成器开发期修正 5 处（均由断言/异常抓出，非静默改结论）：
  1. `types_appr` 键名 `objects`→`tables`；
  2. `trial_pass["comparison"]["comparison_equal"]` 实际键为 `result`；
  3. 合同模型 `inventory_sha256` 为必填，补入（值现取现用 `fb5e6b33…`）；
  4. **NULL 数比较缺陷**：trial-pass 的 `null_counts` 键为**目标列名**，源探针为**源列名**，直接 dict 相等必为假；改为按「源列→目标列」映射对齐后逐列比较，结果 True。
  5. **A 批三分类归属纠正**：初版误设「16 条 NON_TABULAR 全部迁出 7995」，断言抓到 7913≠7981；现取现用 R59 成员身份后确认 —— **a1-* 14 条 = 12 个空间伴生件 + 2 个待裁定成员（m004860/m007903）**，另 **r-* 2 条账本不在 R59 的 7995 分类内**。

## B. 单表合同待批稿（SOCIAL_INSTITUTION_ADDR）

**源侧现取现用（32 只读，`mode=ro&immutable=1`）**
- 源件 sha256 `bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400` / 586485760 B（`sha256sum` 实测，与已批期望一致）。
- 表行数 **3859**；DDL 摘要 `5c207e94c4f09a8e4fc22bf893e5a14b2fd1c7553854a29a40ef47b45d56ec6e`。
- 复合 PK 六列（源序）：`c_inst_addr_id, c_inst_addr_type_code, c_inst_code, c_inst_name_code, inst_xcoord, inst_ycoord`；实测 `pk_distinct == rows == 3859`（**PK 唯一性在源端成立**）。
- 索引：仅 1 个 `sqlite_autoindex_SOCIAL_INSTITUTION_ADDR_1`（`origin=pk`）；**无独立二级索引、无 FK**。
- DEFAULT：仅 **5 列**（begin_year/end_year/c_source/c_pages/c_notes）为 `DEFAULT NULL`；无其它默认值。
- **NOT NULL 6 列**（`c_inst_name_code, c_inst_code, c_inst_addr_type_code, c_inst_addr_id, inst_xcoord, inst_ycoord`），实测 NULL 数全 0；可空 5 列。
- NULL 实测：begin_year 3005 / end_year 3857 / c_source 219 / c_pages 334 / c_notes 752。

**交付件**
- `b-approval-table.json`：11 列逐列（源列/目标候选名/类型/列序/可空性/源 PK 位次/实测 NULL 数/批准状态）+ 六项约束处置（PK/UNIQUE/INDEX/FK/DEFAULT/NOT NULL）+ 已批/待裁定分列 + R62 交叉核。
- `b-contract-draft.json`：可冻结合同草案（正式 `ReleaseContract` 形态）。
- `model-gaps.json` + `model-gap-evidence.txt`：模型不可表达点（全部实证）。

**与源侧期望/R62 回读一致性（通过条件 1）**
- 3859 行、重复 0、42449 字段、双向 sha `2cb8c354…07579`、schema `1f88cd80…`：与已批期望及 R62 `trial-pass` 逐项一致。
- **11 列 NULL 数按映射对齐后全等 True**（前述修正 4）。
- R62 试装为**复用**，本盒未重跑（遵守不重跑约束）。

**模型不可表达（具体字段）** —— 用正式模型在 dev 容器实跑 pydantic 校验取证：
| ID | 缺口 | 位置 | 实证 | 影响 |
|---|---|---|---|---|
| G1 | `double precision` 无法表达（本批唯一硬阻塞） | `contracts.ColumnMapping.pg_type` 正则 `^(text\|bigint\|numeric\(…\))$` | `string_pattern_mismatch` | **2 列（inst_xcoord/inst_ycoord）无法写入合同** |
| G2 | 无约束字段 | `contracts.ObjectTarget` | `extra_forbidden`（primary_key/unique_constraints/indexes） | 六项约束只能落在本盒审批表 |
| G3 | 无 default 字段 | `contracts.ColumnMapping` | `extra_forbidden`（default_value） | 5 列 DEFAULT NULL 无法入合同（影响低） |
| G6 | 列序数必须 1..N 连续 | `ObjectTarget.extended_mapping_consistency` | 剔除两列后报 `Column ordinals must be contiguous` | 降级路径会丢失源列序证据 |
| G4/G5 | targets 仅 IMPORT 允许 / 表名 ≤63 | `DispositionRule` / `ObjectTarget.table` | 本表为 IMPORT，不受阻 | 无当前影响，登记在案 |

- 校验结论：`contract-model-validation.json` —— 全量草案**全部叶子错误均为两列 pg_type 模式不匹配**（另有其级联触发的 `rules: Tuple should have at least 1 item` 次级报错，根因同为 G1，无第二个独立硬阻塞）；剔除两坐标列并按 1..9 重排序数后 **VALIDATED_OK**（9 列，canonical `0ee3717d…`）。即 **G1 是本批唯一的硬阻塞**。

## A. 正式处置账迁移方案（PLAN_ONLY_NOT_EXECUTED）

**授权候选复核**
- 用正式模型重算 `abatch-frozen-candidate.json` → canonical **`fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e`**，与授权值**逐字相等**；23 规则（7 IMPORT + 14 a1-* + 2 r-*）、2 例外、`inventory_sha256 fb5e6b33…`。

**对账预览（通过条件 2）**
- `DispositionLedger.evaluate(inventory, 候选)` 实跑：records **8004**，unmatched **7981**，multiple **0**；**有规则成员 23/23 全部 explained=True**。
  - 措辞澄清（a03 复核提出）：`coverage().unexplained` = 全部 explained=False 记录（含无规则成员），故实为 **7981**，等于未覆盖面本身；本盒此前写的 `unexplained: 0` 是「有规则成员中未解释数」的自定义口径，已在 `a-migration-plan.json` 的 `unexplained_semantics` 中分列澄清。
- **23 + 7981 = 8004 ✅**
- **16 条 NON_TABULAR 逐条反查：每条恰命中 1 个成员、互斥；23/23 规则 exclusive_single_owner，non_exclusive 0 → 无重复归属。**

**三分类归属（精确口径，已纠正初版误判）**
- R59 7995 = 已有处置提案 98（structural 86 + **空间伴生件 12**）+ 待裁定 2 + 待补证 7895。
- 本次 16 条 NON_TABULAR 构成：
  - **a1-* 14 条 = 12 空间伴生件 + 2 待裁定（m004860、m007903）** ← 这 14 个成员从「未正式覆盖」转「已覆盖」；
  - **r-* 2 条（SHA256SUMS-b2、harvard/chgis/SHA256SUMS.txt）不在 R59 的 7995 分类内**，原本已在正式账具名，**不影响 7995→7981 的差值**。
- 校验：7995 − 14 = 7981 ✅；迁移后三分类合计 = 86 + 7895 + 0 = 7981 ✅。

**迁移文件清单（下一批执行时）**
| 文件 | 动作 | 核验 |
|---|---|---|
| `disposition-ledger-<new>.json`（新增） | 写新账，**不覆盖**现行账 | contract_sha==fa28a878 / inventory_sha==fb5e6b33 / records==8004 / unmatched==7981 |
| 正式合同（deploy + 仓内） | 以候选替换 `ba8118fb` | `ReleaseContract.sha256==fa28a878…`；原 9 规则 deep-equal；两例外不变 |
| `datamgmt/docs/IMPORT-PACKAGE-TODO.md` | 新增迁移盒记录行 | 实际提交号 + 证据路径 |
| `docs/log.md` | R-05 记一行 | 单行 ≤300 字 |

**不可改动面（已逐字节核验未被本盒触碰）**
- `inventory.json` sha `fb5e6b33…` == git blob ✅
- 现行 `disposition-ledger-after-selector-fix.json` sha `0b093077…` == git blob ✅
- 首批七表规则、两条例外、首批 scope 7995 门：均未改（本盒零写入）。

**迁移后遗留 issue**：`exception_not_implemented`（两例外需在新合同下重跑取证）/ `incomplete_inventory`（原清点恒门保持）/ `unmatched_member 7981`。`full_ready_for_import=false` 保持。

## 服务与边界
- pg32b `3d93fc77…` R=0 StartedAt `2026-11-26T13:53:41Z`；xiangrugu-dev `29795c60…` R=0；pg32 同——盒前盒后一致，**未重启未连接写**。
- 无残留 `xiangrugu-trial*` 容器；deploy 未新增修改；旧库 cbdb/cbdb_reh 权限未动；源件只读（仅 `sha256sum` + `mode=ro&immutable=1` 读取）。
- 工作树：M=2 两文件为既有保留态（未提交），本盒仅新增 `.task6-bstep1-contract-20261126/`。

## 双跑确定性
- B 构建器 `b-double-run.sha`、A 构建器 `a-double-run.sha`：各两次运行**产物 sha 逐字相等**；且两者均已改为**从仓内输入**读取并复现同一结果。

## 首个剩余缺口
- **B 批**：目标是 G1 —— 合同模型 `pg_type` 不支持 `double precision`，2 个坐标列无法入合同；**G2** 缺约束字段。须另批授权做模型扩展后才能冻结包含完整 11 列的合同。此外仍缺：目标名批准（碰撞检查）、值合同冻结、新写库授权原文、Codex 放行、**PG 生产装载器未实现**。
- **A 批**：方案与对账预览已 PASS，但**正式账迁移本身未执行**（本盒只出方案）；执行需另批授权，且需接受 `exception_not_implemented` 在冻结后重跑取证。
## a03 独立复核收口（R63 PASS）
- **总判定 PASS，8/8 项通过，无翻案项**。a03 零复用：源探针、模型校验、账本复算、反查与归属全部用正式模型现跑现算。
- 独立复现：源 sha/586485760B/3859/DDL 5c207e94/PK 六列序/pk_distinct/单 origin=pk 索引/FK 空/NULL 分布全等；审批表 11 列 0 处不符；**null_counts 键陷阱专项**按其自身映射对齐后 11/11 全等，确认 lead 的 `true` 成立；候选 canonical `fa28a878` 复现；`evaluate` 实跑 8004=23+7981、multiple=0；23/23 规则互斥反查（a1-* 14/14）；**a1-* 14 条映射出的成员集合恰等于 R59「空间伴生件 12 ∪ 待裁定 2」（集合相等）**，r-* 2 账本不在 7995 桶内 → 7995−14=7981、86+7895=7981 精确闭合。
- 两条**非阻塞精度建议**已采纳并修正：①`coverage().unexplained` 实为 7981（非 0），已分列澄清；②全量草案除两列 pg_type 外还有级联的 rules_too_short 次级报错，根因同为 G1，已改写为"无第二个独立硬阻塞"。
- 边界：a03 全程只读、零写库、零重跑试装、临时件已删并实证 GONE，仓库状态与开工一致。

## 事故披露：M=2 误提交与纠偏（本盒，lead 责任）
- **经过**：收口提交时误用 `git commit -aq`（`-a` 自动暂存全部已跟踪改动），把「M=2 永不提交」的两文件
  `xrg_p01_entry.py`（668900d4…）与 `rehearsal-evidence.json`（49205dc2…）一并提交进 **0a46980** 并推送 Gitea。
  盒交付提交 **0435e52 本身是干净的**（不含 M=2）。
- **发现**：推送后复核 `git status` 发现 M=2 从工作树改动中消失，随即核对 `git show --stat 0a46980` 确认误入。
- **处置（茶香指示：选 1，不重写历史）**：以 0a46980 为当前头追加纠偏提交，**未使用 -a / amend / reset / force push**：
  - **6181519**：仅把两文件 index 条目恢复为 0435e52 的 blob，**工作树原字节保留不动**；
  - **37dea68**：修正 6181519 因 `--cacheinfo 100644` 误写的文件模式，恢复 `xrg_p01_entry.py` 的 **100755**。
- **纠偏后的核验**：
  - 远端头 `37dea68` 树中两文件的 (mode, blob) 与基线 `9396418` **逐位相同**：
    `100755 115bd0c5…` / `100644 104b2e8b…`；
  - 工作树恢复为**恰好两条未暂存 M=2**，暂存区为空，工作树摘要与纠偏前逐字节一致（668900d4…/49205dc2…），`git diff --summary` 无 mode 变化；
  - 0a46980 中另外 4 个交付文件的更新（a-double-run.sha / a-migration-plan.json / build_a_migration.py / lead-record.md）保留。
- **遗留**：**0a46980 仍在提交链历史中**（按 R-10 不重写历史）。按项目既有惯例（参照 84386df 历史误提交"当前追踪 0，历史对象仍在祖先提交，不重写"的处置），候茶香/Codex 专项裁定是否另行处理。
- **教训**：收口/纠偏类提交一律显式 `git add <path>` 或 `update-index`，**禁用 `commit -a`**；`update-index --cacheinfo` 必须带正确 mode（从 `git ls-tree` 取，勿硬写 100644）。

## 本轮提交链
| 提交 | 内容 | 状态 |
|---|---|---|
| `9396418` | 基线 | — |
| `0435e52` | 盒交付（18 件，**不含 M=2**） | 已推 |
| `0a46980` | 收口（采纳 a03 两条精度建议）+ **误含 M=2** | 已推（留痕） |
| `6181519` | 纠偏：index 回退两文件 | 已推 |
| `37dea68` | 纠偏补正：恢复 100755 模式 | 已推 / **远端头** |
