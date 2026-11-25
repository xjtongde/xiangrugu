# A 批受控接收与 B 批单表隔离试装 · lead 记录（30 分钟盒）

- 起表 2026-11-25 18:58:23 UTC，硬停 19:28:23。固定基线 e1cded98a23b2e0b310a6f378e71bdfdc8949694（ls-remote 已核）。**本轮只做 A 受控接收+B 单表隔离试装；生产写库另批；不读 CBDB 大组、不扩 B 批范围、不连生产写、不改现役服务/旧库权限；首批 88f4f1ac 不复用**。lead 收口（a02 起始失败惯例接管披露），a03 独立复核。

## A. 受控接收（PASS）
1. **deploy 恢复快照先验**：`/opt/mydocker/xiangrugu/reception-20261125/deploy-recovery-phase2-20261125-174902.tgz` sha **59617d83c6bd583128d99ee3e5539d12d148bcc38ad20a643783180c09a78a73** 在位不变（与 Phase 2 锚一致）。
2. **自 Gitea 接收**：commit `e1cded9` 树、路径 `.task6-abatch-freeze-20261125`；incoming tar sha **3b2e8e85…**、593920 B，落到 32 `reception-20261125/abatch-receive-20261125/incoming-abatch.tar`（落地 sha 与本地一致）；解包 13 件。
3. **接收核验**：8 件关键产物与 `git cat-file` 逐件 sha 全等（MATCH×8）；candidate 文件 sha **95eb741c…**。
4. **规范摘要核验**（32 隔离 dev，正式 ReleaseContract 模型，对**接收副本**）：canonical **fa28a878f48fed506700cbaaf91c6a8ee45bdc28e9fef05904b3c56f4c61929e** == 授权摘要；**原 9 规则深等不变、两例外不变、新增 14 条零业务目标（全 NON_TABULAR）、inventory_sha fb5e6b33 不变**；原合同仍 ba8118fb。
5. **接收通过后才更新未覆盖**：现行未覆盖 **7981**（7995→7981）；**首批生产装载器 scope 的 7995 门未改**（属已验收七表批次自身不变量）；**full_ready_for_import=false 保持**。接收记录 `a-reception-record.json` sha **6ad68f49…** 落 32。

## B. 单表隔离试装（TRIAL_PASS）
- 范围仅 **SOCIAL_INSTITUTION_ADDR** → 候选目标 `cbdb.cbdb__social_u5f_institution_u5f_addr`。
- 源：已核对快照 `cbdb_20260919.sqlite3`（586485760 B，sha **bde1bb8e…83400**），以 `mode=ro&immutable=1` + 只读 bind mount 读取；**只读该表，未读大组**。
- 已批期望复用：`sqlite-value-canary.approved.json` → 3859 行 / 42449 字段 / sha **2cb8c354…** / schema **1f88cd80…**；`summarize_sqlite` 复现逐项相等。
- 隔离实例：`xiangrugu-trial-cbdb-addr-20261125-190500`，镜像 pg32b-full:18-pgdg，**--network none、无发布端口**，Id `e15fbb22…`；scratch 挂 `data/var/<box>` 子目录（用后为空）。
- 最小装载器：11 列（bigint/double precision/text）建表 + COPY text 协议装入 3859 行；**回读 3859 行、重复 0**；结构 11 列类型与映射一致。
- 规范值核验（approved `compare_unordered` + COPY 文本回读）：**comparison_equal、差异 0、缺 0、多 0、42449 字段、source/target sha 均 == 2cb8c354…**；NULL 分布逐列在账。
- **整表回滚**：DROP 后 `to_regclass` 为空 → table_dropped True。
- **反例控制**：注入删 1 行 → `comparison_failed`、missing_rows 1、target 3858，且仍回滚 → 门非空转。
- 实例按核实 Id 销毁，`docker inspect` → `[]`，无残留 trial 容器；scratch 目录已删。
- **未批准项如实保留**：目标映射仍 candidate、NOT NULL/PK/UNIQUE/FK/INDEX/DEFAULT 未执行、值合同未冻结、无写库授权。

## 服务与边界
- pg32b Id `3d93fc77…` StartedAt 2026-11-25T13:43:10Z RestartCount **0**（未重启、未连接写）；dev 同 StartedAt RestartCount 0。旧库 cbdb/cbdb_reh 权限未动。deploy 未新增未回传修改。

## 首个剩余缺口
- **A**：候选规则正式并入处置账（8 本账/冻结合同替换）需另批授权；首批 7995 门与新合同 7981 的口径并存需一次性收编。
- **B**：单表试装只证明装载路径可行；进入生产仍缺：目标映射批准（命名碰撞检查）、nullability/约束执行批准、值合同冻结、新冻结合同、新的茶香写库授权原文、Codex 独立验收放行；并且 PG 生产装载器尚未实现（本次为试装脚本，非生产适配器）。