# Task 6 CHGIS 第 4 行固定路径例外实施 · lead 记录（30 分钟盒）

- 起表 19:15:14 UTC，硬停 19:45:14 UTC。基线 99ff362c95d2e06bf0f48ad2c4f899a3e8bca620（M=2 完好）。
- 茶香授权隔离候选实现+测试；正式冻结/落盘/服务/写库另行授权。
- a02 起始即失败（零产物）→lead 接管实施（披露）。
- lead 预核三面（19:15 UTC 直核真实 inventory）：line4 matched=False（6 断言 1T2T3T4F5T6T）/声明路径 entries 0/外层目标 chain[] file/155774/7452ae6c 恰 1（带链 25 成员不计）；contract_schema() L196 机制；PathBindingCandidate 预览 L122-144 五条件。
- 实施链（19:17–19:23 UTC）：
  1. contracts.py 一行枚举：Literal["checksum_nul"]→Literal["checksum_nul","checksum_path_binding"]。
  2. checksum_reader.py：PATH_BINDING_WHITELIST 固定身份全值+run_fixed_path_binding_exception（审批 frozen+review/恰一白名单声明/外层三元组/expected (file,551,694c101f)/manifest.sha==contract.inventory_sha256/复用 preview/证据保留 declared_target+resolved_target+line+raw_name+双方完整身份+strict_assertion_matched）+path_exception_closed。
  3. disposition.py 一行：closed 计数 nul_closed or path_closed。
  4. fixture：32 只读 base64 取回 harvard/chgis/SHA256SUMS.txt→sha256sums-chgis.b64；核 551B/694c101f/line4 双空格 ✓。
  5. 测试 +12（15→27）：CHGIS 正例/未审批/清单绑定/源账篡改/声明失配（直喂 preview raw_name+line 变体）/声明位置已存在（replace 加 entry 变体）/目标 size/sha 失配（变体）/链式选择器+expected/四态回归（NUL 单独既有/CHGIS 单独/并存双闭/任一失配聚合阻断）。
  6. 容器执行：27 passed T6_EXIT=0 stderr 0B；四套回归首轮 1 failed 129 passed——唯一失败 test_published_schema（发布件未再生）。
  7. **schema 再生落盘**（a03 R35b 抓到缺口）：容器 contract_schema() 生成→按既有格式 indent=2/sort_keys/尾 NL 写 config/contract.schema.json（9475B）→重打 config 复跑 **130 passed REG2_EXIT=0 stderr 0B**。
  8. 机器证据 machine-evidence.json：正例 line4/declared harvard/chgis/…→resolved chgis-v6/…/155774/strict matched=False/双 sha/issues[incomplete_inventory,unmatched_member]/ready false/complete false；六反例全 rejected（错误消息逐字含「declared target exists; binding cannot mask it」「explicit resolved target size or digest differs」）；四态并存无 exception_not_implemented+ready false/任一失配聚合保持。
- a03 R35 一期（三面独立核+门位矩阵 M1 类型缺口现证+零漂移）/R35b 二期（自写驱动 chgisdrive.py 正例+七类反例+四态+27 复跑+范围核；抓 schema 缺口）/终核进行中。
- 范围：rollup 19 件不动（VCS_REF 保持 e3dd139）；五块+model/inventory/checksum_candidates diff 空；改动恰 contracts.py 一行+schema 再生+reader+disposition 一行+测试+fixture+证据目录+TODO；M=2 未触。
- 剩余缺口：exceptions 入正式合同审批（frozen+review）+reader 隔离候选转正受控发布+首批 7 对象 table_names/target_mapping 批准。
