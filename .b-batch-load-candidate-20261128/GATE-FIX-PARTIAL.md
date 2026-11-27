# B 批门禁修正：D1 闭环，但镜像与隔离回读未做（PARTIAL）

交付基线 `4c866e1`｜原运行时 `a5d12b1`｜镜像 `xrg-load-candidate@sha256:2af4d796…8c8c58`（**未重建**）

## 一、判定
**PARTIAL**：formal 误拒已从代码与批准工件两侧闭环，测试可防复发；
但**新 PIN/清单、候选镜像重建、隔离装载、独立全量回读、回滚本轮均未做**。

**不可谈生产重试**，理由不是谁做错了，而是：
> **镜像 `2af4d796…` 里跑的仍是旧 loader**（实测 L150 仍为 `forbidden = ("pg32b","cbdb","cbdb_reh")`）。
> 用它跑生产等于用已知有缺陷的二进制重复上一盒的失败。

## 二、修复内容（两个提交）
### `9b39319` 门禁改用 R52 正向绑定
`cbdb_social_addr_loader.check_instance_identity` 只动 formal 分支：
- 新增 `LEGACY_DATABASES = ("cbdb","cbdb_reh")`、`TARGET_DATABASE = "xiangrugu"`（与 `production_entry.py` 同常量）
- formal 分支不再用库名黑名单，改为**正向绑定**三项，任一不符即拒：
  `instance_marker_mismatch` / `in_session_port_mismatch` / `target_database_mismatch`
- legacy 库仅记录 `legacy_visible` 供审计，**不作通过/拒绝判据**
- 其余五键（container_id/image_id/server_version/inet_server_addr/databases）仍逐项严格比对
- **隔离分支未放宽**：`forbidden = ("pg32b",) + LEGACY_DATABASES + (TARGET_DATABASE,)`
- `check_target_absent` 未改动；未重构装载器

### `dab4305` 同步批准工件 + 接入审计 + 集成用例
- `formal-expected.json` 补四字段（取值取自生产实际观测，只读核实）：
  ```
  dbname                   = xiangrugu
  in_session_port          = 5432
  instance_marker_verified = 3d93fc7741f6…
  databases                = cbdb,cbdb_reh,postgres,template0,template1,xiangrugu  (原为替身形状 3 库)
  ```
- `run_single_table` 接住返回值写入 `evidence["legacy_databases_visible"]`，与 `production_entry.py` L186 对齐
- 新增集成用例 `test_real_formal_expected_artifact_passes_the_formal_gate`

## 三、D1：为什么"修了等于没修"（上一版 `9b39319`）
`9b39319` 的代码是正确的，但批准工件 `formal-expected.json` 缺三键 →
拒绝点从 `production_database_visible` 挪到 `instance_marker_mismatch`，**formal 仍 100% 过不去**。

**关键盲区**：114 个单测全绿也没发现，因为单元用例的 `_expected()` 复制 `_observed()`，
天然带齐所有键，结构上无法发现陈旧**文件**。

**新集成用例的价值得到实证**：加入后立即失败，报
`AssertionError: formal-expected.json lacks 'dbname' required by the formal gate`。
a04 另做三种破坏注入（dbname 改坏 / 删 marker / databases 改回 3 库），**每次都精确变红 1 条**。

## 四、实测（容器内，固定运行时树 + 本修复 + 同步后工件）
用**真实** `formal-expected.json` 跑 `check_instance_identity`：
```
real                     -> PASS legacy_visible=('cbdb','cbdb_reh')     ← 误拒消除
dbname=cbdb/postgres     -> target_database_mismatch
in_session_port=5433     -> in_session_port_mismatch
instance_marker_verified -> instance_marker_mismatch
container_id / inet_server_addr / +surprise_db -> instance_identity_mismatch
branch=test              -> production_database_visible                 ← 隔离仍拒
target_absent            -> target_already_exists                       ← 防覆盖不变
```
测试：**115 passed, 0 failed**（三模块 99 + 回归 16）。
红→绿：同一回归在 `4c866e1` 上 `12 failed, 3 passed`，在修复后 `15→16 passed`。

## 五、口径澄清
- **99** = `loader + entry + runner` 三模块（项目原口径，a04 第十二盒已更正其早前"113"的说法）
- **115** = 99 + 回归 16
- 加 `first_batch_loader` 为 129，**不属于本批口径**

## 六、a04 第十盒/十三盒两处更正（采纳）
1. 隔离分支需要 `CREATE ON DATABASE` **仅对隔离分支成立**；生产 formal 分支 `create_schema=False`，**不需要库级 CREATE**——`xrg_loader` 当前只有 CONNECT 是**正确**的
2. a04 早前报"99 vs 113 口径不符"是其多算 `first_batch_loader`，**99 正确**

## 七、下一盒必做（顺序）
1. 生成新 PIN 与模块清单（`loader` 与测试摘要已变）
2. **重建候选镜像**（当前镜像含旧 loader，是本盒最大的未闭环点）
3. 隔离装载 + 独立全量回读：3859 行 / 11 列 / 六列有序主键 / NULL 保真 / 坐标保真 / 差异 0 / 值摘要 `2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579`
4. 数据库层失败用例回滚后目标表不存在
5. 全部通过后才谈生产重试（需 Codex 再次明确放行，茶香转发）

## 八、已收的小项
- `formal-expected.json` 摘要 `43f7705f…` → `3c31ad20…`，已登记到
  `.b-batch-formal-exitcode-20261128/SPLIT-EXPORT-BOX5.md` 并注明变更原因
  （a04 值级 diff 确认：忽略缩进重排后**仅 4 个字段值变化，其余 40+ 字段一字未动**）

## 九、边界
未重试生产装载、未更新 deploy、未重建生产前置对象、未写生产库、未连 `pg32`。
生产零写入：目标表 ABSENT、`cbdb` schema 内对象 0、`xrg_loader` 保持原状。
镜像与固定运行时均未变。
