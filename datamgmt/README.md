# datamgmt —— 数据导入、验证与维护模块

> 状态：开发中｜as_of 2026-10-06

本目录是 `docs/import-plan.md` 的执行体。方案和阶段只在该文档定义；本文件只说明现有文件、职责和缺口。

## 目录职责

| 路径 | 当前职责 |
|---|---|
| `config/roots.yaml` | 唯一源根、目标实例/数据库和路径政策 |
| `config/g4_assertions.yaml` | 已确认源生现象的机器哨兵 |
| `truth/` | 已有 SQLite、DBF/Shapefile、MapInfo、文本、XLS 等部分源读取能力 |
| `importer/load.py` | 已有部分载体的 staging 装载与发布原型 |
| `verifier/` | 已有完整性及部分独立验证原型 |
| `maintenance/` | 盘点、编码调查和配置生成辅助脚本 |
| `recon/` | 当前盘点证据、草案台账与运行产物 |
| `tests/` | 目前只有 `.gitkeep`，尚无测试代码 |

## 尚不存在或尚未完成

- `config/sources.yaml`、`config/decoding.yaml` 尚未建立；
- MDB、SQL dump、XLSX/CSV/ODS、栅格及多层容器等尚未全部形成端到端闭环；
- 计划中的 PRJ、ZIP 成员和栅格头独立读取能力尚无对应模块；
- 发布操作尚未证明为单事务；
- 缺少单元、故障注入、集成、全库回归和重入测试；
- `db.py`、`rehearse.py`、`verify.py` 和 `load.py` 仍默认连接旧 `cbdb_reh`，schema 列表也未包含新方案的 `cbdb/audit`；
- `build_sources_yaml.py` 仍写死旧 `database=cbdb` 与 `public` schema；部分源读取器写死源路径，XLS 依赖 `/tmp/xlsdeps`；这些都不能直接用于正式运行。

因此，当前状态是“阶段 0 盘点草案已生成，导入合同尚未验收”，不是“阶段一已完成”。当前阶段及出口条件以 `docs/import-plan.md` 为准。

## 不可违反的实现边界

1. 只从 `config/roots.yaml` 取得源根，业务清单只存相对成员链；
2. 源件只读，可重建资产全部入 Git，唯一工作账不得放在 `/tmp`；
3. importer 与 verifier 的值解析实现相互独立；
4. 保真层不靠装后 `UPDATE`/`DELETE` 修补，失败对象应从源重新装载；
5. 每个源成员都必须有处置，禁止按扩展名静默遗漏；
6. 验收证据来自源字节，不来自旧 `cbdb`、装载器输出或人工叙述；
7. 创建数据库、写库、删除库和运行全量任务都须另获用户明确授权。

历史失败模式和必测拦截点见 `PITFALLS.md`。
