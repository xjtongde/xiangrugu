# 首批七对象 · 受控接收方案（草案，未执行）

- 基线版本锚：**8f3d014442e59b1a1af4a1234a465bb874a6426c**（分支 dsh/p01-real-prep-20261113，Gitea ls-remote 已核）。
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

## 4. 回退点
- R0：接收前 deploy 快照 tar（sha256 记录）。
- R1：Git 回退 `git revert 8f3d014`（或受控目录恢复 R0 快照）；分支历史不改写（R-10 禁 reset/clean/stash）。
- 任何验证失败：停止接收，恢复 R0，记录冲突按 docs/index.md 权威顺序处理。

## 5. 分账纪律
- 表名批准 / 正式合同冻结 / 装载授权三账独立（approval-table.json ledgers 逐项 false）；本方案不预支任何批准。