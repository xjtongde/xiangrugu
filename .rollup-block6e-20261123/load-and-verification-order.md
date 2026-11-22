# 导入包合同草案 · 装载与核验顺序（lead 拟案，DRAFT_NOT_APPROVED）

基线 f54dd96；本件为 lead 拟案，正式执行须逐项授权。原则：先冻结合同、再独立核验、后分批装载；每批装载前后均有机器核验；源件全程只读；pg32 生产与 pg32b/cbdb、cbdb_reh 不触。

## 阶段 0 · 包冻结前置（全部为待审批决定，见 pending-decisions.md）
1. NUL 126 兼容解析合同批准（固定摘要 900d98c6…，roots.yaml format_anomaly 政策）——**blocks_package_freeze**。
2. manifest-draft 审批（8004 成员四分类+1293 对象+1311 引用+产物 sha）。
3. 命名草案整体批准（83 保留+1208 候选+2 批准+39 统一；schema_draft chgis/harv 二分规则）。
4. 镜像主从通则裁定（379 同字节组共享存储+来源逻辑保留；V4 两版本分立；合表若采纳另批）。
5. 配准裁定（Peking 沿用现有 GT+tfw 互证升级与否；pdb2 三绑定采用与否+V4 UNRESOLVED 处理）。
6. 装载器合同批准（PG 装载器/读取合同：tabular/spatial/mdb/raster 四面）。
→ 以上批准后方冻结合同版本（git commit 锚+manifest sha），进入阶段 1。

## 阶段 1 · 独立核验（只读，不装载）
1. inventory 8004 件全量 sha 复验（32 :ro 快照，独立验证器）。
2. checksum_deferred **17 件**补跑（逐件清单见 load-blockers；关闭条件=17/17 sha 匹配或差异留证裁定）。
3. CBDB **10 表/235 列**源侧值验证（大组授权后执行；68/78 已覆盖；关闭条件=78/78 或剩余显式豁免裁定）。
4. 源枚举新鲜度复核（顶层 172 vs 172；PAGGQS 排除决定引文在案）。
5. 三历史阻断状态复核（EXCLUDED_BY_DECISION/FORMAT_ANOMALY 合同已批/ASSOCIATED_BY_SHA）。

## 阶段 2 · 首批可执行面（既有批准面，最小风险）
- **tabular 5 既有批准对象**（approved_objects_from_release_evidence，读取政策已批）+**spatial 2 批准对象**（Ca1884route_przh_1251/utf8，component_binding_approved）。
- 前置：阶段 0 全部+阶段 1 通过+目标库 xiangrugu 创建授权+PG 装载器合同。
- 首批缺口证据（当前还缺什么）：装载器合同未批、目标库未建、命名整体未批、NUL 合同未批——**首批尚不可执行**，缺口逐项在 load-blockers 有 closure_condition。
- 装载后核验：独立验证器逐表结构+值追溯源字节（抽样+全量计数），机器证据落盘。

## 阶段 3 · 提案面分批（每批先批准后装载）
- 批 A：tabular 170 提案（批准后）；批 B：spatial 899 提案+SRID 政策裁定；批 C：MDB/SQL 96 提案+值与 geom 合同；批 D：raster 43 装载合同+NoData 113  bands 政策。
- WMF 12（读取工具缺口）与 v5 缺 DBF 1：工具/源事实关闭前不入装载批，带账。
- 每批装载前后独立核验同阶段 2。

## 阶段 4 · 全量收口
- 8004 成员处置闭合报告（四分类终态+未决显式清单）；1293 对象目标名终态；完整性报告（manifest sha 全链）；可重复性验证（同源+同配置+同 commit 重跑字节一致）。
- 32 版本化落盘（拟案 releases/2026-10-06-bootstrap/rollup/<commit>/，sha256sum -c 全 OK 方认接收）——**落盘授权另批**。

## 核验办法总则
- 一切核验以机器可读证据为准（sha256/计数/断言），不以叙述日志或旧库为准。
- 独立验证器与装载器分离（a03 面独立重算惯例）。
- 每阶段退出码显式、stderr 分文件、双跑字节一致（确定性纪律）。