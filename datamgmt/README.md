# datamgmt —— 香如故数据接入模块

> 状态：设计已批准、实现未完成｜as_of 2026-10-06

本模块长期负责首次建库、数据换版、新增来源、独立验证、彩排、发布和回滚。唯一源是 `usedata`，目标是 `pg32b/xiangrugu`。

## 必读入口

| 文档 | 职责 |
|---|---|
| `docs/DESIGN.md` | 唯一权威设计：模块边界、合同、保真、验证、版本与发布 |
| `docs/OPERATIONS.md` | 首次构建、后续更新、失败处理和计划 CLI |
| `docs/PITFALLS.md` | P-01～P-25 强制拦截规则 |
| `config/roots.yaml` | 当前源根、目标实例和安全边界 |

## 当前已有资产

| 路径 | 现状 |
|---|---|
| `config/g4_assertions.yaml` | 旧目标命名下的哨兵原型，阶段 0 必须迁入 release 合同并重建 SQL |
| `truth/` | SQLite、DBF/Shapefile、MapInfo、文本、XLS 等部分源读取能力 |
| `importer/load.py` | 部分载体的 staging 装载原型 |
| `verifier/` | 完整性及部分验证原型 |
| `maintenance/` | 盘点、编码调查和旧配置生成脚本 |
| `recon/` | 首版盘点证据与草案，迁入首个 release 后退役 |
| `tests/` | 只有 `.gitkeep`，测试代码为 0 |

## 已确认的实现缺口

- 长期模块结构、Python 包、统一 CLI、release 合同和运行状态机尚未建立；
- `sources.yaml`、`decoding.yaml` 尚不存在；
- MDB、SQL dump、XLSX/CSV/ODS、栅格和多层容器尚未全部打通；
- PRJ、ZIP 成员和栅格头独立读取能力缺失；
- 发布没有实现影子 schema 和单事务切换；
- `db.py`、`rehearse.py`、`verify.py`、`load.py` 仍默认旧 `cbdb_reh`；
- `build_sources_yaml.py` 仍写死旧 `database=cbdb` 与 `public` schema；
- 部分源读取器写死源路径，XLS 依赖 `/tmp/xlsdeps`；
- 单元、集成、故障注入、重入和全库回归测试均未建立。

因此当前仍处于阶段 0：现有盘点只是草案，尚未形成获批的首个 release 合同。不得直接开始全量导入。

## 操作边界

创建目录骨架、改代码、安装依赖、建库、写库、彩排、发布、回滚或删除旧对象，都必须按项目纪律逐阶段获得用户授权。
