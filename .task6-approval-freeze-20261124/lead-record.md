# 真实批准登记与冻结交付候选 · lead 记录

- 登记时刻 16:10:50 UTC（2026-11-24）。批准锚 c250e03acc25843740fce974bf3f8b9bf1cfcc68（==接收时 HEAD）。批准人：茶香（用户消息直接批准）。**授权限于候选交付；受控接收与数据库写入另行批准**。

## 实施
1. **审批登记**（approval-record.json）：批准原文逐字/锚完整号/approved_scope 五 true（名称/映射/源侧期望/候选分支登记/生成冻结候选）/explicitly_not_authorized 四件（受控接收/写库另批，deploy 替换/服务变更不在本次）/被批工件锚（pending-seven sha 23e44d12…/draft canonical bb715799…/七件/47725/63/74/SRID4326）。
2. **ContractReview 真实三面**：approved_by 茶香/approved_at 2026-11-24T16:10:50Z/approval_ref chaxiang-approval-20261124-first-batch-seven@c250e03…。非 isolated-test。
3. **冻结交付候选**（build_frozen.py）：draft→frozen **仅 status+review 两面差**（freeze-delta-report：changed_top_level_keys [review,status]，rules_identical True）；frozen-candidate.json 生成。
4. **正式冻结门验证**（validate_frozen.py，32 隔离容器 /tmp/af，PYTHONPATH 新 src）：**VF_EXIT=0 formal_frozen_parse PASS**（ReleaseContract.model_validate 正式入口，frozen 门强制首批七检查通过）；**canonical sha 2dd4064250e6c4a9…**；total 47725；**逐项 vs pending-seven+源侧期望 all_match True**（名称/count/attr sha×7/文本逐列映射/63/74/空间 geom sha==源侧/SRID/DBF 身份 0b4b86cb/eb9dfed2@16937B）。
5. **审批包更新**（build_approval_package.py 2bbf659961a12cff）：status FIRST_BATCH_SEVEN_APPROVED_FROZEN_CANDIDATE_DELIVERY；approval_event+frozen_delivery_candidate 节点；七件 ledgers 翻正 table_name_approved=true/formal_contract_frozen=true（冻结交付候选，候选交付为止）/load_authorized=false；integration_status FROZEN_CANDIDATE_INTEGRATED；三账分录更新（受控接收/装载仍另批）。approval-table sha **bfde4531f1a21a69**，双跑字节全等（ITEMS 7 EVIDENCE 18 ROWS 47607）。
6. **回归**：七套 **R8_EXIT=0 stderr 0B 172 passed**（r8.out）。模型零改动（本盒仅登记+候选生成+审批包证据）。
7. 环境披露：跨盒容器 /tmp/dc 失效→/tmp/af 重建树（标准配方）。

## 边界
候选交付为止：受控接收（32 deploy）未 perform/数据库未写/deploy 未替换/服务未改；M=2 未触；rollup/原 inventory/五块零改写；源件只读。

## 首个剩余缺口
受控接收批准事件（promotion 步骤 1：32 受控运行目录接收转正，按预检方案来件锚/恢复点/备份/停手条件执行）→ 装载授权链（loader GAP）。

## 共享工作树事件披露与修复（16:18-16:19 UTC）
- a03 R47b 暂存错置恢复操作在共享工作树执行 checkout 致 HEAD 分离（自 6eb7691）；lead 复核记录提交 600c32b 落于分离头指针，首推 Everything up-to-date。
- 修复（非破坏性，无 reset/clean/stash）：核实 600c32b 父==分支头 6eb7691→`git update-ref` CAS 快进分支引用至 600c32b→`git symbolic-ref` 重附 HEAD→推送 6eb7691..600c32b，ls-remote==600c32bd5b73110fc1426cb24722a8c30038f8b7。M=2 全程未触。
- 纪律重申：共享工作树内取历史版本一律 `git show <commit>:<path>`，禁止 checkout 切换（已告 a03）。
