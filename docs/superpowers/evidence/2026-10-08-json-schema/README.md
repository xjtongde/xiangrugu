# 独立 JSON Schema 校验开发证据

范围：锁定验证器、原始合同文档及 Schema 校验、候选镜像回归。
未读取真实源/NAS/项目快照、未连接数据库、未冻结、未替换长期容器、未提交。
32 工作账：data/var/json-schema-20261008T143630Z；最终候选批次20261008T144709Z。

RED/GREEN 日志、三镜像构建、pip check、runtime smoke、原始文档报告和镜像身份在此留存。
回传逐份 SHA-256 核验；详细执行与评审处置见 ../../plans/2026-10-08-json-schema-progress.md。
独立校验仅证明结构；ready_for_import/conforms 保持 false。
旧常驻 dev 未安装新依赖，同步源码后 watcher 收集失败，不冒充开发环境晋级成功。

官方依据：
- https://pypi.org/pypi/jsonschema/4.26.0/json
- https://pypi.org/pypi/attrs/26.1.0/json
- https://pypi.org/pypi/jsonschema-specifications/2025.9.1/json
- https://pypi.org/pypi/referencing/0.37.0/json
- https://pypi.org/pypi/rpds-py/2026.9.1/json
- https://python-jsonschema.readthedocs.io/en/stable/validate/
- https://python-jsonschema.readthedocs.io/en/stable/referencing/
- https://referencing.readthedocs.io/en/stable/api/

Schema 定义仍由 Pydantic 导出；实例校验由独立 jsonschema 执行。
根声明 Draft202012，子节点不接受 $schema/$id，引用只能指向声明的非根 Schema 节点；
const/default/examples 中的字面数据不作为 Schema 引用处理。
JSON域深度128/100万节点、实例执行200万关键字调用；不是任意不可信正则或
第三方 Schema 的通用安全沙箱，只使用受控审阅的合同 Schema。
