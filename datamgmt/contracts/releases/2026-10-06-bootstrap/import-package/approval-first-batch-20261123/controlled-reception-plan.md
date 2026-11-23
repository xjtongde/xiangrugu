# 首批七对象 · 受控接收方案（草案，未执行）

- 基线版本锚：**44e5f5697d3c842f8eb1647050afe7d3dabae948**（分支 dsh/p01-real-prep-20261113，Gitea ls-remote 已核）；接收时以经核对的当时分支头为完整版本锚。
- 本方案仅为计划；**受控接收、正式合同冻结、落盘、数据库写入均另行授权**，本轮不执行。

## 1. 接收范围
- 32 受控运行目录 `/opt/mydocker/xiangrugu/deploy` 接收经核对的 Git 版本 8f3d014（含核销评估器 writeoff.py 原清单绑定补正 + 两例外 reader + 审批包）。
- 接收前快照：`deploy` 现状 tar 存档（回退点 R0）；接收仅替换受控目录内容，不触 pg32/pg32b 任何数据库。

## 2. 核销评估器调用入口（已按实际 API 补正——旧示例 InventoryManifest.load_json 不存在，失效）
```python
import json
from pathlib import Path
from xiangrugu_datamgmt import writeoff
from xiangrugu_datamgmt.inventory import (InventoryManifest, InventoryEntry,
                                          InventoryIssue, ChecksumAssertion)
from xiangrugu_datamgmt.contracts import ReleaseContract

doc = json.loads(Path(inventory_path).read_text())   # 原清单 fb5e6b33…，complete=false 保留
manifest = InventoryManifest(
    entries=tuple(InventoryEntry(
        relative_path=e["relative_path"], archive_chain=tuple(e.get("archive_chain", ())),
        archive_ordinals=tuple(e.get("archive_ordinals", ())), kind=e["kind"],
        size=e.get("size"), sha256=e.get("sha256"), signature=e.get("signature", "unknown"))
        for e in doc["entries"]),
    issues=tuple(InventoryIssue(
        code=i["code"], relative_path=i["relative_path"],
        archive_chain=tuple(i.get("archive_chain", ())),
        archive_ordinals=tuple(i.get("archive_ordinals", ())),
        detail=i.get("detail", ""), blocking=i.get("blocking", True)) for i in doc["issues"]),
    checksums=tuple(ChecksumAssertion(
        ledger=c["ledger"], line=c["line"], raw_name=c["raw_name"], target=c["target"],
        expected_sha256=c["expected_sha256"], matched=c["matched"],
        archive_chain=tuple(c.get("archive_chain", ())),
        archive_ordinals=tuple(c.get("archive_ordinals", ()))) for c in doc["checksums"]),
    limits=tuple(sorted((k, int(v)) for k, v in doc["limits"])))
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
- R1：回退即**恢复接收前完整版本锚**——受控目录整体恢复 R0 快照，或 `git checkout 44e5f56 -- .` 全量回到锚版本（不做局部挑拣回退）；分支历史不改写（R-10 禁 reset/clean/stash）。
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

## 8. 临时试装结果（单列——非正式接收/非冻结/非落盘/非 pg32b 写入）
- m004812（2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab，29 行 7 列）隔离试装：临时容器 xiangrugu-trial-m004812（postgres:18-bookworm，**--network none 无宿主端口**，写入前实例身份核 True：PGDATA /var/lib/postgresql/18/docker、全新 postmaster、库清单仅 trial+模板、inet_server_addr null、镜像≠pg32b-full）。
- 最小装载路径：canonical.py 源侧流核验（sha b3f6ceb6…==已批）→psql DDL+COPY（exit 0/0）→全量回读 29 行/列名列序类型全合/rownum [1,29]/重复 0/**库值重建流 sha b3f6ceb609a853cb…==已批期望/5605B**。TL_EXIT=0 stderr 0B。
- 试装表 harv.trial_m004812_20261123（显式临时名；候选生产名仍未批）。证据 .task6-trial-load-m004812-20261123/trial-evidence.json。
- **正式接收、冻结、落盘和写入 pg32b:5433/xiangrugu 仍待授权**；临时容器用后销毁，不留常驻。