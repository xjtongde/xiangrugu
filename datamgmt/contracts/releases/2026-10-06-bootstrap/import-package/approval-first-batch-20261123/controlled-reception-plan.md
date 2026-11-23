# 首批七对象 · 受控接收方案（草案，未执行）

- 基线版本锚：**19a77184440f604353cde6a1efe7a0611ebad03c**（分支 dsh/p01-real-prep-20261113，Gitea ls-remote 已核）；接收时以经核对的当时分支头为完整版本锚。
- 本方案仅为计划；**受控接收、正式合同冻结、落盘、数据库写入均另行授权**，本轮不执行。

## 1. 接收范围
- 32 受控运行目录 `/opt/mydocker/xiangrugu/deploy` 接收经核对的 Git 版本 8f3d014（含核销评估器 writeoff.py 原清单绑定补正 + 两例外 reader + 审批包）。
- 接收前快照：`deploy` 现状 tar 存档（回退点 R0）；接收仅替换受控目录内容，不触 pg32/pg32b 任何数据库。

## 2. 核销评估器调用入口
```python
from xiangrugu_datamgmt import writeoff
from xiangrugu_datamgmt.inventory import InventoryManifest
from xiangrugu_datamgmt.contracts import ReleaseContract

manifest = InventoryManifest.load_json(inventory_path)   # 原清单 fb5e6b33…，complete=false 保留
contract = ReleaseContract.model_validate(formal_contract_doc)  # 须 frozen+review，绑 fb5e6b33…
raw_ledgers = {"SHA256SUMS-b2": b2_bytes, "harvard/chgis/SHA256SUMS.txt": chgis_bytes}
result = writeoff.run_writeoff(manifest, contract, raw_ledgers)
# result: WRITEOFF_RESULT_DERIVED；closed_issues 三条；run_evidence 全文可取回重算；
# 仅派生核销 incomplete_inventory；unmatched_member 等其余门照常；原清单绝不改。
```
- 签发前四核：固定原清单摘要 fb5e6b33…/合同所绑清单摘要/三条 issue 完整身份+出现次数/审批 frozen+review。
- 正式合同下须**重跑再生两份例外证据**（evidence_regeneration_required=True；fixture 合同证据不可挪用）。

## 3. 验证命令（32 容器 xiangrugu-dev，/tmp 隔离）
```sh
# 单元五套（141 用例）
PYTHONPATH=src python -m pytest tests/unit/test_disposition.py tests/unit/test_contracts.py \
  tests/unit/test_checksum_candidates.py tests/unit/test_checksum_reader.py tests/unit/test_writeoff.py
# 核销面单跑（11 用例）
PYTHONPATH=src:tests/unit python -m pytest tests/unit/test_writeoff.py
# rollup 三跑收敛 + 38/32 全等（19 件）
python3 build_rollup.py   # ×3，stderr 0B，sha256sum 全等
# 审批包确定性双跑
python3 build_approval_package.py   # ×2，approval-table/evidence-list 字节全等
```

## 4. 回退点（恢复接收前的完整版本锚）
- R0：接收前 deploy 快照 tar（sha256 记录）+ **完整版本锚 19a77184440f604353cde6a1efe7a0611ebad03c**（Gitea ls-remote 已核）。
- R1：回退即**恢复接收前完整版本锚**——受控目录整体恢复 R0 快照，或 `git checkout 19a7718 -- .` 全量回到锚版本（不做局部挑拣回退）；分支历史不改写（R-10 禁 reset/clean/stash）。
- **保留已验收的核销保护**：回退后的版本仍含 writeoff.py 原清单绑定补正（ORIGINAL_INVENTORY_SHA256=fb5e6b33… 锁定 + 签发前四核 + 证据全文可取回重算 + 替代清单拒绝用例）；任何回退不得移除这些保护（11 用例回归须仍全过）。
- 任何验证失败：停止接收，恢复 R0 完整锚，记录冲突按 docs/index.md 权威顺序处理。

## 5. 实际跑通的核销调用（本盒留证）
- 32 容器 xiangrugu-dev /tmp/wb：`writeoff.run_writeoff(manifest, contract, raw_ledgers)`（fixture 合同，原清单 fb5e6b33…）→ **WO_CALL_EXIT=0，stderr 0B**。
- 结果：closed_issues 三条完整身份；derived_issue_codes=[unmatched_member]；ready_for_import=false；run_evidence_sha256 nul b74c33847935…/chgis e24ed0f17ebd…。
- 证据：`.task6-spatial-values-20261123/writeoff-call.json`（正式合同下须重跑再生证据，fixture 证据不可挪用）。

## 6. 提交分列
- **代码基线提交**：源侧值证据驱动器 + 证据（.task6-spatial-values-20261123/）——不含审批包文案。
- **审批包提交**：approval-table/evidence-list/接收方案修正 + TODO + 记录——与代码基线分列，便于逐项审批与回退。

## 7. 分账纪律
- 表名批准 / 正式合同冻结 / 装载授权三账独立（approval-table.json ledgers 逐项 false）；**已批映射与待生成值期望分开**（approved_mapping vs pending_value_expectations / source_side_value_expectations）；本方案不预支任何批准。