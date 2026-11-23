# 首批七对象 · 受控接收方案（草案，未执行）

- **来件完整提交（incoming）**：代码锚 = 审批包锚 = 同一完整版本锚（本盒记录 **df5a7c513cc9912efcb4322c405c1a9af0a913ee**，分支 dsh/p01-real-prep-20261113，Gitea ls-remote 已核）；接收时以经核对的当时分支头为来件完整锚。
- **接收前实际恢复点（deploy 现状，与来件锚分列）**：32 `/opt/mydocker/xiangrugu/deploy` **非 Git 仓库（无 .git）→现役 Git 提交 UNKNOWN**（无法证明，按实记录）；可公开版本标记=**内容 sha256 清单 `62737bd0c16ac23f1c9ba4fd92e73abadb6a6eace014494f605f29e6aa00396f`**（7719 文件/87798110 字节，清单 .task6-reception-precheck-20261123/deploy-content-manifest.txt）；现役镜像 **xiangrugu:dev Id sha256:89f1a0978cb81787…**；deploy→/workspace **ro 挂载**；保护范围=deploy 全部 7719 文件（data/persistent、data/var 独立 rw 绑定不在内）。**恢复点=内容快照（R0 tar+清单），非 Git 锚**；证据 deploy-state.json。
- **备份**：接收动作前对 deploy 全量 `tar czf R0-<timestamp>.tgz`（含权限/路径）+ 重算 sha256 清单；备份落 deploy 之外的安全位置；清单与预检清单（62737bd0…）比对——**漂移即停手**，重新预检并另批。
- **恢复校验**：恢复=从 R0 tar 全量还原（不做局部挑拣）；校验=`sha256sum -c` 全量清单 + 文件数 7719 + 字节和 87798110 + tar 完整性；任一不符→恢复失败停手留证。
- **停手条件**：①预检清单与接收时现状漂移；②无法形成可验证恢复点（快照失败/清单不可复算）；③现役 Git 提交 UNKNOWN 且内容快照亦不可得；④需要改服务/镜像或写 deploy 之外受保护路径；⑤任一审批缺失（表名/冻结/装载三账）。**满足任一→受控接收停在预检，不得继续**。
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
- R1：回退即**恢复接收前实际恢复点**——deploy 非 Git 仓库，回退=从接收前 R0 内容快照（tar+清单 62737bd0…）**全量还原**并按恢复校验节核验（不做局部挑拣回退）；来件 Git 锚（df5a7c5…）仅用于来件侧版本核对，不替代 deploy 内容恢复点；分支历史不改写（R-10 禁 reset/clean/stash）。
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

## 9. 五件文本隔离试装结果（单列——试装通过≠正式合同接入≠生产装载授权）
- 隔离边界：仅 32 已验证项目快照读件；复用本地 postgres:18-bookworm（**实际镜像 Id sha256:882236b897e39051d2368c5ccc6cda944904723506b2dfc97f2a8f5bc9afa382==RepoDigest**）；容器 xiangrugu-trial-text5-20261123-173109 **本次唯一身份**，--network none 无宿主端口；清理仅针对本次创建的容器。
- 逐件试装前核：源 sha+schema sha+行数+XRGVALUE-v1 流 sha+stream_bytes 五核全 PASS 才写入；任何读法/摘要/实例身份失配该件停报留证（本轮无失配）。
- 五表（显式临时名）：harv.trial_m008002/m008003/m008004/m004812_20261123 + chgis.trial_m006642_20261123；m004812 快照路径重跑。
- 全量回读：2957/40199/1033/29/3389 行，列名类型列序全合、全 text NOT NULL 空串保留（null 行 0）、rownum [1,N]、**重复按实际值列（排除唯一源行号）：m008003 63 组/74 多余行，余四件 0**；库值重建流 sha 逐件==已批（475ea1d8/dcbedb5a/d233ed9c/b3f6ceb6/3bad44a0）；**合计 47607**。T5_EXIT=0 stderr 0B。
- 证据 .task6-trial-text5-20261123/trial-evidence.json；**pg32、pg32b、deploy 与正式落盘不在本轮范围**。

## 10. 两件空间对象隔离试装结果（单列——以临时试装为终点）
- PostGIS 能力核：本地 postgres:18-bookworm 无 PostGIS；**pg32b-full:18-pgdg 含 postgis-3.so+postgis.control**（实际镜像 Id **sha256:d562e43664f996da0e4208b375c00c111a543d996475188d852e9189b2a8cd05==RepoDigest**）；以该镜像建**全新隔离容器**（pg32b 实例/数据未触）；CREATE EXTENSION postgis → **3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1**。
- 容器 **xiangrugu-trial-spatial2-20261123-174708-b6e61aa3（本次运行唯一名）**，容器 ID d71bca328f577970…（创建后 inspect 核实）；--network none 无宿主端口；**无固定名预删**（trial_text5.py 与 trial_load_m004812.py 的启动前固定名强删逻辑已同步移除，name collision fail closed）；**清理仅按本次创建并核实的容器 ID**。
- 两件各自核对（SHP 字节相同也分开）：m002709（cp1251）/m002717（utf-8）各 59 行；两份 DBF 身份（0b4b86cb/eb9dfed2）；已批属性类型 text×7/numeric(19,5)×2/bigint×3；源行号 [1,59]；2D Point/SRID 4326；**原始 X/Y 以 hex EWKB 装载（无十进制转换），回读逐点原始 LE 字节 match**。
- 数值列按已核宽度标度（19,5/16,0 右对齐）重建源字段文本==raw；**四摘要逐件全等**：attr 3519649f663f8a6d/a2ad2d24ff4cae8c + geom ff7081a0013d721f/3c6067845a7938e8；dup attr 0/xy 0；null 行 0；合计 118。SP2_EXIT=0 stderr 0B。
- 证据 .task6-trial-spatial2-20261123/trial-evidence.json；**试装通过≠正式合同接入≠生产装载授权；pg32、pg32b、deploy 与正式落盘不在本轮范围**。