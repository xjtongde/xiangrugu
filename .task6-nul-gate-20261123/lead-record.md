# Task 6 固定摘要 NUL 运行门实施 · lead 记录（2026-11-22/23，30 分钟盒）

- 起表 18:34:22 UTC，硬停 19:04:22 UTC。基线 e3dd1399f54cdc9254b5d748cd0e783eb149aa6b（M=2 完好、暂存空）。
- 茶香明确授权隔离实现+测试；真实合同冻结/正式落盘/服务变更/数据库写入另行授权。范围仅 SHA256SUMS-b2 checksum_nul。
- lead 预核（lead-precheck.md）：checksum_candidates.py 全文（150 行，preview 逐条核验逻辑/无 runtime API docstring）；disposition.py L69-71 接线点；ContractException/ReleaseContract/ContractReview 字段；InventoryManifest dataclass（complete 派生自 issues/blocking）；真实 inventory checksums 191 条含 b2 172 条全 matched=True（正例可用真实 inventory）。
- **a02 起始即失败（零产物）→lead 接管实施**（披露；本盒 a02 第四次跨盒失败）。
- lead 实施链（18:36–18:40 UTC）：
  1. fixture：32 快照只读 base64 取回 SHA256SUMS-b2→tests/fixtures/sha256sums-b2.b64；decode 核 22071B/sha 900d98c6…/raw[21945:]==126×NUL/prefix 无 NUL ✓。
  2. checksum_reader.py 新件（~95 行）：白名单常量+run_fixed_nul_exception（审批门 frozen+review/恰一白名单声明/rule 目标固定 ledger/复用 preview/tail_offset 21945 核/证据绑 contract.sha256+manifest.sha256+172 逐条）+nul_exception_closed（失配 False）。
  3. disposition.py 三处最小改：import checksum_reader；evaluate 可选参 exception_run_inputs=None；exception 分支 closed 计数（聚合 issue 形态不变，默认行为不变）。
  4. test_checksum_reader.py 12 用例（正例 2+反例 9+fixture 身份 1）；两处实施期修正：limits JSON 为 list of pairs（非 dict）；selector.location 为三元组（[0] 取 path）——均 lead 自查修正，非 a03 发现。
  5. 容器执行（xiangrugu-dev，rootfs 只读→stdin 管道 docker exec -i 入 /tmp tmpfs；/workspace=deploy ro 未触）：首轮 11 失败（limits）→修正→9 失败（location）→修正→**12 passed exit 0 stderr 0B**；回归首轮 1 失败（tar 缺 config/contract.schema.json，FileNotFoundError 非代码回归）→补入→**115 passed exit 0 stderr 0B**。
  6. 机器证据：容器生成 machine-evidence.json（contract_sha256 0e97147d82c02f5f…/inventory_sha256 fb5e6b334b898d62…==真实重算/issues [incomplete_inventory, unmatched_member]/ready false/complete false/172 matched/tail 21945/126）取回落盘。
  7. rollup：VCS_REF→e3dd139；两候选顶层歧义 raw_sha256/raw_sha256_full_note 清除；NUL runtime_gate_ledger 更新+task6_isolated_implementation 节；CHGIS 单列待实施注；SUMMARY Task 6 节；38 三跑+收敛 cmp 0/0；rsync→32 三跑 0/0；**38/32 全 19 件 sha 全等**。
- a03 R33 一期全 PASS（独立输入就绪+门位预期矩阵 E1–E5 容器实跑+零漂移）；二期独立执行核进行中（硬停 18:58）。
- 关键 sha：exceptions 8fabba2c36af9e36 / manifest 10f608d19acfd8af / SUMMARY a6d94f29da35e2f2 / 生成器 44fa62afaf7898d4 / rgp 6eba2b5c7ae0fcbb / all-members ac773dea3c4e2677。
- 边界：五块零改写；源件只读（fixture 取回不改源）；M=2 未触；不冻结真实合同/不落盘/不写库；deploy 未动。
