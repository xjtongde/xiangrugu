# 正式 vs 隔离 参数对照

| 维度 | 正式（phase2-production） | 隔离（phase1-isolated） |
|---|---|---|
| scope 文件 | `formal-scope.json` | `isolated-scope.template.json`（填替身 ID） |
| expected 文件 | `formal-expected.json` | `isolated-expected.template.json` |
| scope.mode | `production-write` | `isolated-test` |
| 端点 host | **pg32b**（固定） | 替身容器名 / 127.0.0.1 |
| 端点 port | **5433**（固定） | 5432 |
| 会话内端口 | **5432**（核对） | 5432 |
| dbname | **xiangrugu**（固定） | xiangrugu（替身同名库） |
| container_id | `3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc` | 运行时填替身全 ID |
| test_only | **false**（为 true 即拒） | **true**（为 false 即拒） |
| approval_class | **real** | **test** |
| 连接覆盖参数 | **一律拒绝**（`formal_endpoint_override_refused`） | 允许 `--connect-host/--connect-port/--load-role` |
| 指向生产实例 | 必须 | **禁止**（`isolated_mode_targets_production_instance`） |
| 指向生产三元组 | 必须 | **禁止**（`isolated_mode_targets_production_triple`） |
| expected.databases | 剔除 xiangrugu 后比对 | 含 xiangrugu |

## 共用（两边都必须成立）
- 授权原文 sha256 = `4d250c8e…2946`，641 字节（预检硬编码锚点）
- 审批表 sha256 = `a718b0c2…4a0`（预检硬编码锚点）
- 冻结合同规范摘要 = `56b0076d…8237`（由入口 Gate D 重算）
- 代码清单 8 模块含 runner 本身，逐模块摘要
- 装载角色 `xrg_loader`，NOSUPERUSER/NOCREATEDB/NOCREATEROLE
